import { api, asset } from "./client.js";
import { voiceText as copy } from "./copy.js";
import { button, element } from "./dom.js";

export function storyAudio(day, editVoice) {
  const container = element("div", "story-audio");
  const track = day.narration?.full;
  const listen = button(copy.listen, "outline-button", async () => {
    if (!track) {
      editVoice();
      return;
    }
    if (audio.src) {
      if (audio.paused) audio.play().catch(() => { audio.hidden = false; });
      else audio.pause();
      return;
    }
    listen.disabled = true;
    try {
      audio.src = await asset(track.asset);
      audio.hidden = false;
      await audio.play().catch(() => {});
    } catch {
      status.textContent = copy.fullFail;
    } finally {
      listen.disabled = false;
    }
  });
  const audio = element("audio", "original-audio");
  audio.controls = true;
  audio.hidden = true;
  audio.setAttribute("aria-label", copy.listen);
  const status = element("p", "microcopy error");
  status.role = "status";
  container.append(listen, audio, status);
  return container;
}

export function voicePanel(day, updateDay, stageVoice = null) {
  const panel = element("details", "disclosure voice-panel");
  panel.append(element("summary", "", copy.title));
  const form = element("div", "pin-form");
  const voices = element("select");
  voices.setAttribute("aria-label", copy.voice);
  const rates = element("select");
  rates.setAttribute("aria-label", copy.tempo);
  for (const id of ["slow", "normal", "lively"]) {
    const option = element("option", "", copy[id]);
    option.value = id;
    rates.append(option);
  }
  rates.value = day.narration?.rate || day.voiceSuggestion || "normal";
  for (const [label, select] of [[copy.voice, voices], [copy.tempo, rates]]) {
    const field = element("label", "pin-field", label);
    field.append(select);
    form.append(field);
  }
  const sample = button(copy.sample, "outline-button", generate);
  const save = button(copy.save, "primary-button", confirm);
  save.hidden = true;
  sample.disabled = true;
  const player = element("audio", "original-audio");
  player.controls = true;
  player.hidden = true;
  player.setAttribute("aria-label", copy.sampleLabel);
  const status = element("p", "microcopy");
  status.role = "status";
  const buttons = element("div", "track-switch");
  buttons.append(sample);
  if (!stageVoice) buttons.append(save);
  form.append(element("p", "microcopy", copy.private), player, buttons, status);
  panel.append(form);

  let token;
  let generation = 0;
  function invalidate() {
    generation++;
    token = null;
    save.hidden = true;
    player.pause();
    player.hidden = true;
    status.textContent = "";
  }
  form.addEventListener("change", () => {
    invalidate();
    if (stageVoice && voices.value) stageVoice({voice: voices.value, rate: rates.value});
  });
  panel.addEventListener("toggle", () => { if (!panel.open) player.pause(); });

  api("/api/voices").then(({voices: available}) => {
    for (const id of available) {
      const option = element("option", "", copy[id]);
      option.value = id;
      voices.append(option);
    }
    if (available.includes(day.narration?.voice)) voices.value = day.narration.voice;
    sample.disabled = !available.length;
    if (!available.length) status.textContent = copy.unavailable;
  }).catch(() => { status.textContent = copy.unavailable; });

  async function generate() {
    invalidate();
    const request = generation;
    sample.disabled = true;
    status.textContent = copy.loading;
    try {
      const result = await api(`/api/days/${day.id}/voice/preview`, {voice:voices.value, rate:rates.value});
      const url = await asset(result.audio);
      if (request !== generation || !panel.isConnected) return;
      player.src = url;
      player.hidden = false;
      token = result.token;
      save.hidden = false;
      sample.textContent = copy.sample;
      status.textContent = "";
    } catch {
      if (request === generation) {
        sample.textContent = copy.retry;
        status.textContent = copy.fail;
      }
    } finally {
      sample.disabled = false;
    }
  }

  async function confirm() {
    if (!token) return;
    player.pause();
    save.disabled = true;
    sample.disabled = true;
    voices.disabled = true;
    rates.disabled = true;
    status.textContent = copy.loading;
    try {
      const updated = await api(`/api/days/${day.id}/voice/confirm`, {token});
      updateDay(updated);
      save.hidden = true;
      status.textContent = copy.saved;
    } catch {
      status.textContent = copy.fail;
      save.textContent = copy.retry;
    } finally {
      save.disabled = false;
      sample.disabled = false;
      voices.disabled = false;
      rates.disabled = false;
    }
  }
  return panel;
}
