"""Compose a recap from the opening and key shot of each saved day."""

from app.services.emotion import memory_art


def assemble(days, options):
    arts = {day.id: memory_art(day) for day in days}
    if options.order == "date":
        days.sort(key=lambda d: (d.memory_date, d.created_at))
    elif options.order == "energy":
        days.sort(key=lambda d: (arts[d.id]["energy"], d.memory_date))
    shots = []
    cursor = 0.0
    by_id = {str(i.day): i for i in options.items}
    # Distribute the requested length, giving quieter chapters more time to settle.
    weights = {d.id: 1.2 - 0.4 * arts[d.id]["energy"] for d in days}
    total_weight = sum(weights.values())
    continuous = next((d for d in days if d.id == options.music), None)
    for day in days:
        scene = day.scene
        frames = scene["frames"]
        source = scene.get("soundtrack", {})
        track = scene["track"]
        excerpt = source.get("offset", track.get("cue", 0))
        line = by_id[day.id].caption or frames[-1]["caption"] or day.title
        reading_time = min(10, max(2.5, len(line) / 16 + 0.7))
        target = min(
            max(options.seconds * weights[day.id] / total_weight, reading_time + 1.4),
            source.get("duration", sum(f["seconds"] for f in frames)),
        )
        chosen = [frames[0], frames[-1]] if len(frames) > 1 and target >= 4 else [frames[-1]]
        first = target * 0.44
        music_source = continuous.scene.get("soundtrack", {}) if continuous else source
        cue_offset = (
            (music_source.get("offset", 0) + cursor) % continuous.track["duration"]
            if continuous and continuous.track.get("duration")
            else excerpt
        )
        cues = (
            (music_source.get("analysis") or {}).get("cutCues", []) if options.music != "silent" else []
        )
        candidates = [
            c["audioTime"] - cue_offset
            for c in cues
            if 1.6 <= c["audioTime"] - cue_offset <= target - 1.8
            and abs(c["audioTime"] - cue_offset - first) <= 0.7
        ]
        if candidates:
            first = min(candidates, key=lambda v: abs(v - first))
        for idx, frame in enumerate(chosen):
            length = target if len(chosen) == 1 else first if idx == 0 else target - first
            caption = by_id[day.id].caption if idx == len(chosen) - 1 else ""
            shots.append(
                {
                    "day": day.id,
                    "title": day.title,
                    "date": day.memory_date.isoformat(),
                    "asset": f"/api/days/{day.id}/media/{frame['asset']}",
                    "caption": caption or frame["caption"] or day.title,
                    "start": round(cursor, 3),
                    "seconds": round(length, 3),
                    "motion": frame["motion"],
                    "treatment": scene.get("treatment", {}),
                    "transition": frame["transition"],
                    "crop": frame.get("crop", {}),
                    "emotion": arts[day.id],
                    "musicTime": excerpt + (first if idx else 0),
                }
            )
            cursor += length
    tracks = {
        d.id: {
            "url": f"/api/days/{d.id}/media/{d.track['id']}",
            "duration": d.track["duration"],
            "offset": d.scene.get("soundtrack", {}).get("offset", 0),
            "title": d.track["title"],
        }
        for d in days
        if d.track.get("kind") == "file"
    }
    if options.music not in {"sections", "silent", *tracks}:
        raise ValueError("unavailable soundtrack")
    return {
        "version": 1,
        "title": options.title.strip() or "Мой фильм",
        "shots": shots,
        "duration": round(cursor, 3),
        "requestedSeconds": options.seconds,
        "captions": {str(i.day): i.caption for i in options.items if i.caption},
        "tracks": tracks,
        "music": options.music,
        "order": options.order,
        "period": [min(s["date"] for s in shots), max(s["date"] for s in shots)],
    }
