# Phase 3 - Dashboards + Alerts

## Dashboard
- Name: SLO Command Center
- Panels: SLO Target, Error Budget, Alert Count, Services Monitored, p99 Latency, Error Rate, Trace-Log Correlation
- Inserted into PostgreSQL dashboard table
- JSON exported to dashboard-slo-command-center.json

## Alert Rules (3 alerts inserted into rule table)

| # | Name | Severity | Condition | Channel |
|---|---|---|---|---|
| 1 | Error Budget Warning | warning | EB consumed > 50% | slack |
| 2 | Error Budget Critical | critical | EB consumed > 80% | pagerduty, email |
| 3 | Burn Rate Critical | critical | Error rate > 2x | webhook |

## Verification
Open http://localhost:8080 and sign in with admin@signoz.io / Admin@12345!
- Navigate to Dashboards → SLO Command Center
- Navigate to Alerts → see 3 alert rules
- Configure notification channels in Settings → Alert Channels
