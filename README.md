# После дня · After the Day

A private Telegram film journal for the Genesis Hackathon ArtTech case. Record a day in the bot, then open the Mini App to play the memory or return to the story, photographs, and song.

## First-time setup

Run from the repository root with Python 3.11 or newer.

```sh
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
[ -e .env ] || cp .env.example .env
```

Leave the Telegram settings blank to explore the three fictional days. Run this command for everyday use with the virtual environment active.

```sh
python main.py
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000) to see the demo. The process applies the database migration and builds the examples on the first start. Press Ctrl+C to stop it.

## Telegram and deployment

Set `BOT_TOKEN` to the token from BotFather and `WEBAPP_URL` to the public HTTPS origin that forwards to this process, for example `https://journal.example.com`. Both are needed to activate Telegram mode. For a private chat, open the bot and send `/start`. The process registers the archive menu button and runs polling alongside FastAPI.

Run one process per bot token and mount `DATA_DIR` on persistent storage. End HTTPS at a reverse proxy or tunnel and route the full origin to the application's `HOST` and `PORT`. Use loopback for a proxy on the same host, or bind to `0.0.0.0` when the hosting platform requires it. Keep the bot token in the server environment. With `AUTO_MIGRATE=false`, run `python -m alembic upgrade head` in the configured environment before starting the private service.

When either Telegram setting is absent, startup names the missing settings and runs the demo. `DEMO_MODE=true` selects the fictional diary even when both Telegram settings are present. Demo and private modes use separate data directories and should use different ports for simultaneous local runs. The demo is a shared fictional diary for anyone who can reach its origin. Use `DEMO_MODE=true PORT=8001 python main.py` to preview the fictional diary separately while keeping your existing Telegram configuration.

The diary’s **Записать день** action opens the bot’s `/start record` deep link. The app detects the bot username at polling startup. `BOT_USERNAME` is an optional startup override. To enable Telegram stickers, set `WELCOME_STICKER_ID` or `FIRST_SAVE_STICKER_ID` to a file ID usable by this bot. The first-save sticker is sent only for a user’s first published memory. [Telegram deep links](https://core.telegram.org/bots/features#deep-linking)

## How recording works

- Each user has one unfinished draft. Selecting **Записать день** while a draft is open resumes that draft. It is saved as material arrives. Send photos or a song early and the bot will ask for the remaining input. A stand-alone song URL in a photo caption is saved as music. Other captions stay with their photos and can also provide the original story. The first story found is used until you explicitly edit it.
- A day accepts 1–10 still JPEG, PNG, or WebP photos of up to 10 MiB each. Telegram photo messages provide Telegram’s version of the photo. Send a photo as a file to preserve its source bytes.
- Send an HTTP(S) link to a specific song or an MP3, AAC/M4A, Opus/Vorbis Ogg, PCM WAV, or FLAC file up to 20 MiB. File metadata and format are inspected. Recognized genre tags can select a motion profile. For other files and for links the bot asks how the music sounds. Links receive syntax checks and open in the provider, where availability and playback depend on the provider. The app plays files inline and supports a starting cue for the scene.
- Optional dates default to the local date when the draft starts, using `APP_TIMEZONE` (Asia/Almaty by default). The user can override that timezone in the bot with `/timezone Europe/Moscow`. The recording date can be edited independently from the creation and publication timestamps. Time labels remain as written. Locations are supplied by the user as text, a venue, or coordinates.
- A saved cover can use its original sticker, color, and image or the user’s choices. Older days use suggestions until customized. Cover overrides are independent of scene frames and can be reset in the editor. The draft's ID becomes the saved day's ID. The app publishes a day after generating the scene and checking its media. Retrying the same save opens the same day. The Mini App can regenerate a scene from a pinned phrase or a favorite photo.
- SQLite and uploaded files live under `DATA_DIR/private`; back up that whole directory as one unit with the app stopped. Demo data lives under `DATA_DIR/demo`. An interrupted write can leave unreferenced bytes in a day directory. The API only serves media referenced by a published day belonging to the signed-in Telegram user.
- The session starts with Telegram init data up to 10 minutes old and lasts 8 hours in the open page. On expiry, reopen the Mini App from the bot. Media requests use the same authenticated session, and streaming links never pass through a backend fetch. [Telegram Mini Apps documentation](https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app)

## Change the prototype

| Change | Where |
| --- | --- |
| Bot wording | `app/bot/copy.py` and draft status phrases in `app/bot/summaries.py` |
| Mini App wording | `web/scripts/copy.js` and the shell in `web/index.html` |
| Scene rules and track interpretation | `app/services/scene.py` and `app/services/music.py` |
| Palette and appearance | `web/styles/tokens.css`, `web/art/catalog.json`, and `web/styles/cover.css` |
| Sticker rules and original artwork | `web/art/catalog.json` and `web/art/stickers/` |
| Animation timing and transitions | `web/styles/tokens.css`, `web/styles/motion.css`, `web/scripts/motion.js`, and `app/services/scene.py` |
| Archive, editor, and player | `web/scripts/archive.js`, `web/scripts/folder.js`, `web/scripts/sheet.js`, and `web/scripts/player.js` |
| Storage and migration | `app/infrastructure/db/`, `app/infrastructure/media/`, and `migrations/` |
| Deployment and defaults | `.env.example`, `config/settings.py`, and `main.py` |
| Fictional days and original scores | `demo/seed.py`, `demo/photos/`, and `demo/score.py` |

See [the product and media notes](docs/product.md) and [the three-minute demonstration script](docs/demo.md).
