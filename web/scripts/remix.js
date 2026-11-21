import {api, asset} from "./client.js";
import {button, element} from "./dom.js";
import {prepare} from "./player.js";

export function remixPanel(day, open) {
  const panel = element("details", "disclosure"), link = element("input"), file = element("input"),
        profile = element("select");
  panel.append(element("summary", "", "Заменить музыку"));
  const group = element("div", "pin-form");
  function field(name, input) {
    input.setAttribute("aria-label", name);
    const label = element("label", "field", name);
    label.append(input);
    group.append(label);
  }
  link.type = "url";
  file.type = "file";
  file.accept = "audio/*";
  file.onchange = () => {
    if (file.files.length)
      link.value = "";
  };
  link.oninput = () => {
    if (link.value)
      file.value = "";
  };
  for (const [key, label] of [
           ["calm", "Мягко"], ["rhythmic", "Ритмично"], ["tense", "Резко"],
           ["rising", "С нарастанием"]]) {
    const option = element("option", "", label);
    option.value = key;
    profile.append(option);
  }
  field("Ссылка на новую песню", link);
  field("Или аудиофайл", file);
  field("Как звучит эта песня?", profile);
  const result = element("div", "actions"), notice = element("p", "notice");
  notice.role = "status";
  group.oninput = () => result.replaceChildren();
  const preview = button("Подготовить монтаж", "outline-button", async () => {
    const path = "/api/days/" + day.id + "/music/";
    if (!file.files.length && !link.value) {
      notice.textContent = "Добавь файл или ссылку.";
      return;
    }
    group.inert = true;
    notice.textContent = "Собираем новый монтаж…";
    result.replaceChildren();
    try {
      const candidate = file.files.length ?
          await api(path + "file?profile=" + profile.value, file.files[0]) :
          await api(path + "link", {url: link.value, profile: profile.value});
      const sources = await prepare(candidate, candidate.scene, asset);
      result.append(button("Посмотреть", "outline-button", () => {
                      document.querySelectorAll("audio").forEach(a => a.pause());
                      open(candidate, candidate.scene, sources, null);
                    }), button("Сохранить музыку", "primary-button", async () => {
                      group.inert = true;
                      try {
                        await api(
                            "/api/days/" + day.id + "/scene/confirm", {token: candidate.previewToken});
                        location.reload();
                      } catch {
                        notice.textContent = "Монтаж изменился. Подготовь его ещё раз.";
                      } finally {
                        group.inert = false;
                      }
                    }));
      notice.textContent = "Новый монтаж готов к просмотру.";
    } catch {
      notice.textContent = "Не удалось собрать монтаж. Проверь файл или ссылку и повтори.";
    } finally {
      group.inert = false;
    }
  });
  group.append(preview, result, notice);
  panel.append(group);
  return panel;
}
