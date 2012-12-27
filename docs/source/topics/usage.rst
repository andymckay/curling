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
