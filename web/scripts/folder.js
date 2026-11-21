import { memoryCover } from "./art.js";
import { api, asset } from "./client.js";
import { editing, scrapbook as copy, text } from "./copy.js";
import { button, captionedImage, element } from "./dom.js";
import { decorate, icon } from "./icons.js";
import { prepare } from "./player.js";
import { sceneEditor, whyPanel } from "./scene-tools.js";
import { coverEditor, photoViewer } from "./sheet.js";
import { songLink } from "./song-link.js";

function soundtrack(track, telegram) {
  const section = element("section", "reading-section song-section");
  section.append(element("h2", "reading-title", copy.song));
  const card = element("div", "song-card");
  const row = element("div", "song-row");
  const mark = element("span", "song-mark");
  mark.append(icon("music"));
  const label = element("div");
  label.append(element("p", "track-name", track.title));
  if (track.artist) label.append(element("p", "microcopy", track.album ?
    `${track.artist} · ${track.album}` : track.artist));
  row.append(mark, label);
  card.append(row);
  if (track.kind === "link") card.append(songLink(track, telegram, "outline-button"),
    element("p", "microcopy", editing.linked));
  else {
    const audio = element("audio", "original-audio");
    audio.controls = true;
    audio.preload = "metadata";
    audio.setAttribute("aria-label", track.title);
    const failed = () => audio.replaceWith(element("p", "error", text.unavailableAudio));
    audio.addEventListener("error", failed, {once:true});
    asset(track.asset).then((source) => { audio.src = source; }).catch(failed);
    card.append(audio);
  }
  section.append(card);
  return section;
}

