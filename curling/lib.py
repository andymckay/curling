import json
import datetime
import decimal

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
import mock
import requests
from slumber import exceptions
from slumber import Resource, API as SlumberAPI, url_join
from slumber import serialize


date_format = '%Y-%m-%d'
time_format = '%H:%M:%S'


# Make slumber 400 errors show the content.
def verbose(self, *args, **kw):
    res = super(exceptions.SlumberHttpBaseException, self).__str__(*args, **kw)
    res += '\nContent: %s\n' % self.content
    return res


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


# An encoder that encodes our stuff the way we want.
class Encoder(json.JSONEncoder):

    ENCODINGS = {
        datetime.datetime:
            lambda v: v.strftime('%s %s' % (date_format, time_format)),
        datetime.date: lambda v: v.strftime(date_format),
        datetime.time: lambda v: v.strftime(time_format),
        decimal.Decimal: str,
    }

    def default(self, v):
        return self.ENCODINGS.get(type(v), super(Encoder, self).default)(v)


# Serialize using our encoding.
class JsonSerializer(serialize.JsonSerializer):

    key = 'json'

    def dumps(self, data):
        return json.dumps(data, cls=Encoder)



class TastypieResource(TastypieAttributesMixin, Resource):

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
        resp = super(TastypieResource, self)._try_to_serialize_response(resp)
        if (getattr(settings, 'CURLING_FORMAT_LISTS', False)
            and self._is_list(resp)):
            return self._format_list(resp)
        return resp

    def get_object(self, **kw):
        """
        Gets an object and checks that one and only one object is returned.

        Similar to Django get, but called get_object because get is taken.
        """
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
        Calls get_object, raises a 404 if the object isn't there.

        Similar to Djangos get_object_or_404.
        """
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
        res = self.get(**kw)
        if not res:
            raise ObjectDoesNotExist
        return res


mock_lookup = {}


class MockAttributesMixin(TastypieAttributesMixin):

    def __init__(self, *args, **kw):
        super(MockAttributesMixin, self).__init__(*args, **kw)
        self._resource = MockTastypieResource


class MockTastypieResource(MockAttributesMixin, TastypieResource):

    def _lookup(self, method, url, data=None, params=None, headers=None):
        resp = mock.Mock()
        resp.headers = {}
        resp.content = mock_lookup.get('%s:%s' % (method, url), mock.Mock())
        resp.status_code = 200
        return resp

    def _request(self, method, data=None, params=None):
        s = self._store['serializer']
        url = self._store['base_url']

        if self._store['append_slash'] and not url.endswith("/"):
            url = url + '/'

        resp = self._lookup(method, url, data=data, params=params,
                            headers={'content-type': s.get_content_type(),
                                     'accept': s.get_content_type()})

        if 400 <= resp.status_code <= 499:
            raise exceptions.HttpClientError(
                    'Client Error %s: %s\nContent: %s' %
                    (resp.status_code, url, resp.content),
                    response=resp, content=resp.content)
        elif 500 <= resp.status_code <= 599:
            raise exceptions.HttpServerError('Server Error %s: %s' %
                    (resp.status_code, url), response=resp,
                     content=resp.content)

        self._ = resp

        return resp


def make_serializer(**kw):
    serial = serialize.Serializer()
    serial.serializers['json'] = JsonSerializer()
    kw.setdefault('serializer', serial)
    return kw


# Until https://github.com/dstufft/slumber/pull/53 is merged.
class FixedSerializer(object):

    def __init__(self, base_url=None, auth=None, format=None,
                 append_slash=True, session=None, serializer=None):
        if serializer is None:
            serializer = serialize.Serializer(default=format)

        self._store = {
            "base_url": base_url,
            "format": format if format is not None else "json",
            "append_slash": append_slash,
            "session": (requests.session(auth=auth)
                        if session is None else session),
            "serializer": serializer,
        }

        # Do some Checks for Required Values
        if self._store.get("base_url") is None:
            raise exceptions.ImproperlyConfigured("base_url is required")


class API(TastypieAttributesMixin, FixedSerializer, SlumberAPI):

    def __init__(self, *args, **kw):
        return super(API, self).__init__(*args, **make_serializer(**kw))


class MockAPI(MockAttributesMixin, FixedSerializer, SlumberAPI):

    def __init__(self, *args, **kw):
        return super(MockAPI, self).__init__(*args, **make_serializer(**kw))
