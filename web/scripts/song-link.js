import { text } from "./copy.js";
import { element } from "./dom.js";

export function songLink(track, telegram, className) {
  const link = element("a", className, text.openSong);
  link.href = track.url;
  link.target = "_blank";
  link.rel = "noopener noreferrer";
  if (telegram?.initData && track.url.startsWith("https://")) {
    link.addEventListener("click", (event) => {
      try {
        telegram.openLink(track.url);
        event.preventDefault();
      } catch { /* Use the original link when the Telegram bridge is unavailable. */ }
    });
  }
  return link;
}
