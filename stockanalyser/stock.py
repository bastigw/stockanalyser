"""Create Stock objects with financial data.

Classes:
    * Stock_
    * Cap_



.. _Stock: stockanalyser.html#stockanalyser.stock.Stock
.. _Cap: stockanalyser.html#stockanalyser.stock.Cap

"""
import datetime
import json
import logging
import pickle
from enum import Enum, unique


from database import database_interface
from stockanalyser import fileutils
from stockanalyser.config import *
from stockanalyser.data_source.finanzen_net import FinanzenNetScraper
from stockanalyser.data_source.marketscreener import MarketScreenerScraper
from stockanalyser.data_source.onvista import OnvistaScraper

logger = logging.getLogger(__name__)


def _stock_pickle_path(symbol, data_path=DATA_PATH):
    filename = fileutils.to_pickle_filename(symbol)
    path = os.path.join(data_path, filename)
    return path


def _unpickle_stock(symbol):
    path = _stock_pickle_path(symbol)
    return pickle.load(open(path, "rb"))


def _save(stock):
    database_interface.save_information(stock)


@unique
class Cap(Enum):
    """
    Different types of Cap Size:
        * Small: < 2 Billion
        * Medium: 2 Billion - 5 Billion
        * Large: > 5 Billion
    """
    SMALL = 1
    MID = 2
    LARGE = 3

    def __str__(self):
        return self.name[0]


