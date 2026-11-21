import { asset } from "./client.js";
import { captionedImage, dateLabel, element } from "./dom.js";

export let art;
let colors;
let stickers;

export async function loadArt() {
  const response = await fetch("/art/catalog.json");
  if (!response.ok) throw new Error("catalog");
  art = await response.json();
  colors = new Map(art.colors.map((item) => [item.id, item]));
  stickers = new Map(art.stickers.map((item) => [item.id, { ...item, match: new RegExp(`(?:^|[^a-zа-яё])(?:${item.pattern})`, "iu") }]));
}

export function stickerImage(id, className = "") {
  const sticker = stickers.get(id) || stickers.get("spark");
  const img = element("img", className);
  img.src = `/art/stickers/${sticker.id}.svg`;
  img.alt = sticker.label;
  img.width = 120;
  img.height = 122;
  img.draggable = false;
  return img;
}

export function stickerMoment(id, frames) {
  const pattern = stickers.get(id)?.match;
  const specific = pattern ? frames.findIndex((frame) => pattern.test(frame.caption)) : -1;
  if (specific >= 0) return specific;
  const lastCaption = frames.findLastIndex ? frames.findLastIndex((frame) => frame.caption) :
    frames.reduce((last, frame, index) => frame.caption ? index : last, -1);
  return Math.max(0, lastCaption);
}

export function memoryCover(day, variant, { style = day.style, readySrc = "", heading = "h2" } = {}) {
  const palette = style.color === "auto" ? day.coverPalette : null;
  const color = palette ? {id:"auto", hex:palette.field, accent:palette.accent} :
    colors.get(style.color) || colors.get(art.colors[0].id);
  const cover = element("div", `memory-cover cover-${variant}`);
  cover.dataset.tone = color.id;
  cover.classList.toggle("long-title", day.title.length > 42);
  cover.style.setProperty("--cover-tone", color.hex);
  cover.style.setProperty("--cover-accent", color.accent);
  if (palette) {
    cover.style.setProperty("--cover-foreground", palette.foreground);
    cover.style.setProperty("--cover-accent-ink", palette.accentInk);
    cover.style.setProperty("--cover-shadow", palette.shadow);
  }
  const photo = day.photos?.find((item) => item.id === style.photo)?.src || day.cover;
  const composition = element("div", "cover-composition");
  const print = element("div", "cover-print");
  const image = captionedImage(photo, "cover-photo", asset, variant === "hero" ? day.title : "", readySrc);
  print.append(image);
  const stamp = element("time", "cover-stamp", dateLabel(day.date).toLocaleUpperCase("ru"));
  stamp.dateTime = day.date;
  const sticker = stickerImage(style.sticker, "cover-sticker");
  const caption = element("div", "cover-caption");
  caption.append(element(heading, "cover-title", day.title));
  composition.append(print, stamp, sticker);
  cover.append(composition, caption);
  return cover;
}
