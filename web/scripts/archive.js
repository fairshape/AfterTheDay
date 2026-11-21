import { calendar, moodPicker, reminderCenter } from "./collection.js";
import { memoryCover } from "./art.js";
import { api } from "./client.js";
import { scrapbook as copy, text } from "./copy.js";
import { button, element, monthLabel } from "./dom.js";
import { decorate } from "./icons.js";

export function createArchive({ open, record, toggle, demo }) {
  const page = element("div", "archive-page");
  const introduction = element("header", "archive-intro");
  const title = element("h1", "display", copy.home);
  const count = element("p", "archive-count");
  count.setAttribute("aria-live", "polite");
  introduction.append(title, count);

  const tools = element("section", "archive-tools");
  tools.id = "archive-tools";
  tools.hidden = true;
  const search = element("input");
  search.type = "search";
  search.maxLength = 120;
  search.placeholder = copy.search;
  search.setAttribute("aria-label", copy.search);
  const searchLine = element("div", "search-line");
  searchLine.append(decorate(element("span"), "search"), search);
  const controls = element("div", "filter-line");
  const monthLabelNode = element("label", "filter-month", copy.month);
  const month = element("select");
  monthLabelNode.append(month);
  const reset = button(copy.reset, "text-button", () => {
    search.value = "";
    month.value = "";
    selected.clear(); favorites=false;
    if(info) moodArea.replaceChildren(moodPicker(info.moods,selected,render));
    load();
  });
  controls.append(monthLabelNode, reset);
  tools.append(searchLine, controls);

  const results = element("div", "archive-results");
  const dock = element("div", "record-dock");
  const action = decorate(button("", "record-button", record), "add", copy.record);
  dock.append(action);
  page.append(introduction, tools, results, dock);

  let view = new URL(location.href).searchParams.get("view") || "today";
  let calendarView=false;
  let favorites=view==="favorites";
  const selected=new Set();
  const nav=element("nav","book-tabs");
  nav.setAttribute("aria-label","Разделы дневника");
  const tabButtons=new Map();
  function switchView(next) {
    view=next;
    const url=new URL(location.href);
    url.searchParams.set("view", next);
    history.replaceState(history.state,"",url);
    setTools(next==="search" || next==="favorites");
    if (all) render();
  }
  for (const [key,label] of [["today","Сегодня"],["journal","Дневник"],["reminders","Напоминания"]]) {
    const tab=button(label,"book-tab",()=>switchView(key));
    tabButtons.set(key,tab); nav.append(tab);
  }
  page.prepend(nav);
  const modes=element("div","view-options");
  const gridButton=button("Обложки","view-choice",()=>{calendarView=false;render();});
  const calendarButton=button("Календарь","view-choice",()=>{calendarView=true;render();});
  const starred=button("★ Избранное","view-choice",()=>{favorites=!favorites;render();});
  modes.append(gridButton,calendarButton,starred);
  tools.after(modes);
  const moodArea=element("div"); tools.append(moodArea);
  let info=null;
  const active = () => search.value.trim() !== "" || month.value !== "" || selected.size>0 || favorites;
  let all = null;
  let matches = [];
  let serial = 0;
  let timer;

  function setTools(opened) {
    tools.hidden = !opened;
    toggle.setAttribute("aria-expanded", String(opened));
    if (opened) search.focus({preventScroll:true});
  }

  function setMonths() {
    const value = month.value;
    const empty = element("option", "", copy.allMonths);
    empty.value = "";
    month.replaceChildren(empty);
    for (const key of new Set(all.map((day) => day.date.slice(0, 7)))) {
      const option = element("option", "", monthLabel(`${key}-01`));
      option.value = key;
      month.append(option);
    }
    month.value = Array.from(month.options).some((option) => option.value === value) ? value : "";
  }

  function card(day, featured = false) {
    const link = element("a", `memory-link ${featured ? "latest-link" : ""}`);
    link.dataset.memory = day.id;
    link.href = `/?day=${encodeURIComponent(day.id)}`;
    link.append(memoryCover(day, featured ? "latest" : "tile", {heading:"h3"}));
    link.addEventListener("click", (event) => {
      if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
      event.preventDefault();
      open(day.id, link.querySelector(".cover-photo img"), link);
    });
    return link;
  }

  function render() {
    const home=view==="today";
    const reminders=view==="reminders";
    const tab=home?"today":reminders?"reminders":"journal";
    tabButtons.forEach((node,id)=>node.setAttribute("aria-pressed",String(id===tab)));
    title.textContent=home?"Сегодня":reminders?"Напоминания":"Дневник";
    modes.hidden=home || reminders;
    if(home || reminders) tools.hidden=true;
    count.hidden=reminders;
    if(reminders) {results.replaceChildren(reminderCenter(open,demo));return;}
    starred.setAttribute("aria-pressed",String(favorites));
    calendarButton.setAttribute("aria-pressed",String(calendarView));
    gridButton.setAttribute("aria-pressed",String(!calendarView));
    const days = home ? all : matches.filter(day=>(!month.value || day.date.startsWith(month.value))
      && (!favorites || day.favorite) && [...selected].every(label=>day.moods.includes(label)));
    count.textContent = copy.count(days.length);
    results.replaceChildren();
    if(home && info?.anniversaries.length) {
      const group=element("div","today-anniversaries");
      group.append(element("h2","month-title","В этот день"));
      for(const day of info.anniversaries) group.append(button(day.title,"day-link",()=>open(day.id)));
      results.append(group);
    }
    if(days.length && calendarView && !home) {results.append(calendar(days,open)); return;}
    if (!days.length) {
      const empty = element("div", "empty");
      const filtered = active();
      empty.role = "status";
      empty.append(element("h2", "", month.value ? copy.filteredEmpty : filtered ? text.noResults : text.empty),
        element("p", "", month.value ? copy.filteredHelp : filtered ? text.noResultsHelp : text.emptyHelp));
      if (filtered) empty.append(button(copy.reset, "outline-button", () => reset.click()));
      results.append(empty);
      return;
    }

    let rest = days;
    if (home || !active()) {
      const latest = element("section", "latest");
      latest.append(element("h2", "eyebrow", text.latest), card(days[0], true));
      results.append(latest);
      rest = days.slice(1);
    }
    let lastKey;
    let grid;
    const monthGroups = [];
    for (const day of rest) {
      const key = day.date.slice(0, 7);
      if (key !== lastKey) {
        lastKey = key;
        const group = element("section", "month-group");
        monthGroups.push(group);
        grid = element("div", "memory-grid");
        group.append(element("h2", "month-title", monthLabel(day.date)), grid);
        results.append(group);
      }
      grid.append(card(day));
    }
    for (const group of monthGroups) group.classList.toggle("month-solo", group.querySelector(".memory-grid").childElementCount === 1);
  }

  async function load() {
    clearTimeout(timer);
    const request = ++serial;
    const query = search.value.trim();
    results.setAttribute("aria-busy", "true");
    if (!results.firstChild || !all) {
      const loading = element("p", "page-status", text.loading);
      loading.role = "status";
      results.replaceChildren(loading);
    }
    try {
      if(!info) {
        info=await api("/api/collection");
        moodArea.replaceChildren(moodPicker(info.moods,selected,render));
        if(info.draft) decorate(action,"edit","Продолжить черновик");
      }
      if (!all || !query) {
        const days = await api("/api/days");
        if (request !== serial) return;
        all = days;
        setMonths();
      }
      const days = query ? await api(`/api/days?q=${encodeURIComponent(query)}`) : all;
      if (request !== serial) return;
      matches = days;
      render();
    } catch (error) {
      if (request !== serial) return;
      const auth = error.status === 401;
      results.replaceChildren(element("p", "page-status", auth ? text.login : text.unavailable));
      if (!auth) results.append(button(text.retry, "outline-button", load));
    } finally {
      if (request === serial) results.setAttribute("aria-busy", "false");
    }
  }

  search.addEventListener("input", () => {
    ++serial;
    clearTimeout(timer);
    timer = setTimeout(load, 180);
  });
  month.addEventListener("change", () => { if (all) render(); });
  toggle.addEventListener("click", () => {
    if(view==="today" || view==="reminders") switchView("search");
    else setTools(tools.hidden);
  });
  setTools(view==="search" || view==="favorites");
  load();

  return {
    page,
    refresh: load,
    imageFor(id) { return page.querySelector(`[data-memory="${CSS.escape(id || "")}"] .cover-photo img`); },
    update(day) {
      const index = (items) => items?.findIndex((item) => item.id === day.id) ?? -1;
      if (index(all) >= 0) all[index(all)] = day;
      if (index(matches) >= 0) matches[index(matches)] = day;
      if (favorites || selected.size || calendarView) { if(all) render(); return; }
      const before = page.querySelector(`[data-memory="${CSS.escape(day.id)}"]`);
      if (before) before.replaceWith(card(day, before.classList.contains("latest-link")));
    },
  };
}
