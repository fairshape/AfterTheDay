"""Local artistic interpretation. Categories come from words, visual dimensions from the scene."""

import re

from app.services.anniversaries import tags

WORLD_TAGS = {
    "bright": {"радость"},
    "sad": {"грусть", "ностальгия"},
    "funny": {"юмор"},
    "tense": {"напряжение"},
    "pleasant": {"уют", "спокойствие", "облегчение"},
}


def interpret_scene(scene, labels, story, confirmed=False):
    scores = {
        key: round(min(1, 0.52 + 0.18 * len(group.intersection(labels))), 2)
        for key, group in WORLD_TAGS.items()
        if group.intersection(labels)
    }
    if not confirmed and re.search("смеял|смех|расхохот|смешн|шутк", story, re.I):
        scores["funny"] = 0.82
    primary = max(scores, key=scores.get) if scores else None
    track = scene.get("track", {})
    analysis = scene.get("soundtrack", {}).get("analysis") or {}
    envelope = analysis.get("energy", [])
    energy = (
        min(1, sum(envelope) / max(1, len(envelope)))
        if envelope
        else {"calm": 0.25, "rhythmic": 0.75, "tense": 0.82, "rising": 0.65}.get(
            track.get("profile"), 0.5
        )
    )
    pace = min(
        1,
        max(
            0,
            energy
            + 0.17 * scores.get("funny", 0)
            + 0.1 * scores.get("tense", 0)
            - 0.20 * scores.get("sad", 0)
            - 0.10 * scores.get("pleasant", 0),
        ),
    )
    color = scene.get("palette", {}).get("field", "#808080").lstrip("#")
    red, _green, blue = (int(color[i : i + 2], 16) / 255 for i in (0, 2, 4))
    reasons = []
    if labels:
        reasons.append(("Твои метки: " if confirmed else "По словам записи: ") + ", ".join(labels) + ".")
    reasons.append(
        "Цвет обложки рассчитан по снимкам."
        if scene["palette"].get("source") == "photo"
        else "Для обложки выбрана резервная палитра."
    )
    reasons.append(
        "Ритм учитывает акценты аудиофайла."
        if analysis.get("cutCues")
        else "Темп задан характером выбранной песни."
    )
    reflective = bool(scores.get("sad")) or (not confirmed and bool(re.search(r"устал|груст|скучал|тоск", story, re.I)))
    # Narrative space and musical energy have different sources. A fast song can
    # cut between spacious, almost stationary photographs.
    calmness = .85 if "спокойствие" in labels or reflective else .34 if scores.get("tense") else .5
    intimacy = .8 if "уют" in labels else .4
    playfulness = scores.get("funny", 0)
    tension = scores.get("tense", 0)
    family = ("cinema" if reflective else "collage" if scores.get("funny")
              else "geometry" if scores.get("tense") else "wash" if track.get("profile") == "rising"
              else "journal" if scene.get("signals", {}).get("photoCount", 0) >= 3 else "cinema")
    return {
        "family": family,
        "labels": list(labels),
        "confirmed": confirmed,
        "primary": primary,
        "strengths": scores,
        "energy": round(energy, 3),
        "warmth": round((1 + red - blue) / 2, 3),
        "calmness": calmness,
        "intimacy": intimacy,
        "playfulness": playfulness,
        "tension": tension,
        "intensity": round(max(scores.get("tense", 0), energy), 3),
        "nostalgia": 0.8 if "ностальгия" in labels else 0,
        "valence": 0.3
        if primary == "sad"
        else 0.75
        if primary in {"bright", "pleasant", "funny"}
        else 0.5,
        "type": "serif" if pace < 0.55 else "sans",
        "cameraGain": round(.42 if reflective else .82 + .36 * pace, 3),
        "dissolveGain": round(1.22 - 0.44 * pace, 3),
        "captionDelay": round(0.06 + 0.18 * (1 - pace), 3),
        "accent": scene.get("palette", {}).get("accent", "#d9dece"),
        "reasons": reasons,
    }


def memory_art(day, scene=None):
    scene = scene or day.scene
    labels = tags(day)
    confirmed = day.mood_tags is not None
    saved = scene.get("emotion", {})
    if "family" in saved and saved.get("labels") == labels and saved.get("confirmed") == confirmed:
        return saved
    return interpret_scene(scene, labels, day.story, confirmed)
