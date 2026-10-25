"""Read the actual production site at 390px and 1440px. Evidence is never fixture content."""
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright
from same_day_policy import published_same_day
from site_design import desk_for
ROOT=Path(__file__).resolve().parents[1]
SITE=os.getenv('BRIEF_SITE_URL','https://yogeshkaransharma-code.github.io/the-brief-financial-news/').rstrip('/')+'/'
OUT=ROOT/'browser-evidence'

def main():
    articles=json.loads((ROOT/'data/articles.json').read_text());today=[a for a in articles if published_same_day(a)]
    OUT.mkdir(exist_ok=True);results=[]
    with sync_playwright() as p:
        browser=p.chromium.launch()
        for width in [390,1440]:
            context=browser.new_context(viewport={'width':width,'height':844},is_mobile=width==390,has_touch=width==390)
            page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
            page.goto(SITE,wait_until='networkidle',timeout=60000)
            assert page.locator('#lead-story').is_visible()
            assert page.locator('#feed .news-item').count()==len(today[:10]),'Visible today count differs'
            visible='\n'.join(page.locator('#lead-story,#briefing-stories,#feed').all_inner_texts())
            for a in articles:
                if a not in today:assert a['title'] not in visible,'Old story in today edition'
            for a in articles:
                if a.get('retrospective_launch') and page.locator('#launch-edition').count():
                    assert page.locator('#launch-edition').is_visible()
                    assert a['title'] in page.locator('#launch-edition').inner_text()
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'),'Homepage overflows viewport'
            assert page.locator('#publisher-desk').count()==0,'External publisher headlines leaked into the publication'
            assert page.locator('.tb-nav a').count()==3,'Navigation is not exactly Insurance, Banking and About'
            assert page.locator('.tb-sector-visual').count()==2,'Insurance and banking imagery missing'
            assert page.locator('a[href="status.html"]').count()==0,'Technical dashboard link leaked'
            page.screenshot(path=str(OUT/f'home-{width}.png'),full_page=True)
            page.locator('.tb-sector-visual[href="archive.html?category=Banking"]').click()
            page.wait_for_load_state('domcontentloaded')
            try:
                page.wait_for_function("document.querySelector('#archive-category')?.value === 'Banking'",timeout=9000)
            except Exception:
                details=page.evaluate("({href:location.href,select:document.querySelector('#archive-category')?.value,options:[...document.querySelector('#archive-category')?.options||[]].map(x=>x.value),scripts:document.scripts.length,ready:document.readyState})")
                raise AssertionError('Banking section filter failed: '+str(details))
            assert page.locator('article[data-category="Banking"]:visible').count()>0,'Banking section is empty'
            page.goto(SITE+'archive.html',wait_until='domcontentloaded',timeout=60000)
            assert 'The archive.' in page.locator('h1').inner_text()
            assert page.locator('article[data-category]').count()==len(articles),'Archive headline count differs'
            if articles:
                target=articles[0]
                page.locator('#archive-search').fill(target['title'])
                assert page.locator('article[data-category]:visible').count()==1,'Archive search failed'
                page.locator('#archive-category').select_option(desk_for(target))
                assert page.locator('article[data-category]:visible').count()==1,'Archive subject filter failed'
                page.get_by_role('link',name=target['title'],exact=True).click()
                assert target['title']==page.locator('h1').inner_text()
                body=page.locator('main article').inner_text()
                for heading,text in target['blocks']:
                    assert heading in body and text in body,'Full reading content missing'
                original=page.locator('main article .source a[href]').first
                assert original.count()==1,'Article is missing a visible link to its original evidence'
                assert original.get_attribute('href')==target['url'],'Source URL differs'
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'),'Article overflows viewport'
                page.screenshot(path=str(OUT/f'article-{width}.png'),full_page=True)
                # Read original source in the actual browser as well as verifying the href.
                source=context.new_page()
                try:
                    response=source.goto(target['url'],wait_until='domcontentloaded',timeout=30000)
                    results.append({'width':width,'article':target['id'],'source_url':target['url'],'source_http':response.status if response else None,'source_heading':source.locator('h1').first.inner_text() if source.locator('h1').count() else None})
                    source.screenshot(path=str(OUT/f'original-source-{width}.png'),full_page=True)
                    if not response or not response.ok:print('COVERAGE_WARNING: original source currently inaccessible; on-site article and source link verified')
                except Exception as exc:
                    results.append({'width':width,'article':target['id'],'source_url':target['url'],'coverage_warning':type(exc).__name__})
                    print('COVERAGE_WARNING: source browser access failed; complete on-site article verified')
                finally:source.close()
            page.goto(SITE+'sources.html',wait_until='domcontentloaded',timeout=60000)
            page.locator('#source-search').fill('RSS/Atom')
            assert page.locator('[data-source-row]:visible').count()>0,'Source registry search failed'
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'),'Source registry overflows viewport'
            page.goto(SITE+'about.html',wait_until='domcontentloaded',timeout=60000)
            assert page.locator('.tb-nav a').count()==3
            assert page.locator('a[href="status.html"]').count()==0
            assert page.locator('.tb-about-images img').count()==2
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'),'About page overflows viewport'
            page.screenshot(path=str(OUT/f'about-{width}.png'),full_page=True)
            assert not errors,errors
            context.close()
        browser.close()
    (OUT/'result.json').write_text(json.dumps({'today':len(today),'archive':len(articles),'checks':results},indent=2)+'\n')
    print('ACTUAL_LIVE_BROWSER_OK:',json.dumps({'today':len(today),'archive':len(articles),'checks':results}))
if __name__=='__main__':main()

