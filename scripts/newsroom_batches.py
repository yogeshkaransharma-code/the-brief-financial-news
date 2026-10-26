"""Batch drafts and separately challenge every sentence, retaining per-story checks."""
import json
from newsroom_v2 import (write_prompt, make_article, article_sentences, review_prompt,
                        reconcile_reviews, build_audit, prepare_bundle)
from editorial_gate import check

def draft_batch(pairs,call,on_article,on_error):
    ids={f'N{i+1:02}':pair for i,pair in enumerate(pairs)}
    prompt=('Write independent, original articles for these unrelated sources. '
            'Never combine facts between sources. Each article must satisfy its own instructions. '
            'Aim for 120–250 words per article when supported. Return ONLY JSON with articles '
            '(an array of {id, article}); article is the JSON object requested by that source. '
            'Return every supplied ID once. SOURCE PACKETS:\n'+
            '\n\n'.join(ident+'\n'+write_prompt(item,doc) for ident,(item,doc) in ids.items()))
    response=call(prompt)
    rows=response.get('articles') if isinstance(response,dict) else None
    if not isinstance(rows,list):raise ValueError('Batch writer returned no articles array')
    for ident,(item,doc) in ids.items():
        try:
            matches=[r for r in rows if isinstance(r,dict) and r.get('id')==ident]
            if len(matches)!=1:raise ValueError('Writer omitted or repeated this candidate ID')
            article=make_article(matches[0].get('article'),item,doc)
            on_article(item,doc,article)
        except Exception as error:on_error(item,'writing',error)

def review_batch(triples,call,on_bundle,on_error):
    ids={f'N{i+1:02}':triple for i,triple in enumerate(triples)}
    prompt=('You are the independent reviewer for separate articles. Review each ONLY against '
            'its own indexed source passages. Never use another article as evidence. '
            'Return ONLY JSON with articles (array of {id, reviews}); reviews follows the '
            'complete per-sentence schema in each packet. Return every supplied article ID once.\n'+
            '\n\n'.join(ident+'\n'+review_prompt(article,doc,article_sentences(article))
                       for ident,(item,doc,article) in ids.items()))
    response=call(prompt)
    rows=response.get('articles') if isinstance(response,dict) else None
    if not isinstance(rows,list):raise ValueError('Batch reviewer returned no articles array')
    for ident,(item,doc,article) in ids.items():
        try:
            matches=[r for r in rows if isinstance(r,dict) and r.get('id')==ident]
            if len(matches)!=1:raise ValueError('Reviewer omitted or repeated this article ID')
            checks,flags,coverage=reconcile_reviews(article,doc,matches[0])
            bundle=prepare_bundle(article,build_audit(article,doc,item,checks,coverage),doc,flags)
            bundle['revision_history']=[{'revision':0,'problems':flags,'sentences':coverage['total_sentences']}]
            if not flags:
                try:check(bundle)
                except (ValueError,KeyError,TypeError) as error:
                    flags.append({'reason':str(error),'type':'deterministic_check'})
            on_bundle(item,doc,article,bundle,not bool(flags))
        except Exception as error:on_error(item,'independent_review',error)
