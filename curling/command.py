import argparse
import json
import mimetypes
import os
import sys
import tempfile
import urlparse
import webbrowser

from pygments import highlight
try:
    from pygments.lexers import JSONLexer as lexer
except ImportError:
    from pygments.lexers import JsonLexer as lexer

from pygments.formatters import Terminal256Formatter

import requests
from slumber.exceptions import HttpClientError

import lib


def get_config():
    conf = {}
    for filename in ['.curling', '~/.curling']:
        full = os.path.expanduser(filename)
        if os.path.exists(full):
            conf = json.load(open(full, 'r'))
    return conf


def get_domain(domain):
    return get_config().get(domain)


def show(data):
    res = json.dumps(data, indent=2)
    out = highlight(res, lexer(), Terminal256Formatter(bg='dark'))
    print out


def show_text(data, content_type='text/plain'):
    if data:
        if len(data) < 500:
            print data
            return

    if data:
        ext = mimetypes.guess_extension(content_type)
        desc, name = tempfile.mkstemp(suffix=ext)
        open(name, 'w').write(data)
        webbrowser.open('file://%s' % name)


def new(config):
    url = urlparse.urlparse(config.url)
    api = lib.API('{0}://{1}'.format(url.scheme, url.netloc))

    local = get_domain(url.netloc)
    if local:
        api.activate_oauth(local['key'], local['secret'])

    for path in url.path.split('/'):
        api = getattr(api, path)

    method = getattr(api, config.request.lower())

    try:
        res = method(data=config.data)
    except HttpClientError, err:
        res = {
            'status': err.response.status_code,
            'headers': dict(sorted(err.response.headers.items())),
            'body': err.response.content
        }
        show(res)
        sys.exit(1)

    if isinstance(res, dict):
        show(res)
    else:
        show_text(res)


def old(config):
    headers = {'Accept': 'application/json',
               'Content-Type': 'application/json'}
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

    ctype = res.headers['content-type'].split(';')[0]
    if res.content and ctype == 'application/json':
        show(json.loads(res.content))
        return

    show_text(res.content, content_type=ctype)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--data', default=None, required=False)
    parser.add_argument('-X', '--request', default='GET', required=False)
    parser.add_argument('-i', '--include', action='store_true', required=False)
    parser.add_argument('-l', '--legacy', action='store_true', required=False)
    parser.add_argument('url')

    config = parser.parse_args()
    if config.legacy:
        old(config)
    else:
        new(config)


if __name__=='__main__':
    main()