class Stock(object):
    """
    Create Stock-Object with different kinds of Scrapers:
        - OnvistaScraper
        - FinanzenNetScraper
        - MarketscreenerScraper

    Functions:
        * ``update_stock_info(self)``:
            - gets data from Websites
        * ``save(self)``:
            - saves itself to the database
    """

    def __init__(self, isin=None, name=None, auto_update=True):
        """Constructor of the Stock Class

            :param isin: (str): ISIN of specific stock.
                Should be used primarily.

            :param name: (str): Name of Stock. Can be used to find ISIN.
     """
        logging.info("Initializing {}".format(type(self).__name__))
        if not (isin or name):
            logger.critical("No arguments")
            exit(-1)
        self.save_information = False
        self.name = name
        self.ISIN = isin
        self.exchange = None
        stock_data = self.__set_isin_urls_symb(
            isin=isin,
            name=name
        )
        if not self.name:
            self.name = stock_data['name']

        self.OS = OnvistaScraper(
            url=stock_data['onvista_url'],
            isin=stock_data['isin']
        )

        self.FNS = FinanzenNetScraper(
            url=stock_data['finanzennet_url'],
            isin=stock_data['isin'],
            name=stock_data['name']
        )

        self.MSS = MarketScreenerScraper(
            ms_id=stock_data['marketscreener_id'],
            ms_url=stock_data['marketscreener_url'],
            isin=stock_data['isin'],
            name=stock_data['name']
        )

        """ Call update_stock_info automatically """
        if auto_update:
            self.cap_type = self._set_market_cap(self.OS.market_cap)
            self.quote = self.OS.previous_close
            self.currency = "EUR"
            self.benchmark = self.FNS.benchmark

            self.roe = self.OS.roe
            self.ebit_margin = self.OS.ebit_margin
            self.equity_ratio = self.OS.equity_ratio
            self.eps = self.OS.eps
            self.per = self.OS.per
            self.quarterly_figure_dates = self.FNS.quarterly_figure_dates
            self.consensus_ratings = self.MSS.consensus
            self.eval_earning_revision_cy, self.eval_earning_revision_ny = self.MSS.revisions

    def __set_isin_urls_symb(self, isin=None, name=None):
        data = self.__get_isin_urls_symb_from_database(isin=isin, name=name)
        if not data:
            self.save_information = True
            data = self.__set_isin_urls_symb_online(isin=isin, name=name)
        return data

    @staticmethod
    def __get_isin_urls_symb_from_database(isin=None, name=None) -> dict:
        key = None
        key = isin if not key and isin else key
        key = name if not key and name else key
        return database_interface.find_entry_in_aktieninformation(key)  # dict

    def __set_isin_urls_symb_online(self, isin=None, name=None) -> dict:
        # finanzen_net_url: str
        # benchmark: str
        if not isin and name:
            fns = FinanzenNetScraper(name=name)
            fns.lookup_url()
            isin = fns.ISIN
            finanzen_net_url = fns.URL

        if not name and isin:
            fns = FinanzenNetScraper(isin=isin)
            name = fns.name
            finanzen_net_url = fns.URL
            benchmark = fns.benchmark

        onviscraper = OnvistaScraper(isin=isin)
        onvista_url = onviscraper.overview_url

        return self.__prepare_online_data(isin, finanzen_net_url, name,
                                          onvista_url, benchmark)

    @staticmethod
    def __prepare_online_data(isin: str, finanzen_net_url: str, name: str,
                              onvista_url: str, benchmark: str) -> dict:
        return {
            'isin': isin,
            'finanzennet_url': finanzen_net_url,
            'onvista_url': onvista_url,
            'name': name,
            'marketscreener_id': None,
            'marketscreener_url': None,
            'benchmark': benchmark,
        }

    def _get_symbol_local(self, name):
        country = self.ISIN[:2]
        region = {"DE": "de", "US": "us", "NL": "de", "LU": "de"}[country]
        dir_path = 'data/symbol_json/{}.json'.format(region)
        with open(dir_path) as symbols:
            symbols = json.loads(symbols.read())
            for element, symbol in symbols.items():
                name = name.replace("-", " ").lower()
                if name in element.lower():
                    self.name = element
                    return symbol

    def last_quarterly_figures_release_date(self):
        today = datetime.date.today()
        for d in reversed(self.quarterly_figure_dates):
            if d <= today:
                return d
        logger.warning(
            "Could not get Quarterly Figures that have already been "
            "released! Try to find via:"
            "www.finanzen.net/schaetzungen/{}".format(self.FNS.name))
        return None

    def _is_quarterly_figures_release_date_outdated(self):
        if self.quarterly_figure_dates[-1] <= (
                datetime.date.today() - datetime.timedelta(days=60)):
            return True
        return False

    def _price_earnings_ratio(self):
        cur_year = datetime.date.today().year

        return float(self.quote) / self.eps[cur_year]

    def price_earnings_ratio_5year(self) -> int:
        length_per = 0
        values = []
        for year, value in self.per.items():
            if value is not None:
                length_per += 1
                values.append(value)

        if length_per >= 5:
            length_per = 5
        else:
            logger.warning(
                "Not using five values to calculate average "
                "Price Earning Ratio: Using {}!".format(length_per))
        values_len = list(values)[:length_per]
        avg_per = sum(values_len) / length_per
        logger.debug("Calculating PER 5 Years: {}".format(avg_per))

        return round(avg_per, 2)

    @property
    def five_year_per(self):
        return self.price_earnings_ratio_5year()

    @staticmethod
    def _set_market_cap(market_cap: float):
        if market_cap >= (5 * 10 ** 9):
            return Cap.LARGE
        elif market_cap >= (2 * 10 ** 9):
            return Cap.MID
        else:
            return Cap.SMALL

    def save(self):
        """Saves Stock-Object to local database.

        :return: Nothing
        """
        if self.save_information:
            database_interface.save_information(self)
        database_interface.save_yearly(self)

    def __str__(self) -> str:
        string = "{:<35} {:<25}\n".format("Name:", self.name)
        string += "{:<35} {:<25}\n".format("Cap. Type:", self.cap_type.name)
        string += "{:<35} {:<25}\n".format("Quote:",
                                           "{0} {1}".format(self.quote,
                                                            self.currency))
        string += "{:<35} {:<25}\n".format("Earnings per share:",
                                           "{0} {1}".format(self.eps[
                                               datetime.date.today().year],
                                               self.currency))
        string += "{:<35} {:<25}\n".format("Analyst Rating:", "{0}".format(
            self.consensus_ratings["consensus"]))
        string += "{:<35} {:<25}\n".format("Average target price:",
                                           "{0} EUR".format(
                                               self.consensus_ratings[
                                                   "price_target_average"]))
        return string


if __name__ == "__main__":
    # logging.basicConfig(level=logging.DEBUG)
    s = Stock(isin="DE000ZAL1111", auto_update=False)
    print(s)
    # s.save()
    t = Cap.SMALL
    print(t)
