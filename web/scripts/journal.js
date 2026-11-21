import { loadArt } from "./art.js";
import { createArchive } from "./archive.js";
import { api, asset, connect, releaseOldAssets } from "./client.js";
import { scrapbook as copy, text } from "./copy.js";
import { button, element } from "./dom.js";
import { createFolder } from "./folder.js";
import { decorate } from "./icons.js";
import { transitionCover } from "./motion.js";
import { openPlayer } from "./player.js";
import { openSheet } from "./sheet.js";

const main = document.querySelector("#journal");
const brand = document.querySelector("#brand");
const filter = document.querySelector("#search-toggle");
const activeDay = () => new URL(location.href).searchParams.get("day");
let telegram;
let mode;
let archive;
let archiveScroll = 0;
let openedId = null;
let generation = 0;
let overlay;
let coverImage;
history.scrollRestoration = "manual";

async function telegramClient() {
  const sdk = document.createElement("script");
  sdk.src = "https://telegram.org/js/telegram-web-app.js";
  await new Promise((resolve, reject) => {
    sdk.addEventListener("load", resolve, {once:true});
    sdk.addEventListener("error", reject, {once:true});
    document.head.append(sdk);
  });
  return window.Telegram?.WebApp;
}

function syncNavigation() {
  if (openedId || overlay) telegram?.BackButton?.show();
  else telegram?.BackButton?.hide();
  filter.hidden = !!openedId;
}

function nativeChrome(playing = false) {
  const color = getComputedStyle(document.documentElement).getPropertyValue(playing ? "--ink" : "--paper").trim();
  if (telegram?.isVersionAtLeast?.("6.9")) telegram.setHeaderColor(color);
  if (telegram?.isVersionAtLeast?.("6.1")) telegram.setBackgroundColor(color);
}

function showOverlay(open, playing = false) {
  history.pushState({...history.state, overlay:true}, "", location.href);
  overlay = open(() => {
    overlay = null;
    nativeChrome();
    syncNavigation();
    if (history.state?.overlay) history.back();
  });
  nativeChrome(playing);
  syncNavigation();
}

function goBack() {
  if (overlay) overlay.close();
  else if (openedId && history.state?.fromArchive) history.back();
  else if (openedId) {
    history.replaceState(null, "", `/${location.hash}`);
    showArchive();
  }
}

function pauseReadingAudio() {
  main.querySelectorAll("audio").forEach((audio) => audio.pause());
}

function showArchive() {
  pauseReadingAudio();
  const previousId = openedId;
  const from = coverImage?.();
  ++generation;
  openedId = null;
  coverImage = null;
  syncNavigation();
  main.setAttribute("aria-busy", "false");
  if (main.contains(archive.page)) return;
  transitionCover(from, () => {
    main.replaceChildren(archive.page);
    window.scrollTo(0, archiveScroll);
    const target = archive.imageFor(previousId);
    target?.closest("a")?.focus({preventScroll:true});
    return target;
  });
}

async function showDay(id, from = null, link = null) {
  const request = ++generation;
  openedId = id;
  syncNavigation();
  main.setAttribute("aria-busy", "true");
  if (link) link.setAttribute("aria-busy", "true");
  else main.replaceChildren(element("p", "page-status", text.loadingDay));
  try {
    const day = await api(`/api/days/${encodeURIComponent(id)}`);
    if (request !== generation) return;
    const src = await asset(day.cover).catch(() => "");
    if (request !== generation) return;
    const folder = createFolder(day, {
      back:goBack, telegram, overlay:showOverlay,
      updateArchive: (updated) => archive.update(updated),
      open: (memory, scene, assets, source) => {
        showOverlay((close) => openPlayer(memory, scene, assets, close, {from:source, telegram}), true);
      },
    }, src);
    await transitionCover(from, () => {
      if (request !== generation) return null;
      main.replaceChildren(folder.article);
      window.scrollTo(0, 0);
      coverImage = folder.image;
      return folder.image();
    });
  } catch (error) {
    if (request !== generation) return;
    const message = error.status === 401 ? text.login :
      [404, 422].includes(error.status) ? text.missingDay : text.unavailable;
    main.replaceChildren(element("p", "page-status", message), button(copy.back, "outline-button", goBack));
    if (![401,404,422].includes(error.status)) main.append(button(text.retry, "outline-button", () => showDay(id)));
  } finally {
    link?.removeAttribute("aria-busy");
    if (request === generation) main.setAttribute("aria-busy", "false");
  }
}

