# Memory Experience · После дня

Memory Experience is a private photographic diary for Telegram and the browser. Capture a story, photographs and a song. Open the resulting print on **Мой стол**, read the note and choose **Пережить день** to play the saved Day Replay. Find a published day in **Архив эмоций**, or assemble several days into a private **Life Replay**.

## Run the browser demo

Use Python 3.11 or newer. Run these commands from the repository root. The demo supplies six fictional entries and stores its edits in a separate library.

```sh
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
[ -e .env ] || cp .env.example .env
DEMO_MODE=true python main.py
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000). Swipe the table or use its arrows to see both spreads. Find **Осенний парк и какао** in the archive to compare the original edit, an evenly timed version of the same excerpt, and a second soundtrack. The [three-minute demonstration](docs/demo.md) includes the complete capture and replay sequence.

FastAPI serves the interface and native JavaScript modules from the same origin. To run the demo next to an active bot, choose a different port with `DEMO_MODE=true PORT=8001 python main.py`. Reopen the same browser profile to keep access to its demo library. Each separate browser session with no existing demo cookie gets its own editable copy on initialization.

## Run the Telegram bot

1. Set `BOT_TOKEN` in `.env` to the token from BotFather. Use `WEBAPP_URL` for the public HTTPS origin of this installation and set `DEMO_MODE=false`.
2. Forward that origin to Uvicorn with an HTTPS reverse proxy or tunnel. Forward the full origin, including `/api`, `/scripts`, `/styles` and `/art`. The default upstream is `http://127.0.0.1:8000` on the host running the app.
3. With the virtual environment active, run `python main.py`. The process serves the app, registers the Telegram diary menu, polls for messages and sends scheduled reminders. Run one polling instance per bot token.
4. Open a private chat with the bot, send `/start` and choose **Записать день**. Send a story, at least one photograph and a track link or audio file. Choose **Собрать воспоминание** to open the preview, then **Сохранить день**. Use the bot's **Открыть день** button to reopen the published entry.

If either Telegram setting is missing, startup reports it and opens the browser demo. If a tunnel changes address, update `WEBAPP_URL`, restart the service and request new buttons with `/start`. Open the private library from Telegram so the Mini App receives signed launch data.

### Troubleshooting

| Symptom | Check |
| --- | --- |
| `ModuleNotFoundError: No module named 'uvicorn'` | Activate `.venv` and install the requirements with the same Python interpreter that runs `main.py`. |
| Port already in use | For the demo, use another port. For private mode, stop the previous instance or point HTTPS at the intentional bind port. |
| Telegram Mini App fails to open | Verify that `WEBAPP_URL` is the current HTTPS origin, the tunnel forwards requests and the button was issued with the current address. |
| Music link opens outside the diary | That is the linked-track flow. Upload an audio file for playback and waveform-based editing inside the scene. |
| Voice generation is unavailable | Check that the model files and their configuration files are in the configured voice directory. |

## Inputs and optional audio tools

| Input | Accepted values |
| --- | --- |
| Story | Up to 12,000 characters. Bot and web studio share the owner's unfinished draft. |
| Photos | One to ten still JPEG, PNG or WebP files, up to 10 MiB and 32 megapixels each. Telegram album photos can carry individual captions. |
| Music | A direct HTTP(S) track link or an MP3, AAC in MP4/M4A, Ogg Opus/Vorbis, FLAC or PCM WAV file up to 20 MiB. |
| Event details | Date, time, place or a label for a shared location, weather, mood and a detail to highlight. Availability depends on the capture screen or bot step. |

Install FFmpeg on the host for waveform analysis and music–voice mixing. When waveform analysis is unavailable, shot timing follows the track character. Optional local Piper narration uses the Irina and Denis models. Install them from the project environment:

```sh
mkdir -p var/voices
python -m piper.download_voices --download-dir var/voices ru_RU-irina-medium ru_RU-denis-medium
```

## Configuration and storage

| Setting | Effect |
| --- | --- |
| `BOT_TOKEN`, `WEBAPP_URL`, `DEMO_MODE` | A token and a public HTTPS origin enable private mode unless demo mode is forced. |
| `HOST`, `PORT` | Uvicorn bind, default `127.0.0.1:8000`. |
| `DATA_DIR`, `AUTO_MIGRATE` | Default root is `var`. With automatic migration disabled, upgrade the private database with `python -m alembic upgrade head` in its configured environment before startup. Demo startup always migrates. |
| `APP_TIMEZONE` | Default calendar and anniversary zone, initially `Asia/Almaty`. The user can set their own zone. |
| `BOT_USERNAME` | Initial username for the bot recording link until polling resolves the bot's username. |
| `WELCOME_STICKER_ID`, `ASSEMBLY_STICKER_ID`, `FIRST_SAVE_STICKER_ID`, `ANNIVERSARY_STICKER_ID` | Optional Telegram sticker file IDs for chat events. |
| `VOICE_DIRECTORY`, `VOICE_ONE_MODEL`, `VOICE_TWO_MODEL`, `SPEECH_TIMEOUT` | Directory, two Piper model names and synthesis timeout. |

Keep `DATA_DIR/private` on persistent storage. Back up the whole directory with the service stopped, including SQLite and `media/<day-id>/`. The demo uses `DATA_DIR/demo`. Keep credentials in the local environment. See the [configuration template](.env.example) and [validation rules](config/settings.py).

## Project documentation

- Runtime, data model, authentication, API, audio and scene assembly. [ARCHITECTURE.md](ARCHITECTURE.md)
- Design system, art direction, assets and credits. [docs/product.md](docs/product.md)
- Rehearsal steps and screen recording sequence. [docs/demo.md](docs/demo.md)
- Reproducible checks and results from prior runs. [IMPLEMENTATION_PROGRESS.md](IMPLEMENTATION_PROGRESS.md)
- Russian submission text, examples and project links. [HACKATHON_SUBMISSION.md](HACKATHON_SUBMISSION.md)
