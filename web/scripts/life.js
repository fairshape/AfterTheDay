import {deleteAction} from "./delete-action.js";
import {api, asset} from "./client.js";
import {button, captionedImage, dateLabel, element as el} from "./dom.js";
import {prepareFilm} from "./life-player.js";
import {heading, link} from "./museum.js";

function shortlist(days) {
  const picked = [], months = new Set(), moods = new Set(), places = new Set();
  const remaining = [...days];
  while (remaining.length && picked.length < 6) {
    function score(day) {
      const freshMood = day.emotion.primary && !moods.has(day.emotion.primary);
      const newPlace = day.place && !places.has(day.place);
      return Number(day.favorite) * 5 + Number(Boolean(freshMood)) * 3 +
          Number(!months.has(day.date.slice(0, 7))) * 2 + Number(Boolean(newPlace)) +
          Math.min(3, day.photoCount || 1) / 5 + Math.min(80, day.focus?.length || 0) / 100;
    }
    remaining.sort((a,b)=>score(b)-score(a)||a.date.localeCompare(b.date));
    const day=remaining.shift();
    picked.push(day);months.add(day.date.slice(0,7));moods.add(day.emotion.primary);places.add(day.place);
  }
  return picked.sort((a,b)=>a.date.localeCompare(b.date));
}
function select(options) {
  const node = el("select");
  for (const [id, label] of options) {
    const o = el("option", "", label);
    o.value = id;
    node.append(o);
  }
  return node;
}
function field(label, input) {
    input.setAttribute("aria-label", label);
  const l = el("label", "field", label);
  l.append(input);
  return l;
}
export async function life(days, query, today) {
  const root = el("section", "life-workspace"), stored = await api("/api/films");
  root.append(el("span", "mono", "МОНТАЖНАЯ"), el("h1", "page-title", "Life Replay"));
  if (days.length < 2)
    root.append(
        el("p", "notice", "Для фильма нужны хотя бы два сохранённых дня."),
        link("Создать воспоминание", "/?view=create"));
  const work = el("div", "studio-spread"), editor = el("div", "studio-fields"),
        timeline = el("section", "film-timeline"), choices = el("div", "film-options");
  const title = el("input");
  title.value = "Мой фильм";
  title.maxLength = 90;
  const period = select([
    ["all", "Все даты"], ["month", "Этот месяц"], ["prevMonth", "Прошлый месяц"], ["year", "Этот год"],
    ["prevYear", "Прошлый год"], ["custom", "Свой период"]
  ]);
  const from = el("input"), to = el("input");
  from.type = to.type = "date";
  const range = el("div", "actions");
  range.append(field("С", from), field("По", to));
  range.hidden = true;
  const order = select(
      [["date", "По хронологии"], ["energy", "По нарастанию энергии"], ["manual", "Мой порядок"]]);
  const music = select([["sections", "Музыка каждого дня"], ["silent", "Без музыки"]]);
  const length = el("input");
  length.type = "number";
  length.min = 12;
  length.max = 180;
  length.value = 45;
  const pool = el("div", "pick-list"), status = el("p", "notice"), actions = el("div", "actions");
  status.role = "status";
  let editingFilm = null;
  let picked = [], captions = new Map(), selection = new Set(), activeVersion = 0;
  const run = button("Собрать предпросмотр", "solid-btn", () => build(false)),
        save = button("Сохранить фильм", "minor", () => build(true));
  const play = button("▶ Смотреть фильм", "solid-btn", () => ready?.());
  let ready = null;
  play.hidden = true;
  function invalidate() {
    activeVersion++;
    ready = null;
    play.hidden = true;
    status.textContent = "";
  }
  function refresh() {
    if (order.value === "date")
      picked.sort((a, b) => a.date.localeCompare(b.date));
    if (order.value === "energy")
      picked.sort((a, b) => a.emotion.energy - b.emotion.energy || a.date.localeCompare(b.date));
    invalidate();
    selection = new Set(picked.map(d => d.id));
    choices.replaceChildren(...picked.map(day => {
      const span = el("figure", "reel-cell");
      span.append(
          captionedImage(day.cover, "reel-thumb", asset, day.title), el("figcaption", "", day.title));
      return span;
    }));
    timeline.replaceChildren(heading("Главы фильма", String(picked.length)));
    picked.forEach((day, i) => {
      const row = el("div", "timeline-row"), text = el("input");
      text.maxLength = 140;
      text.placeholder = day.focus || day.title;
      text.value = captions.get(day.id) || "";
      text.setAttribute("aria-label", "Подпись · " + day.title);
      text.oninput = () => {
        captions.set(day.id, text.value);
        invalidate();
      };
      const up = button("↑", "minor", () => {
        [picked[i - 1], picked[i]] = [picked[i], picked[i - 1]];
        order.value = "manual";
        refresh();
      });
      up.disabled = i === 0;
      up.setAttribute("aria-label", "Передвинуть раньше");
      row.append(
          el("small", "mono", dateLabel(day.date, true)), el("h3", "", day.title), text, up,
          button("Убрать", "minor", () => {
            picked.splice(i, 1);
            refresh();
          }));
      timeline.append(row);
    });
    pool.replaceChildren();
    for (const d of days.filter(
             d => (!from.value || d.date >= from.value) && (!to.value || d.date <= to.value) &&
                 !selection.has(d.id))) {
      pool.append(button("＋ " + d.title, "minor", () => {
        if (picked.length < 20)
          picked.push(d);
        refresh();
      }));
    }
    const old = music.value;
    music.replaceChildren(...select([
                            ["sections", "Музыка каждого дня"], ["silent", "Без музыки"],
                            ...picked.filter(d => d.audioFile).map(d => [d.id, d.trackLabel])
                          ]).children);
    if ([...music.options].some(o => o.value === old))
      music.value = old;
    run.disabled = save.disabled = picked.length < 2;
  }
  function choosePeriod() {
    const now = new Date(today + "T12:00:00Z");
    let y = now.getUTCFullYear(), m = now.getUTCMonth();
    range.hidden = period.value !== "custom";
    if (period.value === "all") {
      from.value = to.value = "";
    } else if (period.value !== "custom") {
      if (period.value === "prevMonth")
        m--;
      if (period.value === "prevYear")
        y--;
      const year = period.value.toLowerCase().includes("year");
      from.value = new Date(Date.UTC(y, year ? 0 : m, 1)).toISOString().slice(0, 10);
      to.value = new Date(Date.UTC(y, year ? 12 : m + 1, 0)).toISOString().slice(0, 10);
    }
    picked = shortlist(
        days.filter(d => (!from.value || d.date >= from.value) && (!to.value || d.date <= to.value)));
    refresh();
  }
  async function build(persist) {
    const generation = activeVersion;
    status.textContent = "Собираем фильм…";
    run.disabled = save.disabled = true;
    try {
      const film = await api("/api/films/" + (persist ? "save" : "preview"), {
        existing: editingFilm?.id || null,
        revision: editingFilm?.editRevision || 1,
        items: picked.map(d => ({day: d.id, caption: captions.get(d.id) || ""})),
        title: title.value,
        order: order.value,
        music: music.value,
        seconds: Number(length.value)
      });
      if (persist) {
        location.assign("/?view=life&film=" + film.id);
        return;
      }
      const start = await prepareFilm(film);
      if (generation === activeVersion) {
        ready = start;
        play.hidden = false;
        status.textContent = "Готово · " + Math.round(film.duration) + " с";
      }
    } catch {
      status.textContent = "Проверь длительность и доступность записей. Попробуй ещё раз.";
    } finally {
      run.disabled = save.disabled = picked.length < 2;
    }
  }
  if (query.has("film")) {
    const film = await api("/api/films/" + encodeURIComponent(query.get("film")));
    const start = await prepareFilm(film);
    root.append(
        captionedImage(film.shots[0].asset, "screening-poster", asset, film.title), heading(film.title),
        el("p", "notice", film.period.map(d => dateLabel(d, true)).join(" — ")),
        button("▶ Смотреть фильм", "solid-btn", start),
        link("Редактировать фильм", "/?view=life&edit=" + film.id), link("Новый монтаж", "/?view=life"),
        deleteAction({
          label: "Удалить фильм",
          question: "Удалить «" + film.title + "»?",
          details: "Исходные дни останутся в дневнике.",
          path: "/api/films/" + film.id + "/delete",
          payload: () => ({}),
          returnUrl: "/?view=life",
        }), status);
    return root;
  }
  actions.append(run, save, play);
  editor.append(
      field("Название фильма", title), field("Период", period), range, field("Порядок глав", order),
      field("Саундтрек", music), field("Желаемая длительность, с", length), heading("Добавить дни"),
      pool);
  work.append(editor, timeline);
  root.append(choices, work, actions, status);
  period.onchange = from.onchange = to.onchange = choosePeriod;
  order.onchange = refresh;
  [music, title, length].forEach(n => n.oninput = invalidate);
  choosePeriod();
  if(query.has("days")){
    const selectedIds=[...new Set(query.get("days").split(","))].slice(0,20);
    picked=selectedIds.map(id=>days.find(day=>day.id===id)).filter(Boolean);
    order.value="manual";refresh();
  }
  const initial = days.find(d => d.id === query.get("add"));
  if (initial && !picked.includes(initial)) {
    picked.push(initial);
    refresh();
  }
  if (query.has("edit")) {
    editingFilm = await api("/api/films/" + encodeURIComponent(query.get("edit")));
    title.value = editingFilm.title;
    length.value = editingFilm.requestedSeconds || Math.max(12, Math.round(editingFilm.duration));
    order.value = editingFilm.order;
    picked = [...new Set(editingFilm.shots.map(s => s.day))]
                 .map(id => days.find(d => d.id === id))
                 .filter(Boolean);
    captions = new Map(Object.entries(editingFilm.captions || {}));
    refresh();
    music.value = editingFilm.music;
  }
  if (stored.length) {
    root.append(heading("Сохранённые фильмы"));
    for (const f of stored)
      root.append(link(
          f.title + " · " + Math.round(f.duration) + " с ↗", "/?view=life&film=" + f.id, "saved-film"));
  }
  return root;
}
