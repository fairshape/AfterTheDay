import {art, stickerImage} from "./art.js";
import {asset} from "./client.js";
import {button, captionedImage, dateLabel, element as el} from "./dom.js";

export const previewPhoto = url => url + "?preview=1";
function anchor(text, href, css) {
  const node = el("a", css, text);
  node.href = href;
  return node;
}

export function paperNote(day, current = false, readySrc = "") {
  const style = day.style || {};
  const note = el(current ? "article" : "a", current ? "open-note" : "map-piece");
  if (!current) {
    note.href = "/?day=" + encodeURIComponent(day.id) + "&from=gallery";
    note.setAttribute("aria-label", "Открыть заметку «" + day.title + "»");
  }
  note.dataset.family = day.emotion.family || "journal";
  note.dataset.layout = day.emotion.layout || (day.photoCount > 2 ? "spread" : "portrait");
  note.style.setProperty("--paper-accent", art.colors.find(c => c.id === style.color)?.hex || day.coverPalette?.field || "#98886d");
  const print = el("div", "mounted-print");
  const main = captionedImage(previewPhoto(day.cover), "paper-photo cover-photo", asset, day.title, readySrc);
  main.querySelector("img").dataset.original = day.cover;
  print.append(main);
  const alternate = day.stills?.find(path => path !== day.cover);
  if (alternate && (current || note.dataset.family === "collage")) {
    print.append(captionedImage(previewPhoto(alternate), "loose-print", asset, ""));
  }
  const text = el("div", "paper-writing");
  const stamp = el("time", "paper-date", dateLabel(day.date, true));
  stamp.dateTime = day.date;
  text.append(stamp, el(current ? "h1" : "h2", "", day.title));
  if (day.opening && day.opening !== day.title && day.opening !== day.focus) text.append(el("p", "paper-opening", day.opening));
  if (day.focus) text.append(el("p", "paper-phrase", "«" + day.focus + "»"));
  if (current && day.trackLabel) text.append(el("small","paper-track","♫  " + day.trackLabel));
  const sticker = stickerImage(style.sticker, "paper-sticker");
  if (sticker) print.append(sticker);
  note.append(print, text);
  return note;
}

export function memoryTable(days, context, warmDay) {
  const world = el("section", "memory-world");
  const toolbar = el("header", "table-heading");
  toolbar.append(el("h1", "", "Мой стол"), anchor("Календарь ↗", "/?view=archive&calendar=1", "table-link"));
  world.append(toolbar);
  const board = el("div", "table-surface");
  const scene = el("div", "table-objects");
  board.append(scene);
  world.append(board);
  if (!days.length) {
    const blank = el("div", "blank-note");
    blank.append(el("h2", "", "Первый лист"), el("p", "", "Какой момент хочется оставить здесь?"),
      anchor("Записать день ↗", "/?view=create", "table-link"));
    scene.append(blank);
  } else {
    // Number spreads from the oldest day so a new entry leaves earlier arrangements intact.
    const key = "memory-table:" + context.worldKey;
    let slots = [];
    try { slots = JSON.parse(localStorage.getItem(key) || "[]"); } catch {}
    if (!Array.isArray(slots)) slots = [];
    const lookup = new Map(days.map(day => [day.id, day]));
    const visible = slots.filter(id => lookup.has(id));
    const known = new Set(visible);
    for (const day of [...days].reverse()) if (!known.has(day.id)) visible.push(day.id);
    try { localStorage.setItem(key, JSON.stringify(visible)); } catch {}
    const chronological = visible.map(id => lookup.get(id));
    const spreads = [];
    for (let index = 0; index < days.length; index += 3) spreads.push(chronological.slice(index,index+3));
    let page = Math.min(history.state?.tablePage ?? spreads.length - 1, spreads.length - 1);
    const previous = button("←", "table-step", () => turn(page - 1));
    const next = button("→", "table-step", () => turn(page + 1));
    previous.setAttribute("aria-label","Предыдущий разворот");
    next.setAttribute("aria-label","Следующий разворот");
    const number = el("span","table-page");
    number.setAttribute("aria-live","polite");
    const pager = el("div", "table-pager");
    pager.append(previous, number, next);
    board.append(pager);
    const lightKey = key + ":light";
    const light = el("select", "table-light");
    light.setAttribute("aria-label","Освещение стола");
    for (const [value,label] of [["auto","Свет по фото"],["warm","Тёплый свет"],["cool","Прохладный свет"],["plain","Естественный свет"]]) light.add(new Option(label,value));
    try { light.value = localStorage.getItem(lightKey) || "auto"; } catch {}
    function illuminate() {
      const warmth = days.slice(0,8).reduce((v,d)=>v+(d.emotion.warmth ?? .5),0)/Math.min(days.length,8);
      board.dataset.light = light.value === "auto" ? (warmth >= .5 ? "warm":"cool") : light.value;
    }
    light.onchange = () => { illuminate(); try {localStorage.setItem(lightKey,light.value);} catch {} };
    illuminate();
    toolbar.append(light);
    function turn(index) {
      if (!spreads[index]) return;
      page = index;
      history.replaceState({...history.state, tablePage:page},"",location.href);
      const entries = spreads[index];
      const pieces = entries.map((day,i) => {
        const piece = paperNote(day);
        piece.dataset.position = ["center","left","right"][i];
        piece.addEventListener("pointerenter",()=>warmDay(day.id), {once:true});
        return piece;
      });
      scene.replaceChildren(...pieces);
      number.textContent = (index+1) + " / " + spreads.length;
      previous.disabled = !index;
      next.disabled = index === spreads.length-1;
    }
    turn(page);
    let start;
    scene.addEventListener("touchstart", e=> {start=e.touches.length===1 ? [e.touches[0].clientX,e.touches[0].clientY] : null;},{passive:true});
    scene.addEventListener("touchend", e=>{
      if (!start) return;
      const dx=e.changedTouches[0].clientX-start[0], dy=e.changedTouches[0].clientY-start[1];
      if (Math.abs(dx)>75 && Math.abs(dx)>2*Math.abs(dy)) turn(page+(dx<0?1:-1));
      start=null;
    },{passive:true});
    board.addEventListener("pointermove",e=>{
      if(e.pointerType!=="mouse" || matchMedia("(prefers-reduced-motion: reduce)").matches) return;
      const rect=board.getBoundingClientRect();
      board.style.setProperty("--depth", ((e.clientX-rect.left)/rect.width*4-2)+"px");
    });
  }
  const links = el("nav", "table-footer");
  links.append(anchor("Лента ↗", "/?view=feed",""), anchor("Архив эмоций ↗","/?view=archive",""),anchor("Монтажная ↗","/?view=studio",""));
  if(context.draft) links.append(anchor("Продолжить черновик ↗","/?view=create",""));
  for(const day of context.anniversaries) links.append(anchor("В этот день · "+day.title,"/?day="+day.id+"&from=gallery",""));
  world.append(links);
  return world;
}
