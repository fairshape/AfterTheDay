import { element } from "./dom.js";

export let art;
let stickers;

export async function loadArt() {
  const response = await fetch("/art/catalog.json");
  if (!response.ok) throw new Error("catalog");
  art = await response.json();
  stickers = new Map(art.stickers.map((item) => [item.id, { ...item, match: new RegExp(`(?:^|[^a-zа-яё])(?:${item.pattern})`, "iu") }]));
}

export function stickerImage(id, className = "") {
  if (id === "none") return null;
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
