# User-Centric Risk Scoring Engine

A production-grade cybersecurity detection engine that reasons about users over time — not single noisy alerts.

## Architecture

```
SSH / VPN / AD / Cloud logs
        ↓
    Filebeat  (on host)  →  raw-auth-logs  (Redpanda topic)
        ↓
    [normalizer container]    raw-auth-logs → normalized-events
        ↓                     bad events   → dead-letter-events
    [enricher container]      normalized-events → GeoIP + IP Reputation (Redis cached)
        ↓                     stores in ClickHouse + publishes enriched-events
    [scorer container]        enriched-events → feature extraction → risk score
        ↓                     stores in Postgres + publishes scored-events
    [alerter container]       scored-events → Wazuh (CEF/syslog) + Slack webhook
        ↓
    Grafana dashboards (queries ClickHouse + Postgres)
```

## Quick Start

```bash
# 1. Configure secrets
cp .env.example .env
# Edit .env — set ABUSEIPDB_KEY and MAXMIND_DB_PATH at minimum

# 2. Start everything — infrastructure + all application services
docker compose up -d

# 3. Check all containers are healthy
docker compose ps

# 4. Run the attack scenario simulator (optional — fires all 6 test scenarios)
docker compose --profile simulation up simulator
```

That's it. `docker compose up -d` starts:
- **redpanda** — message broker
- **clickhouse** — event store
- **postgres** — user state and baselines
- **redis** — IP reputation cache
- **redpanda-init** — creates all topics once then exits
- **normalizer** — raw logs → validated schema
- **enricher** — adds GeoIP + reputation → ClickHouse
- **scorer** — computes risk scores → Postgres
- **alerter** — routes alerts → Wazuh + Slack

## Viewing Logs

```bash
# All services
docker compose logs -f

# One service
docker compose logs -f scorer

# Only alerts (warnings and above)
docker compose logs -f scorer | grep -E "ALERT|CRITICAL"
```

## Impossible Travel Logic

| Route | Distance | Time | Speed | Verdict | Score |
|-------|----------|------|-------|---------|-------|
| Morocco → Russia | 4,231 km | 1h | 4,231 km/h | **Impossible** | +30 |
| Morocco → France | 1,887 km | 3h | 629 km/h | **Suspicious** | +15 |
| Morocco → France | 1,887 km | 4h | 472 km/h | Plausible | +0 |
| Morocco → Spain | 835 km | 4h | 209 km/h | Plausible | +0 |

**False positive design**: travel is never the sole trigger for Critical.
A legitimate traveller flying MA→RU triggers impossible_travel (+30) + new_country (+20) = **50 → Alert**.
A SOC analyst reviews, confirms it's a business trip, adds it to `travel_whitelist`. Done.
An attacker using that same route would also have brute_force (+50) + sudo (+15) = **95 → Critical**.

## Score Thresholds

| Score | Decision | Action |
|-------|----------|--------|
| 0–19 | Ignore | Nothing |
| 20–39 | Monitor | Log |
| 40–69 | Alert | Notify SOC + Wazuh |
| 70+ | Critical | Incident response |

## MITRE ATT&CK Mapping

| Detection | Technique |
|-----------|-----------|
| Impossible travel | T1078 — Valid Accounts |
| Brute force | T1110 — Brute Force |
| Privilege escalation | T1548 — Abuse Elevation Control Mechanism |
| Off-hours + new country | T1133 — External Remote Services |
| Known malicious IP | T1071 — Application Layer Protocol |