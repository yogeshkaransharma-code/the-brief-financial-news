"""Original publication dating, never dateModified or an unrelated card's time."""
from __future__ import annotations
import datetime as dt
import json
import re
from bs4 import BeautifulSoup
from same_day_policy import source_issued_today, clock, original_date


def parse(value):
    value=str(value or '').strip()
    if re.fullmatch(r'20\d{2}-\d{2}-\d{2}',value):
        return (dt.date.fromisoformat(value).isoformat(),value,'date')
    try:
        stamp=dt.datetime.fromisoformat(value.replace('Z','+00:00'))
        if 'T' in value and stamp.tzinfo:
            return stamp.date().isoformat(),stamp.astimezone(dt.timezone.utc).isoformat(),'timestamp'
    except ValueError:
        pass
    # Only explicit publication elements are passed here, not arbitrary prose.
    cleaned=re.sub(r'(?i)(st|nd|rd|th)\b','',value)
    cleaned=re.sub(r'(?i)^(first published|published|publication date|date published)\s*:?\s*','',cleaned)
    for fmt in ('%d %B %Y','%d %b %Y','%B %d, %Y','%d/%m/%Y','%d.%m.%Y'):
        try:
            day=dt.datetime.strptime(cleaned,fmt).date().isoformat()
            return day,day,'date'
        except ValueError:
            pass
    return None


def published_date(markup):
    soup=BeautifulSoup(markup,'html.parser')
    values=[]
    for m in soup.select('meta[content]'):
        prop=(m.get('property') or m.get('name') or m.get('itemprop') or '').lower()
        if prop in {'article:published_time','datepublished','pubdate','dc.date.issued','dcterms.issued'}:
            values.append(m['content'])
    for node in soup.select('script[type="application/ld+json"]'):
        try:
            data=json.loads(node.string or node.get_text())
            stack=data if isinstance(data,list) else [data]
            while stack:
                record=stack.pop()
                if not isinstance(record,dict):continue
                types=record.get('@type',[])
                if isinstance(types,str):types=[types]
                if any(x in {'NewsArticle','Article','Report','PressRelease','BlogPosting'} for x in types):
                    values.append(record.get('datePublished'))
                stack.extend(record.get('@graph',[]))
                main=record.get('mainEntity')
                if isinstance(main,dict):stack.append(main)
        except (ValueError,TypeError):pass
    # A publication-specific element, never every <time> on the page.
    for node in soup.select('[itemprop="datePublished"], .published, .published-date, .date-published, .publication-date, .field--name-field-date'):
        if node.find_parent(['aside','nav','footer']):continue
        if re.search(r'(?i)updated|modified',node.get_text(' ',strip=True)):continue
        values.append(node.get('datetime') or node.get('content') or node.get_text(' ',strip=True))
    # FCA/other regulators often render an explicit First published label.
    plain=soup.get_text(' ',strip=True)
    for match in re.finditer(r'(?i)\b(?:First published|Date published|Publication date)\s*:\s*(\d{1,2}/\d{1,2}/20\d{2}|\d{1,2} [A-Za-z]+ 20\d{2}|20\d{2}-\d{2}-\d{2})',plain):
        values.append(match.group(1))
    parsed=[v for raw in values if (v:=parse(raw))]
    if parsed:
        days=set()
        for day,raw,precision in parsed:
            item={'dateISO':day,'source_time_precision':precision,'source_published_at':raw}
            days.add(original_date(item))
        if len(days)!=1:raise ValueError('Conflicting original publication dates on source page')
        return next((v for v in parsed if v[2]=='timestamp'),parsed[0])
    # Some releases display one unlabelled dateline beside the article heading.
    # Use only a dedicated date element in article/main; not all page dates.
    area=soup.select_one('article') or soup.select_one('main')
    if area:
        nodes=area.select('time[datetime], .date, .news-date, .release-date')
        candidates=[]
        for node in nodes:
            context=node.parent.get_text(' ',strip=True) if node.parent else ''
            if node.find_parent(['aside','nav','footer']) or re.search(r'(?i)updated|modified',context):continue
            if node.find_parent(class_=re.compile(r'(?i)related|card|recommend')):continue
            val=parse(node.get('datetime') or node.get_text(' ',strip=True))
            if val:candidates.append(val)
        if len(candidates)==1:return candidates[0]
    return None


def verify_announcement(item,doc,now=None):
    value=doc.publication_date
    if not value:raise ValueError('Original document has no unambiguous publication date; listing/RSS date is insufficient')
    day,raw,precision=value
    result=dict(item,dateISO=day,source_time_precision=precision,source_published_at=raw,published_at=raw)
    result['date_evidence']={'url':doc.url,'value':raw,'precision':precision,'method':'original-document publication metadata/dateline'}
    if not source_issued_today(result,now):
        raise ValueError('Original document was not announced today in the UK')
    # A changed listing cannot refresh a source that says something else.
    if item.get('source_time_precision')=='date' and item.get('dateISO') not in {day,original_date(result).isoformat()}:
        raise ValueError('Listing date conflicts with the original document publication date')
    return result
