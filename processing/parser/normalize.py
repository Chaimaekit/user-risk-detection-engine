import json
import logging
import os
from kafka import KafkaConsumer, KafkaProducer
from pydantic import ValidationError
from processing.schemas.event import Event


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [normalizer] %(levelname)s %(message)s",
)
log = logging.getLogger(__name__)


KAFKA_HOST = os.getenv("KAFKA_HOST", "localhost:9092")

consumer = KafkaConsumer(
    "raw-auth-logs",
    bootstrap_servers=KAFKA_HOST,
    auto_offset_reset="earliest",
    enable_auto_commit=True,
    group_id="normalizer-grp",
    value_deserializer=lambda m: json.loads(m.decode("utf-8")),
)

producer = KafkaProducer(
    bootstrap_servers=KAFKA_HOST,
    value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
    acks="all",
    retries=3,
)

FIELD_MAP = {
    "auth_result":    "result",
    "status":         "result",
    "ip":             "source_ip",
    "src_ip":         "source_ip",
    "sAMAccountName": "user", #AD logs have sAMAccountName instead of user
    "hostname":       "device",
}

def map_fields(raw: dict) -> dict:
    mapped = {}
    for k, v in raw.items():
        canonical = FIELD_MAP.get(k, k)
        mapped[canonical] = v

    if "source_ip" not in mapped:
        mapped["source_ip"] = None
    if "action" not in mapped:
        mapped["action"] = "ad_snapshot"
    if "result" not in mapped:
        mapped["result"] = "unknown"

    if "timestamp" not in mapped:
        mapped["timestamp"] = (
            raw.get("lastLogon") or raw.get("collected_at")
        )

    return mapped

stats = {"processed": 0, "valid": 0, "invalid": 0}

log.info("Normalizer started — waiting for events on raw-auth-logs")

for message in consumer:
    raw_event = message.value
    stats["processed"] += 1

    try:
        mapped = map_fields(raw_event)
        event = Event(**mapped)
        producer.send("normalized-events", event.model_dump(mode="json"))
        stats["valid"] += 1
        log.debug("✓ %s %s %s", event.source, event.user, event.action)

    except ValidationError as e:
        stats["invalid"] += 1
        producer.send("dead-letter-events", {
            "raw": raw_event,
            "error": e.errors(),
            "stage": "validation"
        })
        log.warning("✗ validation failed → dead-letter (%d errors)", e.error_count())

    except Exception as e:
        stats["invalid"] += 1
        log.error("✗ unexpected error: %s", e)

    if stats["processed"] % 100 == 0:
        log.info("processed=%d valid=%d invalid=%d",
                 stats["processed"], stats["valid"], stats["invalid"])