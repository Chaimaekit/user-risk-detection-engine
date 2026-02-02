from pydantic import BaseModel
from datetime import datetime

class Event(BaseModel):
    user: str
    action: str
    result: str
    source_ip: str
    timestamp: datetime
