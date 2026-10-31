// Librarian API on Cloudflare: one always-warm container running the Python backend; /api/* and /m/* go to it.
// The Pages site (librarian67.pages.dev) proxies to this Worker (KV "backend"), so the browser stays same-origin.
import { Container, getContainer } from "@cloudflare/containers";

export class Backend extends Container {
  defaultPort = 8800;
  sleepAfter = "6h";
  enableInternet = true;
  constructor(ctx, env) {
    super(ctx, env);
    this.envVars = {
      PUBLIC_URL: env.PUBLIC_URL,
      REACTOR_BASE_URL: env.REACTOR_BASE_URL,
      REACTOR_AGENT_ID: env.REACTOR_AGENT_ID,
      REACTOR_TIMEOUT: "600",
      OMP_NUM_THREADS: "4",
      MKL_NUM_THREADS: "4",
      ...(env.REACTOR_ACCESS_KEY ? { REACTOR_ACCESS_KEY: env.REACTOR_ACCESS_KEY } : {}),
    };
  }
}

const backend = (env) => getContainer(env.BACKEND, "main");

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const { pathname } = url;
    // restart the backend container (new versions roll out on restart): /admin/restart?k=<ADMIN_KEY>
    if (pathname === "/admin/restart") {
      if (!env.ADMIN_KEY || url.searchParams.get("k") !== env.ADMIN_KEY) return new Response("forbidden\n", { status: 403 });
      await backend(env).destroy().catch(() => {});
      return new Response("restarting; the next request boots the latest version\n");
    }
    if (!/^\/(api|m)\//.test(pathname)) return new Response("Librarian API. Try /api/status\n");
    return backend(env).fetch(request);
  },
  // keep the single instance warm through the demo
  async scheduled(_event, env, ctx) {
    ctx.waitUntil(backend(env).fetch("http://container/api/status").catch(() => {}));
  },
};
