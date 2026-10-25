"""Only one minor whole body sentence may be removed before a fresh review."""
import copy
from newsroom_v2 import omit_flagged_context

def main():
    sentence='An unsupported optional regional detail appears in this sentence.'
    paragraph=' '.join(['The fictional regulator published a report describing its research and sample.']*7)
    a={'title':'Fictional report','short':'Fictional summary','blocks':[['First',paragraph+' '+sentence],['Second',paragraph],['Third',paragraph]]}
    flags=[{'sentence':sentence,'reason':'Not supported by this synthetic source'}]
    b=omit_flagged_context(a,flags)
    assert b and sentence not in b['blocks'][0][1] and a['blocks'][0][1].endswith(sentence)
    assert b['title']==a['title'] and b['short']==a['short'] and len(b['blocks'])==3
    assert omit_flagged_context(a,flags*2) is None
    assert omit_flagged_context(a,[{'sentence':a['short']}]) is None
    qualified=copy.deepcopy(a);qualification='However, the programme is only available to existing customers.'
    qualified['blocks'][0][1]+=' '+qualification
    assert omit_flagged_context(qualified,[{'sentence':qualification}]) is None
    empty=copy.deepcopy(a);empty['blocks'][0][1]=sentence
    assert omit_flagged_context(empty,flags) is None
    print('PASS: optional whole-sentence omission preserves original and structure; qualification, headline, multiple flags and empty section rejected')

if __name__=='__main__':main()
