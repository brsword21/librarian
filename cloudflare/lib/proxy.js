// Backend access for the Pages Functions. The backend URL lives in KV ("backend"): the Cloudflare Container Worker
// (librarian67-api), or a laptop tunnel as a fallback (tools/serve_live.sh). No backend -> 503 -> replay mode.
const json = (obj, status) =>
  new Response(JSON.stringify(obj), { status, headers: { "content-type": "application/json", "cache-control": "no-store" } });

export async function backendFetch(env, path, init = {}, request = null) {
  const backend = env.LIB ? await env.LIB.get("backend") : null;
  if (!backend) return json({ online: false, reason: "no live backend registered" }, 503);
  const headers = new Headers(init.headers || {});
  if (request) headers.set("x-public-origin", new URL(request.url).origin);
  const isStatus = path.startsWith("/api/status");
  try {
    // /api/ask waits for Reactor synchronously (1-2 min); everything else is quick or a queued job
    const limit = isStatus ? 15000 : path.startsWith("/api/ask") ? 300000 : 95000;
    const opts = { ...init, headers, redirect: "manual", signal: AbortSignal.timeout(limit) };
    // "service" = the Container Worker through the API service binding; anything else is a URL (laptop tunnel)
    const r = backend === "service" && env.API
      ? await env.API.fetch(new Request("https://librarian67-api" + path, opts))
      : await fetch(backend.replace(/\/$/, "") + path, opts);
    if (r.status >= 520 && r.status <= 530) return json({ online: false, reason: `backend ${r.status}` }, 503);
    const out = new Headers(r.headers);
    out.set("cache-control", "no-store");
    return new Response(r.body, { status: r.status, headers: out });
  } catch (e) {
    return json({ online: false, reason: String(e) }, 503);
  }
}

// /api/* and /m/*: forward as-is (same-origin for the browser; Reactor opens /m/<token>/search links here)
export async function proxy({ request, env }) {
  const url = new URL(request.url);
  const headers = {};
  for (const h of ["content-type", "accept", "user-agent"]) {
    const v = request.headers.get(h);
    if (v) headers[h] = v;
  }
  const init = { method: request.method, headers };
  if (!["GET", "HEAD"].includes(request.method)) init.body = await request.arrayBuffer();
  return backendFetch(env, url.pathname + url.search, init, request);
}
