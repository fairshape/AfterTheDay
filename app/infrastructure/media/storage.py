from io import BytesIO
from pathlib import Path
from uuid import uuid4

from PIL import Image

from app.services.music import inspect_audio

PHOTO_LIMIT = 10 * 1024 * 1024
AUDIO_LIMIT = 20 * 1024 * 1024
PHOTO_TYPES = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}


class MediaStore:
    def __init__(self, root: Path):
        self.root = root
        root.mkdir(parents=True, exist_ok=True)

    def ingest(self, day_id: str, data: bytes, kind: str) -> dict:
        if kind == "photo":
            if not data or len(data) > PHOTO_LIMIT:
                raise ValueError("photo_size")
            try:
                with Image.open(BytesIO(data)) as image:
                    mime = PHOTO_TYPES.get(image.format)
                    if not mime or image.width * image.height > 32_000_000 or getattr(image, "is_animated", False):
                        raise ValueError
                    image.verify()
                with Image.open(BytesIO(data)) as image:
                    image.load()
            except (OSError, ValueError, SyntaxError, Image.DecompressionBombError) as exc:
                raise ValueError("photo_format") from exc
            metadata = {"mime": mime}
        else:
            if not data or len(data) > AUDIO_LIMIT:
                raise ValueError("audio_size")
            metadata = inspect_audio(data)

        return self.write(day_id, data, metadata)

    def write(self, day_id: str, data: bytes, metadata: dict, *, generated: bool = False) -> dict:
        asset_id = ("n-" if generated else "") + uuid4().hex
        path = self.path(day_id, asset_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".part")
        try:
            temporary.write_bytes(data)
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)
        return {"id": asset_id, **metadata}

    def path(self, day_id: str, asset_id: str) -> Path:
        return self.root / day_id / asset_id

    def remove(self, day_id: str, asset_id: str) -> None:
        self.path(day_id, asset_id).unlink(missing_ok=True)
