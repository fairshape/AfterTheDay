# Implementation and verification record

Memory Experience implements a private diary with a Memory Table, per-day notes, two interactive film players and a Telegram capture flow. The latest schema revision is `0009_interface_theme`. The results below are from development runs and describe the code under test at the time.

## What ships together

| Capability | Implemented boundary | Evidence |
| --- | --- | --- |
| Capture and publication | The Telegram bot and web studio share one persistent draft per owner. A confirmed preview can publish the day with its original ID. | [Draft and publication service](app/services/diary.py), [editor regressions](tests/test_editor.py) |
| Memory Table and note | Both paper and neon lead from the same table to the note and Day Replay. Theme follows the account. Fixed lighting and spread placement use device storage scoped to the library. | [Two interface materials](docs/interface-themes.jpg), [theme migration test](tests/test_appearance.py) |
| Day Replay and studio | The server saves frames, crops, captions, transitions, audio excerpt and editing decisions. An uncommitted candidate can be discarded while the published edit remains playable. | [Three generated scenes](docs/art-direction-scenes.jpg), [studio and ownership tests](tests/test_memory_experience.py) |
| Emotion Archive and Life Replay | Search, overlapping mood tags, favorites and date views lead to published memories. Selecting two to twenty days can produce a saved film. A saved film protects its source days from deletion. | [Film routes](app/web/routes/films.py), [browser walkthrough](tests/browser_walkthrough.py) |
| Voice and anniversaries | Local models supply optional speech. A delivery ledger tracks individual anniversary occurrences. Private-mode delivery uses Telegram. | [Voice workflow](app/services/voice_workflow.py), [reminder tests](tests/test_anniversaries.py) |

## Recorded development checks

- **Backend and migrations.** Eleven unit tests passed during the two-theme implementation. They cover failed synthesis, stale and foreign writes, protected media, studio and film edits, source-day deletion protection, reminders and the 0008 → 0009 preference migration. The migration test preserves a pre-existing timezone and notification setting while changing themes independently for two accounts.
- **Browser.** Chromium exercised capture with a track link and with an uploaded file, table navigation, archive search, cover editing, scene pause and seek, Life Replay selection, preview, save and reopening. Studio tests included saving a 12-second still-camera edit. The embedded-frame deletion flow exercised both cancellation and confirmation. Theme checks used 360, 390, 430 and 1280 px viewports, a second demo identity, reopening with the original identity and a simulated theme-save failure.
- **Art direction.** In the generated park, office and platform examples, the stored base shot durations were 4.6, 2.45 and 3.0 seconds. These are timing inputs, not the length of every shot. All three edits used measured cues. The platform's camera gain was 0.42, preserving slow movement within the shot while the music drove faster changes between images. [Screenshots](docs/art-direction-scenes.jpg)
- **Telegram integration.** Earlier tests used an aiogram dispatcher and signed test launch data. They exercised a private-chat deep link, text, two photos, a song link, a track-character choice, publication and the button for the saved day. These were transport and application checks. Native iOS and Android interaction remains a device check.
- **Visual history.** The [earlier home](docs/memory-table-before.jpg) and [earlier note](docs/memory-note-before.jpg) document the previous design. Local checkpoint `720f6e6` captured the working wooden table before the introduction of interface themes.

## Reproduce the checks

From an active project environment, run the backend regressions:

```sh
python -m unittest discover -s tests -v
```

For browser QA, install Playwright in the development environment and start the demo in a temporary storage directory. Keep this process open while running the walkthrough.

```sh
python -m pip install playwright
python -m playwright install chromium
qa_data_dir="$(mktemp -d)"
DEMO_MODE=true DATA_DIR="$qa_data_dir" PORT=8001 python main.py
```

In a second terminal with the project environment active, run the walkthrough against that demo. The deletion check modifies its own fictional browser library.

```sh
python tests/browser_walkthrough.py --origin http://127.0.0.1:8001 --disposable-demo
```

The walkthrough also accepts `--chromium` for a system executable and `--screenshots` for an output directory. The native-module frontend is exercised in the browser and has no bundle step. See the [setup and runtime modes](README.md).

## Remaining acceptance work

1. On a physical Telegram client, open the menu and a saved-day button, start sound with a tap, scrub across a caption and return using Telegram's native back action.
2. Open the same Telegram account on a second device and check the theme. Within an enabled anniversary, confirm the local time and notification text in a real chat.
3. Before submission, verify the public entry link and repository access from a judge's device, add team credits and attach the recorded video.

## Current limits

- Day Replay and Life Replay are browser timelines. The prototype has no MP4 export.
- An external song link opens at its provider. Local rhythm analysis needs a supported uploaded file and FFmpeg. Voice requires the configured Piper models.
- The demo caps independent libraries at 250. A browser that loses its cookie gets a new library. A public installation needs an operator decision on retention. [Demo provisioning](app/web/routes/demo.py)
