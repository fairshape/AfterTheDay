"""Persist a director's choices independently from the order of original uploads."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


class StudioChoices(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    order: list[Annotated[str, Field(pattern=r"^[a-f0-9]{32}$")]] = Field(
        default_factory=list, max_length=10
    )
    motion: Literal["auto", "still", "soft", "expressive"] = "auto"
    seconds: int | None = Field(default=None, ge=8, le=45)
    treatment: Literal["natural", "print", "graphic"] = "natural"


def shot_order(photos, settings, main_photo):
    if explicit := settings.get("order"):
        lookup = {photo["id"]: photo for photo in photos}
        return [lookup[key] for key in explicit if key in lookup] + [
            p for p in photos if p["id"] not in explicit
        ]
    return [p for p in photos if p["id"] != main_photo] + [p for p in photos if p["id"] == main_photo]


def art_settings(settings, grain):
    style = settings.get("treatment", "natural")
    return {
        "style": style,
        "contrast": {"natural": 1, "print": 0.98, "graphic": 1.075}[style],
        "saturation": {"natural": 1, "print": 0.90, "graphic": 0.96}[style],
        "grain": min(0.23, grain + (0.075 if style == "print" else 0)),
    }


def camera_motion(motion, setting):
    amount = {"auto": 1, "still": 0, "soft": 0.55, "expressive": 1.45}.get(setting, 1)
    return {
        key: round(1 + (value - 1) * amount if key in {"from", "to"} else value * amount, 4)
        for key, value in motion.items()
    }
