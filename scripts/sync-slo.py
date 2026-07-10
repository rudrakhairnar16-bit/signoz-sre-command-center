"""
SLO-as-Code sync script.

Validates slo.yaml and optionally syncs configuration to SigNoz.

Usage:
  python scripts/sync-slo.py              # validate only
  python scripts/sync-slo.py --apply      # validate + log what would change
  python scripts/sync-slo.py --apply --dry-run  # validate + print planned changes
"""
import os
import sys
import json
import argparse
import logging
import yaml

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("sync-slo")


def load_slo(path="slo.yaml"):
    if not os.path.exists(path):
        logger.error("File not found: %s", path)
        sys.exit(1)
    with open(path) as f:
        return yaml.safe_load(f)


def validate(config):
    errors = []
    if "slo_target" not in config:
        errors.append("Missing top-level slo_target")
    if "services" not in config or not config["services"]:
        errors.append("Missing services list")

    for name, svc in config.get("services", {}).items():
        if "alert_thresholds" not in svc:
            errors.append(f"{name}: missing alert_thresholds")
            continue
        at = svc["alert_thresholds"]
        if "error_rate_pct" not in at:
            errors.append(f"{name}: missing alert_thresholds.error_rate_pct")

    return errors


def print_config(config):
    logger.info("SLO Target: %.1f%% over %d days",
                 config.get("slo_target", 99.5),
                 config.get("slo_window_days", 30))
    logger.info("Error Budget Window: %s", config.get("error_budget_window", "24h"))
    logger.info("")
    for name, svc in config.get("services", {}).items():
        at = svc.get("alert_thresholds", {})
        logger.info("  %s:", name)
        logger.info("    SLO Target:       %.1f%%", svc.get("slo_target", config.get("slo_target")))
        logger.info("    Error Rate:       > %.0f%%", at.get("error_rate_pct", 0))
        logger.info("    Error Count:      > %d", at.get("error_count", 0))
        logger.info("    Burn Rate:        > %.1fx", at.get("burn_rate", 0))
        logger.info("    Remediation:      %s (cooldown %ds)",
                     svc.get("remediation", {}).get("action", "restart"),
                     svc.get("remediation", {}).get("cooldown_seconds", 300))
        logger.info("")


def sync(config):
    logger.info("--apply: Syncing SLO config to SigNoz (mock)...")
    for name, svc in config.get("services", {}).items():
        slo = svc.get("slo_target", config.get("slo_target"))
        logger.info("  %s → SLO %.1f%%", name, slo)
    logger.info("Sync complete. (No actual SigNoz API mutations implemented — this is a validation layer.)")


def main():
    parser = argparse.ArgumentParser(description="SLO-as-Code sync tool")
    parser.add_argument("--slo-file", default="slo.yaml", help="Path to slo.yaml")
    parser.add_argument("--apply", action="store_true", help="Apply config to SigNoz")
    parser.add_argument("--dry-run", action="store_true", help="Print planned changes only")
    args = parser.parse_args()

    config = load_slo(args.slo_file)
    logger.info("Loaded slo.yaml — validating...\n")

    errs = validate(config)
    if errs:
        for e in errs:
            logger.error("  ❌ %s", e)
        logger.error("\nValidation FAILED — %d error(s)", len(errs))
        sys.exit(1)

    logger.info("  ✅ slo.yaml is valid\n")
    print_config(config)

    if args.apply:
        if args.dry_run:
            logger.info("--dry-run: showing planned changes\n")
            print_config(config)
        else:
            sync(config)


if __name__ == "__main__":
    main()
