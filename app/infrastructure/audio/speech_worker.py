"""Run the local speech engine in a time-bounded child process."""
import json
from pathlib import Path
import sys
import wave

from onnxruntime import disable_telemetry_events
from piper import PiperVoice, SynthesisConfig


def main() -> None:
    disable_telemetry_events()
    model, directory = Path(sys.argv[1]), Path(sys.argv[2])
    request = json.load(sys.stdin)
    voice = PiperVoice.load(model)
    config = SynthesisConfig(length_scale=1 / request["rate"], noise_scale=.42, noise_w_scale=.5, volume=.86)
    for index, line in enumerate(request["texts"]):
        with wave.open(str(directory / f"{index}.wav"), "wb") as output:
            voice.synthesize_wav(line, output, syn_config=config)


if __name__ == "__main__":
    main()
