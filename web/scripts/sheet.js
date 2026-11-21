import { api, asset } from "./client.js";
import { art, memoryCover, stickerImage } from "./art.js";
import { scrapbook as copy, text } from "./copy.js";
import { button, captionedImage, element } from "./dom.js";
import { decorate } from "./icons.js";

const dialog = document.querySelector("#sheet");

export function openSheet(title, body, onClose, { kind = "", footer } = {}) {
  const origin = document.activeElement;
  const wrapper = element("section", `sheet-inner ${kind}`);
  const head = element("header", "sheet-head");
  const heading = element("h2", "", title);
  heading.id = "sheet-title";
  const dismiss = decorate(button("", "icon-button", close), "close");
  dismiss.setAttribute("aria-label", text.close);
  head.append(heading, dismiss);
  wrapper.append(head, body);
  if (footer) wrapper.append(footer);
  dialog.replaceChildren(wrapper);
  dialog.dataset.kind = kind;
  dialog.showModal();
  dismiss.focus({preventScroll:true});

  function cancel(event) {
    event.preventDefault();
    close();
  }

  function backdrop(event) {
    if (event.target === dialog) close();
  }

  function close() {
    if (!dialog.open || !wrapper.isConnected) return;
    dialog.close();
    dialog.replaceChildren();
    dialog.removeEventListener("cancel", cancel);
    dialog.removeEventListener("click", backdrop);
    if (origin instanceof HTMLElement && origin.isConnected) origin.focus({preventScroll:true});
    onClose();
  }

  dialog.addEventListener("cancel", cancel);
  dialog.addEventListener("click", backdrop);
  return { close };
}

export function coverEditor(day, commit, onClose) {
  let style = {...day.style};
  let resetting = false;
  const content = element("div", "sheet-content editor-content");
  const preview = element("div", "cover-preview");
  preview.setAttribute("aria-label", copy.editorPreview);
  const selection = element("div", "editor-tools");
  const status = element("p", "sheet-status");
  status.role = "status";

  const groups = [
    {key:"sticker", label:copy.sticker, items:art.stickers,
      render: (item) => stickerImage(item.id)},
    {key:"color", label:copy.color, items:day.coverPalette ?
      [{id:"auto", label:copy.photoColor, hex:day.coverPalette.field}, ...art.colors] : art.colors, render: (item) => {
      const swatch = element("span", "color-chip");
      swatch.style.backgroundColor = item.hex;
      return swatch;
    }},
    {key:"photo", label:copy.photo, items:day.photos.map((item, index) => ({...item, label:text.imageAlt(index + 1)})),
      render: (item) => captionedImage(item.src, "choice-photo", asset)},
  ];

  const choices = [];
  for (const {key, label, items, render} of groups) {
    const group = element("fieldset", `editor-group editor-${key}`);
    group.append(element("legend", "", label));
    const row = element("div", "editor-choices");
    for (const item of items) {
      const choice = button("", "editor-choice", () => {
        style[key] = item.id;
        resetting = false;
        status.textContent = "";
        update();
      });
      choice.dataset.kind = key;
      choice.dataset.value = item.id;
      choice.append(render(item));
      const suggested = key === "color" && item.id === day.photoColor;
      const labelNode = element("span", "choice-label", suggested ? copy.photoColor : item.label);
      if (suggested) choice.setAttribute("aria-label", `${item.label} · ${copy.photoColor}`);
      if (key === "photo") {
        choice.setAttribute("aria-label", item.label);
        labelNode.classList.add("visually-hidden");
      }
      choice.append(labelNode);
      row.append(choice);
      choices.push(choice);
    }
    group.append(row);
    selection.append(group);
  }

  const reset = button(copy.resetStyle, "text-button", () => {
    style = {...day.originalStyle};
    resetting = true;
    status.textContent = copy.restored;
    update();
  });
  const footer = element("footer", "sheet-footer");
  const save = button(copy.save, "primary-button", async () => {
    save.disabled = true;
    status.textContent = "";
    status.classList.remove("error");
    try {
      const updated = await api(`/api/days/${day.id}/cover`, {style:resetting ? null : style});
      commit(updated);
      controller.close();
    } catch {
      if (save.isConnected) {
        status.textContent = copy.coverError;
        status.classList.add("error");
        save.disabled = false;
      }
    }
  });
  footer.append(status, save, reset);
  content.append(preview, selection);

  function update() {
    const previous = preview.querySelector(".cover-photo img");
    const same = preview.dataset.photo === style.photo && previous?.naturalWidth;
    preview.replaceChildren(memoryCover(day, "preview", {style, readySrc:same ? previous.src : ""}));
    preview.dataset.photo = style.photo;
    for (const choice of choices) choice.setAttribute("aria-pressed", String(style[choice.dataset.kind] === choice.dataset.value));
  }

  update();
  const controller = openSheet(copy.edit, content, onClose, {kind:"editor-sheet", footer});
  return controller;
}

export function photoViewer(day, index, onClose) {
  const content = element("div", "sheet-content gallery-viewer");
  const picture = element("figure");
  const controls = element("div", "gallery-controls");
  const position = element("span", "gallery-position");
  position.role = "status";
  const back = decorate(button("", "icon-button", () => turn(-1)), "back");
  back.setAttribute("aria-label", copy.galleryBack);
  const next = decorate(button("", "icon-button", () => turn(1)), "next");
  next.setAttribute("aria-label", copy.galleryNext);
  controls.append(back, position, next);
  content.append(picture, controls);

  function turn(direction) {
    index = Math.max(0, Math.min(day.photos.length - 1, index + direction));
    const photo = day.photos[index];
    picture.replaceChildren(captionedImage(photo.src, "gallery-full", asset, text.imageAlt(index+1)));
    if (photo.caption) picture.append(element("figcaption", "", photo.caption));
    position.textContent = copy.photoPosition(index+1, day.photos.length);
    back.disabled = index === 0;
    next.disabled = index === day.photos.length-1;
  }

  content.addEventListener("keydown", (event) => {
    if (event.key === "ArrowLeft") turn(-1);
    if (event.key === "ArrowRight") turn(1);
  });
  turn(0);
  return openSheet(copy.photos, content, onClose, {kind:"gallery-sheet"});
}
