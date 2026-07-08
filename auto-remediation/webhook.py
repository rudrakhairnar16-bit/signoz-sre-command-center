import json
import logging
import subprocess
import os
import requests
from datetime import datetime, timezone
from flask import Flask, request, jsonify

app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("remediation")

SERVICE_MAP = {
    "fastapi-svc": "fastapi-svc",
    "express-svc": "express-svc",
    "goworker-svc": "goworker-svc",
    "fastapi": "fastapi-svc",
    "express": "express-svc",
    "goworker": "goworker-svc",
}

COMPOSE_DIR = os.getenv(
    "COMPOSE_DIR",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "services")
)


def log_to_signoz(service: str, alert_name: str, status: str):
    try:
        payload = {
            "title": f"Auto-remediation for {service}",
            "text": json.dumps({
                "alert": alert_name,
                "service": service,
                "action": "docker compose restart",
                "status": status,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }),
            "tags": ["remediation", "auto", service],
            "source": "auto-remediation-webhook"
        }
        requests.post(
            "http://localhost:8080/api/v1/logs",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=5
        )
    except Exception as e:
        logger.warning("Failed to log to SigNoz: %s", e)


def restart_service(service: str) -> str:
    container = SERVICE_MAP.get(service, service)
    logger.info("Restarting container: %s", container)
    try:
        compose_cmd = ["docker", "compose"]
        result = subprocess.run(
            [*compose_cmd, "restart", container],
            capture_output=True, text=True, timeout=30,
            cwd=COMPOSE_DIR
        )
        if result.returncode != 0:
            compose_cmd = ["docker-compose"]
            result = subprocess.run(
                [*compose_cmd, "restart", container],
                capture_output=True, text=True, timeout=30,
                cwd=COMPOSE_DIR
            )
        if result.returncode == 0:
            return f"success: {container} restarted"
        else:
            return f"failed: {result.stderr.strip()}"
    except subprocess.TimeoutExpired:
        return "failed: timeout"
    except Exception as e:
        return f"failed: {str(e)}"


@app.route("/remediate", methods=["POST"])
def remediate():
    data = request.get_json(silent=True) or {}
    logger.info("Webhook received: %s", json.dumps(data, indent=2))

    service = (
        data.get("service")
        or data.get("labels", {}).get("service")
        or data.get("alert", {}).get("service")
        or "fastapi-svc"
    )
    alert_name = data.get("name") or data.get("alertName") or "unknown-alert"

    status = restart_service(service)
    log_to_signoz(service, alert_name, status)
    logger.info("Remediation result for %s: %s", service, status)

    return jsonify({"service": service, "alert": alert_name, "status": status})


@app.route("/remediate/<service>", methods=["GET"])
def remediate_manual(service):
    alert_name = f"manual-{service}"
    status = restart_service(service)
    log_to_signoz(service, alert_name, status)
    logger.info("Manual remediation for %s: %s", service, status)
    return jsonify({"service": service, "alert": alert_name, "status": status})


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()})


if __name__ == "__main__":
    logger.info("Starting remediation webhook on port 9000")
    app.run(host="0.0.0.0", port=9000)
