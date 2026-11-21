from colorsys import hls_to_rgb, rgb_to_hls
from math import dist

from PIL import Image, ImageOps

INK = "#201d2b"
PAPER = "#f8f0dc"
NEUTRAL_PALETTE = {"field": "#baa3f8", "shadow": "#2c2440", "accent": "#daef67"}


def linear(value: float) -> float:
    return value / 12.92 if value <= .04045 else ((value + .055) / 1.055) ** 2.4


def perceptual(rgb):
    r, g, b = (linear(value / 255) for value in rgb)
    l = (.412221 * r + .536333 * g + .051446 * b) ** (1/3)
    m = (.211903 * r + .680700 * g + .107397 * b) ** (1/3)
    s = (.088302 * r + .281719 * g + .629979 * b) ** (1/3)
    return (.210454*l + .793618*m - .004072*s,
            1.977998*l - 2.428592*m + .450594*s,
            .025904*l + .782772*m - .808676*s)


def color(rgb) -> str:
    return "#" + "".join(f"{round(channel):02x}" for channel in rgb)


def luminance(hex_color: str) -> float:
    channels = (linear(int(hex_color[i:i+2], 16)/255) for i in (1, 3, 5))
    return sum(coefficient * channel for coefficient, channel in zip((.2126, .7152, .0722), channels))


def foreground(background: str) -> str:
    light = luminance(background) + .05
    def contrast(candidate):
        value = luminance(candidate) + .05
        return max(value, light) / min(value, light)
    preferred = max((INK, PAPER), key=contrast)
    return preferred if contrast(preferred) >= 4.5 else max(("#000000", "#ffffff"), key=contrast)


def photo_palette(media, day_id: str, photos: list[dict], main_photo: str) -> dict:
    candidates = []
    main_aspect = 1.0
    main_light = 0.5
    for photo in photos:
        with Image.open(media.path(day_id, photo["id"])) as source:
            thumbnail = ImageOps.contain(ImageOps.exif_transpose(source).convert("RGB"), (72, 72))
        if photo["id"] == main_photo:
            main_aspect = thumbnail.width / thumbnail.height
            main_light = sum(thumbnail.convert("L").tobytes()) / (255 * thumbnail.width * thumbnail.height)
        indexed = thumbnail.quantize(colors=12)
        swatches = indexed.getpalette()
        indexes = indexed.tobytes()
        width, height = thumbnail.size
        details = [0] * 12
        for index, value in enumerate(indexes):
            if index % width and indexes[index - 1] != value:
                details[value] += 1
            if index >= width and indexes[index - width] != value:
                details[value] += 1
        weight = .62 if photo["id"] == main_photo else .38 / max(1, len(photos) - 1)
        for count, index in indexed.getcolors():
            rgb = swatches[index*3:index*3+3]
            lab = perceptual(rgb)
            candidates.append((rgb, lab, count/(width*height)*weight, details[index]/max(1,count),
                               photo["id"] == main_photo))

    usable = [item for item in candidates if .23 < item[1][0] < .94 and dist(item[1][1:], (0, 0)) >= .031]
    if not usable:
        roles = dict(NEUTRAL_PALETTE)
        source = "curated"
    else:
        def support(sample):
            return sum(weight for _, lab, weight, _, _ in usable if dist(sample, lab) < .12)

        field = max(usable, key=lambda item: support(item[1]) + .22 * item[4] + .25 * item[2])
        h, light, saturation = rgb_to_hls(*(channel/255 for channel in field[0]))
        field_hex = color(channel * 255 for channel in hls_to_rgb(h, min(.78, max(.49, light + .12)),
                                                               min(.90, max(.47, saturation * 1.22))))
        accent = max(usable, key=lambda item: (dist(item[1], field[1]) * .40
                     + dist(item[1][1:], (0, 0)) * 1.25 + .08 * min(1, item[3]) + .16 * item[2] ** .5))
        ah, al, saturation = rgb_to_hls(*(channel/255 for channel in accent[0]))
        if dist(accent[1], field[1]) < .075:
            ah = (h + .36) % 1
        accent_hex = color(channel * 255 for channel in hls_to_rgb(ah, min(.83, max(.58, al)),
                                                                 min(.9, max(.51, saturation))))
        shadow = color(channel * 255 for channel in hls_to_rgb(h, .16, .32))
        roles = {"field": field_hex, "shadow": shadow, "accent": accent_hex}
        source = "photo"
    return {**roles, "foreground": foreground(roles["field"]), "accentInk": foreground(roles["accent"]),
            "mainAspect": round(main_aspect, 2), "mainLight": round(main_light, 3),
            "ink": PAPER, "background": roles["shadow"], "source": source, "mainPhoto": main_photo}
