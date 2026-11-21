const preference = window.matchMedia("(prefers-reduced-motion: reduce)");
const namedPhotos = new WeakMap();

export function reducedMotion() {
  return preference.matches;
}

export function duration(name) {
  return Number.parseFloat(getComputedStyle(document.documentElement).getPropertyValue(`--${name}-ms`));
}

export function transitionCover(source, apply) {
  const canShare = source?.naturalWidth && document.startViewTransition && !reducedMotion();
  if (canShare) {
    const token = Symbol();
    const mark = (image) => {
      if (!image) return;
      namedPhotos.set(image, token);
      image.style.viewTransitionName = "memory-photo";
    };
    const removeName = (image) => {
      if (image && namedPhotos.get(image) === token) {
        namedPhotos.delete(image);
        image.style.viewTransitionName = "";
      }
    };
    mark(source);
    let target;
    const transition = document.startViewTransition(() => {
      removeName(source);
      target = apply();
      mark(target);
    });
    // The browser can skip a capture when a WebView resizes or a page becomes hidden.
    // ready rejects independently of the finished promise in that case.
    transition.ready.catch(() => {});
    const mounted = transition.updateCallbackDone.catch(() => { if (!target) target = apply(); });
    return Promise.all([mounted, transition.finished.catch(() => {})]).finally(() => removeName(target));
  }
  const target = apply();
  if (!reducedMotion()) target?.closest(".memory-cover")?.animate([{opacity:.4},{opacity:1}], duration("route"));
  return Promise.resolve();
}

export function enterPlayer(stage, projection, source) {
  if (reducedMotion() || !projection.animate) return;
  const rect = source?.naturalWidth ? source.getBoundingClientRect() : null;
  if (!rect?.width || rect.bottom < 0 || rect.top > innerHeight) {
    projection.animate([{opacity: 0}, {opacity: 1}], {duration: duration("player") * .7, easing: "ease-out"});
    return;
  }
  const screen = stage.getBoundingClientRect();
  const destination = projection.getBoundingClientRect();
  if (!screen.width) return;
  const timing = {duration: duration("player"), easing: "cubic-bezier(.2,.75,.23,1)"};
  const flight = projection.animate([
    {left: `${rect.left - screen.left}px`, top: `${rect.top - screen.top}px`,
      width: `${rect.width}px`, height: `${rect.height}px`, borderRadius: "3px"},
    {left: `${destination.left - screen.left}px`, top: `${destination.top - screen.top}px`,
      width: `${destination.width}px`, height: `${destination.height}px`, borderRadius: "0"},
  ], timing);
  const visibility = source.style.visibility;
  source.style.visibility = "hidden";
  flight.finished.catch(() => {}).finally(() => { source.style.visibility = visibility; });
  const reveal = Math.min(duration("reveal"), timing.duration * .8);
  for (const selector of [".scene-heading", ".scene-caption", ".scene-footer"]) {
    stage.querySelector(selector).animate([{opacity:0},{opacity:1}], {
      duration: timing.duration - reveal, delay: reveal, fill: "backwards",
    });
  }
  stage.querySelector(".stage-ink")?.animate([{opacity:0},{opacity:1}], timing);
  stage.querySelector(".film-veil")?.animate([{opacity:0},{opacity:1}], timing);
}
