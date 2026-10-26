"""Actual Gemini transport envelopes, including harmless arrays, without API calls."""
import json
from unittest.mock import patch
from ai_newsroom import fetch_gemini,batch_schema,response_object

def main():
    writing='SOURCE PACKETS: example';review='Return JSON articles (array of {id, reviews})'
    assert batch_schema(writing)['properties']['articles']['items']['required']==['id','article']
    assert batch_schema(review)['properties']['articles']['items']['required']==['id','reviews']
    assert batch_schema('ordinary single story') is None
    rows=[{'id':'N01','article':{'headline':'Example only'}}]
    assert response_object(rows,True)=={'articles':rows}
    for value in [[],['text'],42,rows]:
        try:response_object(value,False)
        except ValueError:pass
        else:raise AssertionError('Invalid non-batch response accepted')
    class Response:
        def __enter__(self):return self
        def __exit__(self,*a):pass
        def read(self,*a):return json.dumps({'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':json.dumps(rows)}]}}]}).encode()
    with patch('ai_newsroom.KEY','fixture-key'),patch('ai_newsroom.urllib.request.urlopen',return_value=Response()) as http:
        result=fetch_gemini(writing)
    assert result['articles']==rows and http.call_count==1
    payload=json.loads(http.call_args.args[0].data)
    assert payload['generationConfig']['responseSchema']['required']==['articles']
    print('PASS: real Gemini adapter accepts numbered batches, sends response schema and makes exactly one metered HTTP request')
if __name__=='__main__':main()
