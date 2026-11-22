import re

from PIL import Image

from app.infrastructure.audio.analysis import analyze_audio
from app.services.art_direction import suggest_sticker
from app.services.palette import photo_palette
from app.services.story import interpret, short_quote
from app.services.anniversaries import suggested_tags
from app.services.emotion import interpret_scene
from app.services.studio import art_settings, camera_motion, shot_order
from app.services.timing import RHYTHMS, edit_points, excerpt

WEATHER_TEXTURE = re.compile(r"дожд|туман|снег|измороз", re.I)


def build_scene(media, day_id: str, story: str, photos: list[dict], track: dict, details: dict,
                *, moods: list | None = None, base: dict | None = None, even_comparison: bool = False,
                match_cut: bool = False) -> dict:
    arc = interpret(story, details)
    title = details.get("custom_title") or (base["title"] if base else arc.title)
    profile = track.get("profile", "calm")
    rhythm = RHYTHMS[profile]
    selected_photo = details.get("favorite_photo")
    explicit_photo = any(photo["id"] == selected_photo for photo in photos)
    palette_photo = selected_photo if explicit_photo else photos[0]["id"]
    cover_photo = next((p["id"] for p in photos if p["id"] == details.get("cover_photo")), palette_photo)
    palette_photo = selected_photo if explicit_photo else cover_photo
    reference = base["frames"] if match_cut and base else []
    palette = base["palette"] if reference else photo_palette(media, day_id, photos, palette_photo)
    studio = details.get("studio", {})
    if reference:
        photos_by_id = {photo["id"]: photo for photo in photos}
        ordered = [photos_by_id[frame["asset"]] for frame in reference]
    else:
        ordered = shot_order(photos, studio, selected_photo)
        if len(ordered) == 1 and arc.opening != arc.ending:
            ordered = ordered * 2
    framed = len(ordered)
    ideal = rhythm.seconds * framed + (2.6 if framed > 1 and (arc.release or arc.intimate) else 0)
    ideal = max(15 if framed > 1 else 12, ideal)
    analysis = None
    if track["kind"] == "file":
        cue = min(track.get("cue", 0), max(0, track["duration"] - min(1.2, track["duration"])))
        analysis = analyze_audio(media.path(day_id, track["id"]), track["mime"], cue)
    requested = studio.get("seconds")
    offset, duration, alternatives = excerpt(track, requested or ideal, analysis, maximum=45 if requested else None)
    if reference:
        captions = [frame["caption"] for frame in reference]
    else:
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

        occurrences = {}
        for index, photo in enumerate(ordered):
            photo_id = photo["id"]
            occurrence = occurrences.get(photo_id, 0)
            # The author can identify what a particular photo means through its caption.
            attached = short_quote(photo.get("caption", "")) if occurrence == 0 else ""
            default = attached or captions[index]
            if index == len(ordered) - 1 and arc.focus in {"pin", "release"}:
                default = arc.ending
            captions[index] = details.get("_captions", {}).get(f"{photo_id}:{occurrence}", default)
            occurrences[photo_id] = occurrence + 1

    cues = analysis.cues if analysis else ()
    highlight = next((i for i, photo in enumerate(ordered) if photo["id"] == selected_photo), None)
    hold_detail = arc.focus in {"pin", "release"} or arc.intimate or arc.quiet or explicit_photo
    points, aligned = edit_points(captions, duration, offset, rhythm,
                                  hold_detail, cues, release=arc.release, highlight=highlight if studio.get("order") else None)
    dissolve = rhythm.transition * (.76 if arc.restless else 1.13 if arc.quiet else 1)
    treatment = art_settings(studio, .13 if WEATHER_TEXTURE.search(details.get("weather", "")) else .075)
    frames = []
    for index, photo in enumerate(ordered):
        final = index == len(ordered) - 1
        still = final and hold_detail
        zoom = 1 + (rhythm.zoom - 1) * (.55 if arc.quiet else 1)
        crop = reference[index].get("crop") if reference else None
        if not crop:
            with Image.open(media.path(day_id, photo["id"])) as image:
                w, h = image.size
                if image.getexif().get(274) in {5, 6, 7, 8}:
                    w, h = h, w
            wide = w/h > 1.08 or (profile == "rising" and final and w/h >= .85)
            crop = {"fit": "contain" if wide else "cover", "x": .50, "y": .45 if index else .42}
        seconds = round(points[index+1] - points[index], 3)
        if final and arc.release:
            motion = {"from": 1, "to": 1, "x": 0, "y": 0}
        elif still:
            motion = {"from": 1, "to": 1.008, "x": 0, "y": 0}
        else:
            framing = 1.08 if arc.release else 1.035 if index and arc.intimate else 1
            if profile == "rising":
                framing += .018 * max(0, min(index, 3))
            motion = {"from": framing, "to": round(max(framing, zoom), 3),
                      "x": .6 if index % 2 else -.35, "y": -.24}
        tail = min(1.45, seconds * .18) if still and seconds >= 5 and len(captions[index]) <= 80 else 0
        frames.append({"asset": photo["id"], "start": points[index], "seconds": seconds, "caption": captions[index],
                       "captionIn": round(min(.80 if arc.quiet else .42 if final else .20, seconds*.20),3),
                       "captionOut": round(seconds - (tail if final else min(.1, seconds*.07)),3),
                       "tail": round(tail, 3),
                       "crop": crop, "transition": min(dissolve, seconds*.25), "motion": camera_motion(motion, studio.get("motion", "auto"))})

    basis = "measured" if aligned else "character"
    measured = None
    if analysis:
        readings = [round(analysis.energy_at(offset+duration*i/8), 3) for i in range(9)]
        measured = {"method": "local_waveform_v1", "tempo": analysis.tempo,
                    "tempoConfidence": analysis.confidence, "cutCues": aligned, "energy": readings,
                    "softEnding": sum(readings[-3:])/3 < sum(readings[1:5])/4 * .66}
    scene = {
        "version": 2, "title": title, "cover": cover_photo, "palette": palette, "frames": frames,
        "sticker": suggest_sticker(story, details),
        "grain": treatment["grain"], "treatment": treatment,
        "track": track,
        "soundtrack": {"basis": basis, "offset": offset, "duration": duration, "alternatives": alternatives,
                       "analysis": measured},
        "signals": {"story": captions[-1], "opening": arc.opening, "turn": arc.turn, "focus": arc.focus,
                    "mainPhoto": ordered[highlight]["id"] if highlight is not None else frames[-1]["asset"], "finalHold": frames[-1]["seconds"],
                    "photoCount": len(photos), "profile": profile, "source": track.get("signal", "default"),
                    "baseSeconds": rhythm.seconds, "transition": round(dissolve, 3),
                    "motion": max(frame["motion"]["to"] for frame in frames)},
    }
    scene["emotion"] = interpret_scene(scene, moods if moods is not None else suggested_tags(story, details), story, moods is not None)
    artistic = scene["emotion"]
    for frame in frames:
        frame["transition"] = round(min(frame["seconds"] * .25, frame["transition"] * artistic["dissolveGain"]), 3)
        frame["captionIn"] = round(min(frame["seconds"] * .25, frame["captionIn"] + artistic["captionDelay"]), 3)
        if frame["tail"]:
            frame["captionIn"] = round(min(1.1, frame["seconds"] * .20), 3)
        if studio.get("motion", "auto") == "auto":
            gain = artistic["cameraGain"]
            motion = frame["motion"]
            for key in ("from", "to"):
                motion[key] = round(1 + (motion[key]-1) * gain, 4)
    scene["signals"]["motion"] = max(frame["motion"]["to"] for frame in frames)
    scene["signals"]["transition"] = frames[-1]["transition"]
    if even_comparison:
        boundaries = [round(duration*i/len(frames),3) for i in range(len(frames)+1)]
        scene["evenFrames"] = [
            {**frame, "start": boundaries[index], "seconds": round(boundaries[index+1]-boundaries[index],3),
             "captionIn": 0, "captionOut": round(boundaries[index+1]-boundaries[index],3), "tail": 0,
             "transition": .2, "motion": {"from": 1, "to": 1.03, "x":0,"y":0}}
            for index, frame in enumerate(frames)
        ]
    return scene
