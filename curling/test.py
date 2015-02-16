import decimal
import json
import unittest

from django.conf import settings

minimal = {
    'DATABASES': {'default': {}},
    # Use the toolbar for tests because it handly caches results for us.
    'STATSD_CLIENT': 'django_statsd.clients.toolbar',
    'STATSD_PREFIX': None,
}

if not settings.configured:
    settings.configure(**minimal)

from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
import mock
from nose.tools import eq_, ok_, raises
from django_statsd.clients import get_client
from slumber.exceptions import HttpServerError

import lib
import command
lib.statsd = get_client()

from requests.exceptions import ConnectionError

# Some samples for the Mock.
samples = {
    'GET:/services/settings/APPEND_SLASH/': {
        'content': json.dumps({
            'key': 'APPEND_SLASH'
        })
    },
    'GET:/services/settings/': {
        'content': json.dumps({
            'meta': {'limit': 20, 'total_count': 185},
            'objects': [
                {'key': 'ABSOLUTE_URL_OVERRIDES'},
                {'key': 'ADMINS'},
            ]
        })
    },
    'GET:/services/setting/': {
        'content': json.dumps({
            'meta': {'limit': 20, 'total_count': 185},
            'objects': [
                {'key': 'ABSOLUTE_URL_OVERRIDES'}
            ]
        })
    },
    'GET:/services/blank/': {
        'content': None,
        'status_code': 204
    },
    'GET:/services/blankfail/': {
        'content': json.dumps({'f': 'b'}),
        'status_code': 204
    },
    'GET:/services/empty/': {
        'content': json.dumps({
            'meta': {'limit': 20, 'total_count': 185},
            'objects': []
        })
    },
    'GET:/unformatted/settings/': {
        'content': json.dumps([
            {'key': 'ABSOLUTE_URL_OVERRIDES'},
            {'key': 'ADMINS'},
        ])
    },
    'GET:/unformatted/empty/': {
        'content': json.dumps([])
    },
    'GET:/services/fatalerror/': {
        'content': '<meta name="robots" ...><body>really bad</body>',
        'content-type': 'text/html'
    },
    'PUT:http://foo.com/services/settings/': {},
    'PATCH:http://foo.com/services/settings/': {},
    'POST:http://foo.com/services/settings/': {},
    'GET:http://foo.com/services/settings/': {}
}

lib.mock_lookup = samples


class MockAttributesMixin(lib.TastypieAttributesMixin):

    def __init__(self, *args, **kw):
        super(MockAttributesMixin, self).__init__(*args, **kw)
        self._resource = MockTastypieResource


def mock_response(method, url, **kw):
    resp = mock.Mock()
    resp.headers = {}
    content = mock.Mock()
    content.__iter__ = mock.Mock(return_value=iter([]))
    lookup = lib.mock_lookup['%s:%s' % (method, url)]
    resp.content = json.dumps({})
    if 'content' in lookup:
        resp.content = lookup['content']
    resp.status_code = lookup.get('status_code', 200)
    resp.headers = {'content-type':
                    lookup.get('content-type', 'application/json')}
    return resp


class MockTastypieResource(MockAttributesMixin, lib.TastypieResource):

    def _call_request(self, method, url, data, params, headers):
        return mock_response(method, url,
            data=data, params=params, headers=headers)


class MockAPI(MockAttributesMixin, lib.CurlingBase, lib.SlumberAPI):

    def __init__(self, *args, **kw):
        return super(MockAPI, self).__init__(
            *args, **lib.make_serializer(**kw))


