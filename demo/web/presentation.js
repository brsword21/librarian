/* Presentation-only enhancements. Retrieval, replay answers and citation logic live in app.js. */
(() => {
 const $=s=>document.querySelector(s);
 const chapters=[
  {label:'THE QUESTION',title:'First, a question.',description:'A single fact may be buried in months of conversation. Start with what you want to remember.',detail:'Every replay above starts with a real question from the benchmark.',alt:'The Librarian receives a question on a punch card through a pneumatic tube.'},
  {label:'THE ROUTER',title:'Choose the right lens.',description:'A personal fact, a recommendation, a change of plans? The router chooses a specialised way to read the history.',detail:'The five lenses below correspond to five kinds of memory questions.',alt:'The Librarian lowers a coloured loupe from his brass headset to read a question.'},
  {label:'LOCAL RETRIEVAL',title:'Find the few pages that matter.',description:'Keyword search finds the words. Local embeddings look for meaning. Reranking brings the most relevant passages to the desk.',detail:'The moth is keyword search; the owl is semantic search; the scales are reranking.',alt:'An owl and moth search the shelves while the Librarian weighs selected pages.'},
  {label:'CONTEXT & CHECKS',title:'Put the evidence in context.',description:'Local code lines up dates, calculates day gaps and checks which value is newest. It also flags mentions that look relevant but refer to somebody else.',detail:'These are the notes shown in the middle panel of the demo. Reactor still produces the final answer.',alt:'The Librarian passes a leather satchel of selected pages to the brass Reactor.'},
  {label:'THE REACTOR',title:'Answer, cite, or abstain.',description:'Reactor reads the selected evidence and returns an answer with references to its conversations. When the history does not support an answer, it can abstain.',detail:'The answer, citations, and original full reply are all visible in the demo above.',alt:'Reactor produces a scroll with wax citations; an inset shows the Librarian shrugging at an empty book.'},
 ];
 let chapter=0;
 function select(i,{focus=false}={}){
  chapter=(i+chapters.length)%chapters.length;const c=chapters[chapter];
  $('#chapterImage').src=`assets/comic_${chapter+1}.webp`;$('#chapterImage').alt=c.alt;
  $('#chapterLabel').textContent=c.label;$('#chapterTitle').textContent=c.title;$('#chapterDescription').textContent=c.description;$('#chapterDetail').textContent=c.detail;$('#chapterCount').textContent=`0${chapter+1} / 05`;
  for(const tab of document.querySelectorAll('[data-chapter]')){const chosen=Number(tab.dataset.chapter)===chapter;tab.setAttribute('aria-selected',chosen);tab.tabIndex=chosen?0:-1;if(chosen&&focus)tab.focus({preventScroll:true});}
  $('#chapterPanel').setAttribute('aria-labelledby',`chapterTab${chapter}`);
 }
 $('#chapterPrev').addEventListener('click',()=>select(chapter-1));$('#chapterNext').addEventListener('click',()=>select(chapter+1));
 document.querySelector('.chapter-tabs').addEventListener('click',e=>{const tab=e.target.closest('[data-chapter]');if(tab)select(Number(tab.dataset.chapter));});
 document.querySelector('.chapter-tabs').addEventListener('keydown',e=>{if(e.key==='ArrowRight'||e.key==='ArrowLeft'){e.preventDefault();e.stopPropagation();select(chapter+(e.key==='ArrowRight'?1:-1),{focus:true});}else if(e.key==='Home'||e.key==='End'){e.preventDefault();select(e.key==='Home'?0:4,{focus:true});}});
 const librarian=$('#librarian img');
 function updatePose(){const state=$('#oracle').dataset.state;const active=document.querySelector('#steps li.on')?.dataset.step;const pose=state==='abstained'?'shrug':state==='answered'?'eureka':state==='sleeping'?'doze':active==='1'?'search':'idle';librarian.src=`assets/char_librarian_${pose}.webp`;}
 const observer=new MutationObserver(updatePose);observer.observe($('#oracle'),{attributes:true,attributeFilter:['data-state']});observer.observe($('#steps'),{subtree:true,attributes:true,attributeFilter:['class']});updatePose();
 // A tour should not advance behind an explanation the presenter is reading.
 new IntersectionObserver(entries=>{if(!entries[0].isIntersecting&&window.__librarian?.S.tour.playing)$('#btnTour').click();},{threshold:.05}).observe($('#app'));
 select(0);
})();
// Keep keyboard focus inside the existing modal surfaces while they are open.
document.addEventListener('keydown',e=>{
 if(e.key!=='Tab')return;
 const modal=document.querySelector('.overlay.open, .drawer.open');if(!modal)return;
 const focusable=[...modal.querySelectorAll('button:not(:disabled),a[href],select,textarea,input,[tabindex="0"]')].filter(el=>el.getClientRects().length&&getComputedStyle(el).visibility!=='hidden');
 if(!focusable.length)return;const first=focusable[0],last=focusable.at(-1);
 if(e.shiftKey&&(document.activeElement===first||!modal.contains(document.activeElement))){e.preventDefault();last.focus();}
 else if(!e.shiftKey&&(document.activeElement===last||!modal.contains(document.activeElement))){e.preventDefault();first.focus();}
});
