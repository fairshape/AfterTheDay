import {art,stickerImage} from "./art.js";
import {icon} from "./icons.js";
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
  const photo = captionedImage(day.cover, "tile-image", asset, day.title);
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
export function dashboard(days, context, demo) {
  const root = el("div", "gallery-home");
  const intro = el("div", "intro-line");
  intro.append(
      el("span", "mono", demo ? "ДЕМОНСТРАЦИОННАЯ КОЛЛЕКЦИЯ" : "ЛИЧНАЯ КОЛЛЕКЦИЯ"),
      el("span", "mono", String(days.length).padStart(2, "0") + " " + ({one:"ЗАПИСЬ",few:"ЗАПИСИ"}[new Intl.PluralRules("ru").select(days.length)]||"ЗАПИСЕЙ")));
  root.append(intro);
  const hero = el("section", "feature");
  const latest = days[0];
  const still=latest?captionedImage(latest.cover,"feature-photo",asset,latest.title):null;
  if(still)hero.append(still);
  const content = el("div", "feature-copy");
  content.append(
      el("span", "feature-type", "●   DAY REPLAY"),
      el("h1", "", latest?.title || "Твоя первая история"));
  content.append(
      el("p", "feature-meta",
         latest ? dateLabel(latest.date, true) + (latest.place ? "   /   " + latest.place : "") :
                  "Сохрани слова, фото и музыку своего дня."));
  content.append(link(
      latest ? "▶   Пережить день" : "＋   Создать запись",
      latest ? dayURL(latest.id) + "&play=1&from=gallery" : "/?view=create", "accent-link"));
  if(latest?.focus) content.querySelector("h1").after(el("p","hero-quote","«"+latest.focus+"»"));
  if(latest){
    const facts=el("div","hero-facts");
    facts.append(icon("music"),el("span","",latest.trackLabel||"Музыка дня"));
    if(latest.duration)facts.append(el("span","film-runtime",Math.round(latest.duration)+" с"));
    content.append(facts);
    const rail=el("div","still-rail");
    let revision=0;
    const images=[...new Set([latest.cover,...(latest.stills||[])])].slice(0,3);
    if(images.length>1){
      for(const [index,path] of images.entries()){
        const pick=el("button","still-choice");pick.type="button";pick.setAttribute("aria-label","Показать кадр "+(index+1));
        pick.setAttribute("aria-pressed",String(!index));pick.append(captionedImage(path,"still-sample",asset,""));
        pick.onclick=async()=>{
          const mark=++revision,img=still.querySelector("img");if(!img)return;
          try{const src=await asset(path);if(mark!==revision)return;img.src=src;
            for(const btn of rail.children)btn.setAttribute("aria-pressed",String(btn===pick));
          }catch{img.alt="Кадр недоступен.";}
        };rail.append(pick);
      }
      hero.append(rail);
    }
  }
  hero.append(content);
  root.append(hero);
  const section = el("section", "moments");
  const row = heading("Недавние воспоминания");
  row.append(link("Весь архив ↗", "/?view=archive"));
  section.append(row);
  const grid = el("div", "tile-grid");
  (days.length > 3 ? days.slice(1, 4) : days.slice(0, 3)).forEach(d => grid.append(memoryTile(d)));
  section.append(grid);
  if(days.length)root.append(section);
  else root.append(link("Как устроен дневник ↗","/?view=welcome"));
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
