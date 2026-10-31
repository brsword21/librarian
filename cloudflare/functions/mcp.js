// Librarian as an MCP server (Streamable HTTP, stateless JSON responses) at https://librarian67.pages.dev/mcp
//   claude mcp add --transport http librarian https://librarian67.pages.dev/mcp
// Tools call the same backend as the demo (/api/*), so any agent gets what Reactor gets: evidence with receipts.
import { backendFetch } from "../lib/proxy.js";

const PROTOCOL = "2025-06-18";
const SERVER = { name: "librarian", title: "Librarian: memory with receipts", version: "1.0.0" };
const INSTRUCTIONS =
  "Librarian searches one person's long chat history with an assistant (months, ~200 conversations) and returns the " +
  "few passages that matter, each with its session id and date. Use recall before answering anything about the " +
  "user's past; cite the session ids you rely on; if no passage states the answer, say it is not in memory instead " +
  "of guessing. Use timeline when a fact may have changed (the latest dated mention wins). list_users shows the 15 " +
  "demo archives (real test histories from the Reactive AI Memory Retrieval Challenge).";

const USER = { type: "string", description: "Archive id from list_users, e.g. \"user-1\" (or just 1)" };
const TOOLS = [
  { name: "list_users", title: "List archives", description: "The 15 demo archives with example questions.",
    inputSchema: { type: "object", properties: {} }, annotations: { readOnlyHint: true } },
  { name: "recall", title: "Recall",
    description: "Evidence for a question about the user's past: Librarian's 3-ish best dated passages, notes computed " +
      "in code (dates, day gaps, latest value), or nothing relevant (then answer 'not in memory').",
    inputSchema: { type: "object", required: ["user", "question"],
      properties: { user: USER, question: { type: "string", description: "The question, as the user asked it" } } },
    annotations: { readOnlyHint: true } },
  { name: "search", title: "Search", description: "Free-text search over one archive; top-k sessions, oldest first.",
    inputSchema: { type: "object", required: ["user", "query"],
      properties: { user: USER, query: { type: "string" }, k: { type: "integer", minimum: 1, maximum: 10, default: 5 } } },
    annotations: { readOnlyHint: true } },
  { name: "timeline", title: "Timeline",
    description: "Every dated mention of a topic, oldest to newest, with the latest marked. Use it when a fact may " +
      "have changed (moved, renamed, new job) or to audit conflicting memories.",
    inputSchema: { type: "object", required: ["user", "topic"], properties: { user: USER, topic: { type: "string" } } },
    annotations: { readOnlyHint: true } },
  { name: "ask_reactor", title: "Ask Reactor",
    description: "Have Reactor (Reactive AI's memory model) answer with citations from Librarian's evidence. Takes 1-3 " +
      "minutes: returns a job id; poll get_answer. search_again also gives Reactor a private archive link to search (experimental).",
    inputSchema: { type: "object", required: ["user", "question"],
      properties: { user: USER, question: { type: "string" }, search_again: { type: "boolean", default: false } } } },
  { name: "get_answer", title: "Get Reactor's answer", description: "Status or result of an ask_reactor job.",
    inputSchema: { type: "object", required: ["job_id"], properties: { job_id: { type: "string" } } },
    annotations: { readOnlyHint: true } },
];

const cors = {
  "access-control-allow-origin": "*",
  "access-control-allow-methods": "GET, POST, DELETE, OPTIONS",
  "access-control-allow-headers": "content-type, accept, mcp-session-id, mcp-protocol-version, authorization",
  "access-control-expose-headers": "mcp-session-id, mcp-protocol-version",
};
const json = (obj, status = 200) =>
  new Response(JSON.stringify(obj), { status, headers: { "content-type": "application/json", ...cors } });

class ToolError extends Error {}

async function users(ctx) {
  const r = await ctx.env.ASSETS.fetch(new URL("/users.json", ctx.request.url));
  return r.json();
}
async function resolveUser(ctx, user) {
  const all = await users(ctx);
  const s = String(user ?? "").trim().toLowerCase();
  const u = all.find((x) => x.id === s || String(x.n) === s || `user ${x.n}` === s || x.history_id === s ||
    x.id === `user-${s.replace(/\D/g, "")}`);
  if (!u) throw new ToolError(`Unknown archive "${user}". Call list_users; ids are user-1 … user-${all.length}.`);
  return u;
}
async function api(ctx, path, body) {
  const r = await backendFetch(ctx.env, path, body === undefined ? { method: "GET" } :
    { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body) }, ctx.request);
  let data = null;
  try { data = await r.json(); } catch { /* not json */ }
  if (r.status === 503) throw new ToolError("Librarian's search backend is offline right now. Try again in a minute.");
  const code = data && data.error;
  if (code === "reactor_disabled") throw new ToolError("Reactor answering is switched off right now. Use recall and answer from the passages, citing session ids.");
  if (code === "busy") throw new ToolError("Reactor is busy with other questions. Try again in a minute, or use recall.");
  if (!r.ok) throw new ToolError(code || `backend error ${r.status}`);
  return data;
}
const passage = (p, i) => `[${i + 1}] ${p.id || "note"} · ${p.date || ""}\n${p.text}`;

