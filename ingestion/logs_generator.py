import json
import random
import time
from kafka import KafkaProducer
from datetime import datetime


#needs to test using other vms(linux,wind etc) using filebeat runned on main machine/host
producer = KafkaProducer(
    bootstrap_servers="localhost:9092",
    value_serializer=lambda v: json.dumps(v).encode()
)

users = ["john", "test", "srv"]

while True:
    event = {
        "user": random.choice(users),
        "action": "login",
        "result": random.choice(["success", "failure"]),
        "source_ip": f"192.168.1.{random.randint(1,254)}",
        "timestamp": datetime.utcnow().isoformat()
    }

    producer.send("raw-auth-logs", event)
    print(event)
    time.sleep(2)
