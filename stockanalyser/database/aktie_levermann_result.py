from peewee import *
from database import aktieninformation
from datetime import datetime


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


class AktieLevermannPunkte(BaseModel):
    analysten = IntegerField(constraints=[SQL("DEFAULT 0")], null=True)
    datum = DateTimeField()
    ebit = IntegerField(constraints=[SQL("DEFAULT 0")], null=True)
    ek_quote = IntegerField(column_name='ek-quote',
                            constraints=[SQL("DEFAULT 0")], null=True)
    ek_rendite = IntegerField(column_name='ek-rendite',
                              constraints=[SQL("DEFAULT 0")], null=True)
    gesamtpunkzahl = IntegerField(null=True)
    gewinnrevision = IntegerField(constraints=[SQL("DEFAULT 0")], null=True)
    gewinnwachstum = IntegerField(constraints=[SQL("DEFAULT 0")], null=True)
    id_aktie = ForeignKeyField(
        column_name='id_aktie', field='aktie_id', model=AktienInformation)
    idaktie_levermann_punkte = AutoField()
    kgv = IntegerField(constraints=[SQL("DEFAULT 0")], null=True)
    kgv5 = IntegerField(constraints=[SQL("DEFAULT 0")], null=True)
    kursverlauf12 = IntegerField(constraints=[SQL("DEFAULT 0")], null=True)
    kursverlauf6 = IntegerField(constraints=[SQL("DEFAULT 0")], null=True)
    momentum = IntegerField(constraints=[SQL("DEFAULT 0")], null=True)
    reaktion_quartals_zahlen = IntegerField(
        constraints=[SQL("DEFAULT 0")], null=True)
    reversaleffekt = IntegerField(constraints=[SQL("DEFAULT 0")], null=True)

    class Meta:
        table_name = 'aktie_levermann_punkte'


def save_points(levermann_result) -> int:
    aktie_id = aktieninformation.read_value('aktie_id', levermann_result.isin)
    sql_data = {
        'analysten': levermann_result.analyst_rating.points,
        'datum': datetime.today().strftime("%Y-%m-%d %H:%M:%S"),
        'ebit': levermann_result.ebit_margin.points,
        'ek_quote': levermann_result.equity_ratio.points,
        'ek_rendite': levermann_result.roe.points,
        'gesamtpunkzahl': levermann_result.score,
        'gewinnrevision': levermann_result.earning_revision.points,
        'gewinnwachstum': levermann_result.earning_growth.points,
        'id_aktie': aktie_id,
        'kgv': levermann_result.price_earnings_ratio.points,
        'kgv5': levermann_result.five_years_price_earnings_ratio.points,
        'kursverlauf12': levermann_result.quote_chg_1year.points,
        'kursverlauf6': levermann_result.quote_chg_6month.points,
        'momentum': levermann_result.momentum.points,
        'reaktion_quartals_zahlen': levermann_result.quarterly_figures_reaction.points,
        'reversaleffekt': levermann_result.three_month_reversal.points,
    }
    return AktieLevermannPunkte.insert(sql_data).execute()
