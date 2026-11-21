let session = "";
const mediaCache = new Map();
const MAX_CACHED_BYTES = 75 * 1024 * 1024;
let cachedBytes = 0;

export class RequestError extends Error {
  constructor(status, detail) {
    super(detail);
    this.status = status;
  }
}

export async function api(path, body) {
  const headers = new Headers();
  if (session) headers.set("Authorization", `Bearer ${session}`);
  if (body) headers.set("Content-Type", "application/json");
  const response = await fetch(path, { headers, method: body ? "POST" : "GET",
    body: body ? JSON.stringify(body) : undefined, cache: "no-store" });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new RequestError(response.status, payload.detail);
  }
  return response.json();
}

export async function connect(telegram) {
  if (!telegram?.initData) throw new RequestError(401, "login");
  const result = await api("/api/session", { initData: telegram.initData });
  session = result.token;
}

export async function asset(url) {
  if (mediaCache.has(url)) return mediaCache.get(url).promise;
  const entry = { bytes: 0 };
  entry.promise = (async () => {
    const headers = session ? { Authorization: `Bearer ${session}` } : {};
    const response = await fetch(url, { headers, cache: "no-store" });
    if (!response.ok) throw new RequestError(response.status, "asset");
    const blob = await response.blob();
    entry.bytes = blob.size;
    cachedBytes += blob.size;
    return URL.createObjectURL(blob);
  })().catch((error) => {
    mediaCache.delete(url);
    throw error;
  });
  mediaCache.set(url, entry);
  return entry.promise;
}

// Keep URLs alive during a route, including the originals and the active player.
export function releaseOldAssets() {
  if (cachedBytes <= MAX_CACHED_BYTES) return;
  for (const [url, entry] of mediaCache) {
    if (!entry.bytes) continue;
    mediaCache.delete(url);
    cachedBytes -= entry.bytes;
    entry.promise.then((src) => URL.revokeObjectURL(src));
    if (cachedBytes <= MAX_CACHED_BYTES / 2) break;
  }
}
