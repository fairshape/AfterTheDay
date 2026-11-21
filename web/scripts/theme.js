import {api} from "./client.js";
import {button, element} from "./dom.js";

function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
  for (const button of document.querySelectorAll(".theme-choice"))
    button.setAttribute("aria-pressed", String(button.dataset.value === theme));
  document.querySelector('meta[name="theme-color"]').content = theme === "neon" ? "#141715" : "#f8f4ea";
}

export async function loadTheme() {
  applyTheme((await api("/api/appearance")).theme);
}

export function themePicker() {
  const group = element("div", "theme-picker");
  group.setAttribute("role", "group");
  group.setAttribute("aria-label", "Тема приложения");
  const status = element("span", "theme-status");
  status.setAttribute("role", "status");
  const choices = [["paper","Бумага"],["neon","Неон"]].map(([value,label]) => {
    const choice = button(label, "theme-choice", async () => {
      const previous = document.documentElement.dataset.theme;
      if (previous === value) return;
      status.textContent = "";
      applyTheme(value);
      sync(true);
      try { await api("/api/appearance", {theme:value}); }
      catch {
        applyTheme(previous);
        status.textContent = "Не удалось сохранить тему. Попробуй ещё раз.";
      } finally { sync(false); }
    });
    choice.dataset.value = value;
    return choice;
  });
  function sync(busy) {
    for (const choice of choices) {
      choice.disabled = busy;
      choice.setAttribute("aria-pressed", String(choice.dataset.value === document.documentElement.dataset.theme));
    }
  }
  sync(false);
  group.append(...choices, status);
  return group;
}
