from peewee import *

database = MySQLDatabase('aktien-test', **{'charset': 'utf8', 'use_unicode': True, 'user': 'root', 'password': 'sbietk2002'})


class UnknownField(object):
    def __init__(self, *_, **__): pass


class BaseModel(Model):
    class Meta:
        database = database


class Aktienimformation(BaseModel):
    art = CharField(column_name='Art', null=True)
    benchmark = CharField(column_name='Benchmark', null=True)
    finanznenet_url = CharField(column_name='FinanzneNet-URL', null=True)
    name = CharField(column_name='Name', null=True)
    groeße = CharField(column_name='Groeße', null=True)
    isin = CharField(column_name='ISIN', null=True, unique=True)
    marketscreener_id = CharField(column_name='Marketscreener-ID', null=True, unique=True)
    marketscreener_url = CharField(column_name='Marketscreener-URL', null=True)
    onvista_url = CharField(column_name='Onvista-URL', null=True)
    symbol = CharField(column_name='Symbol', null=True, unique=True)
    waehrung = CharField(column_name='Waehrung', null=True)
    idaktien = AutoField()

    class Meta:
        table_name = 'aktien-imformation'


def insert_data(stock_object):
    stock = Aktienimformation(art="", benchmark="",name=stock_object.name, finanznenet_url=stock_object.FNS.URL, groeße=stock_object.cap_type.name[0], isin=stock_object.ISIN,
                              marketscreener_id=stock_object.MSS.id, marketscreener_url=stock_object.MSS.URL,
                              onvista_url=stock_object.OS.overview_url, symbol=stock_object.symbol, waehrung=stock_object.quote.currency)
    stock.save()
    database.close()
