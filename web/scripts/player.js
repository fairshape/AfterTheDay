import { stickerImage, stickerMoment } from "./art.js";
import { scrapbook as copy, text } from "./copy.js";
import { button, dateLabel, element } from "./dom.js";
import { decorate } from "./icons.js";
import { duration, enterPlayer, reducedMotion } from "./motion.js";
import { songLink } from "./song-link.js";

const modal = document.querySelector("#theater");

export async function prepare(day, scene, asset) {
  const paths = [...new Set([day.cover, ...scene.frames.map((frame) => frame.asset)])];
  const source = async (path) => {
    try {
      const url = await asset(path);
      if (path !== scene.track.asset) {
        const image = new Image();
        image.src = url;
        await image.decode();
      }
      return url;
    } catch { return ""; }
  };
  const [images, audio] = await Promise.all([
    Promise.all(paths.map(async (path) => [path, await source(path)])),
    scene.track.asset ? source(scene.track.asset) : "",
  ]);
  return { images: new Map(images), audio };
}

export function openPlayer(day, scene, assets, onClose, {from, telegram} = {}) {
  const track = scene.track;
  const intro = assets.images.get(day.cover) && day.cover !== scene.frames[0].asset
    ? [{asset:day.cover, seconds:duration("cover-hold") / 1000, caption:"", transition:.2, motion:{from:1,to:1,x:0,y:0}}] : [];
  const frames = [...intro, ...scene.frames];
  const total = frames.reduce((sum, frame) => sum + frame.seconds, 0);
  const stickerIndex = intro.length + stickerMoment(day.style.sticker, scene.frames);
  const stickerStart = frames.slice(0, stickerIndex).reduce((sum, frame) => sum + frame.seconds, 0) +
    Math.min(.6, frames[stickerIndex].seconds * .26);
  const settle = duration("sticker") / 1000;
  const stickerHold = duration("sticker-hold") / 1000;
  const origin = document.activeElement;

  const stage = element("div", "stage");
  stage.style.setProperty("--scene-grain", scene.grain);
  const ink = element("div", "stage-ink");
  const projection = element("div", "projection");
  const layers = [element("img", "frame"), element("img", "frame")];
  for (const layer of layers) { layer.alt = ""; projection.append(layer); }
  const missing = element("p", "frame-error", text.unavailablePhoto);
  const veil = element("div", "film-veil");
  const heading = element("header", "scene-heading");
  const back = decorate(button("", "player-icon scene-back", destroy), "back");
  back.setAttribute("aria-label", copy.toMemory);
  const date = element("time", "scene-date", dateLabel(day.date));
  date.dateTime = day.date;
  heading.append(back, date);
  const sticker = stickerImage(day.style.sticker, "playback-sticker");
  sticker.hidden = true;
  const caption = element("p", "scene-caption");
  const status = element("p", "scene-status");
  status.role = "status";
  const footer = element("div", "scene-footer");
  const progress = element("progress", "scene-progress");
  progress.max = total;
  progress.value = 0;
  progress.setAttribute("aria-label", text.progress);
  const time = element("span", "player-time");
  const controls = element("div", "scene-controls");
  const pauseButton = button("", "player-icon primary-control", () => {
    if (running) pause();
    else if (elapsed >= total) restart();
    else play();
  });
  const soundButton = button("", "player-icon sound-control", toggleSound);
  const replayButton = decorate(button("", "player-icon replay-control", restart), "replay");
  replayButton.setAttribute("aria-label", copy.replay);
  const audio = element("audio");
  audio.preload = "auto";
  if (assets.audio) audio.src = assets.audio;
  soundButton.hidden = !assets.audio;
  controls.append(pauseButton, soundButton, replayButton, time);
  if (track.kind === "link") controls.append(songLink(track, telegram, "player-link"));
  const finish = element("div", "player-finish");
  finish.hidden = true;
  finish.append(decorate(button("", "player-action", restart), "replay", copy.again),
    button(copy.toMemory, "player-action secondary", destroy));
  footer.append(status, finish, progress, controls);
  stage.append(ink, projection, missing, veil, heading, sticker, caption, footer, audio);

  let elapsed = 0;
  let started = 0;
  let animation = 0;
  let finishTimer;
  let running = false;
  let muted = false;
  let audioFailed = false;
  let currentIndex = -1;
  let missingAudio = !!track.asset && !assets.audio;
  let closed = false;

  function showAudioStatus() {
    status.textContent = missingAudio ? text.unavailableAudio : audioFailed ? text.playbackSound : "";
    decorate(soundButton, muted ? "muted" : "volume");
    soundButton.setAttribute("aria-label", muted ? text.soundOn : text.soundOff);
  }

  function timestamp(value) {
    return `${Math.floor(value / 60)}:${String(Math.floor(value % 60)).padStart(2, "0")}`;
  }

  function transform(frame, fraction) {
    if (reducedMotion()) return "none";
    const { from, to, x, y } = frame.motion;
    return `translate(${x * fraction}%, ${y * fraction}%) scale(${from + (to - from) * fraction})`;
  }

  function draw(seconds) {
    let offset = 0;
    let index = 0;
    while (index < frames.length - 1 && seconds >= offset + frames[index].seconds) {
      offset += frames[index++].seconds;
    }
    const frame = frames[index];
    const prior = frames[index - 1];
    const local = Math.max(0, seconds - offset);
    const blend = prior && frame.transition > 0 && !reducedMotion() ? Math.min(local / frame.transition, 1) : 1;
    if (currentIndex !== index) {
      const currentSource = assets.images.get(frame.asset);
      const priorSource = prior && assets.images.get(prior.asset);
      if (currentSource) layers[1].src = currentSource;
      else layers[1].removeAttribute("src");
      if (priorSource) layers[0].src = priorSource;
      else layers[0].removeAttribute("src");
      layers[0].style.transform = prior ? transform(prior, 1) : "none";
      layers[0].hidden = !priorSource;
      layers[1].hidden = !currentSource;
      missing.hidden = !!currentSource;
      caption.textContent = frame.caption;
      caption.hidden = !frame.caption;
      currentIndex = index;
    }
    layers[0].style.opacity = layers[1].hidden || blend >= 1 ? 0 : 1;
    layers[1].style.opacity = blend;
    layers[1].style.transform = transform(frame, Math.min(1, local / frame.seconds));
    progress.value = seconds;
    time.textContent = `${timestamp(seconds)} / ${timestamp(total)}`;

    const stickerTime = seconds - stickerStart;
    sticker.hidden = stickerTime < 0 || stickerTime > stickerHold;
    if (!sticker.hidden) {
      const slide = Math.min(1, stickerTime / settle);
      const ease = 1 - (1 - slide) ** 3;
      const scale = .72 + .28 * ease + .13 * Math.sin(slide * Math.PI);
      sticker.style.transform = reducedMotion() ? "none" : `rotate(${-14 + 22 * ease}deg) scale(${scale})`;
      sticker.style.opacity = reducedMotion() ? 1 : Math.min(slide * 3, 1, (stickerHold - stickerTime) * 4);
    }
  }

  function tick(now) {
    if (!running) return;
    elapsed = Math.min(total, (now - started) / 1000);
    draw(elapsed);
    if (elapsed >= total) {
      pause();
      finishTimer = setTimeout(() => { finish.hidden = false; }, duration("final-hold"));
    } else animation = requestAnimationFrame(tick);
  }

  function launchAudio() {
    if (!assets.audio || muted || missingAudio) return;
    const playbackTime = (track.cue || 0) + elapsed;
    if (Number.isFinite(audio.duration) && playbackTime >= audio.duration) return;
    audio.currentTime = playbackTime;
    audio.play().then(() => {
      audioFailed = false;
      showAudioStatus();
    }).catch((error) => {
      if (error.name === "AbortError" || !running || closed) return;
      audioFailed = true;
      muted = true;
      showAudioStatus();
    });
  }

  function play() {
    if (running || closed) return;
    running = true;
    started = performance.now() - elapsed * 1000;
    decorate(pauseButton, "pause");
    pauseButton.setAttribute("aria-label", text.pause);
    launchAudio();
    animation = requestAnimationFrame(tick);
  }

  function pause() {
    running = false;
    cancelAnimationFrame(animation);
    audio.pause();
    decorate(pauseButton, elapsed >= total ? "replay" : "play");
    pauseButton.setAttribute("aria-label", elapsed >= total ? copy.again : text.resume);
  }

  function restart() {
    clearTimeout(finishTimer);
    finish.hidden = true;
    pause();
    elapsed = 0;
    draw(0);
    play();
  }

  function toggleSound() {
    muted = !muted;
    showAudioStatus();
    if (muted) audio.pause();
    else if (running) launchAudio();
  }

  function onVisibility() {
    if (document.hidden && running) pause();
  }

  function cancel(event) {
    event.preventDefault();
    destroy();
  }

  function destroy() {
    if (closed) return;
    closed = true;
    clearTimeout(finishTimer);
    pause();
    audio.removeAttribute("src");
    audio.load();
    modal.close();
    modal.replaceChildren();
    document.removeEventListener("visibilitychange", onVisibility);
    window.removeEventListener("pagehide", pause);
    modal.removeEventListener("cancel", cancel);
    if (origin instanceof HTMLElement && origin.isConnected) origin.focus({preventScroll:true});
    onClose();
  }

  layers[1].addEventListener("error", () => {
    if (!layers[1].hasAttribute("src")) return;
    layers[1].hidden = true;
    layers[0].hidden = true;
    missing.hidden = false;
  });
  audio.addEventListener("error", () => {
    if (!closed && assets.audio) {
      missingAudio = true;
      soundButton.hidden = true;
      showAudioStatus();
    }
  });
  modal.addEventListener("cancel", cancel);
  document.addEventListener("visibilitychange", onVisibility);
  window.addEventListener("pagehide", pause);
  modal.replaceChildren(stage);
  modal.showModal();
  back.focus({preventScroll:true});
  showAudioStatus();
  draw(0);
  enterPlayer(stage, projection, from);
  play();
  return { close: destroy, pause };
}
