export const ROUTES = {
 ssu:{name:'Personal facts',hint:'What you told the assistant',icon:'icon_lens_ssu',hue:65},
 ssa:{name:'Advice & recommendations',hint:'What the assistant told you',icon:'icon_lens_ssa',hue:135},
 multi:{name:'Across conversations',hint:'Count the scattered details',icon:'icon_lens_multi',hue:0},
 ku:{name:'Things that changed',hint:'The latest mention wins',icon:'icon_lens_ku',hue:325},
 temporal:{name:'Dates & durations',hint:'Put the dates in order',icon:'icon_lens_temporal',hue:220},
};
export const PEOPLE={h_d99a2da8f8ee:'Carla',h_961be7a385ce:'Grace',h_ba495aa00d0c:'Aisha',h_4fa7f122fcdb:'Lucia',h_8224cd1fdcd0:'Hiroshi',h_5e62f4533db4:'Rafael'};
export const TOUR=['q_62e927862f62','q_06ae4afa8961','q_392fdc44c911','q_068d0a4b3f7b','q_499fc53af8ca'];
export const CHAPTERS=[
 {title:'A question arrives.',label:'CHAPTER I · THE QUESTION',description:'Somewhere in months of conversation lies a small detail. The Librarian starts by working out what kind of memory you need.',note:'One history. Hundreds of conversations.\nA very small reading budget.',alt:'The Librarian receives a question on a punch card through a pneumatic tube.'},
 {title:'The right lens.',label:'CHAPTER II · THE ROUTER',description:'A fact, a recommendation, a change of plans? Five specialised lenses choose how to search. A question about “now” needs a different reading than “how many”.',note:'The brass headset is our question router.\nEach lens has a job of its own.',alt:'The Librarian lowers an amber loupe to inspect a question.'},
 {title:'Find the few that matter.',label:'CHAPTER III · THE SEARCH',description:'The moth searches for words. The owl looks for meaning. A reranker weighs their findings, keeping the useful pages and leaving the near misses on the shelf.',note:'BM25 + local embeddings + reranking.\nA small, relevant evidence pack.',alt:'An owl and moth search the shelves while the Librarian weighs two blank pages.'},
 {title:'A desk, not a haystack.',label:'CHAPTER IV · THE EVIDENCE',description:'The Librarian checks dates, computes day gaps and flags misleading mentions. Then those selected pages and notes are handed to Reactor.',note:'Local code prepares the evidence.\nReactor produces the answer.',alt:'The Librarian feeds a satchel of selected pages into the brass Reactor.'},
 {title:'Remember. Or say you can’t.',label:'CHAPTER V · THE ANSWER',description:'Reactor returns an answer with citations back to the original conversations. If the answer isn’t in the archive, it says so. No invented memories.',note:'An answer is useful.\nAn answer you can trace is better.',alt:'Reactor produces a blank scroll with wax citations; an inset shows the Librarian shrugging at an empty book.'},
];
export const isAbstain=r=>!!r?.abstained || /^\s*(INSUFFICIENT[_ ]EVIDENCE|NOT[_ ]IN[_ ]ARCHIVE)\s*$/i.test(r?.answer||'');
export const normalize=s=>String(s??'').toLowerCase().replace(/[’‘]/g,"'").replace(/[.,!?;:]+$/g,'').replace(/\s+/g,' ').trim();
export function evidenceF1(record){
 const actual=new Set(record.cited||[]),expected=new Set(record.gold?.evidence||[]);
 if(isAbstain(record))return 0;
 const overlap=[...actual].filter(x=>expected.has(x)).length;
 return actual.size+expected.size?2*overlap/(actual.size+expected.size):0;
}
export function calibration(records){
 const sample=records.filter(r=>r.gold);
 const correct=r=>r.gold.abstain?isAbstain(r):!isAbstain(r)&&normalize(r.answer)===normalize(r.gold.answer);
 const answerable=sample.filter(r=>!r.gold.abstain),unanswerable=sample.filter(r=>r.gold.abstain);
 const ratio=xs=>xs.length?xs.filter(correct).length/xs.length:null;
 return {n:sample.length,strict:ratio(sample),f1:answerable.length?answerable.reduce((n,r)=>n+evidenceF1(r),0)/answerable.length:null,
  abstain:ratio(unanswerable),unanswerable:unanswerable.length,
  byRoute:Object.fromEntries(Object.keys(ROUTES).map(route=>{const rows=sample.filter(r=>r.route===route);return[route,{n:rows.length,correct:rows.filter(correct).length,score:ratio(rows)}]}))};
}
