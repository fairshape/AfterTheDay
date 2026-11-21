const paths = {
  brand: "M12 2.5c.9 5.5 4 8.6 9.5 9.5-5.5.9-8.6 4-9.5 9.5-.9-5.5-4-8.6-9.5-9.5 5.5-.9 8.6-4 9.5-9.5Z",
  search: "m20.5 20.5-4.3-4.3m2.2-4.7a6.9 6.9 0 1 1-13.8 0 6.9 6.9 0 0 1 13.8 0Z",
  add: "M12 5v14M5 12h14",
  back: "M20 12H5m7-7-7 7 7 7",
  next: "M4 12h15m-6-6 6 6-6 6",
  play: "M9 5v14l11-7L9 5Z",
  pause: "M9 5v14m6-14v14",
  close: "m6 6 12 12M18 6 6 18",
  volume: "M3 9h4l5-4v14l-5-4H3V9Zm13-1a6 6 0 0 1 0 8m2-10a9 9 0 0 1 0 12",
  muted: "M3 9h4l5-4v14l-5-4H3V9Zm13 1 5 5m0-5-5 5",
  replay: "M4 9a8 8 0 1 1 .5 7M4 4v5h5",
  edit: "m14 5 5 5M4 20l5-1L21 7l-4-4L5 15l-1 5Z",
  music: "M9 17V5l11-2v12M9 17a3 3 0 1 1-3-3c2 0 3 1 3 3Zm11-2a3 3 0 1 1-3-3c2 0 3 1 3 3Z",
  image: "M4 4h16v16H4Zm1 13 5-5 3 3 2-2 5 5M15.5 8h.01",
  calendar: "M4 6h16v14H4Zm0 5h16M8 4v4m8-4v4",
  check: "m5 13 4 4 10-10",
};

export function icon(name) {
  const ns = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(ns, "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("aria-hidden", "true");
  const path = document.createElementNS(ns, "path");
  path.setAttribute("d", paths[name]);
  path.setAttribute("fill", name === "brand" || name === "play" ? "currentColor" : "none");
  path.setAttribute("stroke", "currentColor");
  path.setAttribute("stroke-width", "1.8");
  path.setAttribute("stroke-linecap", "round");
  path.setAttribute("stroke-linejoin", "round");
  svg.append(path);
  return svg;
}

export function decorate(node, name, label = "") {
  node.replaceChildren(icon(name));
  if (label) node.append(document.createTextNode(label));
  return node;
}
