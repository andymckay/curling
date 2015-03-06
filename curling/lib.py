import json
import urllib
import urlparse

from django.conf import settings  # noqa
from django.core.exceptions import (ImproperlyConfigured,
                                    MultipleObjectsReturned,
                                    ObjectDoesNotExist)

import oauthlib.oauth1

try:
    from django_statsd.clients import statsd
except (ImportError, ImproperlyConfigured):
    from mock import MagicMock
    statsd = MagicMock()

from requests.exceptions import ConnectionError

from slumber import exceptions
from slumber import API as SlumberAPI, Resource, url_join
from slumber import serialize

from encoder import Encoder


def sign_request(slumber, extra=None, headers=None, method=None, params=None,
                 url=None, **kwargs):
    if headers is None:
        headers = {}
    resource_owner_key = params.pop('oauth_token', None)
    callback_uri = params.pop('oauth_callback', None)
    verifier = params.pop('oauth_verifier', None)
    if params:
        url = '%s?%s' % (url, urllib.urlencode(params))
    client = oauthlib.oauth1.Client(
        extra['key'], client_secret=extra['secret'],
        resource_owner_key=resource_owner_key,
        callback_uri=callback_uri, verifier=verifier)
    uri, signed_headers, body = client.sign(
        url, http_method=method, headers=headers, realm=extra.get('realm', ''))

    # Update headers that was passed in argument, the caller usually don't use
    # the return value but expects us to have modified the headers passed to
    # the function.
    headers.update(signed_headers)
    return headers


#  Make slumber 400 errors show the content.
def verbose(self, *args, **kw):
    res = super(exceptions.SlumberHttpBaseException, self).__str__(*args, **kw)
    res += '\nContent: %s\n' % getattr(self, 'content', '')
    return res


def merge(orig, new):
    copy = orig.copy() or {}
    new = new or {}
    for key in new.keys():
        if key in orig:
            raise ValueError('Param conflict: %s exists' % key)
    copy.update(new)
    return copy


exceptions.SlumberHttpBaseException.__str__ = verbose


# Mixins to override the Slumber mixin.
class TastypieAttributesMixin(object):

    def __init__(self, *args, **kw):
        super(TastypieAttributesMixin, self).__init__(*args, **kw)
        self._resource = TastypieResource

    def __getattr__(self, item):
        # See Slumber for what this is.
        if item.startswith('_'):
            raise AttributeError(item)

        kwargs = {}
        for key, value in self._store.iteritems():
            kwargs[key] = value

        kwargs.update({'base_url': url_join(self._store["base_url"], item)})

        return self._resource(**kwargs)


class TastypieList(list):
    pass


# Serialize using our encoding.
class JsonSerializer(serialize.JsonSerializer):

    key = 'json'

    def dumps(self, data):
        return json.dumps(data, cls=Encoder)


def default_parser(url):
    """
    A default parser for URLs, you can override this with something different
    so that by_url gets the right thing, if you'd like to use that.

    This copes with a simple /blah/blah/pk/ scenario and should probably be
    made more complicated.

    Returns: list of resources, primary key.
    """
    split = url.split('/')
    return split[1:3], split[3] or None


def safe_parser(url):
    """
    Takes /blah/blah/some-thing-python-won't-like/ and returns the
    URL representing it.
    """
    return tuple(u for u in url.split('/') if u), None


def _key(url, method):
    """Produce a standard key for clients like statsd."""
    return '%s.%s' % (
        '.'.join([u for u in urlparse.urlparse(url).path.split('/') if u]),
        method)


