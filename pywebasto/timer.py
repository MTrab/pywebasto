"""Timer models for Webasto timer operations."""

from dataclasses import dataclass


@dataclass(slots=True)
class SimpleTimer:
    """Representation of an observed `simple` timer payload."""

    start: int
    duration: int
    repeat: int
    latitude: str | None = None
    longitude: str | None = None
    enabled: bool = True

    def validate(self) -> None:
        """Validate timer fields based on observed payload constraints."""
        if self.start <= 0:
            raise ValueError("start must be > 0")
        if self.duration <= 0:
            raise ValueError("duration must be > 0")
        if self.repeat < 0:
            raise ValueError("repeat must be >= 0")
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("latitude and longitude must both be set or both be None")
        if self.latitude is not None and self.latitude == "":
            raise ValueError("latitude must be a non-empty string when provided")
        if self.longitude is not None and self.longitude == "":
            raise ValueError("longitude must be a non-empty string when provided")

    def to_api_dict(self) -> dict:
        """Serialize to the observed API shape."""
        self.validate()
        payload = {
            "type": "simple",
            "start": self.start,
            "duration": self.duration,
            "repeat": self.repeat,
            "enabled": self.enabled,
        }
        if self.latitude is not None and self.longitude is not None:
            payload["location"] = {"lat": self.latitude, "lon": self.longitude}
        return payload

    @classmethod
    def from_api_dict(cls, data: dict) -> "SimpleTimer":
        """Build from a timer dict returned by API data endpoints."""
        if data.get("type") != "simple":
            raise ValueError("timer type must be 'simple'")

        location = data.get("location")
        latitude: str | None = None
        longitude: str | None = None
        if location is not None:
            if not isinstance(location, dict):
                raise ValueError("timer location must be a dict when provided")
            latitude = str(location["lat"])
            longitude = str(location["lon"])

        timer = cls(
            start=int(data["start"]),
            duration=int(data["duration"]),
            repeat=int(data["repeat"]),
            latitude=latitude,
            longitude=longitude,
            enabled=bool(data.get("enabled", True)),
        )
        timer.validate()
        return timer
