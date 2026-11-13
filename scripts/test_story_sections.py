#!/usr/bin/env python3
"""Regression test: source text survives splitting into HTML paragraphs."""
from build_public import article_body
from verify_public import verify_story_sections, verify_desk_story_links
from build_public import story_href


def run():
    item = {
        'id': 'ai-rendered-story-fixture',
        'blocks': [
            ['Broker partnerships & the UK market',
             'A broker handles cross-border risks & local coverage.\n\n'
             'Second paragraph: 40% growth, <capacity> and "quotes" must survive.'],
            ['What changes for clients?',
             'First line remains together\nwith the next line.\n\n'
             'The closing point must not disappear.'],
        ],
    }
    rendered = '<div class="article-body">' + article_body(item) + '</div>'
    verify_story_sections(item, rendered)

    # The exact failure that blocked production: two or more HTML paragraphs
    # are valid representations of one source content block.
    assert rendered.count('<p>') == 4

    # Do not "fix" the deploy by weakening content-integrity checks.
    broken = [
        rendered.replace('Second paragraph:', 'Missing sentence:', 1),
        rendered.replace('<p>The closing point must not disappear.</p>', '', 1),
        rendered.replace('report-section-2', 'report-section-3', 1),
        rendered.replace('Broker partnerships &amp; the UK market', 'Wrong heading', 1),
        rendered.replace('&lt;capacity&gt;', '<capacity>', 1),
    ]
    for index, page in enumerate(broken, start=1):
        try:
            verify_story_sections(item, page)
        except AssertionError:
            pass
        else:
            raise AssertionError(f'Corrupt article fixture {index} passed verification')

    # An old report can share a title with a current report. The desk check
    # must use the selected record's distinct URL, never the headline string.
    current={'id': 'ai-aaaaaa123', 'title': 'UK insurance market update'}
    older={'id': 'ai-bbbbbb456', 'title': 'UK insurance market update'}
    card='<h2><a href="' + story_href(current) + '">UK insurance market update</a></h2>'
    verify_desk_story_links(card, [current], 'Insurance')
    wrong='<h2><a href="' + story_href(older) + '">UK insurance market update</a></h2>'
    try:
        verify_desk_story_links(wrong, [current], 'Insurance')
    except AssertionError:
        pass
    else:
        raise AssertionError('Desk accepted an old article with the same headline')

    print('PASS: complete multi-paragraph reporting, safe HTML and identity-based desk checks')


if __name__ == '__main__':
    run()
