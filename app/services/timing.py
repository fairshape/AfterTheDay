from dataclasses import dataclass
from math import floor

from app.infrastructure.audio.analysis import AudioAnalysis, AudioCue


@dataclass(frozen=True)
class Rhythm:
    seconds: float
    transition: float
    zoom: float
    cut_window: float


RHYTHMS = {
    "calm": Rhythm(4.6, .68, 1.045, 1.05),
    "rhythmic": Rhythm(3.0, .17, 1.085, .72),
    "rising": Rhythm(4.0, .29, 1.08, .88),
    "tense": Rhythm(2.45, .09, 1.065, .82),
}
MAX_EXCERPT = 26
MIN_READABLE_CLIP = 1.2


def excerpt(track: dict, ideal: float, analysis: AudioAnalysis | None, *, maximum: float | None = None) -> tuple[float, float, list[float]]:
    ideal = min(maximum or MAX_EXCERPT, max(MIN_READABLE_CLIP, ideal))
    if track["kind"] != "file":
        return 0, ideal, []
    length = track["duration"]
    maximum = max(0, length - min(length, MIN_READABLE_CLIP))
    if "cue" in track:
        offset = min(maximum, track["cue"])
    else:
        offset = 0.0
    alternatives = []
    if analysis:
        last_start = min(length - ideal, analysis.start + .025*(len(analysis.energy)-1) - ideal)
        choices = []
        for step in range(max(0, floor((last_start - analysis.start) * 2)) + 1):
            start = analysis.start + step / 2
            if start > maximum:
                break
            samples = [analysis.energy_at(start + portion*ideal) for portion in (.035,.16,.35,.55,.73,.91)]
            accents = sum(1 for cue in analysis.cues if start + 1 < cue.at < start + ideal - 2 and cue.score >= .22)
            score = (min(samples[0], .65) * 2 + min(sum(samples)/6, .65)
                     + min(5, accents) * .12 + max(0, samples[2] - samples[-1]) * .30 - step * .037
                     + (.20 if start == 0 and samples[0] >= .12 else 0))
            choices.append((score, start))
        for _, candidate in sorted(choices, key=lambda item: (-item[0], item[1])):
            if all(abs(candidate - previous) >= 2.5 for previous in alternatives):
                alternatives.append(candidate)
            if len(alternatives) >= 3:
                break
        if alternatives and "cue" not in track:
            offset = alternatives[0]
    return round(offset, 3), round(min(ideal, length-offset),3), alternatives


def edit_points(captions: list[str], total: float, offset: float, rhythm: Rhythm,
                final_hold: bool, cues: tuple[AudioCue, ...], *, release: bool = False, highlight: int | None = None) -> tuple[list[float], list[dict]]:
    count = len(captions)
    minimum = [min(3.15, max(1.5, len(caption)/20 + .55)) for caption in captions]
    if final_hold:
        minimum[-1] = max(minimum)
        minimum[-1] += min(1.25, total * .11)
    ratio = min(1, total / sum(minimum))
    minimum = [seconds * ratio for seconds in minimum]
    weights = [1.0] * count
    if count > 1 and final_hold:
        weights[-1] = 3.0 if release else 1.9
    if highlight is not None and 0 <= highlight < count:
        weights[highlight] = max(weights) + .6
        minimum[highlight] = max(minimum)
        scale = min(1, total / sum(minimum))
        minimum = [value * scale for value in minimum]
    if count > 2 and highlight != 0:
        weights[0] = .83
    if rhythm is RHYTHMS["rising"] and count > 1:
        weights[0] *= 1.65
        weights[1] *= .85
    remaining = max(0, total - sum(minimum))
    ideal = [seconds + remaining*weight/sum(weights) for seconds, weight in zip(minimum, weights)]
    points = [0.0]
    aligned = []
    for index in range(1, count):
        low = points[-1] + minimum[index-1]
        high = max(low, total - sum(minimum[index:]))
        target = max(low, min(high, sum(ideal[:index])))
        choices = [cue for cue in cues if cue.score >= (.22 if cue.kind == "onset" else .33) and low <= cue.at-offset <= high
                   and abs(cue.at-offset-target) <= rhythm.cut_window]
        if choices:
            selected = max(choices, key=lambda cue: (cue.score + (.13 if cue.kind == "onset" else 0)
                   - .28 * abs(cue.at-offset-target)/rhythm.cut_window, -cue.at))
            target = selected.at-offset
            aligned.append({"shot": index, "audioTime": selected.at, "kind": selected.kind,
                            "strength": round(selected.score,3)})
        points.append(round(target,3))
    points.append(total)
    return points, aligned
