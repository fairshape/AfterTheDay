import {loadArt} from "./art.js";
import {api, connect, enableMediaStreaming} from "./client.js";
import {reminderCenter} from "./collection.js";
import {button, element as el} from "./dom.js";
import {createFolder} from "./folder.js";
import {transitionCover} from "./motion.js";
import {dayURL, link} from "./museum.js";
import {memoryTable} from "./memory-table.js";
import {openPlayer} from "./player.js";

const main = document.querySelector("#journal");
const query = new URLSearchParams(location.search);
document.body.dataset.room = query.has("day") ? "day" : query.get("view") || "home";
let tg, overlay, previousGallery, opening = false;
const warmDays = new Map();

function warmDay(id) {
  const current = warmDays.get(id);
  if (current && current.expires > performance.now()) return current.request;
  const request = api("/api/days/" + encodeURIComponent(id));
  const entry = {request, expires: performance.now() + 15000};
  warmDays.delete(id);
  warmDays.set(id, entry);
  if (warmDays.size > 8) warmDays.delete(warmDays.keys().next().value);
  request.catch(() => { if (warmDays.get(id) === entry) warmDays.delete(id); });
  return request;
}
function back() {
  if (overlay)
    overlay.close();
  else if (history.state?.lifePlayer)
    history.back();
  else if ((history.state?.galleryOrigin || query.get("from") === "gallery") && history.length > 1)
    history.back();
  else
    location.assign("/");
}
function showOverlay(open) {
  history.pushState({...history.state, dayOverlay: true}, "", location.href);
  overlay = open(() => {
    overlay = null;
    if (history.state?.dayOverlay)
      history.back();
  });
}
window.addEventListener("popstate", () => {
  if (overlay && !history.state?.dayOverlay)
    overlay.close();
});
async function showDay(id, route, source) {
  if(route.has("preview"))main.replaceChildren(el("p","loading","Собираем сцену из твоих фотографий, текста и музыки…"));
  const path = "/api/days/" + encodeURIComponent(id);
  const day = route.has("preview") ? await api(path + "/scene/preview", {}) : await warmDay(id);
  const folder = createFolder(day, {
    back,
    telegram: tg,
    overlay: showOverlay,
    updateArchive: () => {
      warmDays.delete(id);
      if (previousGallery)
        previousGallery.changed = true;
    },
    published: () => location.replace(dayURL(id)),
    open: (memory, scene, assets, from) =>
        showOverlay(close => openPlayer(memory, scene, assets, close, {from, telegram: tg}))
  }, source?.naturalWidth && day.cover === source.dataset.original
    ? source.src : "");
  await transitionCover(source, () => {
    document.body.dataset.room="day";
    main.replaceChildren(folder.article);
    window.scrollTo(0, 0);
    return folder.image();
  });
  if(route.has("studio")){
    const editor=folder.article.querySelector(".montage-editor");
    if(editor){editor.open=true;editor.scrollIntoView({block:"start"});}
  }
  if (route.has("play")) {
    await folder.initialAssets;
    if(folder.article.isConnected && !overlay) folder.play.click();
  }
}
main.addEventListener("click", async event => {
  const anchor = event.target.closest("a");
  if (!anchor || event.defaultPrevented || event.metaKey || event.ctrlKey || event.shiftKey ||
      event.altKey || event.button !== 0)
    return;
  const target = new URL(anchor.href);
  if (target.origin !== location.origin || target.searchParams.get("from") !== "gallery")
    return;
  event.preventDefault();
  if (opening)
    return;
  opening = true;
  const id = target.searchParams.get("day"),
        source = anchor.querySelector("img") || anchor.closest(".memory-shelf")?.querySelector("[aria-current] img");
  const rail = main.querySelector(".shelf-rail");
  previousGallery = {node: main.firstElementChild, scroll: scrollY, source, rail, railScroll: rail?.scrollLeft};
  try {
    history.pushState({galleryOrigin: true}, "", target);
    await showDay(id, target.searchParams, source);
    tg?.BackButton?.show();
  } catch {
    location.replace(target);
  } finally {
    opening = false;
  }
});
window.addEventListener("popstate", () => {
  if (!previousGallery || overlay)
    return;
  const route = new URLSearchParams(location.search);
  if (route.has("day")) {
    if (!main.querySelector(".folder"))
      showDay(route.get("day"), route).catch(() => location.reload());
    return;
  }
  if (main.firstElementChild === previousGallery.node)
    return;
  const gallery = previousGallery;
  if (gallery.changed) {
    history.replaceState({...history.state, scrollY: gallery.scroll}, "", location.href);
    location.reload();
    return;
  }
  transitionCover(main.querySelector(".cover-photo img"), () => {
    document.body.dataset.room=new URLSearchParams(location.search).get("view")||"home";
    main.replaceChildren(gallery.node);
    if (gallery.rail) gallery.rail.scrollLeft = gallery.railScroll;
    scrollTo(0, gallery.scroll);
    return gallery.source;
  }).catch(() => location.reload());
  if (!route.size)
    tg?.BackButton?.hide();
});
async function boot() {
  const id = query.get("day"), view = query.get("view") || "home";
  const extraScreen = !id && !["home", "today", "feed", "settings", "reminders"].includes(view)
    ? import("./screens.js") : null;
  const [mode] = await Promise.all([api("/api/mode"), loadArt()]);
  if (mode.demo)
    await api("/api/demo/start", {});
  else {
    await new Promise((ok, no) => {
      const sdk = document.createElement("script");
      sdk.src = "https://telegram.org/js/telegram-web-app.js";
      sdk.onload = ok;
      sdk.onerror = no;
      document.head.append(sdk);
    });
    tg = window.Telegram?.WebApp;
    await connect(tg);
    tg.ready();
    tg.expand();
    if (query.size)
      tg.BackButton?.show();
    tg.BackButton?.onClick(back);
    function insets() {
      for (const side of ["top", "bottom", "left", "right"])
        document.documentElement.style.setProperty(
            "--telegram-" + side,
            (Number(tg.safeAreaInset?.[side] || 0) + Number(tg.contentSafeAreaInset?.[side] || 0)) +
                "px");
    }
    insets();
    tg.onEvent?.("safeAreaChanged", insets);
    tg.onEvent?.("contentSafeAreaChanged", insets);
  }
  const media = enableMediaStreaming().catch(() => {});
  const needsDays = !id && !["create", "settings", "reminders"].includes(view);
  const needsContext = needsDays && !["welcome", "studio", "feed"].includes(view);
  const daysRequest = needsDays ? api("/api/days") : Promise.resolve([]);
  const contextRequest = needsContext ? api("/api/collection") : Promise.resolve({});
  if (id && !query.has("preview")) warmDay(id);
  for(const anchor of document.querySelectorAll(".museum-header a")){
    const current=new URL(anchor.href).searchParams.get("view")||"home";
    if(!id&&view===current)anchor.setAttribute("aria-current","page");
  }
  if (id) {
    if (document.referrer.startsWith(location.origin + "/") &&
        !new URL(document.referrer).searchParams.has("day"))
      history.replaceState({...history.state, galleryOrigin: true}, "", location.href);
    await media;
    await showDay(id, query);
    return;
  }
  const [days, context] = await Promise.all([daysRequest, contextRequest, media]);
  if (view === "home" || view === "today")
    main.replaceChildren(memoryTable(days, context, warmDay));
  else if (view === "feed") {
    const feed = el("section", "gallery-home");
    feed.append(link("← Мой стол", "/", "back-link"));
    if (days.length) {
      const {memoryShelf} = await import("./memory-shelf.js");
      feed.append(memoryShelf(days, warmDay));
    } else feed.append(link("Записать первый день", "/?view=create", "accent-link"));
    main.replaceChildren(feed);
  } else if (view === "settings" || view === "reminders") {
    const panel = el("section", "profile-panel");
    panel.append(
        el("span", "mono", mode.demo ? "ДЕМОНСТРАЦИОННЫЙ ПРОФИЛЬ" : "ЛИЧНАЯ КОЛЛЕКЦИЯ"),
        el("h1", "page-title", tg?.initDataUnsafe?.user?.first_name || "Мой профиль"),
        el("h2", "reading-title", "Годовщины"),
        reminderCenter(id => location.assign(dayURL(id)), mode.demo));
    if (mode.recordUrl)
      panel.append(link("✍ Записать в Telegram", mode.recordUrl, "solid-btn"));
    const about = el("details", "disclosure");
    about.append(
        el("summary", "", "Как создать первый фильм"),
        el("p", "",
           "Добавь историю, фотографии и песню. Выбери главный кадр и посмотри монтаж перед сохранением. Когда появится второй день, их можно объединить в Life Replay."),
        link("Создать день", "/?view=create"));
    panel.append(about);
    panel.append(link("Знакомство с Memory Experience ↗","/?view=welcome"));
    main.replaceChildren(panel);
  } else {
    const {screen} = await extraScreen;
    main.replaceChildren(await screen(view, {days, context, mode, query, tg}));
  }
}
if (history.state?.dayOverlay)
  history.replaceState({...history.state, dayOverlay: false}, "", location.href);
boot().catch(
    error => main.replaceChildren(
        el("p", "loading",
           error.status === 401 ? "Открой приложение кнопкой в личном чате Telegram." :
                                  "Не удалось открыть страницу."),
        button("Повторить", "solid-btn", () => location.reload())));
