"""Original procedural instrumentals for the fictional diaries."""
from array import array
from io import BytesIO
from math import exp, pi, sin
import sys
import wave

SAMPLE_RATE = 22_050
DURATION = 25


def make_score(profile: str) -> bytes:
    samples = [0.0] * (SAMPLE_RATE * DURATION)
    chord_progression = [(45, 52, 59, 60), (41, 48, 55, 57), (48, 55, 59, 64), (43, 50, 57, 62)]

    def note(start, length, midi, volume, instrument="keys"):
        start_index = int(start * SAMPLE_RATE)
        hz = 440 * 2 ** ((midi - 69) / 12)
        for index in range(min(int(length * SAMPLE_RATE), len(samples) - start_index)):
            t = index / SAMPLE_RATE
            phase = 2 * pi * hz * t
            attack = min(t / 0.009, 1)
            tail = min((length - t) / 0.07, 1)
            if instrument == "kick":
                voice = sin(phase + 9 * (1 - exp(-t * 31))) * exp(-t * 17)
            elif instrument == "tick":
                voice = (sin(phase) + sin(phase * 1.71)) * 0.5 * exp(-t * 48)
            else:
                voice = (sin(phase) * exp(-t * 1.85)
                         + 0.33 * sin(phase * 2.003) * exp(-t * 3.9)
                         + 0.12 * sin(phase * 3.013) * exp(-t * 7))
            samples[start_index + index] += volume * attack * tail * voice

    if profile == "park":
        for when, notes, level in (
            (0.0, (45, 57, 60), .085), (1.2, (64,), .095), (2.4, (59, 67), .10),
            (3.85, (48, 55, 64), .21), (4.95, (62, 67), .11), (6.25, (60, 64), .12),
            (7.45, (57, 64), .10), (8.95, (41, 53, 60), .17),
            (10.7, (60, 65), .066), (12.1, (57,), .042), (14.3, (53,), .027),
            (18.0, (45, 52, 57), .062), (21.4, (52, 64), .052),
        ):
            for index, midi in enumerate(notes):
                note(when + index * .016, 4.0, midi, level / max(1, len(notes)) ** .5)
    elif profile == "calm":
        for bar in range(7):
            chord = chord_progression[bar % 4]
            for offset, midi in ((0, chord[0]), (0.55, chord[2]), (1.55, chord[3] + 12), (2.76, chord[1] + 12)):
                note(bar * 3.65 + offset, 2.8, midi, 0.14)
                note(bar * 3.65 + offset + 0.19, 2.2, midi, 0.032)
    elif profile == "rhythmic":
        for beat in range(51):
            when = beat * 0.49
            chord = chord_progression[(beat // 4) % 4]
            note(when, 0.24, 32, 0.32, "kick")
            note(when + 0.245, 0.115, 99, 0.14, "tick")
            note(when + 0.06, 0.31, chord[beat % 3] + (12 if beat % 2 else 0), 0.20)
            if beat % 2:
                note(when, 0.15, 84, 0.17, "tick")
    else:
        for beat in range(13):
            note(beat * 0.43, 0.44, (36, 42, 37, 47)[beat % 4], 0.23, "kick")
            note(beat * 0.43 + 0.14, 0.18, 85, 0.11, "tick")
        for start, midi in ((5.6, 48), (5.91, 55), (6.28, 64), (7.14, 67)):
            note(start, 3.9, midi, 0.16)

    pcm = array("h", (int(max(-1, min(1, value)) * 30_000) for value in samples))
    if sys.byteorder != "little":
        pcm.byteswap()
    output = BytesIO()
    with wave.open(output, "wb") as wav:
        wav.setparams((1, 2, SAMPLE_RATE, 0, "NONE", "not compressed"))
        wav.writeframes(pcm.tobytes())
    return output.getvalue()
