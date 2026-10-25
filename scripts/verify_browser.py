"""Read the actual production site at 390px and 1440px. Evidence is never fixture content."""
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright
from same_day_policy import published_same_day
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
            assert page.locator('#hourly-radar').is_visible()
            radar=json.loads((ROOT/'data/hourly-radar.json').read_text())
            assert page.locator('#hourly-radar .radar-card').count()==len(radar.get('items',[])),'Hourly headline count differs'
            assert page.locator('#feed .news-item').count()==len(today[:10]),'Visible today count differs'
            visible='\n'.join(page.locator('#lead-story,#briefing-stories,#feed').all_inner_texts())
            for a in articles:
                if a not in today:assert a['title'] not in visible,'Old story in today edition'
            for a in articles:
                if a.get('retrospective_launch') and page.locator('#launch-edition').count():
                    assert page.locator('#launch-edition').is_visible()
                    assert a['title'] in page.locator('#launch-edition').inner_text()
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'),'Homepage overflows viewport'
            page.screenshot(path=str(OUT/f'home-{width}.png'),full_page=True)
            page.get_by_role('link',name='Archive',exact=True).click()
            assert 'The archive.' in page.locator('h1').inner_text()
            assert page.locator('article[data-category]').count()==len(articles),'Archive headline count differs'
            if articles:
                target=articles[0]
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
                response=source.goto(target['url'],wait_until='domcontentloaded',timeout=60000)
                results.append({'width':width,'article':target['id'],'source_url':target['url'],'source_http':response.status if response else None,'source_heading':source.locator('h1').first.inner_text() if source.locator('h1').count() else None})
                source.screenshot(path=str(OUT/f'original-source-{width}.png'),full_page=True)
                assert response and response.ok,'Original evidence is inaccessible to the browser'
            page.goto(SITE+'status.html',wait_until='domcontentloaded',timeout=60000)
            status=json.loads((ROOT/'data/status.json').read_text())
            displayed=page.get_by_role('row').filter(has_text='New articles this run').locator('td').inner_text()
            assert displayed==str(status['published_this_run']),'Status page hides or misstates zero article count'
            page.screenshot(path=str(OUT/f'status-{width}.png'),full_page=True)
            assert not errors,errors
            context.close()
        browser.close()
    (OUT/'result.json').write_text(json.dumps({'today':len(today),'archive':len(articles),'checks':results},indent=2)+'\n')
    print('ACTUAL_LIVE_BROWSER_OK:',json.dumps({'today':len(today),'archive':len(articles),'checks':results}))
if __name__=='__main__':main()
