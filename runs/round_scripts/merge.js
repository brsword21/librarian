export const meta = {
  name: 'librarian-merge',
  description: 'Integrator: pick the best lens per type, update config/router/core, regression + test audit, brief next round',
  phases: [{ title: 'Merge', detail: 'integrator' }],
}

const round = args.round
const resultsFile = args.results_file

phase('Merge')
const out = await agent(
`You are the INTEGRATOR ("scalacz") of the "Librarian" hackathon project after lens ROUND ${round}. You alone own core/, harness/, configs/ and lenses/pipeline.py; lens agents own lenses/<type>/<a|b>_*.

Working directory: ../librarian (Python = .venv/bin/python, run commands from there). Read CONTRACT.md, RESEARCH.md, ../CONTEXT.md, every lenses/*/[ab]_report.md, runs/leaderboard.csv. The model server on 127.0.0.1:8765 is shared: never stop/restart it, never import torch. Never call Reactor or any external model API.

Structured results returned by the 10 lens agents this round are in ${resultsFile} (JSON list; read it).

IMPORTANT about citations: the submitted citations are whatever Reactor cites among the passages we send (labels [E#] -> session ids). Whether our code may post-filter Reactor's citations is NOT confirmed by the organisers, so do not rely on it. cite_plan is only our intent; CF1 measured on cite_plan is optimistic when the pack contains decoy sessions. Prefer designs where the passages we send are close to what we want cited, and/or a short hint asking Reactor to cite only the passages that state the answer (or each counted item). Note this trade-off explicitly in the synthesis.

${args.extra || ''}

Tasks, in order (time box ~40 minutes; use --workers 3 at most):
1. For each type pick the winner on S (dev) that does not lose on dev200 (rule: a challenger must beat the incumbent by >= 2 S points on dev and not lose on dev200; tie -> fewer chars / simpler). Re-run the top-2 per type yourself on the same split if numbers come from different question subsets (--limit) so the comparison is fair. If A and B have complementary strengths and a quick merge is obvious, you may write lenses/<type>/merged_r${round}.py (import from their files, do not edit them).
2. Update configs/best.json (routes: ssu, ssa, multi, ku, temporal + fallback) with the winners.
3. Router (core/router.py): measure accuracy on dev gold types and the confusion matrix; improve it carefully (test phrasing in runs/samples/*.jsonl test rows and ../data/test/questions.jsonl). Lenses must degrade gracefully on misroutes: run the routed system on all of dev and dev200:
   .venv/bin/python -m harness.sweep --lens lenses/pipeline.py --variants routed --split dev --tag merge${round} --workers 3   (and --split dev200)
   Compare per-type S of the routed system with the per-type winners under gold routing; if a misroute hurts badly, fix routing or make the receiving lens more robust via config.
4. Abstention: look at abstain_p AUC per winner and on the routed run; propose (do not hard-code into Reactor calls yet) a global policy: which signal, which threshold, and whether to pass it to Reactor as a hint. Write it into configs/abstain.json {"policy": ..., "threshold": ..., "notes": ...}.
5. CORE REQUESTs from the reports: implement the cheap, safe ones in core/ or harness/, keeping the API backward compatible; re-run anything affected; note what you declined and why.
6. Audit the routed system on test (no gold): .venv/bin/python -m harness.audit --lens lenses/pipeline.py --variant routed --n 146 | tail -5, then read runs/audit/all/pipeline/routed/test_packs.jsonl for flagged items and a sample per route. Fix only general problems.
7. Commit: git add -A && git commit -m "Round ${round} merge" (author: git -c user.name="Mikołaj" -c user.email="brsword21@users.noreply.github.com"; add the line "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" at the end of the message).
8. Write runs/SYNTHESIS_r${round}.md: per type the winner + S/PA/CF1/chars on dev and dev200; routed-system metrics; router accuracy; abstention policy; what worked and what failed; and a BRIEF for the next round: for each type and role (a/b), 2-4 concrete things to try next.

Return the structured summary (the brief texts will be passed verbatim to the next round's agents).`,
  {
    label: `merge-r${round}`,
    phase: 'Merge',
    schema: {
      type: 'object',
      properties: {
        winners: { type: 'array', items: { type: 'object', properties: { type: { type: 'string' }, lens: { type: 'string' }, variant: { type: 'string' }, S_dev: { type: 'number' }, S_dev200: { type: 'number' } }, required: ['type', 'lens', 'variant'] } },
        routed_dev: { type: 'object', properties: { S: { type: 'number' }, PA: { type: 'number' }, CF1: { type: 'number' }, chars: { type: 'number' }, auc: { type: 'number' } } },
        routed_dev200: { type: 'object', properties: { S: { type: 'number' }, PA: { type: 'number' }, CF1: { type: 'number' }, chars: { type: 'number' }, auc: { type: 'number' } } },
        router_accuracy_dev: { type: 'number' },
        abstention_policy: { type: 'string' },
        brief_a: { type: 'string', description: 'brief for the A (structure) agents, per type' },
        brief_b: { type: 'string', description: 'brief for the B (semantic) agents, per type' },
        notes: { type: 'array', items: { type: 'string' } },
      },
      required: ['winners', 'routed_dev', 'routed_dev200', 'router_accuracy_dev', 'abstention_policy', 'brief_a', 'brief_b', 'notes'],
    },
  }
)
return out
