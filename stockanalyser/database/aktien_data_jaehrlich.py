import os

from flask import Flask, g
from peewee import *

from database import aktieninformation
import logging
logger = logging.getLogger(__name__)

# from stockanalyser.stock import Stock

# Flask settings.
DEBUG = bool(os.environ.get('DEBUG'))
# SECRET_KEY = 'secret - change me'  # TODO: change me.

app = Flask(__name__)
app.config.from_object(__name__)

database = MySQLDatabase('aktien-test', **{'charset': 'utf8', 'use_unicode': True,
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
    marketscreener_id = CharField(
        column_name='Marketscreener-ID', null=True, unique=True)
    marketscreener_url = CharField(column_name='Marketscreener-URL', null=True)
    name = CharField(column_name='Name', null=True)
    onvista_url = CharField(column_name='Onvista-URL', null=True)
    symbol = CharField(column_name='Symbol', null=True, unique=True)
    waehrung = CharField(column_name='Waehrung', null=True)
    aktie_id = AutoField()

    class Meta:
        table_name = 'aktien_information'
        indexes = (
            (('isin', 'onvista_url'), False),
        )


class AktienJaehrlicheDaten(BaseModel):
    jahr = IntegerField(column_name='Jahr')
    q1 = DateTimeField(column_name='Q1', null=True)
    q2 = DateTimeField(column_name='Q2', null=True)
    q3 = DateTimeField(column_name='Q3', null=True)
    q4 = DateTimeField(column_name='Q4', null=True)
    aktie = ForeignKeyField(column_name='aktie_id',
                            field='aktie_id', model=AktienInformation)
    ebit = DecimalField(null=True)
    eigenkapitalquote = DecimalField(null=True)
    eps = DecimalField(null=True)
    idaktien_jaehrliche_daten = AutoField()
    kgv = DecimalField(null=True)
    return_on_equity = DecimalField(null=True)

    class Meta:
        table_name = 'aktien_jaehrliche_daten'


def save_yearly(stock_object) -> int:
    lines_changed = 0
    aktie_id = aktieninformation.read_value("aktie_id", stock_object.ISIN)
    for year in stock_object.eps.keys():
        sql_data = _yearly_prepare_dict(stock_object, aktie_id, year)
        exists = row_get(aktie_id, year)
        if not exists:
            lines_changed += row_insert(sql_data)
        else:
            lines_changed += row_update(aktie_id, year, sql_data)
    return lines_changed


def _yearly_prepare_dict(stock_object, aktie_id: int, year: int) -> dict:
    per = stock_object.per
    quarterly_figure_dates = stock_object.quarterly_figure_dates
    ebit = stock_object.ebit_margin
    roe = stock_object.roe
    equity_ratio = stock_object.equity_ratio
    sql_data: dict = {'jahr': year, 'aktie': aktie_id}

    # data_sql['kgv'] = value.amount
    if year in ebit.keys():
        sql_data['ebit'] = ebit[year]
    else:
        sql_data['ebit'] = -1
    if year in roe.keys():
        sql_data['return_on_equity'] = roe[year]
    else:
        sql_data['return_on_equity'] = -1
    if year in equity_ratio.keys():
        sql_data['eigenkapitalquote'] = equity_ratio[year]
    else:
        sql_data['eigenkapitalquote'] = -1
    if year in per.keys():
        sql_data['kgv'] = per[year]
    else:
        sql_data['kgv'] = -1

    this_year_quarterly = sort_quarterly_dates(quarterly_figure_dates, year)
    for idx, elem in enumerate(this_year_quarterly[::-1]):
        sql_data['q' + str(4 - idx)] = elem.strftime("%Y-%m-%d %H:%M:%S")

    return sql_data


def sort_quarterly_dates(quarterly_figure_dates: list, year: int) -> list:
    quarterly_figure_dates.sort()
    this_year_quarterly = []
    for elem in quarterly_figure_dates:
        if year == elem.year:
            this_year_quarterly.append(elem)
    return this_year_quarterly


# TODO fix langugae: Create Tables in English not German!!
def row_get(aktien_id: int, year: int):
    row = AktienJaehrlicheDaten.get_or_none(
        (AktienJaehrlicheDaten.aktie_id == aktien_id) & (AktienJaehrlicheDaten.jahr == year))
    return row


def row_update(aktien_id: int, year: int, colum_value: dict) -> int:
    rows = AktienJaehrlicheDaten.update(colum_value).where(
        (AktienJaehrlicheDaten.aktie_id == aktien_id) & (AktienJaehrlicheDaten.jahr == year)).execute()
    return rows


def row_insert(colum_value: dict) -> int:
    rows = AktienJaehrlicheDaten.insert(colum_value).execute()
    return rows


# Request handlers -- these two hooks are provided by flask and we will use them
# to create and tear down a database connection on each request.
@app.before_request
def before_request():
    g.db = database
    g.db.connection()


@app.after_request
def after_request(response):
    g.db.close()
    return response
