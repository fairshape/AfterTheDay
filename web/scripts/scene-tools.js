import { api } from "./client.js";
import { text } from "./copy.js";
import { element } from "./dom.js";

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
  const descriptions = [
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

export function pinPanel(day, refresh) {
  const panel = expandable(text.pinHeading);
  const form = element("form", "pin-form");
  const phraseLabel = element("label", "pin-field", text.pinLabel);
  const phrase = element("input");
  phrase.maxLength = 108;
  const savedPhrase = day.details.key_detail || "";
  phrase.defaultValue = day.story.toLocaleLowerCase("ru").includes(savedPhrase.toLocaleLowerCase("ru")) ? savedPhrase : "";
  phraseLabel.append(phrase);
  const photoLabel = element("label", "pin-field", text.pinFavorite);
  const select = element("select");
  const blank = element("option", "", text.pinNoPhoto);
  blank.value = "";
  select.append(blank);
  day.photos.forEach((photo, index) => {
    const option = element("option", "", text.imageAlt(index + 1));
    option.value = photo.id;
    select.append(option);
  });
  select.value = day.details.favorite_photo || "";
  photoLabel.append(select);
  const save = element("button", "outline-button", text.pinSave);
  save.type = "submit";
  const status = element("p", "microcopy");
  status.role = "status";
  form.append(element("p", "microcopy", text.pinHint), phraseLabel, photoLabel, save, status);
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    save.disabled = true;
    status.textContent = "";
    try {
      const payload = { photo: select.value };
      if (phrase.value || phrase.defaultValue || !savedPhrase) payload.quote = phrase.value.trim();
      const updated = await api(`/api/days/${day.id}/pin`, payload);
      if (form.isConnected) refresh(updated);
    } catch (error) {
      status.textContent = error.message === "invalid_pin" ? text.pinInvalid : text.pinFailed;
      save.disabled = false;
    }
  });
  panel.append(form);
  return panel;
}

