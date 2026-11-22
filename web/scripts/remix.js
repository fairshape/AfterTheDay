import {api, asset} from "./client.js";
import {button, element} from "./dom.js";
import {prepare} from "./player.js";

function musicError(error) {
  if (error.status === 401) return "Открой приложение заново из Telegram.";
  if (error.status === 413) return "Файл слишком большой. Выбери аудио до 20 МБ.";
  return {
    link: "Вставь ссылку на конкретную песню.",
    audio_format: "Файл не распознан. Попробуй MP3, M4A, OGG, WAV или FLAC.",
    asset_unavailable: "Не удалось прочитать файлы записи. Проверь, открываются ли её фотографии.",
    speech_unavailable: "Не удалось пересобрать озвучку. Попробуй подготовить монтаж ещё раз.",
    stale: "Запись изменилась. Открой её заново и повтори.",
    day: "Запись больше недоступна.",
  }[error.message] || "Не удалось сохранить песню. Проверь подключение и повтори.";
}

export function remixPanel(getDay, open, {alternate = false, confirm} = {}) {
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
  link.inputMode = "url";
  link.autocapitalize = "off";
  link.spellcheck = false;
  link.maxLength = 4096;
  file.type = "file";
  file.accept = "audio/*,.mp3,.m4a,.ogg,.opus,.wav,.flac";
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
  group.append(element("p", "microcopy", "Аудио до 20 МБ. Песня по ссылке открывается отдельно."));
  field("Как звучит эта песня?", profile);
  const result = element("div", "actions"), notice = element("p", "notice");
  notice.role = "status";
  let generation = 0;
  function resetPreview() {
    generation += 1;
    result.replaceChildren();
    notice.textContent = "";
  }
  group.oninput = resetPreview;
  group.onchange = resetPreview;
  const preview = button("Подготовить монтаж", "outline-button", async () => {
    if (group.inert) return;
    const day = getDay();
    const path = "/api/days/" + day.id + "/music/";
    const audio = file.files[0];
    const url = link.value.trim();
    if (!audio && !url) {
      notice.textContent = "Добавь файл или ссылку.";
      return;
    }
    if (audio?.size > 20 * 1024 * 1024) {
      notice.textContent = musicError({status: 413});
      return;
    }
    const mark = ++generation;
    group.inert = true;
    notice.textContent = "Собираем новый монтаж…";
    result.replaceChildren();
    try {
      const query = new URLSearchParams({slot: alternate ? "alternate" : "primary", revision: day.revision});
      let candidate;
      if (audio) {
        query.set("profile", profile.value);
        query.set("name", audio.name.replace(/\.[^.]+$/, "").slice(0, 160));
        candidate = await api(path + "file?" + query, audio);
      } else {
        candidate = await api(path + "link?" + query, {url, profile: profile.value});
      }
      const scene = alternate ? candidate.comparison : candidate.scene;
      if (!scene || !candidate.previewToken) {
        notice.textContent = "Сервер не вернул предпросмотр. Открой запись заново и повтори.";
        return;
      }
      let sources;
      const watch = button("Посмотреть", "outline-button", () => {
                      if (!sources) return;
                      document.querySelectorAll("audio").forEach(a => a.pause());
                      open(candidate, scene, sources, null);
                    });
      watch.disabled = true;
      result.append(watch, button(alternate ? "Сохранить вторую песню" : "Сохранить музыку", "primary-button", async () => {
                      if (group.inert) return;
                      group.inert = true;
                      notice.textContent = "Сохраняем песню…";
                      try {
                        if (confirm) {
                          await confirm(candidate.previewToken);
                          panel.open = false;
                          link.value = "";
                          file.value = "";
                          resetPreview();
                        } else {
                          await api("/api/days/" + day.id + "/scene/confirm", {token: candidate.previewToken});
                          location.reload();
                        }
                      } catch (error) {
                        notice.textContent = musicError(error);
                      } finally {
                        group.inert = false;
                      }
                    }));
      notice.textContent = "Монтаж готов. Загружаем материалы для просмотра…";
      prepare(candidate, scene, asset).then((loaded) => {
        if (mark !== generation) return;
        sources = loaded;
        watch.disabled = false;
        if (!group.inert) notice.textContent = "Новый монтаж готов к просмотру.";
      }).catch(() => {
        if (mark === generation && !group.inert)
          notice.textContent = "Не удалось загрузить предпросмотр. Можно сохранить монтаж и открыть снова.";
      });
    } catch (error) {
      notice.textContent = musicError(error);
    } finally {
      group.inert = false;
    }
  });
  group.append(preview, result, notice);
  panel.append(group);
  return panel;
}
