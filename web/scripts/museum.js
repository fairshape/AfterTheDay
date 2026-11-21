import {art,stickerImage} from "./art.js";
import {memoryShelf, previewPhoto} from "./memory-shelf.js";
import {asset} from "./client.js";
import {captionedImage, dateLabel, element as el} from "./dom.js";

export function link(label, href, cls = "ink-link") {
  const node = el("a", cls, label);
  node.href = href;
  return node;
}
export const dayURL = id => "/?day=" + encodeURIComponent(id);
export function heading(label, mark = "") {
  const row = el("div", "section-title");
  row.append(el("h2", "", label));
  if (mark)
    row.append(el("span", "mono", mark));
  return row;
}
export const worlds = {
  bright: ["Светлые", "#ffcb65"],
  pleasant: ["Тёплые", "#acbd8a"],
  tense: ["Напряжённые", "#b09acc"],
  funny: ["Смешные", "#ff977d"],
  sad: ["Грустные", "#a6bdcf"]
};
export function memoryTile(day) {
  const a = link("", dayURL(day.id) + "&from=gallery", "museum-tile");
  a.dataset.memory = day.id;
  const photo = captionedImage(previewPhoto(day.cover), "tile-image", asset, day.title);
  photo.querySelector("img").dataset.original = day.cover;
  const tag = day.emotion?.primary;
  if (tag) {
    const label = el("span", "film-tag", worlds[tag][0]);
    label.style.backgroundColor = worlds[tag][1];
    photo.append(label);
  }
  const styleColor=art.colors.find(color=>color.id===day.style.color);
  a.style.setProperty("--tile-accent",styleColor?.hex||day.coverPalette?.field||day.emotion?.accent||"var(--line)");
  const sticker=stickerImage(day.style.sticker,"catalog-sticker");if(sticker)photo.append(sticker);
  a.append(
      photo, el("small", "mono", dateLabel(day.date, true)), el("h3", "", day.title),
      el("p", "tile-info", day.trackLabel || "Day Replay"));
  return a;
}
export function dashboard(days, context, warmDay) {
  const root = el("div", "gallery-home");
  if (days.length) {
    root.append(memoryShelf(days, warmDay));
  } else {
    const empty = el("section", "shelf-empty");
    empty.append(el("h1", "", "Твоя первая история"),
      el("p", "", "Сохрани слова, фото и музыку своего дня."),
      link("Создать запись", "/?view=create", "accent-link"),
      link("Как устроен дневник", "/?view=welcome"));
    root.append(empty);
  }
  const lower = el("div", "museum-lower");
  const life = link("", "/?view=life", "life-poster");
  life.append(
      el("span", "mono", "LIFE REPLAY"), el("h2", "", "Собрать фильм"),
      el("span", "poster-arrow", "↗"));
  lower.append(life);
  const bands = el("section", "world-links");
  bands.append(heading("По эмоциям"));
  for (const [key, [name, color]] of Object.entries(worlds)) {
    const a = link(name, "/?view=archive&world=" + key, "world-link");
    a.style.setProperty("--world", color);
    bands.append(a);
  }
  lower.append(bands);
  root.append(lower);
  const tools = el("div", "actions");
  tools.append(
      link("Открыть Memory Studio ↗", "/?view=studio", "minor"),
      link("Календарь", "/?view=archive&calendar=1", "minor"));
  if (context.draft)
    tools.prepend(link("Продолжить черновик", "/?view=create", "solid-btn"));
  root.append(tools);
  if (context.anniversaries.length) {
    root.append(heading("В этот день"));
    for (const d of context.anniversaries) root.append(memoryTile(d));
  }
  return root;
}
