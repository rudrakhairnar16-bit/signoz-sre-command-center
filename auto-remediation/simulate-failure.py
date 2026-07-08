"""
Failure simulator: sends excessive traffic to crash a service,
then triggers remediation webhook.

Usage:
  python simulate-failure.py --service fastapi-svc --mode flood
  python simulate-failure.py --service express-svc --mode stop
"""

import argparse
import subprocess
import time
import requests
import sys
import os

SERVICE_PORTS = {
    "fastapi-svc": ("http://localhost:8001", "GET", "/process"),
    "express-svc": ("http://localhost:3001", "GET", "/execute"),
    "goworker-svc": ("http://localhost:8081", "GET", "/work"),
}

WEBHOOK_URL = "http://localhost:9000/remediate"
COMPOSE_DIR = os.getenv(
    "COMPOSE_DIR",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "services")
)


def flood_service(base_url: str, method: str, path: str, count: int = 500):
    print(f"Flooding {base_url}{path} with {count} requests...")
    success = 0
    failed = 0
    for i in range(count):
        try:
            if method == "GET":
                r = requests.get(f"{base_url}{path}", timeout=2)
            else:
                r = requests.post(f"{base_url}{path}", timeout=2)
            if r.status_code == 200:
                success += 1
            else:
                failed += 1
        except Exception:
            failed += 1
        if (i + 1) % 50 == 0:
            print(f"  Progress: {i+1}/{count} (success={success}, failed={failed})")
            time.sleep(0.01)
    print(f"Done: success={success}, failed={failed}")


def stop_service(service: str):
    container = service
    print(f"Stopping {container} via docker compose...")
    result = subprocess.run(
        ["docker", "compose", "stop", container],
        capture_output=True, text=True, timeout=15,
        cwd=COMPOSE_DIR
    )
    if result.returncode == 0:
        print(f"Service {container} stopped")
    else:
        print(f"Failed to stop: {result.stderr.strip()}")


def trigger_webhook(service: str, alert_name: str = "simulated-burn-rate-alert"):
    payload = {
        "name": alert_name,
        "service": service,
        "severity": "critical",
        "message": f"Burn rate exceeded 2x for {service}",
        "labels": {"service": service, "alert_type": "burn_rate"}
    }
    print(f"Sending webhook to {WEBHOOK_URL}: {payload}")
    try:
        r = requests.post(WEBHOOK_URL, json=payload, timeout=10)
        print(f"Webhook response ({r.status_code}): {r.json()}")
        return r.json()
    except Exception as e:
        print(f"Webhook call failed: {e}")
        return None


STOPPED_SERVICES = []


def _ensure_running(services: list):
    """Restart any stopped services after test completes."""
    for svc in services:
        container = list(SERVICE_PORTS.keys())[0] if svc not in SERVICE_PORTS else svc
        print(f"Ensuring {svc} is running...")
        subprocess.run(
            ["docker", "compose", "start", svc],
            capture_output=True, text=True, timeout=15,
            cwd=COMPOSE_DIR
        )


def main():
    parser = argparse.ArgumentParser(description="Simulate service failure and auto-remediation")
    parser.add_argument("--service", default="fastapi-svc", choices=list(SERVICE_PORTS.keys()))
    parser.add_argument("--mode", default="flood", choices=["flood", "stop", "webhook-only"])
    parser.add_argument("--count", type=int, default=500, help="Number of flood requests")
    args = parser.parse_args()

    if args.mode == "webhook-only":
        trigger_webhook(args.service)
        return

    info = SERVICE_PORTS[args.service]

    try:
        if args.mode == "flood":
            print(f"\n=== Phase 1: Flooding {args.service} ===")
            flood_service(*info, count=args.count)
            print(f"\n=== Phase 2: Checking service health ===")
            time.sleep(2)
            try:
                r = requests.get(info[0], timeout=3)
                print(f"Service responded: {r.status_code}")
            except Exception as e:
                print(f"Service unreachable: {e}")
                print("Service may be degraded. Triggering remediation...")
                trigger_webhook(args.service)

        elif args.mode == "stop":
            print(f"\n=== Stopping {args.service} ===")
            stop_service(args.service)
            STOPPED_SERVICES.append(args.service)
            print(f"\n=== Triggering remediation webhook ===")
            trigger_webhook(args.service)

        print("\nDone.")
    finally:
        if STOPPED_SERVICES:
            _ensure_running(STOPPED_SERVICES)


if __name__ == "__main__":
    main()
