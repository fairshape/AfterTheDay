import {paperNote} from "./memory-table.js";
import {element as el} from "./dom.js";

export function link(label, href, cls = "ink-link") {
  const node = el("a", cls, label);
  node.href = href;
  return node;
}
export const dayURL = id => "/?day=" + encodeURIComponent(id);
export function heading(label, mark = "") {
  const row = el("div", "section-title");
  row.append(el("h2", "", label));
  if (mark)
    row.append(el("span", "mono", mark));
  return row;
}
export const worlds = {
  bright: ["Светлые", "#ffcb65"],
  pleasant: ["Тёплые", "#acbd8a"],
  tense: ["Напряжённые", "#b09acc"],
  funny: ["Смешные", "#ff977d"],
  sad: ["Грустные", "#a6bdcf"]
};
export function memoryTile(day) {
  const note = paperNote(day);
  note.classList.add("archive-note");
  note.dataset.memory = day.id;
  return note;
}
