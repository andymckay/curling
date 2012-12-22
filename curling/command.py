import argparse
import json

from pygments import highlight
from pygments.lexers import JSONLexer
from pygments.formatters import Terminal256Formatter

import requests


def run(config):
    headers = {'Content-Type': 'application/json'}
    try:
        method = getattr(requests, config.request.lower())
    except AttributeError:
        print 'No method: %s' % config.request
        return

    res = method(config.url, data=config.data, headers=headers)
    if config.include:
        print 'HTTP', res.status_code, res.reason
        for k in sorted(res.headers.keys()):
            print '%s: %s' % (k.title(), res.headers[k])
    if res.content:
        res = json.dumps(json.loads(res.content), indent=2)
        out = highlight(res, JSONLexer(), Terminal256Formatter(bg='dark'))
        print out


if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--data', default=None, required=False)
    parser.add_argument('-X', '--request', default='GET', required=False)
    parser.add_argument('-i', '--include', action='store_true', required=False)
    parser.add_argument('url')
    run(parser.parse_args())
