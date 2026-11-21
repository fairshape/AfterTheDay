import {api, asset} from "./client.js";
import {moodPicker} from "./collection.js";
import {button, captionedImage, element as el} from "./dom.js";
import {dayURL, heading} from "./museum.js";

export async function capture() {
  let draft = await api("/api/capture", {}), step = 0;
  const root = el("section", "workspace capture"), panel = el("div", "capture-panel"),
        bar = el("div", "steps"), status = el("p", "notice");
  status.role = "status";
  const story = el("textarea"), title = el("input"), date = el("input"), reflection = el("textarea"),
        url = el("input"), profile = el("select");
  date.type = "date";
  date.value = draft.date;
  story.value = draft.story;
  story.placeholder = "Какую деталь дня хочется запомнить?";
  title.value = draft.title;
  reflection.value = draft.reflection;
  url.value = draft.track.url || "";
  for (const [key, name] of Object.entries({
         calm: "Мягко",
         rhythmic: "Ритмично",
         tense: "Напряжённо",
         rising: "Постепенно нарастает"
       })) {
    const opt = el("option", "", name);
    opt.value = key;
    profile.append(opt);
  }
  profile.value = draft.track.profile || "calm";
  const moods = new Set(draft.moods || []);
  let moodEdited = draft.moods !== null;
  const labels = ["История", "Фотографии", "Музыка", "Монтаж"];
  function field(name, input) {
    input.setAttribute("aria-label", name);
    const lab = el("label", "field", name);
    lab.append(input);
    return lab;
  }
  function endpoint(tail) {
    return "/api/capture/" + draft.id + "/" + tail;
  }
  async function persist() {
    draft = await api(endpoint("fields"), {
      revision: draft.revision,
      story: story.value,
      title: title.value,
      date: date.value,
      reflection: reflection.value,
      moods: moodEdited ? [...moods] : null,
      order: draft.photos.map(p => p.id),
      coverPhoto:draft.coverPhoto||null,
      link: url.value.trim(),
      profile: profile.value
    });
  }
  async function task(fn) {
    root.inert = true;
    try {
      status.textContent = "";
      await fn();
    } catch (e) {
      status.textContent = e.status === 409 ?
          "Черновик изменился. Открой его заново." :
          "Не удалось сохранить. Проверь дату, ссылку или формат файла и повтори.";
    } finally {
      root.inert = false;
    }
  }
  function upload(kind) {
    const input = el("input");
    input.type = "file";
    input.multiple = kind === "photo";
    input.accept = kind === "photo" ? "image/jpeg,image/png,image/webp" : "audio/*";
    input.onchange = () => task(async () => {
      await persist();
      const files = [...input.files];
      let i = 0;
      for (const file of files) {
        status.textContent = "Загружаем " + (++i) + " / " + files.length;
        draft = await api(endpoint("upload/" + kind) + "?revision=" + draft.revision, file);
      }
      if (kind === "audio") {
        url.value = "";
        profile.value = draft.track.profile || profile.value;
      }
      status.textContent = "Загружено";
      render();
    });
    return field(kind === "photo" ? "Добавить фотографии" : "Загрузить аудиофайл", input);
  }
  function render() {
    bar.replaceChildren(...labels.map((name, i) => {
      const b = button(name, "step", () => task(async () => {
                                       await persist();
                                       step = i;
                                       render();
                                     }));
      b.setAttribute("aria-current", i === step ? "step" : "false");
      return b;
    }));
    panel.replaceChildren(heading(labels[step]));
    if(!moodEdited){moods.clear();for(const label of draft.suggestions||[])moods.add(label);}
    if (step === 0)
      panel.append(
          field("Исходный текст", story), field("Название · по желанию", title), field("Дата", date),
          field("Что осталось с тобой?", reflection));
    if (step === 1) {
      panel.append(upload("photo"));
      const list = el("div", "capture-photos");
      draft.photos.forEach((p, i) => {
        const cell = el("div");
        cell.append(captionedImage(p.src, "tile-image", asset, "Фото " + (i + 1)));
        const earlier = button("← Раньше", "minor", () => task(async () => {
                                                      [draft.photos[i - 1], draft.photos[i]] =
                                                          [draft.photos[i], draft.photos[i - 1]];
                                                      await persist();
                                                      render();
                                                    }));
        earlier.disabled = i === 0;
        const isCover=draft.coverPhoto===p.id;
        const cover=button(isCover?"Обложка ✓":"На обложку","minor",()=>task(async()=>{
          const previous=draft.coverPhoto;draft.coverPhoto=p.id;
          try{await persist();}catch(e){draft.coverPhoto=previous;throw e;}
          render();
        }));cover.setAttribute("aria-pressed",String(isCover));cell.append(cover);
        cell.append(earlier, button("Убрать", "minor", () => task(async () => {
                                                         draft = await api(
                                                             endpoint("remove/" + p.id) +
                                                                 "?revision=" + draft.revision,
                                                             {});
                                                         render();
                                                       })));
        list.append(cell);
      });
      panel.append(list);
    }
    if (step === 2) {
      panel.append(field("Ссылка на песню", url), upload("audio"), field("Как звучит трек?", profile));
      if (draft.track.asset) {
        const a = el("audio");
        a.controls = true;
        asset(draft.track.asset)
            .then(src => a.src = src)
            .catch(() => status.textContent = "Аудио недоступно.");
        panel.append(a);
      }
      panel.append(el(
          "p", "tile-info", "Песню по ссылке можно открыть отдельно. Аудиофайл звучит внутри фильма."));
    }
    if (step === 3) {
      panel.append(
          el("p", "", draft.photos.length + " фото · " + (draft.track.title || "Добавь песню")),
          el("h3", "", "Твои эмоции"), moodPicker(draft.options, moods, () => {
            moodEdited = true;
          }));
    }
    const footer = el("div", "actions");
    footer.append(
        button("Сохранить черновик", "minor", () => task(async () => {
                                                await persist();
                                                status.textContent = "Черновик сохранён.";
                                              })),
        button(
            step === 3 ? "Собрать Day Replay" : "Продолжить →", "solid-btn",
            () => task(async () => {
              await persist();
              if (step < 3) {
                step++;
                render();
              } else if (draft.story.trim() && draft.photos.length && draft.track.kind) {
                location.assign(dayURL(draft.id) + "&preview=1");
              } else
                status.textContent = "Для монтажа нужны рассказ, фото и песня.";
            })));
    panel.append(footer);
  }
  root.append(
      el("span", "mono", "MEMORY STUDIO"), el("h1", "page-title", "Новое воспоминание"), bar, panel,
      status);
  render();
  return root;
}
