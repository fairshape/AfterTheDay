import {asset} from "./client.js";
import {button, captionedImage, element} from "./dom.js";

export function studioControls(day, changed) {
  const settings = day.details.studio || {};
  const section = element("fieldset", "director-controls");
  section.append(element("legend", "", "Режиссура"));
  function select(label, choices, value) {
    const field = element("label", "field", label);
    const input = element("select");
    input.setAttribute("aria-label", label);
    for (const [id, name] of choices) {
      const option = element("option", "", name);
      option.value = id;
      input.append(option);
    }
    input.value = value;
    field.append(input);
    section.append(field);
    return input;
  }
  const style = select("Обработка фотографии", [
    ["natural", "Естественный свет"], ["print", "Мягкий отпечаток"], ["graphic", "Графичный контраст"]
  ], settings.treatment || "natural");
  const motion = select("Движение камеры", [
    ["auto", "По истории и музыке"], ["still", "Статично"], ["soft", "Лёгкое движение"], ["expressive", "Выразительно"]
  ], settings.motion || "auto");
  const seconds = element("input");
  seconds.type = "number"; seconds.min = 8; seconds.max = 45; seconds.step = 1;
  seconds.value = settings.seconds ?? "";
  seconds.placeholder = "По музыке";
  const length = element("label", "field", "Длительность, с");
  length.append(seconds);
  section.append(length);
  if(day.track.kind==="file")section.append(element("p","microcopy","Короткий файл ограничивает длительность фильма доступным звуком."));
  const listing = element("div", "shot-sequence");
  const original = day.photos.map(p=>p.id);
  let explicit = !!settings.order?.length;
  let order = explicit ? [...settings.order] : [...original];
  function draw() {
    listing.replaceChildren();
    for (const [i, id] of order.entries()) {
      const photo = day.photos.find(p=>p.id===id);
      if(!photo)continue;
      const row=element("div","order-shot");
      const left=button("←","minor",()=>move(i,-1)), right=button("→","minor",()=>move(i,1));
      left.disabled=i===0;right.disabled=i===order.length-1;
      left.setAttribute("aria-label","Передвинуть фото "+(i+1)+" раньше");right.setAttribute("aria-label","Передвинуть фото "+(i+1)+" позже");
      row.append(captionedImage(photo.src,"order-thumb",asset,photo.caption||"Фото "+(i+1)),element("span","mono",String(i+1).padStart(2,"0")),left,right);listing.append(row);
    }
  }
  function move(i, delta) {
    [order[i],order[i+delta]]=[order[i+delta],order[i]];
    explicit=true;draw();changed();
  }
  if(day.photos.length>1){section.append(element("h3","","Порядок кадров"),listing);draw();}
  section.append(button("Вернуть автоматическую режиссуру","text-button",()=>{
    style.value="natural";motion.value="auto";seconds.value="";explicit=false;order=[...original];draw();changed();
  }));
  return {section, value:()=>({order:explicit?order:[],motion:motion.value,treatment:style.value,seconds:seconds.value===""?null:seconds.valueAsNumber})};
}
