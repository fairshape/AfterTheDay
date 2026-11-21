import {capture} from "./capture.js";
import {api, asset} from "./client.js";
import {calendar, moodPicker} from "./collection.js";
import {button, captionedImage, dateLabel, element as el} from "./dom.js";
import {icon} from "./icons.js";
import {previewPhoto} from "./memory-shelf.js";
import {life} from "./life.js";
import {dayURL, heading, link, memoryTile, worlds} from "./museum.js";

export async function screen(view, {days, context, query}) {
  if (view === "life")
    return life(days, query, context.today);
  if (view === "create")
    return capture();
  if (view === "welcome") {
    const welcome = el("section","welcome-spread"), intro = el("div","welcome-copy");
    intro.append(el("span","mono","MEMORY EXPERIENCE"),el("h1","page-title","У каждого дня есть история"),
      el("p","original-story","Сохрани фразу, снимок и песню. Фотографии зададут свет, музыка — ритм, а твои слова останутся в кадре."),
      link("Начать запись","/?view=create","accent-link"));
    welcome.append(intro);
    if(days[0])welcome.append(captionedImage(previewPhoto(days[0].cover),"welcome-image",asset,days[0].title));
    welcome.append(link("Смотреть дневник","/?view=archive"));return welcome;
  }
  if (view === "studio") {
    const studio=el("section","studio-library");
    studio.append(el("span","mono","МОНТАЖ И ОФОРМЛЕНИЕ"),el("h1","page-title","Memory Studio"),
      link("＋ Новое воспоминание","/?view=create","solid-btn"));
    if(!days.length)studio.append(el("p","notice","После первой записи здесь появятся её обложка и монтаж."));
    for(const day of days){
      const item=el("article","studio-entry"), info=el("div");
      info.append(el("small","mono",dateLabel(day.date,true)),el("h2","",day.title),el("p","tile-info",day.trackLabel));
      item.append(captionedImage(previewPhoto(day.cover),"studio-thumb",asset,day.title),info,link("В монтажную ↗",dayURL(day.id)+"&studio=1&from=gallery","minor"));
      studio.append(item);
    }
    return studio;
  }
  const root = el("section", "exhibition"), grid = el("div", "tile-grid"),
        filters = el("div", "archive-filter"), worldsNav = el("div", "world-tabs");
  const saved = history.state?.archive || {};
  let world = saved.world ?? query.get("world"), favorite = saved.favorite ?? (view === "favorites"),
      oldest = saved.oldest || false, dates = saved.dates ?? query.has("calendar"), request = 0;
  const text = el("input"), month = el("input"), moods = new Set(saved.moods || []);
  text.value = saved.q || "";
  month.value = saved.month || "";
  text.type = "search";text.maxLength=120;
  text.placeholder = "Найти фразу, название или место";
  text.setAttribute("aria-label", "Поиск");
  month.type = "month";
  month.setAttribute("aria-label", "Месяц");
  const title = el("h1", "page-title"), result = el("p", "notice");
  root.append(el("span", "mono", "EMOTION ARCHIVE"), title, worldsNav, filters, result, grid);
  function worldLink(key, label) {
    const b = button(label, "world-tab", () => {
      world = key;
      render();
    });
    b.dataset.world = key || "";
    b.style.setProperty("--world", worlds[key]?.[1] || "#fff");
    worldsNav.append(b);
  }
  worldLink("", "Все");
  Object.entries(worlds).forEach(([k, [label]]) => worldLink(k, label));
  const fav = button("☆ Избранное", "minor", () => {
    favorite = !favorite;
    render();
  }), sort = button("Сначала новые", "minor", () => {
        oldest = !oldest;
        render();
      }), cal = button("Календарь", "minor", () => {
            dates = !dates;
            render();
          });
  const extra = el("details","filter-extra"),options=el("div","filter-options");
  extra.open=Boolean(saved.month||saved.moods?.length||oldest||favorite);
  options.append(month,fav,sort,moodPicker(context.moods,moods,()=>render()),button("Сбросить фильтры","minor",()=>location.assign("/?view=archive")));
  extra.append(el("summary","","Фильтры"),options);filters.append(text,cal,extra);
  const selection = new Set(saved.selection||[]);
  const makeFilm = button("В монтажную","solid-btn",()=>location.assign("/?view=life&days="+[...selection].join(",")));
  const tray = el("div","archive-tray"),selectionStatus=el("span","", "");
  tray.append(selectionStatus,makeFilm,button("Снять выбор","minor",()=>{selection.clear();render();}));root.append(tray);
  function archivePrint(day){
    const print=el("article","archive-print"), tile=memoryTile(day), overlay=el("div","print-actions");
    const play=link("",dayURL(day.id)+"&play=1&from=gallery","print-action");play.setAttribute("aria-label","Пережить день · "+day.title);play.append(icon("play"));
    const add=button("","print-action",()=>{if(selection.has(day.id))selection.delete(day.id);else if(selection.size<20)selection.add(day.id);render();});
    add.append(icon(selection.has(day.id)?"check":"add"));add.setAttribute("aria-pressed",String(selection.has(day.id)));add.setAttribute("aria-label","Выбрать для Life Replay · "+day.title);
    overlay.append(play,add);print.append(tile,overlay);return print;
  }
  let timer;
  text.oninput = () => {
    request++;
    clearTimeout(timer);
    timer = setTimeout(render, 180);
  };
  month.onchange = render;
  async function render() {
    const mark = ++request;
    tray.hidden=!selection.size;makeFilm.disabled=selection.size<2;
    selectionStatus.textContent=selection.size===1?"Выбери ещё один день":"Выбрано дней: "+selection.size;
    history.replaceState(
        {
          ...history.state,
          archive:
              {world, favorite, oldest, dates, moods: [...moods], month: month.value, q: text.value,selection:[...selection]}
        },
        "", location.href);
    title.textContent = worlds[world]?.[0] + " моменты";
    if (!worlds[world])
      title.textContent = view === "studio" ? "Memory Studio" : "Архив эмоций";
    root.dataset.world = world || "";
    root.style.setProperty("--collection-color", worlds[world]?.[1] || "#d9dece");
    for (const b of worldsNav.children)
      b.setAttribute("aria-pressed", String(b.dataset.world === (world || "")));
    fav.setAttribute("aria-pressed", String(favorite));
    sort.textContent = oldest ? "Сначала ранние" : "Сначала новые";
    cal.textContent = dates ? "Обложки" : "Календарь";
    try {
      let items =
          text.value.trim() ? await api("/api/days?q=" + encodeURIComponent(text.value.trim())) : days;
      if (mark !== request)
        return;
      items = items.filter(
          d => (!world || d.emotion.strengths[world]) && (!favorite || d.favorite) &&
              (!month.value || d.date.startsWith(month.value)) &&
              [...moods].every(m => d.moods.includes(m)));
      if (oldest)
        items = [...items].reverse();
      result.textContent = items.length ? "" : "Подходящих записей пока нет.";
      grid.className = dates ? "date-gallery" : "tile-grid";
      grid.replaceChildren(
          ...(dates ? [calendar(items, id => location.assign(dayURL(id) + "&from=gallery"))] :
                      items.map(archivePrint)));
    } catch {
      result.textContent = "Не удалось загрузить архив.";
      result.append(button("Повторить", "minor", render));
    }
  }
  const y = history.state?.scrollY || 0;
  window.addEventListener(
      "pagehide", () => history.replaceState({...history.state, scrollY: scrollY}, "", location.href));
  await render();
  if (y)
    requestAnimationFrame(() => window.scrollTo(0, y));
  return root;
}
