import { remixPanel } from "./remix.js";
import {deleteAction} from "./delete-action.js";
import { dayCollection } from "./collection.js";
import { memoryCover } from "./art.js";
import { api, asset } from "./client.js";
import { editing, musicText, scrapbook as copy, text, voiceText } from "./copy.js";
import { button, captionedImage, element } from "./dom.js";
import { decorate, icon } from "./icons.js";
import { prepare } from "./player.js";
import { sceneEditor, whyPanel } from "./scene-tools.js";
import { coverEditor, photoViewer } from "./sheet.js";
import { songLink } from "./song-link.js";
import { storyAudio, voicePanel } from "./voice.js";

function soundtrack(track, telegram, scene) {
  const section = element("section", "reading-section song-section");
  section.append(element("h2", "reading-title", copy.song));
  const card = element("div", "song-card");
  const row = element("div", "song-row");
  const mark = element("span", "song-mark");
  mark.append(icon("music"));
  const label = element("div");
  label.append(element("p", "track-name", track.title));
  const metadata = [track.artist, track.album, track.genre, track.year].filter(Boolean);
  if (metadata.length) label.append(element("p", "microcopy", metadata.join(" · ")));
  row.append(mark, label);
  card.append(row);
  const source = track.provider === "itunes" ? musicText.catalogue : track.kind === "file" ? musicText.local : musicText.link;
  card.append(element("p", "microcopy", source));
  const analysis = scene?.soundtrack?.analysis;
  const traits = [];
  if (analysis?.tempoConfidence >= .5 && analysis.tempo) {
    traits.push(musicText.approximateBpm(Math.round(analysis.tempo)));
    if (analysis.tempoConfidence >= .72) traits.push(musicText.steady);
  }
  if (analysis?.softEnding) traits.push(musicText.softEnding);
  if (analysis?.cutCues?.length) traits.push(musicText.cueCount(analysis.cutCues.length));
  if (traits.length) card.append(element("p", "microcopy", `${musicText.measured} · ${traits.join(" · ")}`));
  else if (track.profile && text.profile[track.profile]) {
    card.append(element("p", "microcopy", `${track.signal === "genre_tag" ? musicText.genre : musicText.described} · ${text.profile[track.profile]}`));
  }
  if (analysis?.energy?.length) {
    const energy = element("div", "track-energy");
    energy.role = "img";
    energy.setAttribute("aria-label", musicText.energy);
    for (const sample of analysis.energy) {
      const bar = element("span");
      bar.style.setProperty("--level", `${Math.min(100, 11 + sample * 64)}%`);
      energy.append(bar);
    }
    card.append(energy);
  }
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
  for (const key of ["time", "place", "weather"]) {
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
    article.querySelectorAll("audio").forEach(audio => audio.pause());
    overlay((close) => coverEditor(day, (updated) => {
      day = updated;
      renderHero();
      updateArchive(day);
      status.textContent = copy.saved;
      preload();
      if (!day.draft) {
        const previous = article.querySelector(".day-collection");
        previous?.replaceWith(dayCollection(day,updateArchive));
      }
      refreshStorySound();
      const nextVoice = voicePanel(day, updateVoice);
      voice.replaceWith(nextVoice);
      voice = nextVoice;
      renderTools();
      renderComparison();
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
  if (day.draft) actions.append(edit);
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
  const storySound = element("div");
  story.append(storySound);
  let voice = voicePanel(day, updateVoice);
  function refreshStorySound() {
    storySound.replaceChildren(storyAudio(day, () => {
      voice.open = true;
      voice.scrollIntoView({block:"nearest"});
    }));
  }

  function updateVoice(updated) {
    day = updated;
    refreshStorySound();
    refreshWhy();
    preload();
    status.textContent = voiceText.saved;
  }
  refreshStorySound();
  article.addEventListener("play", (event) => {
    if (event.target instanceof HTMLAudioElement) {
      for (const audio of article.querySelectorAll("audio")) if (audio !== event.target) audio.pause();
    }
  }, true);
  const details = element("dl", "memory-details");
  for (const key of ["mood", "key_detail"]) {
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
  if(day.details.reflection)story.append(element("blockquote","reflection",day.details.reflection));

  const secondary = element("div", "scene-details");
  const comparison = element("section", "comparison");
  function variants() {
    const entries = [{label:day.scene.track.title, scene:day.scene}];
    if (day.comparison) entries.push({label:day.comparison.track.title, scene:day.comparison});
    if (day.scene.evenFrames) {
      entries.push({label:editing.even, scene:{...day.scene, frames:day.scene.evenFrames,
        soundtrack:{...day.scene.soundtrack, basis:"even"}, narrationKey:null,
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
    refreshStorySound();
    const nextVoice = voicePanel(day, updateVoice);
    voice.replaceWith(nextVoice);
    voice = nextVoice;
    renderTools();
    renderComparison();
    preload();
    status.textContent = editing.confirmed;
  }

  const interpretation=element("details","disclosure");
  const why = element("div");
  function refreshWhy() {
    const activeScene = variants()[selected].scene;
    why.replaceChildren(whyPanel(activeScene, day.narration, day.photos));
    interpretation.replaceChildren(element("summary","","Эмоции и ритм"));
    for(const reason of (selected ? activeScene.emotion : day.emotion)?.reasons||[])
      interpretation.append(element("p","microcopy",reason));
  }
  function renderTools() {
    refreshWhy();
    secondary.replaceChildren(why, interpretation, sceneEditor(day, {
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
  reading.append(story, photos, soundtrack(day.track, telegram, day.scene), comparison, voice, secondary);
  article.append(header, hero, context, actions, linkedSong, status);
  if (!day.draft) article.append(dayCollection(day, updateArchive));
  article.append(reading);
  if (!day.draft) {
    const film=element("a","ink-link","Добавить в Life Replay ↗");film.href="/?view=life&add="+day.id;
    const metadata=element("details","disclosure");
    metadata.append(element("summary","","Изменить сведения о записи"));
    const inputs={};
    for (const [key,name,value] of [["title","Название",day.title],["date","Дата",day.date],["reflection","Послесловие",day.details.reflection||""]]) {
      const label=element("label","field",name),input=element("input");input.value=value;
      input.type=key==="date"?"date":"text";input.maxLength=key==="title"?90:360;
      label.append(input);metadata.append(label);inputs[key]=input;
    }
    const notice=element("p","notice");notice.role="status";
    metadata.append(button("Сохранить сведения","solid-btn",async()=>{
      try{await api("/api/days/"+day.id+"/metadata",{revision:day.revision,title:inputs.title.value,date:inputs.date.value,reflection:inputs.reflection.value});location.reload();}
      catch{notice.textContent="Проверь название и дату. Если запись менялась, обнови страницу.";}
    }), deleteAction({
      label: "Удалить запись",
      question: "Удалить «" + day.title + "»?",
      details: "Из дневника исчезнут запись, её фотографии, аудио и напоминания.",
      path: "/api/days/" + day.id + "/delete",
      payload: () => ({revision: day.revision}),
      returnUrl: "/?view=archive",
    }),notice);
    reading.append(remixPanel(day,open),film,metadata);
  }

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
  const initialAssets = preload();

  return { article, initialAssets, play, image: () => hero.querySelector(".cover-photo img") };
}
