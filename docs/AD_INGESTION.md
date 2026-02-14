# Active Directory ingestion

This project can ingest user data from Active Directory instead of synthetic logs. The repository includes `ingestion/ad_ingest.py`, which queries AD and emits newline-delimited JSON events.

Required environment variables:

- `LDAP_SERVER` - LDAP URI (e.g. `ldap://ad.example.com`) (optional, defaults to `ldap://localhost`)
- `LDAP_USER` - Bind username (e.g. `DOMAIN\\serviceaccount` or `user@domain.com`)
- `LDAP_PASSWORD` - Bind password
- `LDAP_BASE_DN` - Base DN for user search (e.g. `DC=example,DC=com`)
- `OUTPUT_PATH` - Path to write NDJSON events (default: `logs/ad_users.log`)

Run once:

```bash
python ingestion/ad_ingest.py --once
```

Run continuously (poll every 5 minutes):

```bash
python ingestion/ad_ingest.py --interval 300
```

Note: ensure `Filebeat.yaml` or your ingestion pipeline reads the `OUTPUT_PATH` file so events are forwarded to the processing layer.
