import { stickerImage, stickerMoment } from "./art.js";
import { editing, scrapbook as copy, text, voiceText } from "./copy.js";
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
  const narration = day.narration?.sceneKey && day.narration.sceneKey === scene.narrationKey ?
    (day.narration.mix || day.narration.voiceOnly) : null;
  const audioSource = async (url) => url ? asset(url).catch(() => "") : "";
  const [images, audio, voiced] = await Promise.all([
    Promise.all(paths.map(async (path) => [path, await source(path)])),
    audioSource(scene.track.asset), audioSource(narration?.asset),
  ]);
  return { images: new Map(images), audio, voiced };
}

export function openPlayer(day, scene, assets, onClose, {from, telegram} = {}) {
  const track = scene.track;
  const precise = scene.version >= 2;
  const soundtrack = scene.soundtrack;
  const intro = !precise && !assets.voiced && assets.images.get(day.cover) && day.cover !== scene.frames[0].asset
    ? [{asset:day.cover, seconds:duration("cover-hold") / 1000, caption:"", transition:.2, motion:{from:1,to:1,x:0,y:0}}] : [];
  const frames = [...intro, ...scene.frames];
  const total = soundtrack?.duration ?? frames.reduce((sum, frame) => sum + frame.seconds, 0);
  const musicOffset = soundtrack?.offset ?? track.cue ?? 0;
  let narrated = !!assets.voiced;
  const offset = () => narrated ? 0 : musicOffset;
  const selectedAudio = () => narrated ? assets.voiced : assets.audio;
  const stickerIndex = intro.length + stickerMoment(day.style.sticker, scene.frames);
  const stickerStart = frames.slice(0, stickerIndex).reduce((sum, frame) => sum + frame.seconds, 0) +
    Math.min(.6, frames[stickerIndex].seconds * .26);
  const settle = duration("sticker") / 1000;
  const stickerHold = duration("sticker-hold") / 1000;
  const origin = document.activeElement;

  const stage = element("div", "stage");
  stage.style.setProperty("--scene-grain", scene.grain);
  const ink = element("div", "stage-ink");
  if (precise) {
    ink.style.backgroundColor = scene.palette.shadow;
    stage.style.setProperty("--scene-accent", scene.palette.accent);
  }
  const projection = element("div", "projection");
  projection.style.filter = `contrast(${scene.treatment?.contrast ?? 1}) saturate(${scene.treatment?.saturation ?? 1})`;
  const layers = [element("img", "frame"), element("img", "frame")];
  for (const layer of layers) { layer.alt = ""; projection.append(layer); }
  const openingPrint = frames[0].asset !== day.cover && from?.naturalWidth ? from.cloneNode() : null;
  if(openingPrint) {
    openingPrint.className="opening-print";
    openingPrint.alt="";
    projection.append(openingPrint);
  }
  const missing = element("p", "frame-error", text.unavailablePhoto);
  const veil = element("div", "film-veil");
  const heading = element("header", "scene-heading");
  const back = decorate(button("", "player-icon scene-back", destroy), "back");
  back.setAttribute("aria-label", copy.toMemory);
  const date = element("time", "scene-date", dateLabel(day.date));
  date.dateTime = day.date;
  heading.append(back, date);
  const sticker = stickerImage(day.style.sticker, "playback-sticker");
  if (sticker) sticker.hidden = true;
  const caption = element("p", "scene-caption");
  caption.style.fontFamily = day.emotion?.type === "serif" ? "var(--serif)" : "var(--body)";
  let captionsOn = true;
  const status = element("p", "scene-status");
  status.role = "status";
  const footer = element("div", "scene-footer");
  const progress = element("progress", "scene-progress");
  progress.max = total;
  progress.value = 0;
  progress.setAttribute("aria-label", text.progress);
  const scrub = element("input", "scene-scrub");
  scrub.type = "range";
  scrub.min = 0;
  scrub.max = total;
  scrub.step = .01;
  scrub.value = 0;
  scrub.setAttribute("aria-label", editing.seek);
  const progressBar = element("div", "scene-scrubber");
  progressBar.append(progress, scrub);
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
  if (selectedAudio()) audio.src = selectedAudio();
  soundButton.hidden = !selectedAudio();
  const narrationButton = decorate(button("", "player-icon narration-control", toggleNarration), "voice");
  narrationButton.hidden = !assets.voiced;
  controls.append(pauseButton, soundButton, narrationButton, replayButton, time);
  const options = element("details", "play-options");
  options.append(element("summary", "", "Настройки показа"));
  const captionsButton = button("Подписи", "player-action", () => {
    captionsOn = !captionsOn;
    captionsButton.setAttribute("aria-pressed", String(captionsOn));
    draw(elapsed);
  });
  captionsButton.setAttribute("aria-pressed","true");
  options.append(captionsButton);
  if (selectedAudio()) {
    const volume = element("input");
    volume.type = "range"; volume.min = 0; volume.max = 1; volume.step = .05; volume.value = 1;
    volume.setAttribute("aria-label", "Громкость");
    volume.oninput = () => {audio.volume = Number(volume.value);}; options.append(volume);
  }
  if(document.fullscreenEnabled) options.append(button("Полный экран","player-action",async()=>{
    try{if(document.fullscreenElement)await document.exitFullscreen();else await document.documentElement.requestFullscreen();}
    catch{status.textContent="Полный экран недоступен.";}
  }));
  heading.append(options);
  const linkedSong = element("div", "player-song");
  if (track.kind === "link") {
    linkedSong.append(element("p", "", editing.linkedScene), songLink(track, telegram, "player-link"));
  } else linkedSong.hidden = true;
  const finish = element("div", "player-finish");
  finish.hidden = true;
  finish.append(decorate(button("", "player-action", restart), "replay", copy.again),
    button(copy.toMemory, "player-action secondary", destroy));
  footer.append(status, finish, linkedSong, progressBar, controls);
  stage.append(ink, projection, missing, veil, heading);
  if (sticker) stage.append(sticker);
  stage.append(caption, footer, audio);

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
  let buffering = false;
  const useAudioClock = () => (precise || !!assets.voiced) && !!selectedAudio() && !missingAudio && !audioFailed;

  function showAudioStatus() {
    status.textContent = missingAudio ? text.unavailableAudio : audioFailed ? text.playbackSound : buffering && running ? editing.buffering : "";
    decorate(soundButton, muted ? "muted" : "volume");
    soundButton.setAttribute("aria-label", muted ? text.soundOn : text.soundOff);
    narrationButton.setAttribute("aria-label", narrated ? voiceText.toggleOff : voiceText.toggleOn);
    narrationButton.classList.toggle("voice-active", narrated);
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
    if(openingPrint) {
      openingPrint.hidden=seconds>=.72;
      openingPrint.style.opacity=reducedMotion()?0:String(Math.min(1,Math.max(0,(.72-seconds)/.38)));
    }
    let shotStart = 0;
    let index = 0;
    while (index < frames.length - 1 && seconds >= (frames[index + 1].start ?? shotStart + frames[index].seconds)) {
      shotStart = frames[index + 1].start ?? shotStart + frames[index].seconds;
      index++;
    }
    const frame = frames[index];
    const prior = frames[index - 1];
    const local = Math.max(0, seconds - shotStart);
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
      for (const [layer, shot] of [[layers[0], prior], [layers[1], frame]]) {
        layer.style.objectFit = shot?.crop?.fit ?? "";
        layer.style.objectPosition = shot?.crop ? `${shot.crop.x*100}% ${shot.crop.y*100}%` : "";
      }
      currentIndex = index;
    }
    layers[0].style.opacity = layers[1].hidden || blend >= 1 ? 0 : 1;
    layers[1].style.opacity = blend;
    layers[1].style.transform = transform(frame, Math.min(1, local / frame.seconds));
    const captionOut = frame.captionOut ?? frame.seconds;
    caption.hidden = !captionsOn || !frame.caption || local < (frame.captionIn ?? 0) || (local > captionOut && index !== frames.length - 1);
    progress.value = seconds;
    scrub.value = seconds;
    scrub.setAttribute("aria-valuetext", timestamp(seconds));
    time.textContent = `${timestamp(seconds)} / ${timestamp(total)}`;

    const stickerTime = seconds - stickerStart;
    if (sticker) sticker.hidden = stickerTime < 0 || stickerTime > stickerHold;
    if (sticker && !sticker.hidden) {
      const slide = Math.min(1, stickerTime / settle);
      const ease = 1 - (1 - slide) ** 3;
      const scale = .72 + .28 * ease + .13 * Math.sin(slide * Math.PI);
      sticker.style.transform = reducedMotion() ? "none" : `rotate(${-14 + 22 * ease}deg) scale(${scale})`;
      sticker.style.opacity = reducedMotion() ? 1 : Math.min(slide * 3, 1, (stickerHold - stickerTime) * 4);
    }
  }

  function finishScene() {
    elapsed = total;
    draw(total);
    pause();
    finishTimer = setTimeout(() => { finish.hidden = false; }, duration("final-hold"));
  }

  function tick(now) {
    if (!running) return;
    elapsed = Math.min(total, Math.max(0, useAudioClock() ? audio.currentTime - offset() : (now - started) / 1000));
    draw(elapsed);
    if (elapsed >= total - .008) finishScene();
    else animation = requestAnimationFrame(tick);
  }

  function launchAudio() {
    if (!selectedAudio() || missingAudio || (!precise && !assets.voiced && muted)) return;
    const playbackTime = offset() + elapsed;
    if (Number.isFinite(audio.duration) && playbackTime >= audio.duration) return;
    if (Math.abs(audio.currentTime - playbackTime) > .03) audio.currentTime = playbackTime;
    audio.play().then(() => {
      audioFailed = false;
      showAudioStatus();
    }).catch((error) => {
      if (error.name === "AbortError" || !running || closed) return;
      audioFailed = true;
      buffering = false;
      started = performance.now() - elapsed * 1000;
      muted = true;
      audio.muted = true;
      showAudioStatus();
    });
  }

  scrub.addEventListener("input", () => {
    clearTimeout(finishTimer);
    finish.hidden = true;
    elapsed = Math.min(total, Number(scrub.value));
    if (selectedAudio() && !missingAudio) audio.currentTime = offset() + elapsed;
    started = performance.now() - elapsed * 1000;
    draw(elapsed);
    if (elapsed >= total) finishScene();
    else if (!running) pause();
  });

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
    buffering = false;
    showAudioStatus();
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
    if (precise || assets.voiced) {
      audio.muted = muted;
      if (!muted && running && audioFailed) launchAudio();
    } else if (muted) audio.pause();
    else if (running) launchAudio();
  }

  function toggleNarration() {
    if (!assets.voiced) return;
    const wasRunning = running;
    pause();
    narrated = !narrated;
    audioFailed = false;
    missingAudio = false;
    if (selectedAudio()) audio.src = selectedAudio();
    else audio.removeAttribute("src");
    audio.load();
    audio.muted = muted;
    soundButton.hidden = !selectedAudio();
    showAudioStatus();
    if (wasRunning) play();
  }

  function onVisibility() {
    if (document.hidden && running) pause();
  }

  function cancel(event) {
    event.preventDefault();
    destroy();
  }

  function destroy() {
    if(document.fullscreenElement)document.exitFullscreen().catch(()=>{});
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
  audio.addEventListener("waiting", () => {
    if (useAudioClock()) {
      buffering = true;
      showAudioStatus();
    }
  });
  audio.addEventListener("playing", () => {
    buffering = false;
    showAudioStatus();
  });
  audio.addEventListener("ended", () => {
    if (running && useAudioClock()) finishScene();
  });
  audio.addEventListener("error", () => {
    if (!closed && selectedAudio()) {
      started = performance.now() - elapsed * 1000;
      buffering = false;
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
