from functools import lru_cache
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageOps


@lru_cache(maxsize=128)
def photo_preview(path: Path, modified_ns: int) -> bytes:
    with Image.open(path) as image:
        image.draft("RGB", (768, 768))
        preview = ImageOps.exif_transpose(image)
        preview.thumbnail((768, 768), Image.Resampling.LANCZOS)
        output = BytesIO()
        preview.convert("RGB").save(output, "WEBP", quality=76)
        return output.getvalue()