class TastypieResource(TastypieAttributesMixin, Resource):

    def __init__(self, *args, **kw):
        super(TastypieResource, self).__init__(*args, **kw)

    def _is_list(self, resp):
        try:
            return set(['meta', 'objects']).issubset(set(resp.keys()))
        except (AttributeError, TypeError):
            return False

    def _format_list(self, resp):
        tpl = TastypieList(resp['objects'])
        for k, v in resp['meta'].iteritems():
            setattr(tpl, k, v)
        return tpl

    def _try_to_serialize_response(self, resp):
        headers = resp.headers
        # 204 specifically does not return any data so we shouldn't try and
        # parse it.
        if resp.status_code == 204:
            if resp.content:
                raise exceptions.HttpServerError(
                    'Server Error, not empty: %s' % resp.status_code,
                    response=resp)
            return

        resp = super(TastypieResource, self)._try_to_serialize_response(resp)
        if isinstance(resp, dict) and u'meta' in resp:
            resp[u'meta'][u'headers'] = headers
        if self.format_lists and self._is_list(resp):
            return self._format_list(resp)
        return resp

    def get(self, data=None, headers=None, **kwargs):
        """
        Allow a body in GET, because that's just fine.
        """
        s = self._store['serializer']
        resp = self._request('GET', data=s.dumps(data) if data else None,
                             headers=headers, params=kwargs)
        if 200 <= resp.status_code <= 299:
            return self._try_to_serialize_response(resp)
        elif resp.status_code == 304:
            return resp
        else:
            return

    def post(self, data, headers=None, **kwargs):
        s = self._store['serializer']

        resp = self._request('POST', data=s.dumps(data),
                             headers=headers, params=kwargs)
        if 200 <= resp.status_code <= 299:
            return self._try_to_serialize_response(resp)
        else:
            # @@@ Need to be Some sort of Error Here or Something
            return

    def patch(self, data, headers=None, **kwargs):
        s = self._store['serializer']

        resp = self._request('PATCH', data=s.dumps(data),
                             headers=headers, params=kwargs)
        if 200 <= resp.status_code <= 299:
            return self._try_to_serialize_response(resp)
        else:
            # @@@ Need to be Some sort of Error Here or Something
            return

    def put(self, data, headers=None, **kwargs):
        s = self._store['serializer']

        resp = self._request('PUT', data=s.dumps(data),
                             headers=headers, params=kwargs)
        if 200 <= resp.status_code <= 299:
            return self._try_to_serialize_response(resp)
        else:
            return False

    def get_object(self, **kw):
        """
        Gets an object and checks that one and only one object is returned.

        * first it will convert a Tastypie style response into the list of
          objects.
        * then it will return the first element unless
            * if there is more than one element raises MultipleObjectsReturned
            * if there is less than one element raises ObjectDoesNotExist
        * if a list is not found but another item, that will be returned
        """
        self.format_lists = True
        res = self.get(**kw)
        if isinstance(res, list):
            if len(res) < 1:
                raise ObjectDoesNotExist
            if len(res) > 1:
                raise MultipleObjectsReturned
            return res[0]
        return res

    def get_object_or_404(self, **kw):
        """
        Wrapper around get_object. The only difference is that if the
        server returns a HTTP 404, this then alters that into an
        ObjectDoesNotExist error.
        """
        self.format_lists = True
        try:
            return self.get_object(**kw)
        except exceptions.HttpClientError, exc:
            if exc.response.status_code == 404:
                raise ObjectDoesNotExist
            raise

    def get_list_or_404(self, **kw):
        """
        Calls get on a list, returns a 404 if the list isn't there.

        Similar to Djangos get_list_or_404.
        """
        self.format_lists = True
        res = self.get(**kw)
        if not res:
            raise ObjectDoesNotExist
        return res

    def _call_request(self, method, url, data, params, headers):
        return self._store["session"].request(method, url, data=data,
                                              params=params, headers=headers)

    def _request(self, method, data=None, params=None, headers=None):
        """
        Overwrite so we can pass through custom headers, like oauth
        or something useful.
        """
        s = self._store["serializer"]
        url = self._store["base_url"]

        if self._store["append_slash"] and not url.endswith("/"):
            url = url + "/"
        hdrs = {"accept": s.get_content_type(),
                "content-type": s.get_content_type()}
        hdrs.update(headers or {})
        for callback in self._store.get('callbacks', []):
            callback['method'](self, data=data, extra=callback.get('extra'),
                               headers=hdrs, method=method,
                               params=merge(params, callback.get('params')),
                               url=url)

        stats_key = _key(url, method)
        with statsd.timer(stats_key):
            try:
                resp = self._call_request(method, url, data, params, hdrs)
            except ConnectionError:
                # In the case of connection errors, there isn't a response
                # so let's explicitly set up to None.
                raise exceptions.HttpServerError('Connection Error',
                                                 response=None,
                                                 content=None)

        statsd.incr('%s.%s' % (stats_key, resp.status_code))
        if 400 <= resp.status_code <= 499:
            raise exceptions.HttpClientError(
                "Client Error %s: %s" % (resp.status_code, url),
                response=resp, content=self._try_to_serialize_error(resp))
        elif 500 <= resp.status_code <= 599:
            raise exceptions.HttpServerError(
                "Server Error %s: %s" % (resp.status_code, url),
                response=resp, content=self._try_to_serialize_error(resp))

        self._ = resp

        return resp

    def _try_to_serialize_error(self, response):
        try:
            return self._try_to_serialize_response(response)
        except ValueError:
            return response


class CurlingBase(object):

    def by_url(self, url, parser=None):
        """
        Converts a URL such as:

            /generic/transaction/ > generic.transaction

        And one such as:

            /generic/transaction/8/ > generic.transaction(8)

        This scheme is assuming that you've got two names and a primary key,
        if you would like a different parser you could pass in a new one.
        """
        parser = parser or default_parser
        resources, pk = parser(url)
        current = self
        for resource in resources:
            current = getattr(current, resource)
        return current(pk) if pk else current

    def _add_callback(self, callback_dict):
        self._store.setdefault('callbacks', [])
        self._store['callbacks'].append(callback_dict)

    def activate_oauth(self, key, secret, realm='', params=None):
        params = params or {}
        self._add_callback({
            'method': sign_request,
            'extra': {'key': key, 'secret': secret, 'realm': realm},
            'params': params
        })


def make_serializer(**kw):
    serial = serialize.Serializer(default=kw.get('format', None))
    serial.serializers['json'] = JsonSerializer()
    kw.setdefault('serializer', serial)
    return kw


class API(TastypieAttributesMixin, CurlingBase, SlumberAPI):

    def __init__(self, *args, **kw):
        return super(API, self).__init__(*args, **make_serializer(**kw))
