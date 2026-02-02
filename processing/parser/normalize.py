import json
from kafka import KafkaConsumer, KafkaProducer
from pydantic import ValidationError
from processing.schemas.event import Event




consumer = KafkaConsumer(
    "raw-auth-logs",
    bootstrap_servers="localhost:9092",
    auto_offset_reset="earliest",
    enable_auto_commit=True,
    group_id="normalizer-grp",#consuming group name
    value_deserializer=lambda m: json.loads(m.decode("utf-8")),
)


producer = KafkaProducer(
    bootstrap_servers="localhost:9092",
    value_serializer=lambda v: json.dumps(v).encode("utf-8"),
)

print("Normalizer started. Waiting for events...")

for message in consumer:
    raw_event = message.value

    try:
        event = Event(**raw_event)
        normalized_event = event.model_dump(mode="json")
        producer.send("normalized-events", normalized_event)

        print("Normalized event:", normalized_event)

    except ValidationError as e:
        print("Invalid event dropped:", raw_event, "Error:", e)
