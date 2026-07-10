import os
import json
import time
import logging
import requests
from collections import defaultdict
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

SLO_TARGET = float(os.getenv("SLO_TARGET", "99.5"))
SLO_WINDOW_HOURS = int(os.getenv("SLO_WINDOW_HOURS", "24"))

last_triggered = {}
history = defaultdict(list)
MAX_HISTORY = 2880


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


def compute_burn_rate(svc_name):
    samples = history.get(svc_name, [])
    if len(samples) < 2:
        return None, None, None

    total_errors = 0
    total_calls = 0
    for s in samples:
        total_errors += s["errors"]
        total_calls += s["calls"]

    if total_calls == 0:
        return None, None, None

    observed_error_rate = total_errors / total_calls * 100
    allowed_error_rate = 100 - SLO_TARGET
    budget_remaining_pct = max(0, allowed_error_rate - observed_error_rate)
    budget_remaining_pct = (budget_remaining_pct / allowed_error_rate * 100) if allowed_error_rate > 0 else 0

    oldest = samples[0]
    newest = samples[-1]
    elapsed_hours = (newest["ts"] - oldest["ts"]) / 3600
    if elapsed_hours < 0.01:
        return None, None, None

    errors_per_hour = total_errors / elapsed_hours
    allowed_errors_per_hour = (allowed_error_rate / 100) * (total_calls / elapsed_hours)
    burn_rate = errors_per_hour / allowed_errors_per_hour if allowed_errors_per_hour > 0 else 999

    if burn_rate > 0:
        hours_to_exhaustion = budget_remaining_pct / (burn_rate * 100 / SLO_WINDOW_HOURS) if False else (
            (total_calls * (allowed_error_rate / 100) - total_errors) / errors_per_hour
        ) if errors_per_hour > 0 else 999
        hours_to_exhaustion = max(0, hours_to_exhaustion)
    else:
        hours_to_exhaustion = 999

    return burn_rate, budget_remaining_pct, hours_to_exhaustion


def trigger_remediation(service, reason=""):
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
        "source": "slo-poller",
        "reason": reason,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    try:
        resp = requests.post(
            WEBHOOK_URL, json=payload, headers=headers, timeout=10
        )
        if resp.ok:
            logger.info(
                "Remediated %s: %s", service, resp.json()
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

        now = time.time()
        history[svc_name].append({"ts": now, "errors": err_count, "calls": total_calls})
        if len(history[svc_name]) > MAX_HISTORY:
            history[svc_name].pop(0)

        reasons = []

        # reactive trigger
        if err_rate >= THRESHOLD_ERROR_RATE:
            reasons.append(f"error rate {err_rate:.1f}% >= {THRESHOLD_ERROR_RATE}%")
        if err_count >= THRESHOLD_ERROR_COUNT:
            reasons.append(f"error count {err_count} >= {THRESHOLD_ERROR_COUNT}")

        # predictive SLO
        burn_rate, budget_pct, hours_left = compute_burn_rate(svc_name)
        pred = ""
        if burn_rate is not None:
            pred = f"burn={burn_rate:.1f}x, budget={budget_pct:.0f}% left, exhaustion={hours_left:.1f}h"
            if hours_left < 2:
                reasons.append(f"SLO exhaustion in {hours_left:.1f}h (burn rate {burn_rate:.1f}x)")
            elif hours_left < 6:
                logger.warning("%s SLO risk: %s", svc_name, pred)

        if reasons:
            logger.warning("%s unhealthy: %s", svc_name, "; ".join(reasons))
            trigger_remediation(svc_name, "; ".join(reasons))
        else:
            logger.info("%s healthy — %s", svc_name, pred if burn_rate else "no data")


def main():
    logger.info(
        "SLO Poller started: services=%s, rate>=%.0f%%, errors>=%d, "
        "interval=%ds, cooldown=%ds, SLO=%.1f%%/%dh",
        SERVICES, THRESHOLD_ERROR_RATE, THRESHOLD_ERROR_COUNT,
        INTERVAL, COOLDOWN, SLO_TARGET, SLO_WINDOW_HOURS,
    )
    while True:
        try:
            check_and_remediate()
        except Exception as e:
            logger.error("Poll cycle failed: %s", e)
        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()
