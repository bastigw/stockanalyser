""" Onivsta Scraper
Gets all data from the onvista.de webpage!

"""

import re
import urllib.request
import datetime
import csv
from typing import Union
import logging

from stockanalyser import exceptions
from stockanalyser.data_source import common

logger = logging.getLogger(__name__)

BENCHMARKS = {
    "DAX 30": {
        "notation_id": 20735,
    },
    "MDAX": {
        "notation_id": 323547,
    },
    "TecDAX": {
        "notation_id": 6623216,
    },
    "SDAX": {
        "notation_id": 324724,
    },
}


def is_number(txt) -> bool:
    """ Tries to convert string into number """
    try:
        float(txt)
        return True
    except (ValueError, TypeError):
        return False


class OnvistaScraper(object):
    """
    OnivstaScraper Class


    """

    def __init__(self, url=None, isin=None):
        logger.info("Initializing {}".format(type(self).__name__))
        if not url and isin:
            self.ISIN = isin
            self._lookup_url()
        elif not (url and isin):
            raise exceptions.MissingDataError(
                "Not enough Inputs! Check function call!")
        elif url:
            self.overview_url = url

        self.fundamental_url = self._build_fundamental_url(self.overview_url)
        self.__fundamental_url_etree = self._fetch_fundamental_webpage()

        self.__overview_url_etree = self._fetch_overview_webpage()

        self._name = None
        self._previous_close = None
        self._currency = None  # Currently not used
        self._market_cap = None

        self._notation_id = None

        self._eps = None
        self._per = None
        self._roe = None
        self._ebit_margin = None
        self._equity_ratio = None

    @property
    def eps(self):
        if self._eps is None:
            self._eps = self._get_eps()
        return self._eps

    @property
    def per(self):
        if self._per is None:
            self._per = self._get_price_earnings_ratio()
        return self._per

    @property
    def roe(self):
        if self._roe is None:
            self._roe = self._get_roe()
        return self._roe

    @property
    def ebit_margin(self):
        if self._ebit_margin is None:
            self._ebit_margin = self._get_ebit_margin()
        return self._ebit_margin

    @property
    def equity_ratio(self):
        if self._equity_ratio is None:
            self._equity_ratio = self._get_equity_ratio()
        return self._equity_ratio

    @property
    def notation_id(self):
        """ Notation ID for historic data """
        if self._notation_id is None:
            self._notation_id = self._get_notation_id()
        return self._notation_id

    @property
    def market_cap(self):
        if self._market_cap is None:
            self._market_cap = self._get_market_cap()
        return self._market_cap

    @property
    def previous_close(self):
        if self._previous_close is None:
            self._previous_close = self._get_previous_close()
        return self._previous_close

    @property
    def name(self):
        if self._name is None:
            self._name = self._get_name()
        return self._name

    def _lookup_url(self):
        url_base = 'https://www.onvista.de/aktien/'
        url_base_redirect = url_base + self.ISIN
        http_request = urllib.request.Request(url_base_redirect)
        http_respnse = urllib.request.urlopen(http_request)
        if (url_base and self.ISIN) in http_respnse.url:
            self.overview_url = http_respnse.url
            return self.overview_url
        elif url_base not in http_respnse.url:
            raise ValueError("Couldn't find Onvista Url")

    def _fetch_fundamental_webpage(self):
        return common.url_to_etree(self.fundamental_url)

    def _fetch_overview_webpage(self):
        return common.url_to_etree(self.overview_url)

    def _get_notation_id(self) -> str:
        url = self.overview_url.split("/")
        notation_id_url = "https://www.onvista.de/aktien/{}/{}".format(
            "times+sales", url[-1])
        etree = common.url_to_etree(notation_id_url)
        page_xpath = '//*[@id="exchangesLayerTs"]/ul/li/a'

        table_ul = etree.xpath(page_xpath)
        for li in table_ul:
            exchange = li.text.strip()
            if exchange == "Xetra":
                notation_id = li.get("href").split("=")[1]
                return notation_id

    def get_historic_data(self,
                          day: Union[str, datetime.datetime, datetime.date]) \
            -> Union[float, None]:
        if isinstance(day, (str, datetime.datetime, datetime.date)):
            if common.is_weekday(day):
                day = common.convert_to_datetime(day)
            else:
                day = common.prev_weekday(day)
        else:
            raise exceptions.DataTypeNotSupportedError(
                "Only str in the format: '%d.%m.%Y' or datetime."
                "datetime and datetime.date are supported.")
        day = day.strftime("%d.%m.%Y")
        url = "http://www.onvista.de/onvista/boxes/historicalquote/" \
              "export.csv?notationId={}&dateStart={}&interval=M1".format(
                  self.notation_id, day)  # 323547
        str_onivista_historic = common.request_url_to_str(url).decode("utf-8")
        csv_onvista_historic = csv.reader(str_onivista_historic.splitlines(),
                                          delimiter=";")
        for row in csv_onvista_historic:
            if row[0].strip() == day:
                # float(x) can't handle dots and commas -> format string
                row[-2] = _normalize_number(row[-2])
                return float(row[-2])
        return None

    @staticmethod
    def _get_table_header(header):
        # onvista uses 2 different presentation for the year:
        # "18/19e   17/18e  16/17e  15/16" and
        # "2019e    2018e   2017e   2016e"
        theader = []
        for column in header:
            value = column.text.lower().strip()
            if not len(value):
                continue
            # handle presentation of years as
            # "18/19e   17/18e  16/17e  15/16", convert them to the
            # YYYY (eg 2018) format
            if "/" in value:
                value = "20" + value.split("/")[1]
            # remove the "e" for estimated from year endings
            if re.match("\d+e", value):
                value = int(value[:-1])
            elif is_number(value):
                value = int(value)
            theader.append(value)
        return theader

    @staticmethod
    def _build_fundamental_url(url):
        spl = url.split("/")
        spl.insert(4, "fundamental")
        return "/".join(spl)

    def _extract_from_table(self, table_xpath, table_header, row_xpath,
                            row_header):
        if self.__fundamental_url_etree is None:
            self.__fundamental_url_etree = self._fetch_fundamental_webpage()
        table = self.__fundamental_url_etree.findall(table_xpath)
        theader = self._get_table_header(table)
        if theader[0] != table_header:
            raise exceptions.ParsingError(
                "Unexpected table header: '%s'" % theader[0])

        columns = self.__fundamental_url_etree.findall(row_xpath)
        table_elements = []
        for column in columns:
            column_value = _normalize_number(column.text)
            if column_value is "CONTINUE":
                continue
            if isinstance(column_value, (float, int)):
                column_value = column_value
            table_elements.append(column_value)

        if table_elements[0] != row_header:
            raise exceptions.ParsingError(
                "Unexpected 1. row header: '%s' != '%s'" % (
                    table_elements[0], row_header))

        if len(theader) != len(table_elements):
            raise exceptions.ParsingError(
                "Parsing error, table header contains"
                " more elements than rows:'%s' vs '%s'" % (
                    theader, table_elements))

        result = {}
        for i in range(len(table_elements)):
            if theader[i] == table_header:
                continue
            result[theader[i]] = table_elements[i]
        logger.debug("Extracted '%s' from onvista: %s" % (row_header, result))

        return result

    def _get_eps(self):
        table_xpath = './/*[@id="ONVISTA"]/div[1]/div[1]/div[1]' \
                      '/article/article/div/table[1]/thead/tr/'
        row_xpath = './/*[@id="ONVISTA"]/div[1]/div[1]/div[1]' \
                    '/article/article/div/table[1]/tbody/tr[1]/'

        return self._extract_from_table(table_xpath, "gewinn", row_xpath,
                                        "gewinn pro aktie in eur")

    def _get_ebit_margin(self):
        table_xpath = './/*[@id="ONVISTA"]/div[1]/div[1]/div[1]' \
                      '/article/article/div/table[8]/thead/tr/'
        row_xpath = './/*[@id="ONVISTA"]/div[1]/div[1]/div[1]' \
                    '/article/article/div/table[8]/tbody/tr[2]/'

        return self._extract_from_table(table_xpath, "rentabilität", row_xpath,
                                        "ebit-marge")

    def _get_equity_ratio(self):
        table_xpath = './/*[@id="ONVISTA"]/div[1]/div[1]/div[1]' \
                      '/article/article/div/table[6]/thead/tr/'
        row_xpath = './/*[@id="ONVISTA"]/div[1]/div[1]/div[1]' \
                    '/article/article/div/table[6]/tbody/tr[2]/'

        return self._extract_from_table(table_xpath, "bilanz", row_xpath,
                                        "eigenkapitalquote")

    def _get_roe(self):
        table_xpath = './/*[@id="ONVISTA"]/div[1]/div[1]/div[1]' \
                      '/article/article/div/table[8]/thead/tr/'
        row_xpath = './/*[@id="ONVISTA"]/div[1]/div[1]/div[1]' \
                    '/article/article/div/table[8]/tbody/tr[4]/'

        return self._extract_from_table(table_xpath, "rentabilität", row_xpath,
                                        "eigenkapitalrendite")

    def _get_price_earnings_ratio(self):
        table_xpath = './/*[@id="ONVISTA"]/div[1]/div[1]/div[1]' \
                      '/article/article/div/table[1]/thead/tr/'
        row_xpath = './/*[@id="ONVISTA"]/div[1]/div[1]/div[1]' \
                    '/article/article/div/table[1]/tbody/tr[2]/'

        return self._extract_from_table(table_xpath, "gewinn", row_xpath,
                                        "kgv")

    def _get_name(self):
        xapth_name = '//*[@id="ONVISTA"]/div[1]/div[1]/div[1]/article' \
                     '/div[2]/span/a/@title'
        name = common.solve_xpath(self.__overview_url_etree, xapth_name)[0]
        name = name.encode("utf-8").decode("utf-8")
        return name

    def _get_previous_close(self):
        xapth_previous_close = '//*[@id="ONVISTA"]/div[1]/div[1]/div[1]' \
                               '/article/table/tr[2]/td[4]/text()'
        previous_close = common.solve_xpath(self.__overview_url_etree,
                                            xapth_previous_close)[0]
        previous_close = previous_close.encode("utf-8").decode("utf-8")
        return float(_normalize_number(previous_close))

    def _get_market_cap(self) -> float:
        xapth_market_cap = '//*[@id="ONVISTA"]/div[1]/div[1]/div[1]/article' \
                           '/div[6]/section[8]/article/div/table[1]/tbody/tr' \
                           '/td[1]/text()'
        market_cap = common.solve_xpath(self.__overview_url_etree,
                                        xapth_market_cap)[0]
        return self.__configure_market_cap(market_cap)

    def __configure_market_cap(self, market_cap: str) -> int:
        if market_cap.endswith("Mio EUR"):
            market_cap = market_cap.replace("Mio EUR", "")
            market_cap = market_cap.strip()
            market_cap = _normalize_number(market_cap)
            return market_cap * 10 ** 6
        else:
            return -1


def _normalize_number(value: str) -> Union[None, str, float]:
    value = value.lower().strip()
    if value is "-":
        return None
    if value in ("", " "):
        return "CONTINUE"
    # replace german decimal seperator "," with "."
    number = re.search('[+|-]?([\d|\.]{0,12},\d{0,2})%?', value)
    if number is None:
        return value
    else:
        number = number.group(1)
        number = number.replace(".", "")
        number = number.replace(",", ".")
        return float(number)


if __name__ == "__main__":
    o = OnvistaScraper(isin="DE000BAY0017")
    print(o.overview_url)
    print(o.ebit_margin)
    print(o.eps)
    print(o.equity_ratio)
    print(o.per)
    # print(o.get_historic_data("20.1.2019"))
    # print(o.analyst_ratings())
    # print("ROE: %s" % o.roe())
    # print("EPS: %s" % o.eps())
    # print("EBIT-MARGIN: %s" % o.ebit_margin())
    # print("EQUITY RATIO: %s" % o.equity_ratio())
    # print(o._fetch_fundamental_webpage())
    # print(o._fetch_overview_webpage())
