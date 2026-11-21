# Memory Experience · После дня

Memory Experience is a private photographic diary for Telegram and the browser. Record a story, one to ten photographs and a song. Open the print on **Мой стол**, read the note and tap **Пережить день** to play its saved Day Replay. **Life Replay** edits several published days into a longer film. The browser demo supplies six fictional days.

## First run

Use Python 3.11+ from the repository root. Install FFmpeg on the host for local audio analysis and voice mixing. The following setup preserves an existing environment file. The last two commands install the local Russian voices and can be deferred for a silent or music-only demonstration.

```sh
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
[ -e .env ] || cp .env.example .env
mkdir -p var/voices
python -m piper.download_voices --download-dir var/voices ru_RU-irina-medium ru_RU-denis-medium
```

With the virtual environment active, the everyday command is:

```sh
python main.py
```

Open the [local application](http://127.0.0.1:8000). With the example configuration the first launch migrates a demo database and seeds the examples. FastAPI serves the HTML, fonts and JavaScript modules. There is no frontend build step. Stop a foreground launch with Ctrl+C.

## Connect Telegram

1. Set `BOT_TOKEN` in `.env` to the token from BotFather. Set `WEBAPP_URL` to the public **HTTPS origin** forwarding to the web process. A reverse proxy or tunnel must forward both the UI and `/api` on that origin. A loopback address on a phone points to the phone itself.
2. Use `DEMO_MODE=false` and restart the process after changing the configuration. Run one polling instance per token. The bot registers its diary menu button at startup. If a temporary tunnel changes address, update the origin, restart and request fresh buttons with `/start`.
3. Open the private chat, send `/start` and choose **Записать день**. Send text, photographs and a music file or track link. Open the preview, save and follow **Открыть день**. In private mode the Mini App uses Telegram's signed launch data.
4. For a separate local demonstration alongside the private service, use `DEMO_MODE=true PORT=8001 python main.py` and open [the demo on port 8001](http://127.0.0.1:8001).

If either Telegram setting is absent the service reports the missing configuration and starts in demo mode. Each demo browser library is identified by a cookie. Reuse the same browser profile to see its changes.

## Configuration and storage

| Setting | Effect |
| --- | --- |
| `HOST`, `PORT` | Uvicorn bind address, default `127.0.0.1:8000`. |
| `DATA_DIR`, `AUTO_MIGRATE` | Default storage root is `var`. Private startup normally upgrades the database. If automatic migration is disabled, use `python -m alembic upgrade head` with the same private configuration first. Demo startup always migrates. |
| `APP_TIMEZONE` | Default event date and anniversary zone, initially `Asia/Almaty`. A user can change their zone. |
| `BOT_USERNAME` | Optional username for bot deep links until polling resolves the bot's username. |
| `WELCOME_STICKER_ID`, `ASSEMBLY_STICKER_ID`, `FIRST_SAVE_STICKER_ID`, `ANNIVERSARY_STICKER_ID` | Optional Telegram sticker file IDs for the corresponding chat events. |
| `VOICE_DIRECTORY`, `VOICE_ONE_MODEL`, `VOICE_TWO_MODEL`, `SPEECH_TIMEOUT` | Local Piper model directory, two model names and synthesis timeout. |

On a persistent volume, keep the entire `DATA_DIR/private` directory together. It contains `diary.sqlite3` and `media/<day-id>/<asset-id>`. Stop the process for a filesystem backup and copy both. The demo uses the parallel `DATA_DIR/demo` tree. The environment template and validation logic are in [the example configuration](.env.example) and [Settings](config/settings.py).

## Where to work

| Task | Entry point |
| --- | --- |
| Follow a draft from Telegram through publication | [Bot handlers](app/bot/handlers/) and [Diary](app/services/diary.py) |
| Change how words, photos and music become shots | [Scene assembly](app/services/scene.py), [palette](app/services/palette.py), [editing timeline](app/services/timing.py) |
| Change the table, note or interface themes | [Print composition](web/scripts/memory-table.js), [table materials](web/styles/table.css), [theme tokens](web/styles/themes.css) |
| Change stickers, bot text or controls | [Sticker catalog](web/art/catalog.json), [bot copy](app/bot/copy.py), [keyboards](app/bot/keyboards.py) |
| Edit a cross-day film or its player | [Film assembler](app/services/life.py), [film studio](web/scripts/life.js), [film player](web/scripts/life-player.js) |

**Read next.** Follow data, identity and requests in the [architecture](ARCHITECTURE.md). See the [product and asset credits](docs/product.md), [three-minute demo](docs/demo.md), [verification record](IMPLEMENTATION_PROGRESS.md) and [Russian hackathon submission](HACKATHON_SUBMISSION.md).
