from __future__ import annotations
from typing import Optional, Literal
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
import ipaddress

class Event(BaseModel):
    user: str
    source: Literal["ssh", "vpn", "active_directory", "cloud", "unknown"] = "unknown"
    action: str
    result: Literal["success", "failure", "unknown"] = "unknown"
    source_ip: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None 
    asn: Optional[str] = None
    is_tor: bool = False
    device: Optional[str] = None
    timestamp: datetime
    abuse_score: Optional[int] = None
    is_known_bad_ip: bool = False
    raw: Optional[dict] = None

    @field_validator("user")
    @classmethod
    def normalise_user(cls, v: str) -> str:
        v = v.strip().lower()
        if "\\" in v:
            v = v.split("\\")[-1]
        if "@" in v:
            v = v.split("@")[0]
        return v

    @field_validator("source_ip")
    @classmethod
    def validate_ip(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        try:
            ipaddress.ip_address(v)
            return v
        except ValueError:
            return None

    @field_validator("timestamp", mode="before")
    @classmethod
    def parse_timestamp(cls, v):
        if isinstance(v, datetime):
            return v
        if isinstance(v, str):
            return datetime.fromisoformat(v.replace("Z", "+00:00"))
        raise ValueError(f"Cannot parse timestamp: {v}")

    class Config:
        extra = "ignore"