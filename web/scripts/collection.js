import { api } from "./client.js";
import { button, element, dateLabel, monthLabel } from "./dom.js";

export function moodPicker(labels, selected, change) {
  const group = element("div", "mood-picker");
  for (const label of labels) {
    const choice = button(label, "mood-choice", () => {
      if (selected.has(label)) selected.delete(label);
      else selected.add(label);
      choice.setAttribute("aria-pressed", String(selected.has(label)));
      change();
    });
    choice.setAttribute("aria-pressed", String(selected.has(label)));
    group.append(choice);
  }
  return group;
}

export function calendar(days, open) {
  const section = element("section", "calendar");
  const months = new Map();
  for (const day of days) {
    const month = day.date.slice(0,7);
    if (!months.has(month)) months.set(month, []);
    months.get(month).push(day);
  }
  for (const [month, entries] of months) {
    section.append(element("h2", "month-title", monthLabel(month + "-01")));
    const grid = element("div", "calendar-grid");
    for (const label of ["Пн","Вт","Ср","Чт","Пт","Сб","Вс"]) grid.append(element("span","weekday",label));
    const first = new Date(month+"-01T12:00:00Z");
    const shift = (first.getUTCDay()+6)%7;
    for (let i=0; i<shift; i++) grid.append(element("span"));
    const last = new Date(Date.UTC(first.getUTCFullYear(),first.getUTCMonth()+1,0)).getUTCDate();
    const listing = element("div","calendar-list");
    listing.setAttribute("aria-live","polite");
    const dates = new Map();
    function selectDate(number) {
      listing.replaceChildren();
      for (const [dateNumber, cell] of dates) cell.setAttribute("aria-pressed",String(dateNumber===number));
      for (const day of entries.filter(day=>Number(day.date.slice(-2))===number)) {
        listing.append(button(day.title,"calendar-entry",()=>open(day.id)));
      }
    }
    for (let i=1; i<=last; i++) {
      const onDate=entries.filter(day=>Number(day.date.slice(-2))===i);
      if (!onDate.length) {grid.append(element("span","calendar-cell",String(i))); continue;}
      const cell=button(String(i),"calendar-cell occupied",()=>selectDate(i));
      cell.setAttribute("aria-label",dateLabel(onDate[0].date,true));
      dates.set(i,cell);
      grid.append(cell);
    }
    selectDate(Number(entries[0].date.slice(-2)));
    section.append(grid,listing);
  }
  return section;
}

export function reminderCenter(open, demo) {
  const panel = element("section","reminders-panel");
  const status = element("p","microcopy","Открываем напоминания…");
  status.role = "status";
  const content = element("div","reminder-list");
  panel.append(status, content);
  async function load(path="/api/reminders", body) {
    content.inert = true;
    try {
      const data = await api(path,body);
      status.textContent = demo ? "В демо можно настроить годовщину. Уведомления приходят в личном дневнике." : "";
      content.replaceChildren();
      for (const [key,label] of [["auto","Напоминать о годовщинах новых записей"],["titles","Показывать название в уведомлении"]]) {
        const field = element("label","switch-row",label);
        const box = element("input"); box.type="checkbox"; box.checked=data[key];
        box.onchange = ()=>load("/api/reminders/settings",{[key]:box.checked});
        field.append(box); content.append(field);
      }
      const zone = element("input"); zone.value=data.timezone; zone.setAttribute("aria-label","Часовой пояс");
      const line = element("div","reminder-row");
      line.append(zone, button("Сохранить пояс","outline-button",()=>load("/api/reminders/settings",{timezone:zone.value.trim()})));
      content.append(element("h3","","Часовой пояс"),line,element("h2","reading-title","Ближайшие"));
      if (!data.items.length) content.append(element("p","microcopy","Открой запись и нажми «Напомнить», чтобы вернуться к ней через год."));
      for (const item of data.items) {
        const row = element("article","reminder-item");
        const clock = element("input"); clock.type="time"; clock.value=item.clock; clock.setAttribute("aria-label","Время напоминания");
        const path = "/api/reminders/"+item.id;
        row.append(button(item.title,"day-link",()=>open(item.id)),element("p","microcopy",dateLabel(item.when.slice(0,10),true)),clock,
          button("Перенести","text-button",()=>load(path,{enabled:true,clock:clock.value})),
          button("Отключить","text-button",()=>load(path,{enabled:false})));
        content.append(row);
      }
    } catch {
      status.textContent="Не удалось загрузить настройки. Проверь время и часовой пояс.";
      status.append(button("Повторить","text-button",()=>load()));
    } finally {content.inert=false;}
  }
  load();
  return panel;
}

export function dayCollection(day, update) {
  const panel = element("section","day-collection");
  const status=element("p","microcopy"); status.role="status";
  const fav=button("", "collection-action", async ()=>{
    fav.disabled=true;
    try {const card=await api("/api/days/"+day.id+"/marks",{favorite:!day.favorite}); Object.assign(day,card); update(day); paint();}
    catch {status.textContent="Не удалось сохранить. Попробуй ещё раз.";}
    finally {fav.disabled=false;}
  });
  function paint(){fav.textContent=day.favorite?"★ В избранном":"☆ В избранное"; fav.setAttribute("aria-pressed",String(day.favorite));}
  paint();
  const remind=button("📅 Напомнить","collection-action",async ()=>{
    remind.disabled=true;
    try {
      const data=await api("/api/reminders/"+day.id,{enabled:!enabled});
      display(data);
    } catch {status.textContent="Не удалось изменить напоминание.";}
    finally {remind.disabled=false;}
  });
  let enabled=false;
  function display(data){
    const item=data.items.find(item=>item.id===day.id);
    enabled=!!item; remind.textContent=enabled?"🔔 Отменить напоминание":"📅 Напомнить";
    status.textContent=item ? dateLabel(item.when.slice(0,10),true)+" · "+item.clock+" · "+data.timezone : "";
  }
  remind.disabled=true;
  api("/api/reminders").then(display).catch(()=>{status.textContent="Проверь настройки в «Напоминаниях».";}).finally(()=>{remind.disabled=false;});
  const moods=element("details","disclosure");
  moods.append(element("summary","","Настроение дня"));
  const chosen=new Set(day.moods);
  {
    const label=element("p","microcopy",day.moodsConfirmed?"Твои метки":"Выбери подходящие метки. Можно несколько.");
    const save=button("Сохранить настроение","outline-button",async ()=>{
      save.disabled=true;
      try {const card=await api("/api/days/"+day.id+"/marks",{moods:[...chosen]}); Object.assign(day,card); update(day); label.textContent="Метки сохранены.";}
      catch {label.textContent="Не удалось сохранить метки.";} finally {save.disabled=false;}
    });
    moods.append(label,moodPicker(day.moodOptions,chosen,()=>{}),save);
  }
  panel.append(fav,remind,status,moods);
  return panel;
}
