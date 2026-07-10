"""
SLO-aware canary deployment with auto-rollback.

Simulates deploying a new version of a service, monitors error rate
for a validation window, and rolls back if SLO degrades.

Usage:
  python scripts/canary-deploy.py express-svc --version v2.1.0
  python scripts/canary-deploy.py --list
"""
import os
import sys
import json
import time
import argparse
import logging
import requests
from datetime import datetime, timezone

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("canary")

MCP_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8000/mcp")
API_KEY = os.getenv("SIGNOZ_API_KEY", "dbe4dc0e-69a7-4245-81cc-37ad39178e04")
WEBHOOK_URL = os.getenv("REMOTE_URL", "http://localhost:9000/remediate")
COMPOSE_DIR = os.getenv(
    "COMPOSE_DIR",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "services"),
)

VALIDATION_SECONDS = int(os.getenv("CANARY_VALIDATION_SECONDS", "60"))
SLO_TARGET = float(os.getenv("SLO_TARGET", "99.5"))
ROLLBACK_ERROR_RATE = float(os.getenv("CANARY_ROLLBACK_ERROR_RATE", "10"))
ROLLBACK_ERROR_COUNT = int(os.getenv("CANARY_ROLLBACK_ERROR_COUNT", "10"))


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
    texts = [
        c.get("text", "") for c in
        result.get("result", {}).get("content", [])
        if c.get("type") == "text"
    ]
    if not texts:
        return []
    return json.loads(texts[0]).get("data", [])


def get_initial_errors(svc_name):
    stats = get_service_stats()
    for s in stats:
        if s["serviceName"] == svc_name:
            return s.get("numErrors", 0), s.get("errorRate", 0)
    return None, None


def rollback(service, version):
    logger.warning("⛔ Rolling back %s (version %s)...", service, version)
    payload = {
        "name": f"canary-rollback-{service}",
        "service": service,
        "source": "canary-deploy",
        "message": f"Canary rollback: {version} failed SLO validation",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    try:
        resp = requests.post(WEBHOOK_URL, json=payload, timeout=15)
        if resp.ok:
            logger.info("✅ Rollback triggered for %s: %s", service, resp.json())
            return True
        else:
            logger.error("Rollback webhook failed: %s", resp.text)
            return False
    except Exception as e:
        logger.error("Rollback error: %s", e)
        return False


def simulate_deploy(service, version):
    logger.info("")
    logger.info("=" * 50)
    logger.info("  CANARY DEPLOY: %s → %s", service, version)
    logger.info("=" * 50)

    v1_errors, v1_rate = get_initial_errors(service)
    logger.info("  Baseline: %d errors, %.1f%% error rate", v1_errors or 0, v1_rate or 0)
    logger.info("  Deploying %s (simulated)...", version)

    logger.info("")
    logger.info("  Monitoring for %d seconds...", VALIDATION_SECONDS)
    logger.info("  Rollback if: error rate >= %.0f%% OR errors >= %d",
                ROLLBACK_ERROR_RATE, ROLLBACK_ERROR_COUNT)
    logger.info("")

    poll_interval = 10
    elapsed = 0
    passed = True

    while elapsed < VALIDATION_SECONDS:
        time.sleep(poll_interval)
        elapsed += poll_interval

        errors, rate = get_initial_errors(service)
        if errors is None:
            logger.warning("  ⚠️  Could not fetch stats for %s", service)
            continue

        logger.info("  [%ds] %s: %d errors, %.1f%% rate",
                    elapsed, service, errors, rate)

        if rate >= ROLLBACK_ERROR_RATE:
            logger.error("  ❌ Error rate %.1f%% exceeds threshold %.0f%%",
                         rate, ROLLBACK_ERROR_RATE)
            passed = False
            break
        if errors >= ROLLBACK_ERROR_COUNT:
            logger.error("  ❌ Error count %d exceeds threshold %d",
                         errors, ROLLBACK_ERROR_COUNT)
            passed = False
            break

    if passed:
        logger.info("")
        logger.info("  ✅ CANARY PASSED: %s %s is healthy", service, version)
        logger.info("  Promote to production.")
        return True
    else:
        logger.info("")
        rollback(service, version)
        return False


def list_services():
    stats = get_service_stats()
    if not stats:
        logger.info("No services found (is SigNoz running?)")
        return
    logger.info("Available services:")
    for s in stats:
        logger.info("  - %s: %d calls, %.1f%% errors",
                    s["serviceName"], s.get("numCalls", 0),
                    s.get("errorRate", 0))


def main():
    parser = argparse.ArgumentParser(description="SLO-aware canary deployment")
    parser.add_argument("service", nargs="?", help="Service name to deploy")
    parser.add_argument("--version", default="v2.0.0", help="Version label (default: v2.0.0)")
    parser.add_argument("--wait", type=int, default=60,
                        help="Validation window in seconds (default: 60)")
    parser.add_argument("--list", action="store_true", help="List available services")
    args = parser.parse_args()

    if args.list:
        return list_services()

    if not args.service:
        parser.print_help()
        return

    global VALIDATION_SECONDS
    VALIDATION_SECONDS = args.wait

    result = simulate_deploy(args.service, args.version)
    sys.exit(0 if result else 1)


if __name__ == "__main__":
    main()
