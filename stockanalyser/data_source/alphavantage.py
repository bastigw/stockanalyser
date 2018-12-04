import urllib.request
import logging
import json
import datetime
import time
from stockanalyser.exceptions import InvalidValueError
from stockanalyser.data_source import common

logger = logging.getLogger(__name__)

API_KEY = "7MU4HCSA2Y0BWMJP"
BASE_URL = "http://www.alphavantage.co/query"
BASE_SEARCH_URL = 'https://www.alphavantage.co/query?function=SYMBOL_SEARCH&keywords='
cache = {}


class EmptyStockDataResponse(Exception):
    pass


def stock_quote(symbol, date):
    assert date.weekday() not in (6, 7)
    str_date = date.strftime("%Y/%m/%d")
    if symbol not in cache:
        url = (BASE_URL + "?function=TIME_SERIES_DAILY_ADJUSTED&apikey=" + API_KEY +
               "&outputsize=full" +
               "&symbol=" + symbol)
        logger.debug("Retrieving stock quote for '%s' on %s (%s)" % (symbol, date,
                                                                     url))
        # TODO: only use outputsize=full if older than the last 100day quotes are
        # requested
        r = urllib.request.urlopen(url).read()
        r_json = json.loads(r.decode("utf-8"))
        cache[symbol] = r_json
    else:
        logger.debug("Retrieving stock quote for '%s' on %s from cache" %
                     (symbol, date))
        r_json = cache[symbol]

    f = float(r_json["Time Series (Daily)"][str(date)]["4. close"])
    logger.debug("stock quote for '%s' on %s: %s" % (symbol, date, f))
    if f == 0.0:
        raise InvalidValueError("Stock Quote from alphavantage is invalid (0) "
                                "data: %s" %
                                r_json["Time Series (Daily)"][str(date)]
                                ["4.  close"])

    return f


def getPageAlpha(search):
    url = BASE_SEARCH_URL + search + '&apikey=' + API_KEY
    response = urllib.request.urlopen(url)
    logger.debug("Retrieving search for '%s' on %s" % (search,
                                                       url))
    json_response_page = response.read().decode('utf-8')
    return json_response_page


def findCurrency(json_response_page, currency=None, markt=None):
    if currency is None:
        currency = 'EUR'
    if markt is None:
        markt = "Frankfurt"
    loaded_json = json.loads(json_response_page)
    try:
        loaded_json = loaded_json["bestMatches"]
        for data in loaded_json:
            if currency in data["8. currency"] and markt in data["4. region"]:
                return data["1. symbol"]
                break
            else:
                continue
    except KeyError as err:
        raise ValueError('Data isn´t correct. Check inputs!')


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    r = stock_quote("FRA:VOW", (datetime.datetime.now() -
                                datetime.timedelta(days=1)).date())
    print(r)
    print(findCurrency(getPageAlpha("")))
