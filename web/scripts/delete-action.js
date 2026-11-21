import {api} from "./client.js";
import {button, element} from "./dom.js";

// Embedded browsers can suppress window.confirm. Keep confirmation within the Mini App.
export function deleteAction({label, question, details, path, payload, returnUrl}) {
  const root = element("div", "delete-action");
  const panel = element("div", "delete-confirmation");
  panel.setAttribute("role", "group");
  panel.setAttribute("aria-label", label);
  panel.hidden = true;
  const status = element("p", "microcopy");
  status.role = "status";
  const trigger = button(label, "minor", () => {
    panel.hidden = false;
    trigger.hidden = true;
    cancel.focus();
  });
  const cancel = button("Отмена", "outline-button", () => {
    panel.hidden = true;
    trigger.hidden = false;
    status.replaceChildren();
    submit.hidden = false;
    trigger.focus();
  });
  let pending = false;
  const submit = button("Да, удалить", "outline-button delete-submit", async () => {
    if (pending) return;
    pending = true;
    submit.disabled = cancel.disabled = true;
    status.textContent = "Удаляем…";
    try {
      await api(path, payload());
    } catch (error) {
      // A retry after a lost response can find that the first request already completed.
      if (!(error.status === 404 && ["day", "film"].includes(error.message))) {
        pending = false;
        submit.disabled = cancel.disabled = false;
        if (error.message === "film_uses_day") {
          const films = element("a", "ink-link", "Открыть фильмы");
          films.href = "/?view=life";
          status.replaceChildren("День входит в сохранённый Life Replay. Убери его из монтажа или удали фильм. ", films);
          submit.hidden = true;
        } else if (error.message === "stale") {
          status.replaceChildren("Запись изменилась. Проверь свежую версию перед удалением. ",
            button("Обновить запись", "minor", () => location.reload()));
          submit.hidden = true;
        } else {
          status.textContent = "Не удалось подтвердить удаление. Попробуй ещё раз.";
        }
        return;
      }
    }
    location.replace(returnUrl);
  });
  const controls = element("div", "actions");
  controls.append(cancel, submit);
  panel.append(element("strong", "", question), element("p", "microcopy", details), controls, status);
  root.append(trigger, panel);
  return root;
}
