# Memory Experience · После дня

A private Telegram film journal for the Genesis Hackathon ArtTech case. Record a day in the bot or browser studio. Play a single Day Replay, find it in an emotional collection, or combine several days into a private Life Replay.

## First-time setup

Run from the repository root with Python 3.11 or newer.

```sh
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
mkdir -p var/voices
python -m piper.download_voices --download-dir var/voices ru_RU-irina-medium ru_RU-denis-medium
[ -e .env ] || cp .env.example .env
```

Install FFmpeg and make it available on the server PATH for waveform analysis and voice/music mixing. Leave the Telegram settings blank to explore the six fictional days. Run this command for everyday use with the virtual environment active.

```sh
python main.py
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000) to see the demo. The process applies the database migration and builds the examples on the first start. Press Ctrl+C to stop it.

## Three-minute product walkthrough

1. Open the demo. Play **Осенний парк и какао**, **Ночь в офисе перед сдачей**, and **Смех на кухне**. Compare the last still frame and the captions against the original stories.
2. Open **Архив эмоций**. Select an emotional collection or search for a phrase, use the calendar and return from a day to the same search.
3. Open **Life Replay**. Select a period or add and remove days, adjust a chapter caption, choose a score, and preview. Save the film, reopen it from **Сохранённые фильмы**, and use **Редактировать фильм** to revise it.
4. Use **Создать** to try the complete capture flow. Add text, select photographs, attach an audio file or a song URL, preview the Day Replay and choose **Сохранить день**. The Telegram bot can start or resume the same private draft.

The frontend is served by FastAPI. Native browser modules require no Node installation, bundler or separate server. [Architecture](ARCHITECTURE.md) · [Verification and limitations](IMPLEMENTATION_PROGRESS.md)

## Telegram and deployment

Set `BOT_TOKEN` to the token from BotFather and `WEBAPP_URL` to the public HTTPS origin that forwards to this process, for example `https://journal.example.com`. Both are needed to activate Telegram mode. For a private chat, open the bot and send `/start`. The process registers the archive menu button and runs polling alongside FastAPI.

Run one process per bot token and mount `DATA_DIR` on persistent storage. End HTTPS at a reverse proxy or tunnel and route the full origin to the application's `HOST` and `PORT`. Use loopback for a proxy on the same host, or bind to `0.0.0.0` when the hosting platform requires it. Keep the bot token in the server environment. With `AUTO_MIGRATE=false`, run `python -m alembic upgrade head` in the configured environment before starting the private service.

When either Telegram setting is absent, startup names the missing settings and runs the demo. `DEMO_MODE=true` selects the fictional diary even when both Telegram settings are present. Demo and private modes use separate data directories and should use different ports for simultaneous local runs. Each browser gets a separate demo library with six fictional memories. Keep the browser cookie to revisit edits. Use `DEMO_MODE=true PORT=8001 python main.py` to preview the fictional diary separately while keeping your existing Telegram configuration.

