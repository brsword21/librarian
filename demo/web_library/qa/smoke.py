"""Frontend-only smoke checks. All API writes are mocked; no Reactor calls."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

ROOT=Path(__file__).resolve().parent.parent
URL='http://127.0.0.1:8804/'
DATA=json.loads((ROOT.parent/'replay.json').read_text())
REC=next(r for r in DATA['test'] if r['question_id']=='q_62e927862f62')
report=[]

def choose(page,qid):
    page.locator('#browseQuestions').click()
    page.locator(f'[data-choose="{qid}"]').click()

def no_overflow(page):
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'horizontal overflow'

with sync_playwright() as p:
    browser=p.chromium.launch(headless=True)
    context=browser.new_context(viewport={'width':1440,'height':900})
    page=context.new_page(); errors=[];missing=[]
    page.on('pageerror',lambda error:errors.append(str(error)))
    page.on('response',lambda res:missing.append(res.url) if res.status==404 else None)
    page.route('**/api/status',lambda route:route.fulfill(json={'reactor_busy':True}))
    page.route('**/api/ask',lambda route:route.fulfill(status=409,json={'error':'busy'}))
    page.route('**/api/pack',lambda route:route.fulfill(json={**REC,'answer':None,'cited':[]}))
    page.goto(URL);page.wait_for_load_state('networkidle');expect(page.locator('#replayButton')).to_be_enabled()
    no_overflow(page);page.screenshot(path=str(ROOT/'qa/quiet-ask-1440.png'))
    assert page.locator('#evidenceList').is_hidden()
    page.locator('#replayButton').click();expect(page.locator('#answerText')).to_have_text(REC['answer'])
    assert page.locator('#questionInput').is_hidden()
    page.screenshot(path=str(ROOT/'qa/quiet-answer-1440.png'))
    page.locator('#sourcesButton').click();expect(page.locator('#sourcesDialog')).to_be_visible()
    assert page.locator('.source-card').count()==len(REC['passages'])
    # Cited pages are shown first; extra selected evidence stays collapsed.
    assert page.locator('#evidenceList > .source-card').count()==len(set(REC['cited']))
    page.locator('[data-passage]').first.click();expect(page.locator('#passageDialog')).to_be_visible()
    expect(page.locator('#passageBody')).to_contain_text('user:')
    page.keyboard.press('Escape');expect(page.locator('#sourcesDialog')).to_be_visible()
    page.screenshot(path=str(ROOT/'qa/quiet-sources-1440.png'));page.keyboard.press('Escape')
    page.locator('#anotherButton').click();expect(page.locator('#askView')).to_be_visible()
    report.append('replay, progressive disclosure, cited sources, nested full-passage dialog, return')
    choose(page,'q_499fc53af8ca');page.locator('#replayButton').click()
    expect(page.locator('#answerText')).to_have_text('Some things were never said.')
    expect(page.locator('#answerMeta')).to_contain_text('not to guess')
    page.screenshot(path=str(ROOT/'qa/quiet-abstain-1440.png'));page.locator('#anotherButton').click()
    report.append('recorded abstention')
    choose(page,REC['question_id']);page.locator('#replayButton').click();page.locator('#cancelButton').click()
    page.wait_for_timeout(1800);expect(page.locator('#askView')).to_be_visible();expect(page.locator('#answerView')).to_be_hidden()
    report.append('cancelled replay does not publish a late answer')
    page.locator('#questionInput').fill('A custom question without a recording?')
    expect(page.locator('#replayButton')).to_contain_text('Find the evidence');page.locator('#replayButton').click()
    expect(page.locator('#answerEyebrow')).to_have_text('THE PAGES ARE READY');expect(page.locator('#liveButton')).to_be_hidden()
    expect(page.locator('#answerMeta')).to_contain_text('unavailable');page.locator('#anotherButton').click()
    report.append('custom question uses retrieval; busy Reactor cannot be invoked')
    page.unroute('**/api/pack');pending=[]
    page.route('**/api/pack',lambda route:pending.append(route))
    page.locator('#replayButton').click();expect(page.locator('#workingView')).to_be_visible()
    page.locator('#cancelButton').click();expect(page.locator('#askView')).to_be_visible()
    for route in pending:
        try:route.fulfill(json=REC)
        except Exception:pass
    page.wait_for_timeout(300);expect(page.locator('#answerView')).to_be_hidden()
    page.unroute('**/api/pack')
    page.route('**/api/pack',lambda route:route.fulfill(status=500,json={'error':'Local archive unavailable.'}))
    page.locator('#replayButton').click();expect(page.locator('#message')).to_have_text('Local archive unavailable.')
    expect(page.locator('#askView')).to_be_visible();report.append('aborted retrieval and server errors leave a usable form')
    page.locator('#aboutButton').click();expect(page.locator('#comicPage')).to_have_text('01 / 05')
    for i in range(4):page.locator('#comicNext').click()
    expect(page.locator('#comicPage')).to_have_text('05 / 05')
    page.screenshot(path=str(ROOT/'qa/quiet-story-1440.png'));page.keyboard.press('Escape')
    page.locator('#ledgerButton').click();expect(page.locator('#metrics')).to_contain_text('Evidence F1')
    expect(page.locator('#sampleLabel')).to_contain_text(str(len(DATA['dev'])))
    page.screenshot(path=str(ROOT/'qa/quiet-ledger-1440.png'));page.keyboard.press('Escape')
    page.locator('#motionToggle').click();expect(page.locator('body')).to_have_class('motion-paused')
    report.append('five comic chapters, dev-only metrics, ambient-light pause')
    # Known-available status is mocked too. The actual API write is intercepted as 409.
    available=context.new_page();available.route('**/api/status',lambda r:r.fulfill(json={'reactor_busy':False}))
    available.route('**/api/pack',lambda r:r.fulfill(json={**REC,'answer':None,'cited':[]}))
    available.route('**/api/ask',lambda r:r.fulfill(status=409,json={'error':'busy'}))
    available.goto(URL);available.wait_for_load_state('networkidle');available.locator('#questionInput').fill('Custom question?')
    available.locator('#replayButton').click();expect(available.locator('#liveButton')).to_be_visible();available.locator('#liveButton').click()
    expect(available.locator('#message')).to_contain_text('occupied');expect(available.locator('#askView')).to_be_visible();available.close()
    report.append('live conflict handled without a real Reactor request')
    page.set_viewport_size({'width':1920,'height':1080});choose(page,REC['question_id']);no_overflow(page)
    page.screenshot(path=str(ROOT/'qa/quiet-ask-1920.png'))
    page.set_viewport_size({'width':390,'height':844});no_overflow(page);expect(page.locator('#replayButton')).to_be_visible()
    page.screenshot(path=str(ROOT/'qa/quiet-ask-mobile.png'))
    page.locator('#browseQuestions').click();page.locator('#questionSearch').fill('a completely nonexistent phrase')
    expect(page.locator('.no-results')).to_be_visible();page.keyboard.press('Escape')
    report.append('1920×1080, mobile fallback, empty question search')
    reduced_page=context.new_page();reduced_page.emulate_media(reduced_motion='reduce');reduced_page.goto(URL)
    reduced_page.wait_for_load_state('networkidle');assert reduced_page.locator('.diode-one').evaluate('(e)=>getComputedStyle(e).animationName')=='none'
    reduced_page.locator('#replayButton').click();expect(reduced_page.locator('#answerText')).to_have_text(REC['answer']);reduced_page.close()
    broken=context.new_page();broken.route('**/replay.json',lambda r:r.fulfill(status=503,body='unavailable'))
    broken.goto(URL);expect(broken.locator('#message')).to_contain_text('could not be opened')
    expect(broken.locator('#replayButton')).to_be_disabled();broken.close()
    assert not errors,errors
    assert not missing,missing
    report.append('reduced motion, load failure, no JS errors or missing assets')
    browser.close()
(ROOT/'qa/report.json').write_text(json.dumps({'result':'pass','checks':report,'real_reactor_calls':0},indent=2)+'\n')
print(json.dumps({'result':'pass','checks':report,'real_reactor_calls':0},indent=2))
