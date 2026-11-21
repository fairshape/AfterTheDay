import {asset} from "./client.js";
import {button, captionedImage, dateLabel, element as el} from "./dom.js";
import {reducedMotion} from "./motion.js";

export const previewPhoto = url => url + "?preview=1";

export function memoryShelf(days, warmDay) {
  const shelf = el("section", "memory-shelf");
  const backdrop = el("div", "shelf-backdrop");
  backdrop.setAttribute("aria-hidden", "true");
  const photos = [el("img"), el("img")];
  for (const photo of photos) photo.alt = "";
  backdrop.append(...photos);

  const deck = el("div", "shelf-deck");
  const bar = el("div", "shelf-bar");
  const rail = el("div", "shelf-rail");
  rail.setAttribute("role", "group");
  rail.setAttribute("aria-label", "Воспоминания");
  const title = el("h1", "shelf-title");
  const meta = el("p", "shelf-meta");
  const play = el("a", "accent-link", "▶ Пережить день");
  const controls = el("div", "shelf-controls");
  const counter = el("span", "shelf-counter");
  const previous = button("←", "shelf-arrow", () => go(active - 1));
  const next = button("→", "shelf-arrow", () => go(active + 1));
  previous.setAttribute("aria-label", "Предыдущее воспоминание");
  next.setAttribute("aria-label", "Следующее воспоминание");
  controls.append(previous, counter, next);
  bar.append(el("h2", "shelf-label", "Воспоминания"), controls);

  const cards = days.map((day, index) => {
    const card = el("a", "shelf-card");
    card.href = "/?day=" + encodeURIComponent(day.id) + "&from=gallery";
    card.setAttribute("aria-label", day.title);
    card.append(captionedImage(previewPhoto(day.cover), "shelf-print", asset));
    card.addEventListener("focus", () => go(index));
    card.addEventListener("pointerenter", () => warmDay(day.id));
    card.querySelector("img").dataset.original = day.cover;
    rail.append(card);
    return card;
  });

  let active = -1, shown = 0, generation = 0, frame = 0, warmTimer;
  async function reveal(day, mark) {
    const other = day.stills?.find(path => path !== day.cover);
    const incoming = photos[1 - shown];
    for (const path of new Set([other, day.cover].filter(Boolean))) {
      try {
        const src = await asset(previewPhoto(path));
        if (mark !== generation) return;
        const test = new Image();
        test.src = src;
        await test.decode();
        if (mark !== generation) return;
        incoming.src = src;
        incoming.classList.add("is-visible");
        photos[shown].classList.remove("is-visible");
        shown = 1 - shown;
        return;
      } catch {
        if (mark !== generation) return;
      }
    }
    photos[shown].classList.remove("is-visible");
  }

  function select(index) {
    if (index === active) return;
    cards[active]?.removeAttribute("aria-current");
    active = index;
    const day = days[index];
    cards[index].setAttribute("aria-current", "true");
    title.textContent = day.title;
    meta.textContent = [dateLabel(day.date, true), day.place].filter(Boolean).join(" · ");
    play.href = cards[index].href + "&play=1";
    previous.disabled = index === 0;
    next.disabled = index === days.length - 1;
    counter.textContent = (index + 1) + " / " + days.length;
    reveal(day, ++generation);
    clearTimeout(warmTimer);
    warmTimer = setTimeout(() => { if (shelf.isConnected) warmDay(day.id); }, 180);
  }

  function position(index) {
    return cards[index].offsetLeft - cards[0].offsetLeft;
  }

  function go(index) {
    if (!cards[index]) return;
    rail.scrollTo({left: position(index), behavior: reducedMotion() ? "instant" : "smooth"});
  }

  rail.addEventListener("scroll", () => {
    if (frame) return;
    frame = requestAnimationFrame(() => {
      frame = 0;
      const gap = cards.length > 1 ? position(1) : 1;
      const index = Math.min(cards.length - 1, Math.max(0, Math.round(rail.scrollLeft / (gap || 1))));
      select(index);
    });
  }, {passive: true});
  shelf.addEventListener("keydown", event => {
    if (!["ArrowLeft", "ArrowRight"].includes(event.key) || event.altKey || event.metaKey || event.ctrlKey) return;
    event.preventDefault();
    go(active + (event.key === "ArrowLeft" ? -1 : 1));
  });
  const info = el("div", "shelf-info");
  const caption = el("div", "shelf-caption");
  caption.append(title, meta);
  info.append(caption, play);
  deck.append(bar, rail, info);
  shelf.append(backdrop, deck);
  select(0);
  return shelf;
}
