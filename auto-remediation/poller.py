import os
import json
import time
import logging
import requests
from datetime import datetime, timezone

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("poller")

MCP_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8000/mcp")
API_KEY = os.getenv("SIGNOZ_API_KEY", "dbe4dc0e-69a7-4245-81cc-37ad39178e04")
WEBHOOK_URL = os.getenv("REMOTE_URL", "http://localhost:9000/remediate")
WEBHOOK_API_KEY = os.getenv("WEBHOOK_API_KEY", "")

SERVICES = os.getenv("POLLER_SERVICES", "express-svc,goworker-svc").split(",")
THRESHOLD_ERROR_RATE = float(os.getenv("POLLER_THRESHOLD_ERROR_RATE", "10"))
THRESHOLD_ERROR_COUNT = int(os.getenv("POLLER_THRESHOLD_ERROR_COUNT", "20"))
INTERVAL = int(os.getenv("POLLER_INTERVAL", "30"))
COOLDOWN = int(os.getenv("POLLER_COOLDOWN", "300"))

last_triggered = {}


def get_service_stats():
    payload = {
        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {"name": "signoz_list_services", "arguments": {}}
    }
    resp = requests.post(
        MCP_URL, json=payload,
        headers={"SIGNOZ-API-KEY": API_KEY},
        timeout=15
    )
    resp.raise_for_status()
    result = resp.json()
    if "error" in result:
        logger.error("MCP error: %s", result["error"])
        return []

    content = result.get("result", {}).get("content", [])
    texts = [c.get("text", "") for c in content if c.get("type") == "text"]
    if not texts:
        return []

    data = json.loads(texts[0]).get("data", [])
    return data


def trigger_remediation(service):
    now = time.time()
    if service in last_triggered and (now - last_triggered[service]) < COOLDOWN:
        remaining = int(COOLDOWN - (now - last_triggered[service]))
        logger.info(
            "%s in cooldown (%ds remaining), skipping", service, remaining
        )
        return

    headers = {"Content-Type": "application/json"}
    if WEBHOOK_API_KEY:
        headers["X-API-KEY"] = WEBHOOK_API_KEY

    payload = {
        "name": f"poller-auto-{service}",
        "service": service,
        "source": "error-rate-poller",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    try:
        resp = requests.post(
            WEBHOOK_URL, json=payload, headers=headers, timeout=10
        )
        if resp.ok:
            logger.info(
                "Triggered remediation for %s: %s", service, resp.json()
            )
            last_triggered[service] = now
        else:
            logger.warning(
                "Webhook returned %s for %s: %s",
                resp.status_code, service, resp.text
            )
    except Exception as e:
        logger.error("Failed to call webhook for %s: %s", service, e)


def check_and_remediate():
    services = get_service_stats()
    if not services:
        logger.warning("No service data from MCP")
        return

    svc_map = {s["serviceName"]: s for s in services}

    for svc_name in SERVICES:
        svc_name = svc_name.strip()
        if svc_name not in svc_map:
            continue

        stats = svc_map[svc_name]
        err_rate = stats.get("errorRate", 0)
        err_count = stats.get("numErrors", 0)
        total_calls = stats.get("numCalls", 0)

        triggered = False
        reasons = []

        if err_rate >= THRESHOLD_ERROR_RATE:
            reasons.append(
                f"error rate {err_rate:.1f}% >= {THRESHOLD_ERROR_RATE}%"
            )
        if err_count >= THRESHOLD_ERROR_COUNT:
            reasons.append(
                f"error count {err_count} >= {THRESHOLD_ERROR_COUNT}"
            )

        if reasons:
            logger.warning(
                "%s unhealthy: %s (calls=%d)", svc_name, "; ".join(reasons),
                total_calls
            )
            trigger_remediation(svc_name)
        else:
            logger.debug(
                "%s healthy (rate=%.1f%%, errors=%d, calls=%d)",
                svc_name, err_rate, err_count, total_calls
            )


def main():
    logger.info(
        "Poller started: services=%s, rate>=%.0f%%, errors>=%d, "
        "interval=%ds, cooldown=%ds",
        SERVICES, THRESHOLD_ERROR_RATE, THRESHOLD_ERROR_COUNT,
        INTERVAL, COOLDOWN,
    )
    while True:
        try:
            check_and_remediate()
        except Exception as e:
            logger.error("Poll cycle failed: %s", e)
        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()