Use **Создать** for the web capture flow or **Записать в Telegram** in the profile for the bot’s `/start record` deep link. The app detects the bot username at polling startup. `BOT_USERNAME` is an optional startup override. To enable Telegram stickers, set `WELCOME_STICKER_ID` or `FIRST_SAVE_STICKER_ID` to a file ID usable by this bot. The first-save sticker is sent only for a user’s first published memory. [Telegram deep links](https://core.telegram.org/bots/features#deep-linking)

## How recording works

- Each user has one unfinished draft. Selecting **Записать день** while a draft is open resumes that draft. It is saved as material arrives. Send photos or a song early and the bot will ask for the remaining input. A stand-alone song URL in a photo caption is saved as music. Other captions stay with their photos. The bot offers to use a caption as the original story when the draft has none.
- A day accepts 1–10 still JPEG, PNG, or WebP photos of up to 10 MiB each. Telegram photo messages provide Telegram’s version of the photo. Send a photo as a file to preserve its source bytes.
- Send an HTTP(S) link to a specific song or an MP3, AAC/M4A, Opus/Vorbis Ogg, PCM WAV, or FLAC file up to 20 MiB. File metadata and format are inspected. A confidently measured pulse can suggest a motion profile. For files with weak signals and for links the bot asks how the music sounds. Links receive syntax checks and open in the provider, where availability and playback depend on the provider. The app plays files inline and supports a starting cue for the scene.
- When the user leaves the event date blank, the diary uses the local creation date for archive placement and the stamp. The default timezone is `APP_TIMEZONE` (Asia/Almaty by default). The user can override that timezone in the bot with `/timezone Europe/Moscow`. The recording date can be edited independently from the creation and publication timestamps. Time labels remain as written. The details menu supports weather presets, custom text, a typed place, and an explicitly shared Telegram pin. A pin stays private, and only its optional readable label appears in the diary. Details can be skipped or cleared independently.
- A saved cover can use its original sticker, color, and image or the user’s choices. Older days use suggestions until customized. Cover overrides are independent of scene frames and can be reset in the editor. The draft's ID becomes the saved day's ID. The app publishes a day after generating the scene and checking its media. Retrying the same save opens the same day. The Mini App can regenerate a scene from a pinned phrase or a favorite photo.
- SQLite and uploaded files live under `DATA_DIR/private`; back up that whole directory as one unit with the app stopped. Demo data lives under `DATA_DIR/demo`. An interrupted write can leave unreferenced bytes in a day directory. Private media handlers serve referenced assets of the owner’s published day or current draft.
- The session starts with Telegram init data up to 10 minutes old and lasts 8 hours in the open page. On expiry, reopen the Mini App from the bot. Media requests use the same authenticated session, and streaming links never pass through a backend fetch. [Telegram Mini Apps documentation](https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app)

## Music attachment and editing

Install FFmpeg on the server PATH for local analysis of uploaded audio. The app starts and plays files without FFmpeg by using track-character pacing. Decoder limits are in `app/infrastructure/audio/analysis.py`. Analysis stays on the server and scans up to 75 seconds from the start or manual cue. It estimates pulse and derives onset and energy-change candidates. These signals guide eligible cuts. A manual start is bounded to leave up to 1.2 seconds of playable audio at the end of a short excerpt. [FFmpeg documentation](https://ffmpeg.org/ffmpeg.html)

A ready draft opens the private Mini App preview through **Собрать воспоминание**. **Сохранить день** publishes its current version and sends a Telegram button for the exact saved memory. In the Mini App, **Настроить монтаж** lets the owner change the main photo, choose a short quote, and test a music start. **Сохранить монтаж** publishes the exact pending version. Older scenes play in their original format. Manual cover colors and stickers take priority over suggestions.

## Narration

**Голос** previews a short line in Irina or Denis at 0.85×, 1.0×, or 1.15×. **Сохранить озвучку** generates the whole story for **Послушать запись** and places up to three shorter lines in the scene based on measured speech duration. For an uploaded track FFmpeg renders one seekable mix with fades around the spoken lines. A linked song opens in its service, and the scene can play the voice on its own. The scene's microphone toggle lets the viewer choose. The generated audio and selected settings persist. If generation fails, the previous saved version stays available. Use **Повторить озвучку** to try again.

Piper runs on the server with local model files. It receives the story through a local process pipe. Only the one-time model installation connects to the model repository. Set `VOICE_DIRECTORY`, `VOICE_ONE_MODEL`, `VOICE_TWO_MODEL` and `SPEECH_TIMEOUT` in the server environment if needed. Existing stories and scenes remain available when models are absent. [Piper Python API](https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/API_PYTHON.md)

## Demo comparisons

**Осенний парк и какао** has two original soundtracks and **Ровный монтаж**, which uses the first track and the same excerpt, text and photos. **Ночь в офисе перед сдачей** shows a fast progression settling on **Отправили**. Existing local demo entries keep their saved versions, and the new examples are added when their seed dates are absent.

## Change the prototype

| Change | Where |
| --- | --- |
| Bot wording | `app/bot/copy.py` and draft status phrases in `app/bot/summaries.py` |
| Mini App wording | `web/scripts/copy.js` and the shell in `web/index.html` |
| Caption progression and shot assembly | `app/services/story.py` and `app/services/scene.py` |
| Photo palette roles and weighting | `app/services/palette.py` |
| Excerpt length and cut timing | `app/services/timing.py` |
| Narration, voice models, and scene mix | `app/services/narration.py`, `app/services/voice_workflow.py`, `app/infrastructure/audio/speech.py`, and `config/settings.py` |
| Audio decode limits and signal analysis | `app/infrastructure/audio/analysis.py` |
| Palette and appearance | `web/styles/cinema.css`, `web/styles/museum.css`, `web/styles/tokens.css`, `web/art/catalog.json`, and `web/styles/cover.css` |
| Sticker rules and original artwork | `web/art/catalog.json` and `web/art/stickers/` |
| Animation timing and transitions | `web/styles/tokens.css`, `web/styles/motion.css`, `web/scripts/motion.js`, and `app/services/scene.py` |
| Life Replay assembly and studio | `app/services/life.py`, `app/services/emotion.py`, `web/scripts/life.js`, `web/scripts/life-player.js` |
| Day Replay studio and camera treatment | `app/services/studio.py`, `web/scripts/studio-controls.js`, `web/scripts/scene-tools.js` |
| Archive, editor, and player | `web/scripts/screens.js`, `web/scripts/folder.js`, `web/scripts/sheet.js`, and `web/scripts/player.js` |
| Storage and migration | `app/infrastructure/db/`, `app/infrastructure/media/`, and `migrations/` |
| Deployment and defaults | `.env.example`, `config/settings.py`, and `main.py` |
| Fictional days and original scores | `demo/seed.py`, `demo/photos/`, and `demo/score.py` |

See [the product and media notes](docs/product.md) and [the three-minute demonstration script](docs/demo.md).

## Photobook and annual reminders

The home tab shows the latest cover and earlier years on today's local date. The journal supports covers, a month calendar, favorites, search, and the intersection of multiple mood tags. The owner can confirm, replace, or clear locally suggested tags. The cover sheet previews the cover, selected main frame, mood tags and voice sample together. A single save applies the changes after scene assembly and speech synthesis succeed. Closing the sheet discards unconfirmed edits. Use the bot's search button or `/find какао` for up to five direct day links.

Reminders are opt-in. Enable an individual anniversary from the save message or day folder. The reminders tab lists upcoming dates and supports changing the local clock, time zone, automatic enrollment of future publications, and notification title visibility. Automatic enrollment defaults off. Notifications default to a generic heading and a private day button. The default clock is 19:00 and the launch timezone is Asia/Almaty. The next occurrence follows the event month and day, falling back to the recording date. February 29 falls on February 28 in a common year.

The private service polls SQLite every 45 seconds. It catches up within 24 hours, skips older occurrences, and records each year separately. The worker claims an occurrence before contacting Telegram. After an ambiguous network result or a crash during sending, it suppresses another send for that year to avoid duplicate messages. Explicit rate limits are rescheduled. The browser demo exercises the same management screens and keeps delivery disabled.

| Responsibility | Files |
| --- | --- |
| Anniversary dates, delivery ledger, and mood rules | `app/services/anniversaries.py`, `app/bot/anniversaries.py` |
| Telegram search and anniversary actions | `app/bot/handlers/collection.py`, `app/bot/copy.py` |
| Optional chat stickers | `WELCOME_STICKER_ID`, `ASSEMBLY_STICKER_ID`, `FIRST_SAVE_STICKER_ID`, `ANNIVERSARY_STICKER_ID` |
| Photobook layout, palette and motion | `web/styles/museum.css`, `web/styles/tokens.css`, `web/styles/motion.css` |
| Home, calendar, filters, favorites, reminders | `web/scripts/screens.js`, `web/scripts/collection.js` |


## Verification

Run the backend regression suite with `python -m unittest discover -s tests -v`. For a browser walkthrough, start the app in demo mode. With the optional Playwright test package and Chromium installed, run `python tests/browser_walkthrough.py --origin http://127.0.0.1:8000`. Use `--chromium /path/to/chromium` for a system installation. The walkthrough makes its own browser library and never writes to the private service.

In **Memory Studio**, open **В монтажную** to change photo order, movement, treatment, captions and target duration. Watch the proposed result before committing it. The order of the original gallery stays intact. **На обложку** in the upload step chooses a cover independently.
