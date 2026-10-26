"""Shared review units: retain initials and abbreviations with their sentence."""
import re

def split(text):
    result=[];start=0
    for boundary in re.finditer(r'(?<=[.!?])\s+(?=[A-Z0-9£])|\n+',text):
        prefix=text[start:boundary.start()]
        # Preserve original text; never drop an initial or alter evidence.
        if '\n' not in boundary.group() and re.search(
                r'(?:(?<![\w.])[A-Z]\.|\b(?:Mr|Mrs|Ms|Dr|Prof|Jr|Sr)\.)$',prefix):
            continue
        if prefix.strip():result.append(prefix.strip())
        start=boundary.end()
    if text[start:].strip():result.append(text[start:].strip())
    return result

if __name__=='__main__':
    text='J. Patrick Gallagher leads Arthur J. Gallagher & Co. The company announced an acquisition. Financial terms were undisclosed.'
    assert split(text)==['J. Patrick Gallagher leads Arthur J. Gallagher & Co.','The company announced an acquisition.','Financial terms were undisclosed.']
    assert split('Arthur J. Gallagher announced a deal. It serves clients.')==['Arthur J. Gallagher announced a deal.','It serves clients.']
    assert split('First heading\nSecond heading')==['First heading','Second heading']
    assert split('One statement. Another statement! Final statement?')==['One statement.','Another statement!','Final statement?']
    print('PASS: initials and abbreviations retain complete claim context; no text omitted')
