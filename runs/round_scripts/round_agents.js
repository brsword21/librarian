export const meta = {
  name: 'librarian-round',
  description: 'Lens round: implement, sweep, iterate per question type (one role per run)',
  phases: [{ title: 'Lenses', detail: 'implement + sweep + iterate + report, one agent per type' }],
}

const TYPES = [
  { short: 'ssu', long: 'single-session-user', share: '~32% of test' },
  { short: 'ssa', long: 'single-session-assistant', share: '~17% of test' },
  { short: 'multi', long: 'multi-session', share: '~16% of test' },
  { short: 'ku', long: 'knowledge-update', share: '~10% of test' },
  { short: 'temporal', long: 'temporal-reasoning', share: '~24% of test' },
]
const ROLE = { a: 'A "Struktura" (rules, dates, timelines, entities, computed answers, hint wording)', b: 'B "Semantyka" (retrieval models, hybrid weights, granularity, rerank depth, neighbours, diversity, time-decay)' }
const letter = args.letter
const round = args.round
const other = letter === 'a' ? 'b' : 'a'
const brief = args.brief || ''

phase('Lenses')
const res = await parallel(TYPES.map(t => () => agent(
`You are lens agent ${letter.toUpperCase()} — ${ROLE[letter]} — for question type **${t.long}** (\`${t.short}\`, ${t.share}) in the "Librarian" hackathon project. This is ROUND ${round}: implement, evaluate, iterate.

Working directory: /Users/mikolaj/Developer/start-hackathon-2/librarian (run every command from there; Python = .venv/bin/python).
The core is LIVE: everything documented in CONTRACT.md exists (core/index.py, core/pack.py, core/dates.py, core/router.py, harness/sweep.py, harness/failures.py, harness/audit.py). Re-read CONTRACT.md (API, lens contract, metrics, HARD RULES) — it is the source of truth; if your Round-0 draft assumed something different, adapt your draft.
The shared model server is running on 127.0.0.1:8765: never start, stop or restart it, never import torch/sentence-transformers. Embeddings are cached; a background job is still filling dev/dev200 caches, so the FIRST dense call on a cold history can take seconds — iterate with \`--limit 40\`, run full sweeps for decisions.

Reference numbers (dev): kit naive keyword baseline S=42.9 PA=0.43 (lenses/generic.py variant naive); generic hybrid+rerank (lenses/generic.py variant hybrid_rr) S≈73 PA≈0.93 CF1≈0.55 chars≈11.9k on an 80-question sample. Your first command: measure the bar for YOUR type:
  .venv/bin/python -m harness.sweep --lens lenses/generic.py --variants hybrid_rr --split dev --type ${t.short} --tag r${round}-${t.short}-${letter} --workers 2
and the same on --split dev200 (test scale: 200 sessions/history; dev at 48 sessions is much easier, so dev200 is where lenses really separate).

Your files: lenses/${t.short}/${letter}_*.py, lenses/${t.short}/${letter}_*.md, lenses/${t.short}/scratch_${letter}/. Start from your design (lenses/${t.short}/${letter}_design.md) and draft lens; read the other agent's design/lens (lenses/${t.short}/${other}_*) to avoid duplicating it — you may borrow ideas, credit them.
${brief ? 'Integrator brief for this round:\n' + brief + '\n' : ''}
Loop (one hypothesis per change):
  1. sweep your lens variants: .venv/bin/python -m harness.sweep --lens lenses/${t.short}/${letter}_<name>.py --variants all --split dev --type ${t.short} --tag r${round}-${t.short}-${letter} --workers 2
  2. .venv/bin/python -m harness.failures runs/r${round}-${t.short}-${letter}/${t.short}/<lens>/<variant>/dev --n 15   (where did the gold turn rank, what did we take instead)
  3. change one thing, re-sweep; confirm the best variant on --split dev200.
  4. audit on test (no gold, qualitative): .venv/bin/python -m harness.audit --lens lenses/${t.short}/${letter}_<name>.py --variant <best> --type ${t.short} --n 12 ; fix only GENERAL problems you see (never per-question rules).
Objective per CONTRACT.md: maximise S (PA first, then CF1 = citation precision of cite_plan, then fewer chars) on dev AND dev200; abstain_p should separate unanswerable questions (AUC column). Gold accepts N or N+1 for day counts; Reactor is a fast instruct model, so computed answers and short factual hints help it. Budget: chars <= 16000 is the client default; 12000 is a good default; more chars cost Reactor time.
Time box: about 70 minutes, roughly 8-12 sweeps. --workers 2 max. Do not edit core/, harness/, configs/ or anyone else's files (write CORE REQUESTs in your report instead).

Finish by writing lenses/${t.short}/${letter}_report.md: variants tried (one line each), a table of S / PA / ATR / SR / CF1 / chars / AUC on dev and dev200 for the baseline and your variants, the best variant, top failure patterns with 2-3 concrete examples, CORE REQUESTs, ideas for the next round. Then return the structured summary.`,
  {
    label: `r${round}:${t.short}:${letter}`,
    phase: 'Lenses',
    schema: {
      type: 'object',
      properties: {
        lens_file: { type: 'string' },
        best_variant: { type: 'string' },
        dev: { type: 'object', properties: { S: { type: 'number' }, PA: { type: 'number' }, CF1: { type: 'number' }, chars: { type: 'number' } }, required: ['S', 'PA'] },
        dev200: { type: 'object', properties: { S: { type: 'number' }, PA: { type: 'number' }, CF1: { type: 'number' }, chars: { type: 'number' } }, required: ['S', 'PA'] },
        baseline_dev: { type: 'object', properties: { S: { type: 'number' }, PA: { type: 'number' } } },
        baseline_dev200: { type: 'object', properties: { S: { type: 'number' }, PA: { type: 'number' } } },
        failure_patterns: { type: 'array', items: { type: 'string' } },
        core_requests: { type: 'array', items: { type: 'string' } },
        next_ideas: { type: 'array', items: { type: 'string' } },
      },
      required: ['lens_file', 'best_variant', 'dev', 'dev200', 'failure_patterns', 'core_requests', 'next_ideas'],
    },
  }
)))
return res.map((r, i) => r ? { type: TYPES[i].short, letter, ...r } : { type: TYPES[i].short, letter, failed: true })
