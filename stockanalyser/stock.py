import datetime
import json
import logging
import pickle
from enum import Enum, unique

from stockanalyser import fileutils
from stockanalyser import input
from stockanalyser.config import *
from stockanalyser.data_source import yahoo
from stockanalyser.data_source.finanzen_net import FinanzenNetScraper
from stockanalyser.data_source.marketscreener import MarketScreenerScraper
from stockanalyser.data_source.onvista import OnvistaScraper
from stockanalyser.mymoney import Money

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def stock_pickle_path(symbol, dir=DATA_PATH):
    filename = fileutils.to_pickle_filename(symbol)
    path = os.path.join(dir, filename)
    return path


def unpickle_stock(symbol):
    path = stock_pickle_path(symbol)
    return pickle.load(open(path, "rb"))


def save(stock, dir=DATA_PATH):
    path = stock_pickle_path(stock.symbol, dir)
    with open(path, "wb") as output:
        pickle.dump(stock, output, pickle.HIGHEST_PROTOCOL)


@unique
class Cap(Enum):
    SMALL = 1
    MID = 2
    LARGE = 3


class Stock(object):
    def __init__(self, symbol=None, isin=None, name=None, url_finanzen_net=None, url_onivsta=None):

        self.symbol = symbol
        self.name = name
        self.ISIN = isin
        self.exchange = None
        self.__set_isin_urls_symb(
            symbol=symbol,
            isin=isin,
            name=name
        )

        self.OS = OnvistaScraper(
            url=url_onivsta,
            isin=self.ISIN
        )

        self.FNS = FinanzenNetScraper(
            url=url_finanzen_net,
            isin=self.ISIN,
            name=self.name
        )

        self.MSS = MarketScreenerScraper(
            isin=self.ISIN,
            name=self.name,
            exchange=None  # "Deutsche Boerse AG"
        )

        self.cap_type = None
        self.roe = {}
        self.ebit_margin = {}
        self.equity_ratio = {}
        self.eps = {}
        self.quarterly_figure_dates = []
        self.consensus_ratings = {}
        self.eval_earning_revision_cy = {}
        self.eval_earning_revision_ny = {}

    def __set_isin_urls_symb(self, symbol=None, isin=None, name=None):
        if not isin and name:
            fns = FinanzenNetScraper(name=name)
            fns.lookup_url()
            self.ISIN = fns.ISIN
            self.finanzen_net_url = fns.URL

            os = OnvistaScraper(isin=self.ISIN)
            self.onvista_url = os.overview_url
        # if not (symbol and name) and isin:
        #     fns = FinanzenNetScraper(isin=isin)
        #     self.name = fns.get_name()
        if not symbol and self.name:
            self.symbol = self._get_symbol_local()
            if not self.symbol:
                self.symbol, self.exchange, self.name = yahoo.lookup_symbol(name=self.name)

    def _get_symbol_local(self):
        country = self.ISIN[:2]
        region = {"DE": "de", "US": "us"}[country]
        DIR_PATH = '../data/symbol_json/{}.json'.format(region)
        with open(DIR_PATH, 'r') as symbols:
            symbols = json.loads(symbols.read())
            for element, symbol in symbols.items():
                self.name = self.name.replace("-", " ").lower()
                if self.name in element.lower():
                    self.name = element
                    return symbol

    def _fetch_finanzen_net_data(self):
        self.quarterly_figure_dates = self.FNS.fetch_recent_quarterly_figures_release_date()

    def _fetch_onvista_data(self):
        eps = self.OS.eps()
        for year, value in eps.items():
            if value:
                self.eps[year] = value

        ebit_margin = self.OS.ebit_margin()
        for year, value in ebit_margin.items():
            if value:
                self.ebit_margin[year] = value

        equity_ratio = self.OS.equity_ratio()
        for year, value in equity_ratio.items():
            if value:
                self.equity_ratio[year] = value

        roe = self.OS.roe()
        for year, value in roe.items():
            if value:
                input.validate_percent_value(value)
                self.roe[year] = value

    def _fetch_consensus_ratings(self):
        self.consensus_ratings = self.MSS.get_consensus()

    def _fetch_eval_earnings(self):
        self.eval_earning_revision_cy, self.eval_earning_revision_ny = self.MSS.get_revison()

    def last_quarterly_figures_release_date(self):
        today = datetime.date.today()
        for d in reversed(self.quarterly_figure_dates):
            if d <= today:
                return d

    def is_quarterly_figures_release_date_outdated(self):
        if (self.quarterly_figure_dates[-1] <= (datetime.date.today() -
                                                datetime.timedelta(days=60))):
            return True
        return False

    def update_stock_info(self):
        data = yahoo.get_stock_info(self.symbol)
        self.name = data["Name"]
        self.quote = Money(data["PreviousClose"], data["Currency"])
        self._set_market_cap(float(data["MarketCapitalization"]))

        self._fetch_consensus_ratings()
        self._fetch_onvista_data()
        self._fetch_finanzen_net_data()
        self._fetch_eval_earnings()

    def _set_market_cap(self, market_cap):
        if market_cap >= (5 * 10 ** 9):
            self.cap_type = Cap.LARGE
        elif market_cap >= (2 * 10 ** 9):
            self.cap_type = Cap.MID
        else:
            self.cap_type = Cap.SMALL

    # def set_eps(self, year, val):
    #     if not isinstance(val, Money):
    #         raise input.InvalidValueError("Expected value to be from typeMoney not {}".format(type(val)))
    #     # eps = EPS(val, datetime.date.today())
    #
    #     if year in self.eps:
    #         for e in self.eps[year]:
    #             # If we already have a EPS value for that year, only store it
    #             # the value differs or the other one is older than 6 months
    #             if e.value == val and (e.update_date > datetime.date.today() - datetime.timedelta(days=6 * 30)):
    #                 break
    #
    #     if year in self.eps:
    #         self.eps[year].append(eps)
    #     else:
    #         self.eps[year] = [eps]

    def save(self, dir=DATA_PATH):
        path = stock_pickle_path(self.symbol, dir)
        with open(path, "wb") as output:
            pickle.dump(self, output, pickle.HIGHEST_PROTOCOL)

    def price_earnings_ratio(self):
        cur_year = datetime.date.today().year

        return self.quote / self.eps[cur_year].amount

    def price_earnings_ratio_5year(self):
        cur_year = datetime.date.today().year
        avg_per = (self.eps[cur_year + 1].amount +
                   self.eps[cur_year].amount +
                   self.eps[cur_year - 1].amount +
                   self.eps[cur_year - 2].amount +
                   self.eps[cur_year - 3].amount) / 5
        logger.debug("Calculating PER 5 Years: "
                     "%s / (%s + %s + %s %s + %s) / 5" %
                     (self.quote, self.eps[cur_year + 1].amount,
                      self.eps[cur_year].amount, self.eps[cur_year - 1].amount,
                      self.eps[cur_year - 2].amount, self.eps[cur_year - 3].amount))

        return self.quote / avg_per

    def __str__(self):
        string = "{:<35} {:<25}\n".format("Name:", self.name)
        string += "{:<35} {:<25}\n".format("Symbol:", self.symbol)
        string += "{:<35} {:<25}\n".format("Cap. Type:", self.cap_type.name)
        string += "{:<35} {:<25}\n".format("Quote:", "{0} {1}".format(round(self.quote.amount, 2), self.quote.currency))
        string += "{:<35} {:<25}\n".format("Earnings per share:", "{0} {1}".format(self.eps[datetime.date.today().year].amount, self.eps[datetime.date.today().year].currency))
        string += "{:<35} {:<25}\n".format("Analyst Rating:", "{0}".format(self.consensus_ratings["consensus"]))
        string += "{:<35} {:<25}\n".format("Average target price:", "{0}EUR".format(self.consensus_ratings["price_target_average"]))
        return string


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    s = Stock(name="leg-immobilien", isin="DE000LEG1110")
    s.update_stock_info()
    print(s)
    # save(s, "..\data")
    # print(Cap(2))
    # eps = s.eps
    #
    # print(eps[datetime.date.today().year].amount)

    # print(s.eps[datetime.date.today().year + 1][-1].value)
    # print(s.eps[datetime.date.today().year][-1].value)

    # path = stock_pickle_path("VOW.DE", "..\data")
    # print(path)
    """
    s2 = Stock("MUV2.DE")
    s2.onvista_fundamental_url = "http://www.onvista.de/aktien/Muenchener-Rueck-Aktie-DE0008430026"
    s2.update_stock_info()
    """