export function createFolder(initialDay, {back, open, overlay, updateArchive, telegram, published}, readyCover = "") {
  let day = initialDay;
  let selected = 0;
  let ready;
  const article = element("article", "folder");
  const header = element("div", "folder-header");
  const returnLink = element("a", "back-link");
  returnLink.href = "/";
  decorate(returnLink, "back", copy.back);
  returnLink.addEventListener("click", (event) => {
    if (event.metaKey || event.ctrlKey || event.altKey || event.shiftKey) return;
    event.preventDefault();
    back();
  });
  header.append(returnLink);
  if (day.draft) header.append(element("p", "microcopy", editing.draft));
  const hero = element("div", "folder-cover");
  const context = element("div", "folder-context");
  for (const key of ["time", "place"]) {
    if (day.details[key]) context.append(element("span", "", day.details[key]));
  }
  context.hidden = !context.childElementCount;

  const actions = element("div", "folder-actions");
  const play = decorate(button("", "primary-button", () => {
    if (!ready) return;
    article.querySelectorAll("audio").forEach((audio) => audio.pause());
    open(day, variants()[selected].scene, ready, hero.querySelector(".cover-photo img"));
  }), "play", text.preparing);
  play.disabled = true;
  const edit = decorate(button("", "outline-button", () => {
    overlay((close) => coverEditor(day, (updated) => {
      day = updated;
      renderHero();
      updateArchive(day);
      status.textContent = copy.saved;
      preload();
    }, close));
  }), "edit", copy.edit);
  const saveDraft = button(editing.saveDay, "primary-button", async () => {
    saveDraft.disabled = true;
    try { await confirm(day.previewToken); }
    catch (error) {
      status.textContent = error.status === 409 ? editing.conflict : editing.failure;
      status.classList.add("error");
      saveDraft.disabled = false;
    }
  });
  actions.append(play, day.draft ? saveDraft : edit);
  const linkedSong = element("div", "linked-song-note");
  if (day.track.kind === "link") {
    const description = day.track.provider === "itunes" ? editing.linkedApple : editing.linkedExternal;
    linkedSong.append(element("p", "microcopy", description),
      songLink(day.track, telegram, "outline-button"));
  } else linkedSong.hidden = true;
  const status = element("p", "folder-status");
  status.role = "status";

  const reading = element("div", "reading");
  const story = element("section", "reading-section");
  story.append(element("h2", "reading-title", copy.story), element("p", "original-story", day.story));
  const details = element("dl", "memory-details");
  for (const key of ["weather", "mood", "key_detail"]) {
    if (!day.details[key]) continue;
    const row = element("div");
    row.append(element("dt", "", text.fields[key]), element("dd", "", day.details[key]));
    details.append(row);
  }
  if (details.childElementCount) story.append(details);
  const photos = element("section", "reading-section");
  photos.append(element("h2", "reading-title", copy.photos));
  const strip = element("div", "photo-strip");
  day.photos.forEach((photo, index) => {
    const tile = button("", "gallery-tile", () => overlay((done) => photoViewer(day, index, done)));
    tile.setAttribute("aria-label", text.imageAlt(index+1));
    tile.append(captionedImage(photo.src, "gallery-thumb", asset));
    strip.append(tile);
  });
  photos.append(strip);

  const secondary = element("div", "scene-details");
  const comparison = element("section", "comparison");
  function variants() {
    const entries = [{label:day.scene.track.title, scene:day.scene}];
    if (day.comparison) entries.push({label:day.comparison.track.title, scene:day.comparison});
    if (day.scene.evenFrames) {
      entries.push({label:editing.even, scene:{...day.scene, frames:day.scene.evenFrames,
        soundtrack:{...day.scene.soundtrack, basis:"even"},
        signals:{...day.scene.signals, finalHold:day.scene.evenFrames.at(-1).seconds}}});
    }
    return entries;
  }

  async function confirm(token) {
    const updated = await api(`/api/days/${day.id}/scene/confirm`, {token});
    if (day.draft) {
      published(updated);
      return;
    }
    day = updated;
    updateArchive(day);
    renderHero();
    renderTools();
    renderComparison();
    preload();
    status.textContent = editing.confirmed;
  }

  function renderTools() {
    secondary.replaceChildren(whyPanel(variants()[selected].scene), sceneEditor(day, {
      confirm,
      preview: async (candidate) => {
        const prepared = await prepare(candidate, candidate.scene, asset);
        if (day.draft && article.isConnected) {
          day = candidate;
          ready = prepared;
          renderHero();
        }
        return () => {
          article.querySelectorAll("audio").forEach((audio) => audio.pause());
          open(candidate, candidate.scene, prepared, hero.querySelector(".cover-photo img"));
        };
      },
    }));
  }

  function renderComparison() {
    const entries = variants();
    comparison.hidden = entries.length === 1;
    comparison.replaceChildren();
    if (comparison.hidden) return;
    const label = day.scene.evenFrames ? editing.compare : text.comparison;
    comparison.append(element("h2", "reading-title", label));
    const list = element("div", "track-switch");
    list.role = "group";
    list.setAttribute("aria-label", label);
    entries.forEach(({label}, index) => {
      const switcher = button(label, "track-choice", () => {
        if (index === selected) return;
        article.querySelectorAll("audio").forEach((audio) => audio.pause());
        selected = index;
        [...list.children].forEach((choice, i) => choice.setAttribute("aria-pressed", String(i === selected)));
        renderTools();
        preload();
      });
      switcher.setAttribute("aria-pressed", String(selected === index));
      list.append(switcher);
    });
    comparison.append(list);
  }
  renderComparison();
  reading.append(story, photos, soundtrack(day.track, telegram), comparison, secondary);
  article.append(header, hero, context, actions, linkedSong, status, reading);

  let generation = 0;
  async function preload() {
    const mark = ++generation;
    const scene = variants()[selected].scene;
    ready = null;
    play.disabled = true;
    decorate(play, "play", text.preparing);
    const loaded = await prepare(day, scene, asset);
    if (mark !== generation) return;
    ready = loaded;
    play.disabled = false;
    decorate(play, "play", text.play);
  }

  function renderHero(src = "") {
    hero.replaceChildren(memoryCover(day, "hero", {readySrc:src, heading:"h1"}));
  }
  renderHero(readyCover);
  renderTools();
  preload();

  return { article, image: () => hero.querySelector(".cover-photo img") };
}
