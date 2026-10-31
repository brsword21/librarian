import {ROUTES,PEOPLE,TOUR,CHAPTERS,isAbstain,calibration} from './data.js';
const $=s=>document.querySelector(s);
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt=n=>Number(n||0).toLocaleString('en-US');
const reduced=matchMedia('(prefers-reduced-motion: reduce)');
const S={data:null,records:[],selected:null,hid:null,current:null,token:0,busy:false,controller:null,reactorBusy:null,chapter:0};
const nameFor=id=>PEOPLE[id]||`Reader ${Object.keys(S.data?.timelines||{}).indexOf(id)+1}`;
const date=str=>{const m=String(str||'').match(/(\d{4})\/(\d{2})\/(\d{2})/);return m?new Intl.DateTimeFormat('en-GB',{day:'numeric',month:'short',year:'numeric',timeZone:'UTC'}).format(new Date(`${m[1]}-${m[2]}-${m[3]}T00:00:00Z`)):String(str||'Undated');};
const nap=ms=>new Promise(resolve=>setTimeout(resolve,reduced.matches?0:ms));
const percent=n=>n===null?'—':`${Math.round(n*100)}%`;
function show(view){for(const name of ['ask','working','answer'])$(`#${name}View`).hidden=view!==name;$('#mainContent').setAttribute('aria-busy',view==='working');}
function message(text){$('#message').textContent=text;$('#message').hidden=!text;}
function cancel(){S.token++;S.controller?.abort();S.controller=null;S.busy=false;S.current=null;message('');show('ask');updateAction();}
function choose(record){cancel();S.selected=record;S.hid=record.history_id;$('#questionInput').value=record.question;$('#archiveName').textContent=`${nameFor(S.hid)}’s archive · choose a memory`;updateAction();}
function updateAction(){const text=$('#questionInput').value.trim();S.selected=S.records.find(r=>r.history_id===S.hid&&r.question===text)||null;
 $('#replayButton').disabled=S.busy||!S.data||!text;$('#replayButton').innerHTML=`${S.selected?'Find this memory':'Find the evidence'} <span aria-hidden="true">→</span>`;
 $('#questionHelp').textContent=S.selected?'Instant replay · a real recorded Reactor answer.':'Your own question · searches the local archive first.';
}
function answer(record,{live=false,evidenceOnly=false}={}){S.current=record;S.busy=false;show('answer');const abstain=isAbstain(record);
 $('#askedQuestion').textContent=record.question;$('#answerEyebrow').textContent=evidenceOnly?'THE PAGES ARE READY':abstain?'NOT IN THIS ARCHIVE':'A MEMORY FOUND';
 const text=evidenceOnly?'The evidence is on the desk.':abstain?'Some things were never said.':record.answer||'No answer was returned.';
 $('#answerText').textContent=text;$('#answerText').classList.toggle('long-answer',text.length>65);
 $('#answerMeta').textContent=evidenceOnly?'Read the selected conversations, or ask Reactor for an answer.':abstain?'Reactor could not find enough evidence, so it chose not to guess.':live?'Answered just now by Reactor.':'Reactor’s original answer, replayed from a recorded run.';
 const sourceIds=[...new Set(record.cited||[])],sourceCount=evidenceOnly?(record.passages||[]).length:sourceIds.length;
 $('#sourcesButton').innerHTML=`${evidenceOnly?'View selected pages':sourceCount?`View ${sourceCount} ${sourceCount===1?'source':'sources'}`:'Inspect the evidence'} <span aria-hidden="true">↗</span>`;
 $('#liveButton').hidden=!evidenceOnly||S.reactorBusy!==false;$('#sourcesButton').disabled=!(record.passages||[]).length;
 if(evidenceOnly&&S.reactorBusy!==false)$('#answerMeta').textContent+=' Live answers are unavailable right now.';
 $('#answerText').focus({preventScroll:true});
}
async function replay(record){cancel();const token=S.token;S.busy=true;show('working');$('#workingLabel').textContent='READING THE ARCHIVE';$('#workingTitle').innerHTML='A moment,<br>please.';$('#phaseText').textContent='Looking for the right pages.';
 await nap(700);if(token!==S.token)return;$('#phaseText').textContent='A few pages. One small memory.';
 await nap(800);if(token!==S.token)return;answer(record);
}
async function live(ask=false){cancel();const token=S.token,question=$('#questionInput').value.trim();if(!question||!S.hid)return;S.busy=true;S.controller=new AbortController();show('working');$('#workingLabel').textContent=ask?'CONSULTING REACTOR':'READING THE ARCHIVE';$('#workingTitle').innerHTML='A moment,<br>please.';$('#phaseText').textContent=ask?'Reactor is reading. This can take a minute or two.':'Finding the conversations behind your question.';
 const doze=ask?setTimeout(()=>{if(token===S.token&&S.busy)$('#phaseText').textContent='Still thinking. Even the Librarian is taking a little rest.';},15000):null;
 try{const res=await fetch(ask?'/api/ask':'/api/pack',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({history_id:S.hid,split:S.records.find(r=>r.history_id===S.hid)?.split||'test',question}),signal:S.controller.signal});const record=await res.json();if(token!==S.token)return;
 if(!res.ok)throw new Error(res.status===409?'Reactor is occupied with the benchmark. You can still replay recorded memories.':record.error||'The archive could not complete this request.');
 if(ask&&record.status&&record.status!=='answered')throw new Error(`Reactor did not return an answer (${record.status}). Please try another memory.`);
 answer(record,{live:ask,evidenceOnly:!ask});
 }catch(error){if(token!==S.token||error.name==='AbortError')return;S.busy=false;show('ask');updateAction();message(error.message);}
 finally{clearTimeout(doze);if(token===S.token){S.busy=false;S.controller=null;}}
}
function renderQuestions(){const query=$('#questionSearch').value.toLowerCase().trim(),rank=r=>{const i=TOUR.indexOf(r.question_id);return i<0?99:i;};const rows=S.records.filter(r=>[r.question,nameFor(r.history_id),ROUTES[r.route]?.name].join(' ').toLowerCase().includes(query)).sort((a,b)=>rank(a)-rank(b));
 $('#questionResults').innerHTML=rows.length?rows.map(r=>`<button class="question-result" data-choose="${esc(r.question_id)}"><small>${esc(nameFor(r.history_id))} · ${esc(ROUTES[r.route]?.name||'A recorded memory')}</small><span>${esc(r.question)}</span></button>`).join(''):'<p class="no-results">No memories match. Try a different word.</p>';
}
function sources(){const r=S.current;if(!r)return;const cited=new Set(r.cited||[]),all=r.passages||[];const selected=all.map((p,index)=>({p,index}));const hasAnswer=!$('#liveButton').hidden||$('#answerEyebrow').textContent==='THE PAGES ARE READY';const primary=cited.size?selected.filter(({p})=>cited.has(p.id)):selected,other=cited.size?selected.filter(({p})=>!cited.has(p.id)):[];
 $('#sourceSummary').textContent=cited.size?`${cited.size} cited conversations. These are the passages Reactor referred to.`:hasAnswer?'The passages selected by local retrieval. Reactor has not answered this question yet.':'These pages were selected for Reactor. It did not find enough evidence for an answer.';
 const render=({p,index})=>`<article class="source-card"><div class="source-card-head"><span>${cited.has(p.id)?'CITED CONVERSATION':'SELECTED EVIDENCE'}</span><time>${esc(date(p.date))}</time></div><p>${esc(p.text.slice(0,330))}${p.text.length>330?'…':''}</p><button class="text-link" data-passage="${index}">Read the conversation ↗</button><small>${esc(p.id)}</small></article>`;
 $('#evidenceList').innerHTML=primary.map(render).join('')+(other.length?`<details><summary>${other.length} other selected ${other.length===1?'page':'pages'}</summary>${other.map(render).join('')}</details>`:'');$('#sourcesDialog').showModal();
}
function passage(index){const r=S.current,p=r?.passages?.[index];if(!p)return;$('#passageLabel').textContent=(r.cited||[]).includes(p.id)?'CITED BY REACTOR':'SELECTED EVIDENCE';$('#passageDate').textContent=`${date(p.date)} · ${p.id}`;$('#passageBody').innerHTML=esc(p.text).replace(/^(user|assistant):/gm,'<b>$1:</b>');$('#passageDialog').showModal();}
function chapter(index){S.chapter=(index+CHAPTERS.length)%CHAPTERS.length;const c=CHAPTERS[S.chapter];$('#comicImage').src=`assets/comic_${S.chapter+1}.webp`;$('#comicImage').alt=c.alt;$('#comicLabel').textContent=c.label;$('#comicTitle').textContent=c.title;$('#comicDescription').textContent=c.description;$('#comicPage').textContent=`0${S.chapter+1} / 05`;}
function renderMetrics(){const c=calibration(S.data.dev||[]);$('#sampleLabel').textContent=`${c.n} recorded questions from our dev calibration sample.`;$('#metrics').innerHTML=`<div><strong>${percent(c.strict)}</strong><span>Strict answer match</span><small>${c.n} dev questions</small></div><div><strong>${c.f1===null?'—':c.f1.toFixed(2)}</strong><span>Evidence F1</span><small>Answerable questions</small></div><div><strong>${percent(c.abstain)}</strong><span>Abstention recall</span><small>${c.unanswerable} unanswerable questions</small></div>`;
 $('#routeResults').innerHTML=Object.entries(c.byRoute).map(([route,row])=>`<p><span>${ROUTES[route].name}</span><span>${row.n?`${row.correct} / ${row.n}`:'No sample'}</span></p>`).join('');
}
async function poll(){try{const r=await fetch('/api/status',{cache:'no-store'});if(!r.ok)throw new Error('offline');S.reactorBusy=!!(await r.json()).reactor_busy;}catch{S.reactorBusy=null;}if(S.current&&$('#answerEyebrow').textContent==='THE PAGES ARE READY')$('#liveButton').hidden=S.reactorBusy!==false;}
function bind(){
 $('#questionForm').addEventListener('submit',e=>{e.preventDefault();if(S.busy||!S.data)return;updateAction();if(!$('#questionInput').value.trim())return;S.selected?replay(S.selected):live(false);});
 $('#questionInput').addEventListener('input',()=>{message('');updateAction();});$('#cancelButton').addEventListener('click',cancel);$('#anotherButton').addEventListener('click',()=>{cancel();$('#questionInput').focus();});$('#liveButton').addEventListener('click',()=>{if(S.reactorBusy===false)live(true);});$('#sourcesButton').addEventListener('click',sources);
 $('#browseQuestions').addEventListener('click',()=>{$('#questionSearch').value='';renderQuestions();$('#questionDialog').showModal();$('#questionSearch').focus();});$('#questionSearch').addEventListener('input',renderQuestions);
 $('#aboutButton').addEventListener('click',()=>$('#aboutDialog').showModal());$('#ledgerButton').addEventListener('click',()=>$('#ledgerDialog').showModal());$('#comicPrev').addEventListener('click',()=>chapter(S.chapter-1));$('#comicNext').addEventListener('click',()=>chapter(S.chapter+1));
 $('#motionToggle').addEventListener('click',()=>{const paused=document.body.classList.toggle('motion-paused');$('#motionToggle').setAttribute('aria-pressed',paused);$('#motionToggle').textContent=`Indicator lights: ${paused?'off':'on'}`;$('#motionToggle').setAttribute('aria-label',paused?'Resume indicator lights':'Pause indicator lights');});
 document.addEventListener('click',e=>{const close=e.target.closest('[data-close]');if(close)document.getElementById(close.dataset.close).close();const choice=e.target.closest('[data-choose]');if(choice){const r=S.records.find(x=>x.question_id===choice.dataset.choose);$('#questionDialog').close();if(r)choose(r);}const source=e.target.closest('[data-passage]');if(source)passage(Number(source.dataset.passage));});
 document.addEventListener('keydown',e=>{if(e.key==='Escape'&&S.busy&&!$('dialog[open]'))cancel();});
}
async function boot(){bind();chapter(0);try{const res=await fetch('/replay.json');if(!res.ok)throw new Error('The archive could not be opened. Reload the page to try again.');S.data=await res.json();S.records=[...(S.data.test||[]),...(S.data.dev||[])];if(!S.records.length)throw new Error('No recorded memories are available yet.');const first=S.records.find(r=>r.question_id===TOUR[0])||S.records[0];$('#questionInput').disabled=false;$('#browseQuestions').disabled=false;choose(first);renderMetrics();poll();setInterval(poll,20000);}catch(error){S.data=null;$('#archiveName').textContent='The archive is unavailable';$('#questionHelp').textContent='Please reload to try again.';$('#sampleLabel').textContent='Calibration data is unavailable.';message(error.message);}}
boot();
