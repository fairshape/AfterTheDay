import { api } from "./client.js";
import { editing, text } from "./copy.js";
import { button, element } from "./dom.js";

function expandable(label) {
  const panel = element("details", "disclosure");
  panel.append(element("summary", "", label));
  return panel;
}

export function whyPanel(scene) {
  const panel = expandable(text.why);
  const list = element("dl", "rationale");
  const { signals } = scene;
  const words = signals.focus === "release" ? text.whyRelease(signals.story)
    : signals.focus === "pin" ? (signals.pinText ? text.whyPin(signals.pinText) : text.whyPhotoPin)
    : text.whyExcerpt(signals.story);
  const ratio = (number) => new Intl.NumberFormat("ru").format(number);
  const measured = scene.soundtrack?.analysis?.cutCues || [];
  const descriptions = scene.version === 2 ? [
    [text.whyWords, editing.hold(signals.story, ratio(signals.finalHold))],
    [text.whyPhotos, scene.palette.source === "photo" ? editing.palette : editing.curated],
    [text.whyMusic, scene.soundtrack.basis === "even" ? editing.evenBasis : measured.length ?
      editing.measured(measured.map((cue) => ratio(cue.audioTime)).join(", ")) :
      `${editing.fallback} ${text.profile[signals.profile] || ""}.`],
  ] : [
    [text.whyWords, words],
    [text.whyPhotos, text.whyPalette(signals.photoCount)],
    [text.whyMusic, text.whyRhythm(text.profile[signals.profile], text.source[signals.source],
      ratio(signals.baseSeconds), ratio(signals.transition), Math.round(signals.motion * 100))],
  ];
  for (const [label, copy] of descriptions) {
    const row = element("div");
    row.append(element("dt", "", label), element("dd", "", copy));
    if (label === text.whyPhotos) {
      const palette = element("span", "swatches");
      for (const color of [scene.palette.background, scene.palette.accent]) {
        const swatch = element("i");
        swatch.style.backgroundColor = color;
        palette.append(swatch);
      }
      row.lastChild.append(palette);
    }
    list.append(row);
  }
  panel.append(list);
  return panel;
}

export function sceneEditor(day, {preview, confirm}) {
  const panel = expandable(editing.title);
  const form = element("form", "pin-form");
  const photoLabel = element("label", "pin-field", editing.main);
  const photo = element("select");
  photo.setAttribute("aria-label", editing.main);
  const automatic = element("option", "", editing.automatic);
  automatic.value = "";
  photo.append(automatic);
  day.photos.forEach((item, index) => {
    const option = element("option", "", text.imageAlt(index + 1));
    option.value = item.id;
    photo.append(option);
  });
  photo.value = day.details.favorite_photo || "";
  photoLabel.append(photo);

  const phraseLabel = element("label", "pin-field", text.pinLabel);
  const phrase = element("input");
  phrase.maxLength = 108;
  const existing = day.details.key_detail || "";
  phrase.defaultValue = day.story.toLocaleLowerCase("ru").includes(existing.toLocaleLowerCase("ru")) ? existing : "";
  phraseLabel.append(phrase);
  form.append(photoLabel, phraseLabel);

  const seconds = new Intl.NumberFormat("ru", {maximumFractionDigits:2});
  let cue;
  let cueChanged = false;
  if (day.track.kind === "file") {
    const cueLabel = element("label", "pin-field", editing.cue);
    cue = element("input");
    cue.type = "number";
    cue.setAttribute("aria-label", editing.cue);
    cue.min = 0;
    cue.step = "any";
    cue.max = Math.max(0, day.track.duration - Math.min(1, day.track.duration));
    cue.value = day.track.cue ?? "";
    cue.placeholder = String(day.scene.soundtrack?.offset ?? 0);
    cue.addEventListener("input", () => { cueChanged = true; });
    cueLabel.append(cue, element("span", "microcopy", editing.excerptHint));
    form.append(cueLabel);
    if (day.scene.soundtrack) {
      const {offset, duration} = day.scene.soundtrack;
      form.append(element("p", "microcopy", editing.excerpt(seconds.format(offset), seconds.format(offset+duration))));
    }
    const alternatives = day.scene.soundtrack?.alternatives || [];
    if (alternatives.length > 1) {
      const options = element("div", "track-switch");
      options.setAttribute("aria-label", editing.options);
      for (const start of alternatives) {
        options.append(button(`${new Intl.NumberFormat("ru").format(start)} с`, "track-choice", () => {
          cue.value = start;
          cueChanged = true;
          invalidate();
        }));
      }
      form.append(options);
    }
  }

  const build = element("button", "outline-button", editing.generate);
  build.type = "submit";
  const status = element("p", "microcopy");
  status.role = "status";
  const result = element("div", "track-switch");
  form.append(build, status, result);
  const proposed = element("p", "microcopy");
  form.insertBefore(proposed, result);
  let changes = 0;
  function invalidate() {
    changes++;
    if (result.childElementCount || build.disabled) {
      status.textContent = editing.changed;
      proposed.textContent = "";
      result.replaceChildren();
    }
  }
  form.addEventListener("input", invalidate);
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    build.disabled = true;
    status.classList.remove("error");
    status.textContent = editing.building;
    result.replaceChildren();
    proposed.textContent = "";
    const started = changes;
    const choices = {photo:photo.value};
    if (phrase.value || phrase.defaultValue || !existing) choices.quote = phrase.value.trim();
    if (cue && cueChanged) choices.cue = cue.value === "" ? null : cue.valueAsNumber;
    try {
      const candidate = await api(`/api/days/${day.id}/scene/preview`, choices);
      if (started !== changes || !form.isConnected) return;
      const prepared = await preview(candidate);
      if (started !== changes || !form.isConnected) return;
      if (candidate.track.kind === "file") {
        const {offset,duration} = candidate.scene.soundtrack;
        proposed.textContent = editing.proposedExcerpt(seconds.format(offset), seconds.format(offset+duration));
      }
      status.textContent = editing.pending;
      const watch = button(editing.watch, "outline-button", prepared);
      const save = button(day.draft ? editing.saveDay : editing.save, "primary-button", async () => {
        save.disabled = true;
        try { await confirm(candidate.previewToken); }
        catch (error) {
          status.textContent = error.status === 409 ? editing.conflict : editing.failure;
          status.classList.add("error");
          save.disabled = false;
        }
      });
      result.append(watch, save);
      if (!day.draft) result.append(button(editing.discard, "text-button", () => {
        status.textContent = editing.discarded;
        proposed.textContent = "";
        result.replaceChildren();
        build.focus();
      }));
    } catch (error) {
      status.textContent = error.message === "invalid_pin" ? text.pinInvalid : editing.failure;
      status.classList.add("error");
    } finally {
      build.disabled = false;
    }
  });
  panel.append(form);
  return panel;
}