function openFromArchive(id, image, link) {
  if (openedId) return;
  releaseOldAssets();
  archiveScroll = window.scrollY;
  history.pushState({fromArchive:true}, "", `/?day=${encodeURIComponent(id)}${location.hash}`);
  showDay(id, image, link);
}

function onHistory() {
  const next = activeDay();
  if (overlay) {
    overlay.close();
    if (next === openedId) return;
  }
  if (next === openedId && main.contains(archive.page)) return;
  if (next && next !== openedId) showDay(next, archive.imageFor(next));
  else if (!next) showArchive();
}

async function record() {
  if (!mode.demo && !mode.recordUrl) {
    try { mode = await api("/api/mode"); } catch { /* Show a retryable message below. */ }
  }
  if (mode.recordUrl && telegram?.openTelegramLink) {
    try {
      telegram.openTelegramLink(mode.recordUrl);
      if (telegram.isVersionAtLeast?.("7.0")) telegram.close();
      return;
    } catch { /* Show a retryable message below. */ }
  }
  showOverlay((close) => openSheet(copy.record,
    element("p", "sheet-content record-help", mode.demo ? copy.recordDemo : copy.recordWait), close));
}

function updateInsets() {
  const safe = telegram?.safeAreaInset || {};
  const content = telegram?.contentSafeAreaInset || {};
  for (const key of ["top", "right", "bottom", "left"]) {
    document.documentElement.style.setProperty(`--telegram-${key}`, `${(safe[key] || 0) + (content[key] || 0)}px`);
  }
}

async function start() {
  try {
    const [info] = await Promise.all([api("/api/mode"), loadArt()]);
    mode = info;
    if (!mode.demo) {
      telegram = await telegramClient();
      await connect(telegram);
      telegram.ready();
      telegram.expand();
      nativeChrome();
      if (telegram.isVersionAtLeast?.("6.1")) telegram.BackButton.onClick(goBack);
      if (telegram.isVersionAtLeast?.("8.0")) {
        telegram.onEvent("deactivated", () => {
          overlay?.pause?.();
          pauseReadingAudio();
        });
        telegram.onEvent("safeAreaChanged", updateInsets);
        telegram.onEvent("contentSafeAreaChanged", updateInsets);
        updateInsets();
      }
    }
    document.querySelector("#demo-label").hidden = !mode.demo;
    decorate(document.querySelector(".brand-mark"), "brand");
    decorate(filter, "search");
    filter.setAttribute("aria-controls", "archive-tools");
    archive = createArchive({open:openFromArchive, record, toggle:filter});
    brand.addEventListener("click", (event) => {
      if (event.metaKey || event.ctrlKey || event.altKey || event.shiftKey) return;
      event.preventDefault();
      if (openedId) goBack();
      else window.scrollTo(0, 0);
    });
    if (history.state?.overlay) history.replaceState({...history.state, overlay:false}, "", location.href);
    window.addEventListener("popstate", onHistory);
    if (activeDay()) showDay(activeDay());
    else showArchive();
  } catch (error) {
    telegram?.ready();
    main.setAttribute("aria-busy", "false");
    main.replaceChildren(element("p", "page-status", error.status === 401 ? text.login : text.unavailable));
    if (error.status !== 401) main.append(button(text.retry, "outline-button", () => location.reload()));
  }
}

start();
