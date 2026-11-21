import { text } from "./copy.js";

export function element(tag, className = "", content = "") {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (content) node.textContent = content;
  return node;
}

export function button(label, className, activate) {
  const node = element("button", className, label);
  node.type = "button";
  node.addEventListener("click", activate);
  return node;
}

export function dateLabel(day, withYear = false) {
  const utc = new Date(`${day}T12:00:00Z`);
  return new Intl.DateTimeFormat("ru", {
    month: "long", day: "numeric", ...(withYear ? { year: "numeric" } : {}), timeZone: "UTC",
  }).format(utc).replace(/\sг\.$/, "");
}

export function monthLabel(day) {
  return new Intl.DateTimeFormat("ru", { month: "long", year: "numeric", timeZone: "UTC" })
    .format(new Date(`${day}T12:00:00Z`)).replace(/\sг\.$/, "");
}

export function captionedImage(url, className, asset, alt = "", readySrc = "") {
  const wrap = element("div", `image-wrap ${className}`);
  const figure = element("img");
  figure.alt = alt;
  figure.decoding = "async";
  if (className === "tile-image" || className === "reel-thumb" || className === "shelf-print") figure.loading = "lazy";
  wrap.append(figure);
  const failed = () => {
    if (!figure.parentNode) return;
    figure.remove();
    wrap.append(element("span", "asset-error", text.unavailablePhoto));
  };
  figure.addEventListener("error", failed, { once: true });
  if (readySrc) figure.src = readySrc;
  else asset(url).then((src) => {figure.src = src;}).catch(failed);
  return wrap;
}
