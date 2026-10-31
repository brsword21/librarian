"""Verify the styled existing demo. All API writes intercepted; no Reactor calls."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
ROOT=Path(__file__).resolve().parent.parent
URL='http://127.0.0.1:8800/'
report=[]
with sync_playwright() as p:
    b=p.chromium.launch(headless=True)
    context=b.new_context(viewport={'width':1440,'height':900})
    page=context.new_page();errors=[];missing=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.on('response',lambda r:missing.append(r.url) if r.status==404 else None)
    page.route('**/api/status',lambda r:r.fulfill(json={'reactor_busy':True}))
    page.route('**/api/ask',lambda r:r.fulfill(status=409,json={'error':'busy'}))
    page.route('**/api/pack',lambda r:r.fulfill(status=500,json={'error':'local test error'}))
    page.goto(URL+'?instant=1');page.wait_for_load_state('networkidle')
    page.wait_for_function('document.querySelector("#loading").classList.contains("gone")')
    assert page.locator('.book').count()==200
    assert page.locator('.book').first.evaluate('(e)=>getComputedStyle(e).backgroundImage').find('ui_spine_')>=0
    report.append('full 200-session archive uses local illustrated book spines')
    ids=['q_62e927862f62','q_06ae4afa8961','q_392fdc44c911','q_068d0a4b3f7b','q_499fc53af8ca','q_40f751819121']
    for qid in ids:
        page.evaluate('async id=>{const {S,play}=window.__librarian; await play(S.byId.get(id));}',qid)
        rec=page.evaluate('window.__librarian.S.rec')
        abstain=rec.get('abstained') or rec.get('answer')=='INSUFFICIENT_EVIDENCE'
        expected='abstained' if abstain else 'answered'
        expect(page.locator('#oracle')).to_have_attribute('data-state',expected)
        if not abstain:
            actual=page.locator('#answer').evaluate('(e)=>e.childNodes[0].textContent.trim()')
            assert actual==rec['answer'].strip(),(qid,actual,rec['answer'])
        else:expect(page.locator('#answer')).to_contain_text('Not written in the archive')
        # No panels or controls overlap; internal transcript and note scrolling is intentional.
        rects=page.evaluate('Object.fromEntries(["#banner","#archive","#stage","#ribbon","#question","#caption"].map(s=>{let r=document.querySelector(s).getBoundingClientRect();return[s,{top:r.top,bottom:r.bottom,height:r.height}]}))')
        assert rects['#banner']['bottom']<=rects['#archive']['top']
        assert rects['#archive']['bottom']<=rects['#stage']['top']
        assert rects['#stage']['bottom']<=rects['#ribbon']['top']
        assert rects['#question']['bottom']<=rects['#banner']['bottom']
        assert rects['#caption']['bottom']<=rects['#banner']['bottom']+2,(qid,rects)
        if qid=='q_40f751819121':
            expect(page.locator('#computed')).to_have_class('computed write rejected')
        if qid=='q_499fc53af8ca':
            page.wait_for_timeout(900);page.screenshot(path=str(ROOT/'qa/abstain-1440.png'))
    report.append('five question types, abstention and rejected code candidate preserve recorded answers')
    page.evaluate('async()=>{const {S,play}=window.__librarian;await play(S.byId.get("q_62e927862f62"));}')
    page.wait_for_timeout(1000);page.screenshot(path=str(ROOT/'qa/styled-1440.png'))
    assert page.locator('.page-body').first.evaluate('(e)=>parseFloat(getComputedStyle(e).fontSize)')>=18
    # Transcript can be opened with the keyboard, and close restores focus to it.
    pg=page.locator('.page').first;pg.focus();page.keyboard.press('Enter')
    expect(page.locator('#glass')).to_have_class('overlay open')
    expect(page.locator('#glassBody')).to_contain_text('Carla')
    page.wait_for_timeout(400);page.screenshot(path=str(ROOT/'qa/source-1440.png'));page.keyboard.press('Escape')
    expect(pg).to_be_focused()
    report.append('larger transcript type, full evidence view and keyboard focus return')
    page.locator('#btnQuestions').click();expect(page.locator('#drawer')).to_have_class('drawer open')
    page.wait_for_timeout(400);page.screenshot(path=str(ROOT/'qa/chooser-1440.png'))
    page.locator('.qbtn[data-id="q_068d0a4b3f7b"]').click()
    page.wait_for_function('window.__librarian.S.rec.question_id === "q_068d0a4b3f7b" && document.querySelector("#oracle").dataset.state === "answered"')
    assert page.locator('#drawer').get_attribute('aria-hidden')=='true'
    page.locator('#btnTour').click();assert page.evaluate('window.__librarian.S.tour.playing')
    page.locator('#btnTour').click();assert not page.evaluate('window.__librarian.S.tour.playing')
    report.append('existing question chooser and guided-tour controls preserved')
    page.locator('#btnHow').click();page.wait_for_function('scrollY > document.querySelector("#app").offsetHeight')
    page.wait_for_timeout(700);page.screenshot(path=str(ROOT/'qa/method-1440.png'))
    before=page.evaluate('window.__librarian.S.rec.question_id');page.keyboard.press('PageDown')
    assert page.evaluate('window.__librarian.S.rec.question_id')==before
    page.locator('#chapterTab0').scroll_into_view_if_needed();page.locator('#chapterTab0').focus();page.keyboard.press('ArrowRight')
    expect(page.locator('#chapterTab1')).to_have_attribute('aria-selected','true')
    expect(page.locator('#chapterTab1')).to_be_focused()
    for n in range(5):
        page.locator(f'#chapterTab{n}').click()
        expect(page.locator('#chapterImage')).to_have_attribute('src',f'assets/comic_{n+1}.webp')
    page.locator('#walkthrough').scroll_into_view_if_needed();page.screenshot(path=str(ROOT/'qa/walkthrough-1440.png'))
    page.locator('#lensTitle').scroll_into_view_if_needed();page.screenshot(path=str(ROOT/'qa/lenses-1440.png'))
    page.locator('.closing-story a').click();page.wait_for_function('scrollY < 20')
    report.append('scroll explanation, five illustrated steps, tab keyboard, return to demo; no tour-key conflicts')
    page.set_viewport_size({'width':1920,'height':1080})
    page.evaluate('async()=>{const {S,play}=window.__librarian;await play(S.byId.get("q_06ae4afa8961"));}')
    page.wait_for_timeout(1000);page.screenshot(path=str(ROOT/'qa/styled-1920.png'))
    assert page.locator('.page-body').first.evaluate('(e)=>parseFloat(getComputedStyle(e).fontSize)')>=22
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    report.append('1920×1080 projector view with 22px evidence text')
    page.set_viewport_size({'width':390,'height':844});page.goto(URL+'?instant=1&q=q_62e927862f62');page.wait_for_load_state('networkidle')
    page.wait_for_function('document.querySelector("#oracle").dataset.state==="answered"')
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    page.screenshot(path=str(ROOT/'qa/mobile.png'),full_page=True)
    report.append('mobile fallback has no horizontal page overflow')
    reduced=context.new_page();reduced.emulate_media(reduced_motion='reduce');reduced.goto(URL+'?q=q_62e927862f62')
    reduced.wait_for_function('document.querySelector("#oracle").dataset.state==="answered"')
    assert reduced.locator('.reactor-diode').evaluate('(e)=>getComputedStyle(e).animationName')=='none'
    reduced.close();report.append('reduced-motion disables ambient light and shortens replay')
    assert not errors,errors
    assert not missing,missing
    b.close()
(ROOT/'qa/report.json').write_text(json.dumps({'result':'pass','checks':report,'real_reactor_calls':0},indent=2)+'\n')
print(json.dumps({'result':'pass','checks':report,'real_reactor_calls':0},indent=2))
