import asyncio
from collections.abc import Callable

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import SimpleEventIsolation
from aiogram.types import BotCommand, MenuButtonWebApp, WebAppInfo

from app.bot.copy import COMMANDS
from app.bot.handlers import draft, materials, songs, start
from app.bot.handlers.materials import AlbumReplies
from app.infrastructure.catalogue.itunes import ITunesCatalogue
from app.services.diary import Diary
from app.services.song_search import SongSearch
from config.settings import Settings


async def poll(settings: Settings, diary: Diary, shutdown: asyncio.Event,
               publish_username: Callable[[str | None], None]) -> None:
    dispatcher = Dispatcher(events_isolation=SimpleEventIsolation())
    albums = AlbumReplies()
    dispatcher.include_routers(start.router, draft.router, songs.router, materials.router)
    ready = asyncio.Event()

    async def signal_ready() -> None:
        ready.set()

    async def stop_when_requested() -> None:
        await shutdown.wait()
        await ready.wait()
        await dispatcher.stop_polling()

    dispatcher.startup.register(signal_ready)
    async with Bot(settings.bot_token.get_secret_value()) as bot:
        stopper = None
        try:
            publish_username((await bot.me()).username)
            await bot.set_my_commands([
                BotCommand(command=command, description=description)
                for command, description in COMMANDS.items()
            ])
            await bot.set_chat_menu_button(menu_button=MenuButtonWebApp(
                text="Дневник", web_app=WebAppInfo(url=f"{settings.webapp_url}/"),
            ))
            stopper = asyncio.create_task(stop_when_requested())
            await dispatcher.start_polling(bot, handle_signals=False, close_bot_session=False,
                                           tasks_shutdown_timeout=8,
                                           allowed_updates=dispatcher.resolve_used_update_types(),
                                           diary=diary, settings=settings, albums=albums,
                                           song_search=SongSearch(ITunesCatalogue(settings.music_storefront, settings.catalogue_timeout)))
        finally:
            if stopper:
                stopper.cancel()
                await asyncio.gather(stopper, return_exceptions=True)
            await albums.close()
