import {api, asset} from "./client.js";
import {button, element} from "./dom.js";
import {prepare} from "./player.js";

export function remixPanel(day, open, {alternate = false, confirm} = {}) {
  const panel = element("details", "disclosure"), link = element("input"), file = element("input"),
        profile = element("select");
  panel.append(element("summary", "", alternate ? "Настроить вторую песню" : "Заменить музыку"));
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
  field(alternate ? "Ссылка на вторую песню" : "Ссылка на новую песню", link);
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
      const query = new URLSearchParams({slot: alternate ? "alternate" : "primary"});
      let candidate;
      if (file.files.length) {
        const audio = file.files[0];
        query.set("profile", profile.value);
        query.set("name", audio.name.replace(/\.[^.]+$/, "").slice(0, 160));
        candidate = await api(path + "file?" + query, audio);
      } else {
        candidate = await api(path + "link?" + query, {url: link.value, profile: profile.value});
      }
      const scene = alternate ? candidate.comparison : candidate.scene;
      const sources = await prepare(candidate, scene, asset);
      result.append(button("Посмотреть", "outline-button", () => {
                      document.querySelectorAll("audio").forEach(a => a.pause());
                      open(candidate, scene, sources, null);
                    }), button(alternate ? "Сохранить вторую песню" : "Сохранить музыку", "primary-button", async () => {
                      group.inert = true;
                      try {
                        if (confirm) {
                          await confirm(candidate.previewToken);
                          panel.open = false;
                          link.value = "";
                          file.value = "";
                          result.replaceChildren();
                        } else {
                          await api("/api/days/" + day.id + "/scene/confirm", {token: candidate.previewToken});
                          location.reload();
                        }
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