class TestAPI(unittest.TestCase):

    def setUp(self):
        self.api = MockAPI('')

    def test_get_one(self):
        eq_(self.api.services.settings('APPEND_SLASH').get_object(),
            samples['GET:/services/settings/APPEND_SLASH/'])

    def test_list(self):
        res = self.api.services.settings.get()
        eq_(len(res), 2)
        ok_(isinstance(res, lib.TastypieList))
        eq_(res.limit, 20)
        eq_(res.total_count, 185)

    @raises(MultipleObjectsReturned)
    def test_get_raises(self):
        self.api.services.settings.get_object()

    def test_get_blank(self):
        eq_(self.api.services.blank.get(), None)

    @raises(HttpServerError)
    def test_get_blank_fail(self):
        self.api.services.blankfail.get()

    def test_get_empty(self):
        res = self.api.services.nothing.get()
        eq_(len(res), 0)

    @raises(ObjectDoesNotExist)
    def test_get_empty(self):
        self.api.services.empty.get_object()

    @raises(MultipleObjectsReturned)
    def test_get_many(self):
        self.api.services.settings.get_object()

    def test_get_one(self):
        eq_(self.api.services.setting.get_object(),
            {'key': 'ABSOLUTE_URL_OVERRIDES'})

    def test_get_unformatted(self):
        eq_(self.api.unformatted.settings.get_object(),
            {'key': 'ABSOLUTE_URL_OVERRIDES'})

    @raises(ObjectDoesNotExist)
    def test_get_unformatted(self):
        self.api.unformatted.empty.get_object()

    @raises(ObjectDoesNotExist)
    def test_get_404(self):
        self.api.services.empty.get_object_or_404()

    @raises(ObjectDoesNotExist)
    def test_get_list_404(self):
        self.api.services.empty.get_list_or_404()

    def test_get_list_404_works(self):
        res = self.api.services.settings.get_list_or_404()
        eq_(len(res), 2)

    @raises(ObjectDoesNotExist)
    @mock.patch.object(MockTastypieResource, '_call_request')
    def test_get_404_reraised(self, _call_request):
        response = mock.Mock()
        response.status_code = 404
        _call_request.side_effect = lib.HttpClientError(response=response)
        self.api.services.empty.get_object_or_404()

    @mock.patch.object(MockTastypieResource, '_call_request')
    def test_post_decimal(self, _call_request):
        self.api.services.settings.post({
            'amount': decimal.Decimal('1.0')
        })
        eq_(json.loads(_call_request.call_args[0][2]), {u'amount': u'1.0'})

    def test_by_url(self):
        eq_(len(self.api.by_url('/services/settings/').get()), 2)
        eq_(self.api.by_url('/services/settings/APPEND_SLASH/').get(),
            {'key': 'APPEND_SLASH'})

    def test_by_url_borked(self):
        self.assertRaises(IndexError, self.api.by_url, '/')

    @raises(lib.HttpServerError)
    @mock.patch.object(MockTastypieResource, '_call_request')
    def test_connection_error(self, _call_request):
        _call_request.side_effect = ConnectionError
        self.api.services.nothing.get_object()

    def test_non_dict_is_ignored(self):
        eq_(self.api.services.fatalerror.get(),
            samples['GET:/services/fatalerror/']['content'])


@mock.patch.object(MockTastypieResource, '_call_request')
class TestOAuth(unittest.TestCase):

    def setUp(self):
        self.api = MockAPI('http://foo.com')

    def test_none(self, _call_request):
        self.api.services.settings.get()
        _call_request.assert_called_with(
            'GET',
            'http://foo.com/services/settings/', None, {},
            {'content-type': 'application/json', 'accept': 'application/json'})

    def test_some(self, _call_request):
        self.api.activate_oauth('key', 'secret')
        self.api.services.settings.get()
        _call_request.assert_called_with(
            'GET',
            'http://foo.com/services/settings/', None, {}, mock.ANY)
        ok_('OAuth realm=""' in _call_request.call_args[0][4]['Authorization'])

    def test_realm(self, _call_request):
        self.api.activate_oauth('key', 'secret', realm='r')
        self.api.services.settings.get()
        ok_('OAuth realm="r"' in
            _call_request.call_args[0][4]['Authorization'])

    def test_query_string(self, _call_request):
        self.api.activate_oauth('key', 'secret')
        self.api.services.settings.get(foo='bar')
        _call_request.assert_called_with(
            'GET',
            'http://foo.com/services/settings/', None, {'foo': 'bar'},
            mock.ANY)
        assert 'oauth_token' not in _call_request.call_args[0][-1]

    def test_with_params(self, _call_request):
        self.api.activate_oauth('key', 'secret', params={'oauth_token': 'f'})
        self.api.services.settings.get(foo='bar')
        _call_request.assert_called_with(
            'GET',
            'http://foo.com/services/settings/', None, {'foo': 'bar'},
            mock.ANY)
        assert ('oauth_token="f"' in
                _call_request.call_args[0][-1]['Authorization'])

    @raises(ValueError)
    def test_merge_conflict(self, _call_request):
        self.api.activate_oauth('key', 'secret', params={'oauth_token': 'f'})
        self.api.services.settings.get(oauth_token='bar')


