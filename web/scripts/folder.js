import { memoryCover } from "./art.js";
import { asset } from "./client.js";
import { scrapbook as copy, text } from "./copy.js";
import { button, captionedImage, element } from "./dom.js";
import { decorate, icon } from "./icons.js";
import { prepare } from "./player.js";
import { pinPanel, whyPanel } from "./scene-tools.js";
import { coverEditor, photoViewer } from "./sheet.js";
import { songLink } from "./song-link.js";

function soundtrack(track, telegram) {
  const section = element("section", "reading-section song-section");
  section.append(element("h2", "reading-title", copy.song));
  const card = element("div", "song-card");
  const row = element("div", "song-row");
  const mark = element("span", "song-mark");
  mark.append(icon("music"));
  row.append(mark, element("p", "track-name", track.title));
  card.append(row);
  if (track.kind === "link") card.append(songLink(track, telegram, "outline-button"));
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

export function createFolder(initialDay, {back, open, overlay, updateArchive, telegram}, readyCover = "") {
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
    open(day, selected ? day.comparison : day.scene, ready, hero.querySelector(".cover-photo img"));
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
  actions.append(play, edit);
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
  function renderTools() {
    secondary.replaceChildren(whyPanel(selected ? day.comparison : day.scene), pinPanel(day, (updated) => {
      day = updated;
      updateArchive(day);
      renderTools();
      preload();
      status.textContent = text.pinSaved;
    }));
  }

  const comparison = element("section", "comparison");
  if (day.comparison) {
    comparison.append(element("h2", "reading-title", text.comparison));
    const list = element("div", "track-switch");
    list.role = "group";
    list.setAttribute("aria-label", text.comparison);
    [day.scene, day.comparison].forEach((version, index) => {
      const switcher = button(version.track.title, "track-choice", () => {
        if (index === selected) return;
        article.querySelectorAll("audio").forEach((audio) => audio.pause());
        selected = index;
        [...list.children].forEach((choice, i) => choice.setAttribute("aria-pressed", String(i === selected)));
        renderTools();
        preload();
      });
      switcher.setAttribute("aria-pressed", String(index === selected));
      list.append(switcher);
    });
    comparison.append(list);
  }
  comparison.hidden = !day.comparison;
  reading.append(story, photos, soundtrack(day.track, telegram), comparison, secondary);
  article.append(header, hero, context, actions, status, reading);

  let generation = 0;
  async function preload() {
    const mark = ++generation;
    const scene = selected ? day.comparison : day.scene;
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
