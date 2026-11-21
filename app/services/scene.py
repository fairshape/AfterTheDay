import re

from PIL import Image, ImageOps

from app.infrastructure.audio.analysis import analyze_audio
from app.services.palette import photo_palette
from app.services.story import interpret
from app.services.timing import RHYTHMS, edit_points, excerpt

WEATHER_TEXTURE = re.compile(r"дожд|туман|снег|измороз", re.I)


def build_scene(media, day_id: str, story: str, photos: list[dict], track: dict, details: dict,
                *, base: dict | None = None, even_comparison: bool = False) -> dict:
    arc = interpret(story, details)
    title = base["title"] if base else arc.title
    profile = track.get("profile", "calm")
    rhythm = RHYTHMS[profile]
    selected_photo = details.get("favorite_photo")
    explicit_photo = any(photo["id"] == selected_photo for photo in photos)
    palette_photo = selected_photo if explicit_photo else photos[0]["id"]
    palette = photo_palette(media, day_id, photos, palette_photo)
    ordered = photos if not explicit_photo else [photo for photo in photos if photo["id"] != selected_photo] + [
        photo for photo in photos if photo["id"] == selected_photo]
    if len(ordered) == 1 and arc.opening != arc.ending:
        ordered = ordered * 2
    framed = len(ordered)
    ideal = rhythm.seconds * framed + (2.6 if framed > 1 and (arc.release or arc.intimate) else 0)
    analysis = None
    if track["kind"] == "file":
        cue = min(track.get("cue", 0), max(0, track["duration"] - min(1.2, track["duration"])))
        analysis = analyze_audio(media.path(day_id, track["id"]), track["mime"], cue)
    offset, duration, alternatives = excerpt(track, ideal, analysis)
    count = min(framed, max(1, int(duration / 1.8)))
    if count == 1:
        ordered = ordered[-1:]
    elif count < framed:
        ordered = [ordered[round(i * (framed-1)/(count-1))] for i in range(count)]
    captions = [""] * len(ordered)
    captions[0] = arc.opening
    if len(captions) >= 3 and arc.turn != arc.opening:
        captions[1] = arc.turn
    captions[-1] = arc.ending
    if len(captions) > 1 and captions[0] == captions[-1]:
        captions[0] = ""

    cues = analysis.cues if analysis else ()
    points, aligned = edit_points(captions, duration, offset, rhythm, arc.release or arc.intimate or arc.quiet or explicit_photo, cues)
    dissolve = rhythm.transition * (.76 if arc.restless else 1.13 if arc.quiet else 1)
    frames = []
    for index, photo in enumerate(ordered):
        final = index == len(ordered) - 1
        still = final and (arc.release or explicit_photo or arc.intimate)
        zoom = 1 + (rhythm.zoom - 1) * (.55 if arc.quiet else 1)
        with Image.open(media.path(day_id, photo["id"])) as image:
            w, h = ImageOps.exif_transpose(image).size
        crop = {"fit": "contain" if w/h > 1.08 else "cover", "x": .50, "y": .45 if index else .42}
        seconds = round(points[index+1] - points[index], 3)
        if final and arc.release:
            motion = {"from": 1, "to": 1, "x": 0, "y": 0}
        elif still:
            motion = {"from": 1, "to": 1.008, "x": 0, "y": 0}
        else:
            motion = {"from": 1.025 if index and arc.intimate else 1, "to": round(zoom, 3),
                      "x": .6 if index % 2 else -.35, "y": -.24}
        frames.append({"asset": photo["id"], "start": points[index], "seconds": seconds, "caption": captions[index],
                       "captionIn": round(min(.42 if final else .20, seconds*.16),3),
                       "captionOut": round(seconds if final else seconds - min(.1, seconds*.07),3),
                       "crop": crop, "transition": min(dissolve, seconds*.25), "motion": motion})

    basis = "measured" if aligned else "character"
    scene = {
        "version": 2, "title": title, "cover": photos[0]["id"], "palette": palette, "frames": frames,
        "grain": .13 if WEATHER_TEXTURE.search(details.get("weather", "")) else .075,
        "track": track,
        "soundtrack": {"basis": basis, "offset": offset, "duration": duration, "alternatives": alternatives,
                       "analysis": {"method": "local_waveform_v1", "tempo": analysis.tempo,
                                    "tempoConfidence": analysis.confidence, "cutCues": aligned} if analysis else None},
        "signals": {"story": arc.ending, "opening": arc.opening, "turn": arc.turn, "focus": arc.focus,
                    "mainPhoto": frames[-1]["asset"], "finalHold": frames[-1]["seconds"],
                    "photoCount": len(photos), "profile": profile, "source": track.get("signal", "default"),
                    "baseSeconds": rhythm.seconds, "transition": round(dissolve, 3),
                    "motion": max(frame["motion"]["to"] for frame in frames)},
    }
    if even_comparison:
        boundaries = [round(duration*i/len(frames),3) for i in range(len(frames)+1)]
        scene["evenFrames"] = [
            {**frame, "start": boundaries[index], "seconds": round(boundaries[index+1]-boundaries[index],3),
             "captionIn": 0, "captionOut": round(boundaries[index+1]-boundaries[index],3),
             "transition": .2, "motion": {"from": 1, "to": 1.03, "x":0,"y":0}}
            for index, frame in enumerate(frames)
        ]
    return scene
