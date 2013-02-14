import argparse
import json
import mimetypes
import tempfile
import webbrowser

from pygments import highlight
try:
    from pygments.lexers import JSONLexer as lexer
except ImportError:
    from pygments.lexers import JsonLexer as lexer

from pygments.formatters import Terminal256Formatter

import requests

from encoder import Encoder


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--data', default=None, required=False)
    parser.add_argument('-X', '--request', default='GET', required=False)
    parser.add_argument('-i', '--include', action='store_true', required=False)
    parser.add_argument('url')

    config = parser.parse_args()
    headers = {'Content-Type': 'application/json'}
    try:
        method = getattr(requests, config.request.lower())
    except AttributeError:
        print 'No method: %s' % config.request
        return

    if config.data is not None:
        config.data = json.dumps(json.loads(config.data), cls=Encoder)

    res = method(config.url, data=config.data, headers=headers)
    if config.include:
        print 'HTTP', res.status_code, res.reason
        for k in sorted(res.headers.keys()):
            print '%s: %s' % (k.title(), res.headers[k])

    ctype = res.headers['content-type'].split(';')[0]
    if res.content and ctype == 'application/json':
        res = json.dumps(json.loads(res.content), indent=2)
        out = highlight(res, lexer(), Terminal256Formatter(bg='dark'))
        print out
        return

    if res.content and ctype == 'text/html':
        if len(res.content) < 500:
            print res.content
            return

    if res.content:
        desc, name = tempfile.mkstemp(suffix=mimetypes.guess_extension(ctype))
        open(name, 'w').write(res.content)
        webbrowser.open('file://%s' % name)


if __name__=='__main__':
    main()
