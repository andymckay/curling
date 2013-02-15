import datetime
import decimal
import json

date_format = '%Y-%m-%d'
time_format = '%H:%M:%S'


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
