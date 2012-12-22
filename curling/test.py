import decimal
import json
import lib
import unittest

from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
import mock
from nose.tools import eq_, ok_, raises

# Some samples for the Mock.
samples = {
    'GET:/services/settings/APPEND_SLASH/': {
        'key': 'APPEND_SLASH'
    },
    'GET:/services/settings/': {
        'meta': {'limit': 20, 'total_count': 185},
        'objects': [
            {'key': 'ABSOLUTE_URL_OVERRIDES'},
            {'key': 'ADMINS'},
        ]
    },
    'GET:/services/nothing/': {
        'meta': {},
        'objects': []
    }
}
lib.mock_lookup = samples


class TestAPI(unittest.TestCase):

    def setUp(self):
        self.api = lib.MockAPI('')

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

    def test_get_empty(self):
        res = self.api.services.nothing.get()
        eq_(len(res), 0)

    @raises(ObjectDoesNotExist)
    def test_get_none(self):
        self.api.services.nothing.get_object()

    @raises(ObjectDoesNotExist)
    def test_get_404(self):
        self.api.services.nothing.get_object_or_404()

    @raises(ObjectDoesNotExist)
    def test_get_list_404(self):
        self.api.services.nothing.get_list_or_404()

    def test_get_list_404_works(self):
        res = self.api.services.settings.get_list_or_404()
        eq_(len(res), 2)

    @mock.patch('curling.lib.MockTastypieResource._lookup')
    def test_post_decimal(self, lookup):
        self.api.services.settings.post({
            'amount': decimal.Decimal(1.0)
        })
        eq_(json.loads(lookup.call_args[1]['data']), {'amount': '1'})
