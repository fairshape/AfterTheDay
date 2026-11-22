import {asset} from "./client.js";
import {button, dateLabel, element as el} from "./dom.js";

export async function prepareFilm(film) {
  const urls = new Map(), tracks = new Map();
  await Promise.all([...new Set(film.shots.map(s => s.asset))].map(async path => {
    urls.set(path, await asset(path));
  }));
  const needed = film.music === "sections" ? Object.keys(film.tracks) :
      film.music === "silent"              ? [] :
                                             [film.music];
  await Promise.all(needed.map(async key => tracks.set(key, await asset(film.tracks[key].url))));
  return () => playFilm(film, urls, tracks);
}

function playFilm(film, urls, tracks) {
  const dlg = document.querySelector("#theater"), stage = el("section", "life-screen"),
        picture = el("img", "life-photo"), shade = el("div", "life-shade");
  picture.alt = "";
  const previous=el("img","life-photo previous-exposure");previous.alt="";previous.hidden=true;
  const head = el("header", "life-heading"), chapter = el("span", "mono");
  const story = el("div", "life-caption"), date = el("small", "mono"), caption = el("h2");
  const controls = el("div", "life-controls"), seek = el("input"), volume = el("input"),
        notice = el("p", "microcopy");
  const audio = el("audio");
  let at = 0, last = performance.now(), running = false, raf = 0, index = -1, music = null,
      failed = false, visible = true;
  seek.type = "range";
  seek.min = 0;
  seek.max = film.duration;
  seek.step = .01;
  seek.setAttribute("aria-label", "Позиция в фильме");
  volume.type = "range";
  volume.min = 0;
  volume.max = 1;
  volume.step = .05;
  volume.value = .8;
  volume.setAttribute("aria-label", "Громкость");
  const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
  picture.onerror = () => {
    notice.textContent = "Фотография недоступна.";
  };
  audio.onerror = () => {
    failed = true;
    notice.textContent = "Звук недоступен. Фильм продолжается.";
  };
  function stop() {
    running = false;
    cancelAnimationFrame(raf);
    audio.pause();
    toggle.textContent = at >= film.duration ? "Повторить" : "Продолжить";
  }
  function close() {
    stop();
    audio.onerror = null;
    audio.removeAttribute("src");
    audio.load();
    dlg.removeEventListener("cancel", cancel);
    dlg.close();
    dlg.replaceChildren();
    document.removeEventListener("visibilitychange", visibility);
    window.removeEventListener("pagehide", stop);
    window.removeEventListener("popstate", pop);
    if (history.state?.lifePlayer)
      history.back();
  }
  function cancel(e) {
    e.preventDefault();
    close();
  }
  function pop() {
    if (dlg.open)
      close();
  }
  function visibility() {
    if (document.hidden)
      stop();
  }
  function render(force = false) {
    let j = film.shots.findIndex(s => at < s.start + s.seconds);
    if (j < 0)
      j = film.shots.length - 1;
    const s = film.shots[j], local = Math.max(0, at - s.start);
    if (j !== index) {
      const next=film.shots[j+1];if(next){const preload=new Image();preload.src=urls.get(next.asset);}
      if(j>0&&!reduced){
        const left=film.shots[j-1];previous.src=urls.get(left.asset);
        previous.style.objectFit=left.crop.fit||"cover";previous.style.objectPosition=((left.crop.x??.5)*100)+"% "+((left.crop.y??.5)*100)+"%";
        previous.style.transform="scale("+left.motion.to+")";
      }
      picture.src = urls.get(s.asset);
      picture.style.filter=`contrast(${s.treatment?.contrast??1}) saturate(${s.treatment?.saturation??1})`;
      picture.style.objectFit = s.crop.fit || "cover";
      picture.style.objectPosition = ((s.crop.x ?? .5) * 100) + "% " + ((s.crop.y ?? .5) * 100) + "%";
      caption.textContent = s.caption;
      date.textContent = dateLabel(s.date, true) + "  /  " + s.title;
      chapter.textContent = "LIFE REPLAY   /   " + film.title;
      stage.style.setProperty("--film-accent", s.emotion.accent);
      caption.classList.toggle("serif-caption", s.emotion.type === "serif");
      index = j;
    }
    picture.style.transform = reduced ? "none" :
                                        "scale(" +
            (s.motion.from + (s.motion.to - s.motion.from) * Math.min(1, local / s.seconds)) + ")";
    const dissolve=reduced||j===0?1:Math.min(1,local/Math.max(.04,s.transition));
    picture.style.opacity=String(dissolve);
    previous.hidden=dissolve>=1;
    caption.style.opacity=String(reduced?1:Math.min(1,Math.max(0,(local-.12)/.18)));
    const key = film.music === "sections" ? s.day : film.music;
    const config = film.tracks[key];
    if (tracks.has(key)) {
      const desired = film.music === "sections" ? s.musicTime + local : config.offset + at;
      const playAt = desired % config.duration;
      if (music !== key) {
        audio.src = tracks.get(key);
        music = key;
        failed = false;
        force = true;
      }
      if (!failed && (force || Math.abs(audio.currentTime - playAt) > .28) && audio.readyState >= 1)
        audio.currentTime = playAt;
      if (!failed && running && audio.paused)
        audio.play().catch(e => {
          if (e.name !== "AbortError") {
            failed = true;
            notice.textContent = "Звук недоступен. Фильм продолжается.";
          }
        });
      const chapterStart = at - local - (s.musicTime - config.offset);
      const nextChapter =
          film.shots.slice(j + 1).find(shot => shot.day !== s.day)?.start ?? film.duration;
      const chapterFade = film.music === "sections" ?
          Math.min((at - chapterStart + .02) / .25, (nextChapter - at) / .25) :
          1;
      audio.volume = Number(volume.value) *
          Math.max(0, Math.min(1, (at + .01) / .3, (film.duration - at) / .4, chapterFade));
    } else {
      audio.pause();
      music = null;
    }
    seek.value = at;
  }
  function tick(now) {
    if (!running)
      return;
    const delta = (now - last) / 1000;
    last = now;
    if (!music || failed || audio.readyState >= 3)
      at = Math.min(film.duration, at + delta);
    render();
    if (at >= film.duration)
      stop();
    else
      raf = requestAnimationFrame(tick);
  }
  function start() {
    if (at >= film.duration)
      at = 0;
    running = true;
    last = performance.now();
    toggle.textContent = "Пауза";
    render(true);
    raf = requestAnimationFrame(tick);
  }
  const toggle = button("Пауза", "solid-btn", () => running ? stop() : start());
  seek.oninput = () => {
    at = Number(seek.value);
    last = performance.now();
    render(true);
  };
  volume.oninput = () => render();
  head.append(chapter, button("Закрыть ×", "player-action", close));
  story.append(date, caption);
  controls.append(seek, toggle, button("С начала", "player-action", () => {
                    at = 0;
                    render(true);
                    if (!running)
                      start();
                  }), button("Текст", "player-action", () => {
                    visible = !visible;
                    caption.hidden = !visible;
                  }), button("Звук", "player-action", e => {
                    audio.muted = !audio.muted;
                    e.currentTarget.textContent = audio.muted ? "Включить звук" : "Звук";
                  }), volume, notice);
  stage.append(previous,picture, shade, head, story, controls, audio);
  dlg.replaceChildren(stage);
  dlg.showModal();
  dlg.addEventListener("cancel", cancel);
  history.pushState({lifePlayer: true}, "", location.href);
  window.addEventListener("popstate", pop);
  document.addEventListener("visibilitychange", visibility);
  window.addEventListener("pagehide", stop);
  start();
}