async function call(ctx, name, a) {
  if (name === "list_users") {
    const all = await users(ctx);
    const text = all.map((u) => `${u.id} · ${u.sessions} conversations · asked ${u.question_date.slice(0, 10)} · e.g. ` +
      u.questions.slice(0, 2).map((q) => `“${q}”`).join(" ")).join("\n");
    return { text, data: all.map(({ id, sessions, question_date, questions }) => ({ id, sessions, question_date, questions })) };
  }
  if (name === "get_answer") {
    const j = await api(ctx, `/api/jobs/${encodeURIComponent(a.job_id || "")}`);
    if (j.status !== "done") {
      return { text: `Status: ${j.status} (${j.stage}), ${j.elapsed_s}s` + (j.position ? `, position ${j.position} in queue` : "") +
        (j.error ? `. Error: ${j.error}` : ". Poll again in ~15 s."), data: j };
    }
    const r = j.result || {};
    const ans = r.abstained || !r.answer || r.answer === "INSUFFICIENT_EVIDENCE" ? "Not in memory." : r.answer;
    const first = r.first ? ` First look: ${r.first.abstained ? "not in memory" : r.first.answer}.` : "";
    const searched = (j.searches || []).length ? ` Reactor searched again: ${j.searches.map((s) => `“${s.q}”`).join(", ")}.` : "";
    return { text: `${ans}\nCited sessions: ${(r.cited || []).join(", ") || "none"} · ${r.latency_s}s.${first}${searched}`, data: j };
  }
  const u = await resolveUser(ctx, a.user);
  if (name === "recall") {
    if (!a.question) throw new ToolError("question is required");
    const p = await api(ctx, "/api/pack", { split: "test", history_id: u.history_id, question: a.question });
    const notes = [p.notes && `Librarian's note: ${p.notes}`, p.computed && `Computed in code: ${p.computed}`].filter(Boolean);
    const body = p.passages.length ? p.passages.map(passage).join("\n\n") : "No relevant passages.";
    return {
      text: `${u.id}, question asked on ${p.question_date}. ${p.passages.length} passage(s), picked in ${p.build_ms} ms ` +
        `(question type: ${p.route}).\n${notes.join("\n")}\n\n${body}\n\nCite the session ids you use. If none of these ` +
        `passages states the answer, it is not in memory.`,
      data: { user: u.id, ...p },
    };
  }
  if (name === "search" || name === "timeline") {
    const q = name === "search" ? a.query : a.topic;
    if (!q) throw new ToolError(`${name === "search" ? "query" : "topic"} is required`);
    const k = name === "timeline" ? 8 : Math.max(1, Math.min(10, Number(a.k) || 5));
    const s = await api(ctx, "/api/search", { split: "test", history_id: u.history_id, query: q, k });
    const hits = s.hits || [];
    const text = hits.length
      ? hits.map((h, i) => passage(h, i) + (name === "timeline" && i === hits.length - 1 ? "\n(latest mention)" : "")).join("\n\n")
      : "Nothing in this archive matches.";
    return { text: `${u.id} · ${name === "timeline" ? "mentions over time" : "search"} for “${q}”, oldest first:\n\n${text}`, data: { user: u.id, ...s } };
  }
  if (name === "ask_reactor") {
    if (!a.question) throw new ToolError("question is required");
    const j = await api(ctx, "/api/jobs", { kind: a.search_again ? "askback" : "ask", split: "test",
      history_id: u.history_id, question: a.question });
    return { text: `Reactor is on it. job_id: ${j.job_id} (position ${j.position}). Call get_answer in ~60 s; answers take 1-3 minutes.`, data: j };
  }
  throw new ToolError(`Unknown tool ${name}`);
}

async function handle(ctx, msg) {
  const { id, method, params = {} } = msg || {};
  if (id === undefined || id === null) return null;   // notification: no response
  const ok = (result) => ({ jsonrpc: "2.0", id, result });
  const err = (code, message) => ({ jsonrpc: "2.0", id, error: { code, message } });
  try {
    switch (method) {
      case "initialize":
        return ok({ protocolVersion: params.protocolVersion || PROTOCOL, capabilities: { tools: { listChanged: false } },
          serverInfo: SERVER, instructions: INSTRUCTIONS });
      case "ping": return ok({});
      case "tools/list": return ok({ tools: TOOLS });
      case "tools/call": {
        if (!TOOLS.some((t) => t.name === params.name)) return err(-32602, `Unknown tool: ${params.name}`);
        try {
          const out = await call(ctx, params.name, params.arguments || {});
          return ok({ content: [{ type: "text", text: out.text }], structuredContent: out.data });
        } catch (e) {
          if (e instanceof ToolError) return ok({ content: [{ type: "text", text: e.message }], isError: true });
          throw e;
        }
      }
      case "resources/list": return ok({ resources: [] });
      case "prompts/list": return ok({ prompts: [] });
      default: return err(-32601, `Method not found: ${method}`);
    }
  } catch (e) {
    return err(-32603, String(e && e.message || e));
  }
}

export async function onRequest(ctx) {
  const { request } = ctx;
  if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: cors });
  if (request.method === "GET") {
    if ((request.headers.get("accept") || "").includes("text/event-stream")) return new Response(null, { status: 405, headers: cors });
    return json({ server: SERVER, transport: "streamable-http", connect: "claude mcp add --transport http librarian " + new URL(request.url).href,
      tools: TOOLS.map((t) => t.name) });
  }
  if (request.method === "DELETE") return new Response(null, { status: 204, headers: cors });
  if (request.method !== "POST") return new Response(null, { status: 405, headers: cors });
  let body;
  try { body = await request.json(); } catch { return json({ jsonrpc: "2.0", id: null, error: { code: -32700, message: "Parse error" } }, 400); }
  if (Array.isArray(body)) {
    const out = (await Promise.all(body.map((m) => handle(ctx, m)))).filter(Boolean);
    return out.length ? json(out) : new Response(null, { status: 202, headers: cors });
  }
  const out = await handle(ctx, body);
  return out ? json(out) : new Response(null, { status: 202, headers: cors });
}