@mock.patch.object(MockTastypieResource, '_call_request')
class TestCallable(unittest.TestCase):

    def setUp(self):
        self.api = MockAPI('http://foo.com')

    def test_some(self, _call_request):
        def foo(slumber, headers=None, **kwargs):
            headers['Foo'] = 'bar'

        self.api._add_callback({'method': foo})

        self.api.services.settings.get()
        ok_('Foo' in _call_request.call_args[0][4])

    def test_some_extra(self, _call_request):
        def foo(slumber, headers=None, **kwargs):
            ok_(kwargs['extra'], 'boo')

        self.api._add_callback({'method': foo, 'extra': 'bar'})
        self.api.services.settings.get()


class TestStatsd(unittest.TestCase):

    def setUp(self):
        self.api = MockAPI('http://foo.com')
        lib.statsd.reset()

    def test_get(self):
        self.api.services.settings.get()
        eq_(lib.statsd.cache, {'services.settings.GET.200|count': [[1, 1]]})
        eq_(len(lib.statsd.timings), 1)

    @mock.patch.object(MockTastypieResource, '_call_request')
    def test_get_with_etag_header(self, _call_request):
        _call_request.return_value = mock.Mock(status_code=304)
        self.api.services.settings.get(headers={'If-None-Match': 'etag'})
        eq_(lib.statsd.cache, {'services.settings.GET.304|count': [[1, 1]]})
        eq_(len(lib.statsd.timings), 1)

    def test_post(self):
        self.api.services.settings.post(data={}, headers={})
        eq_(lib.statsd.cache, {'services.settings.POST.200|count': [[1, 1]]})

    def test_put(self):
        self.api.services.settings.put(data={}, headers={})
        eq_(lib.statsd.cache, {'services.settings.PUT.200|count': [[1, 1]]})

    def test_patch(self):
        self.api.services.settings.patch(data={}, headers={})
        eq_(lib.statsd.cache, {'services.settings.PATCH.200|count': [[1, 1]]})


def test_parser():
    for k, v in [
            ('/a/b/1', (('a', 'b', '1'), None)),
            ('/a/b/c/1', (('a', 'b', 'c', '1'), None)),
            ('/a/b/c/1/', (('a', 'b', 'c', '1'), None))]:
        eq_(lib.safe_parser(k), v)



class TestCommand(unittest.TestCase):

    def setUp(self):
        self.url = '/services/settings/'
        self.method = 'GET'
        self.api = MockAPI('')

    def setup_config(self, data):
        cmd = mock.Mock()
        cmd.url = self.url
        cmd.request = self.method
        cmd.data = data if data is not None else ''

        content = json.loads(
            samples['%s:%s' % (self.method, self.url)]['content'])
        if isinstance(content, dict):
            self.expected = content['objects']
        else:
            self.expected = content
        return cmd

    def correct(self, data):
        return [
            self.method,
            self.url,
            data,
            {},
            {'content-type': 'application/json', 'accept': 'application/json'}
        ]

    @mock.patch.object(command, 'show')
    @mock.patch.object(MockTastypieResource, '_call_request')
    def _test_new_valid(self, _call_request, _show, data=None):
        cmd = self.setup_config(data)
        _call_request.return_value = mock_response(self.method, self.url)
        result = command.new(cmd, lib_api=self.api)

        _call_request.assert_called_with(*self.correct(data))
        eq_(result, self.expected)
        eq_(_show.call_args[0][0], self.expected)

    @mock.patch.object(command, 'show')
    @mock.patch.object(MockTastypieResource, '_call_request')
    def _test_new_invalid(self, _call_request, _show, data=None):
        cmd = self.setup_config(data)
        _call_request.return_value = mock_response(self.method, self.url)
        result = command.new(cmd, lib_api=self.api)

        assert not _call_request.called
        eq_(result, None)

    def test_no_data(self):
        self._test_new_valid()

    def test_some_data(self):
        self._test_new_valid(data='{"foo": "bar"}')

    def test_invalid_data(self):
        self._test_new_invalid(data='{"foo":')

    def test_show_dict(self):
        self._test_new_valid()

    def test_show_list(self):
        self.url = '/unformatted/settings/'
        self._test_new_valid()
