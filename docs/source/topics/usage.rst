.. _usage:

Usage
-----

See the slumber `documentation <http://slumber.readthedocs.org/en/latest/>`_ for
using slumber. Use curling in the same way::

        from curling.lib import API
        API('http://slumber.in/api/v1/').note.get()

Curling sniffs out Tastypie and automatically turns a list of records into
a list. For example::

        res = self.api.services.settings.get()

The settings API returns a Tastypie style list. We turn it into a Python list.

We provide a few extra methods for accessing objects that mirror Django
methods. For example::

        res = self.api.services.settings.get_object()

Will test that one and only one record is returned and access that object.

.. autoclass:: curling.lib.TastypieResource
   :members:

If you've got URLs to items, then *by_url* can be a handy way to access them.

.. autoclass:: curling.lib.CurlingBase
   :members: by_url

Errors
======

Just like slumber any response in the 400 range is treated as HttpClientError.
We'll also assume that the response body contains JSON and parse that.

So in the example::

    from lib import API, HttpClientError, HttpServerError

    api = API('http://localhost:8001')

    try:
        api.by_url('/generic/buyer/').post(data={'foo': 'bar', 'uuid': 'asd'})
    except (HttpClientError, HttpServerError), exc:
        print type(exc.content), exc.content
        print type(exc.message), exc.message

You'll get::

    <type 'dict'> {u'uuid': [u'Buyer with this Uuid already exists.']}
    <type 'str'> Client Error 400: http://localhost:8001/generic/buyer/

* *content*: the body parsed as JSON, if possible
* *message*: the nice message of the error
* *response*: the response object, so *response.status_code* will give you the
  status

OAuth
=====

Curling can add in OAuth headers, using OAuth 1.x. These OAuth headers are ones
that `solitude <https://solitude.readthedocs.org/en/latest/>` can understand,
so might not implement the complete OAuth spec..

For example::

    api = API('http://localhost:8001', format='jwt')
    api.activate_oauth('key', 'secret', realm='optional.realm')

Headers
=======

Curling supports optional headers for GET, POST, PUT and PATCH methods.
If a GET request contains the *If-None-Match* header with a proper Etag,
a 304 response will be returned with an empty content, as expected.
