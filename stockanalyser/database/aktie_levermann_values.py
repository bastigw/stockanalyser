from peewee import *
from datetime import datetime

from stockanalyser.database import aktieninformation
# from database import aktieninformation

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


class AktieLevermannValues(BaseModel):
    analyst_bewertung = IntegerField(null=True)
    analysten_anzahl = IntegerField(null=True)
    datum = DateTimeField()
    gewinn = DecimalField(null=True)
    gewinn_nj = DecimalField(null=True)
    gewinn_veraenderung = DecimalField(null=True)
    gewinn_veraenderung_nj = DecimalField(null=True)
    id_aktie = ForeignKeyField(
        column_name='id_aktie', field='aktie_id', model=AktienInformation)
    idaktie_levermann_values = AutoField()
    kgv = DecimalField(null=True)
    kgv_5 = DecimalField(null=True)
    kurs = DecimalField(null=True)
    kurs_ziel = DecimalField(null=True)
    quartalszahlen_letzte = DateTimeField(null=True)
    veraenderung_index_quartaltag = DecimalField(null=True)
    veraenderung_kurs_12m = DecimalField(null=True)
    veraenderung_kurs_6m = DecimalField(null=True)
    veraenderung_kurs_quartaltag = DecimalField(null=True)

    class Meta:
        table_name = 'aktie_levermann_values'


def save_points(levermann) -> int:
    sql_data = _prep_data(levermann)
    return AktieLevermannValues.insert(sql_data).execute()


def _prep_data(levermann):
    eps = _prep_eps(levermann.stock.eps)
    analyst_ratings = _prep_analyst_ratings(levermann.stock.consensus_ratings)
    quarterly_reaction = levermann.eval_quarterly_figures_reaction(
        case='sql_data')
    data = {
        'analyst_bewertung': analyst_ratings[0],
        'analysten_anzahl': analyst_ratings[1],
        'datum': datetime.today().strftime("%Y-%m-%d %H:%M:%S"),
        'gewinn': eps[0],
        'gewinn_nj': eps[1],
        'gewinn_veraenderung': levermann.stock.eval_earning_revision_cy['Change current Year'],
        'gewinn_veraenderung_nj': levermann.stock.eval_earning_revision_ny['Change next Year'],
        'id_aktie': aktieninformation.read_value('aktie_id', levermann.stock.ISIN),
        'kgv': levermann.stock.per[datetime.today().year],
        'kgv_5': levermann.stock.five_year_per,
        'kurs': levermann.stock.quote,
        'kurs_ziel': levermann.stock.consensus_ratings["price_target_average"],
        'quartalszahlen_letzte': levermann.stock.last_quarterly_figures_release_date(),
        'veraenderung_index_quartaltag': quarterly_reaction[1],
        'veraenderung_kurs_quartaltag': quarterly_reaction[0],
        'veraenderung_kurs_12m': levermann.eval_quote_chg_12month().value,
        'veraenderung_kurs_6m': levermann.eval_quote_chg_6month().value,
    }

    return data


def _prep_eps(eps: dict) -> tuple:
    this_year = datetime.today().year
    eps_cur_year = eps[this_year]
    try:
        eps_next_year = eps[this_year + 1]
    except KeyError:
        eps_next_year = eps_cur_year
        eps_cur_year = eps[this_year - 1]

    return eps_cur_year, eps_next_year


def _prep_analyst_ratings(rating: dict) -> tuple:
    consensus = rating["consensus"]
    number_of_analysts = int(rating["n_of_analysts"])
    ratings = {
        "KAUFEN": 1,
        "AUFSTOCKEN": 2,
        "HALTEN": 3,
        "REDUZIEREN": 4,
        "VERKAUFEN": 5
    }
    score = ratings[consensus]

    return score, number_of_analysts
