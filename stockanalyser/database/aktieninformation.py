import os

from flask import Flask, g
from peewee import *
import logging

logger = logging.getLogger(__name__)

# Flask settings.
DEBUG = bool(os.environ.get('DEBUG'))
SECRET_KEY = 'secret - change me'  # TODO: change me.

app = Flask(__name__)
app.config.from_object(__name__)

database = MySQLDatabase('aktien-test',
                         **{'charset': 'utf8', 'use_unicode': True,
                            'host': 'localhost', 'user': 'user', 'password': 'password'})


class UnknownField(object):
    def __init__(self, *_, **__):
        pass


class BaseModel(Model):
    class Meta:
        database = database


class AktienInformation(BaseModel):
    art = CharField(column_name='Art', null=True)
    benchmark = CharField(column_name='Benchmark', null=True)
    finanzennet_url = CharField(column_name='FinanzenNet-URL', null=True)
    groeße = CharField(column_name='Groeße', null=True)
    isin = CharField(column_name='ISIN', null=True, unique=True)
    marketscreener_id = CharField(column_name='Marketscreener-ID', null=True,
                                  unique=True)
    marketscreener_url = CharField(column_name='Marketscreener-URL', null=True)
    name = CharField(column_name='Name', null=True)
    onvista_url = CharField(column_name='Onvista-URL', null=True)
    notation_id = CharField(column_name='notation_id', null=True, unique=True)
    aktie_id = AutoField()

    class Meta:
        table_name = 'aktien_information'
        indexes = (
            (('isin', 'onvista_url'), False),
        )


def insert_data(stock_object) -> int:
    exist = read_value('isin', stock_object.ISIN)
    if not exist:
        sql_data = {
            'art': "",
            'benchmark': stock_object.benchmark,
            'name': stock_object.name,
            'finanzennet_url': stock_object.FNS.URL,
            'groeße': stock_object.cap_type.__str__() if hasattr(stock_object,
                                                                 'cap_type') else 'X',
            'isin': stock_object.ISIN,
            'marketscreener_id': stock_object.MSS.id,
            'marketscreener_url': stock_object.MSS.URL,
            'onvista_url': stock_object.OS.overview_url,
            'notation_id': stock_object.OS.notation_id,
        }
        return AktienInformation.insert(sql_data).execute()
    else:
        return -1


def read_value(case: str, isin: str):
    row = AktienInformation.get_or_none(AktienInformation.isin == isin)
    if row:
        cases = {
            'art': row.art,
            'benchmark': row.benchmark,
            'finanzennet_url': row.finanzennet_url,
            'aktie_id': row.aktie_id,
            'isin': row.isin,
            'marketscreener_id': row.marketscreener_id,
            'marketscreener_url': row.marketscreener_url,
            'name': row.name,
            'onvista_url': row.onvista_url,
            'notation_id': row.notation_id,
            'groeße': row.groeße
        }
        return cases.get(case, 'Invalid')
    else:
        return None


def find_data_entry(fields: str or int) -> dict:
    """Searches for data entry in local database.

    :param fields: Can be anything
    :return: first matching entry
    """
    columns = [AktienInformation.art, AktienInformation.benchmark,
               AktienInformation.finanzennet_url, AktienInformation.groeße,
               AktienInformation.isin,
               AktienInformation.marketscreener_id,
               AktienInformation.marketscreener_url, AktienInformation.name,
               AktienInformation.onvista_url, AktienInformation.notation_id,
               AktienInformation.aktie_id, ]
    for elem in columns:
        try:
            row = AktienInformation.get_or_none(elem.contains(fields))
        except ValueError:
            continue
        if row:
            return row.__dict__['__data__']


# Request handlers -- these two hooks are provided by flask and we will use
# them to create and tear down a database connection on each request.
@app.before_request
def before_request():
    g.db = database
    g.db.connection()


@app.after_request
def after_request(response):
    g.db.close()
    return response


logger.info("Connected to database {}".format(database.database))

if __name__ == '__main__':
    find_data_entry(1)
