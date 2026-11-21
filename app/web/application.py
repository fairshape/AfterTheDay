import asyncio
from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.services.diary import Diary
from app.web.routes.demo import router as demo_router
from app.web.routes.remix import router as remix_router
from app.web.routes.library import router as library_router
from app.web.routes.capture import router as capture_router
from app.web.routes.films import router as films_router
from app.web.routes.collection import router as collection_router
from app.bot.anniversaries import dispatch
from app.web.auth import TelegramAuth
from app.web.routes.diary import NO_CACHE, router
from config.settings import ROOT, Settings

logger = logging.getLogger(__name__)
CSP = (
    "default-src 'none'; script-src 'self' https://telegram.org; style-src 'self'; "
    "img-src 'self' blob:; media-src 'self' blob:; font-src 'self'; connect-src 'self'; "
    "base-uri 'none'; form-action 'none'"
)


def create_app(settings: Settings, diary: Diary) -> FastAPI:
    @asynccontextmanager
    async def lifespan(application: FastAPI):
        task = None
        reminders = None
        notification_bot = None
        shutdown = asyncio.Event()
        if settings.private_enabled:
            from aiogram import Bot
            from app.bot.polling import poll
            from app.bot.publication import notify_publication

            notification_bot = Bot(settings.bot_token.get_secret_value())

            reminders = asyncio.create_task(dispatch(notification_bot, diary, settings))

            if settings.assembly_sticker_id:
                async def assembly(owner):
                    from aiogram.exceptions import TelegramAPIError
                    try:
                        await asyncio.wait_for(notification_bot.send_sticker(owner, settings.assembly_sticker_id), timeout=4)
                    except (TelegramAPIError, TimeoutError):
                        logger.info("Optional assembly sticker unavailable")
                application.state.notify_assembly = assembly

            async def notify(day):
                sticker_id = settings.first_save_sticker_id
                if sticker_id and await asyncio.to_thread(diary.first_saved_id, day.owner_id) != day.id:
                    sticker_id = ""
                try:
                    await asyncio.wait_for(notify_publication(notification_bot, settings.webapp_url, day, sticker_id),
                                           timeout=4)
                except TimeoutError:
                    logger.warning("Telegram publication notification timed out")

            application.state.notify_publication = notify

            def publish_username(username: str | None) -> None:
                if username:
                    application.state.bot_username = username

            task = asyncio.create_task(poll(settings, diary, shutdown, publish_username))

            def report_polling_failure(finished: asyncio.Task):
                if not finished.cancelled() and (error := finished.exception()):
                    logger.error("Telegram polling stopped (%s). Check BOT_TOKEN, network access, and other pollers.",
                                 type(error).__name__)

            task.add_done_callback(report_polling_failure)
        try:
            yield
        finally:
            if task:
                shutdown.set()
                _, pending = await asyncio.wait({task}, timeout=12)
                for worker in pending:
                    worker.cancel()
                await asyncio.gather(task, return_exceptions=True)
            if reminders:
                reminders.cancel()
                await asyncio.gather(reminders, return_exceptions=True)
            if notification_bot:
                await notification_bot.session.close()

    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
    app.state.diary = diary
    app.state.bot_username = settings.bot_username or None
    app.state.auth = TelegramAuth(settings.bot_token.get_secret_value()) if settings.private_enabled else None
    app.include_router(router)
    app.include_router(demo_router)
    app.include_router(films_router)
    app.include_router(capture_router)
    app.include_router(library_router)
    app.include_router(remix_router)
    app.include_router(collection_router)
    web = ROOT / "web"
    app.mount("/styles", StaticFiles(directory=web / "styles"), name="styles")
    app.mount("/scripts", StaticFiles(directory=web / "scripts"), name="scripts")
    app.mount("/art", StaticFiles(directory=web / "art"), name="art")
    app.mount("/fonts", StaticFiles(directory=web / "fonts"), name="fonts")

    @app.middleware("http")
    async def set_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        if request.url.path.startswith("/api/") or request.url.path == "/":
            response.headers.update(NO_CACHE)
        return response

    @app.exception_handler(RequestValidationError)
    async def invalid_request(_request: Request, _error: RequestValidationError):
        return JSONResponse({"detail": "invalid_request"}, status_code=422)

    @app.get("/")
    def index():
        return FileResponse(web / "index.html", headers={"Content-Security-Policy": CSP})

    return app
