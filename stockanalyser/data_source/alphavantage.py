import datetime
import json
import logging
import urllib.request

from stockanalyser.data_source import common

logger = logging.getLogger(__name__)

API_KEY = "YOUR_API_KEY"
BASE_URL = "http://www.alphavantage.co/query"
BASE_SEARCH_URL = 'https://www.alphavantage.co/query?function=SYMBOL_SEARCH&keywords='
cache = {}


class EmptyStockDataResponse(Exception):
    pass


def stock_quote(symbol, date):
    date_difference = common._date_difference(date)
    date = date.strftime("%Y-%m-%d")
    if symbol not in cache:
        outputsize = "&outputsize=full" if date_difference >= 100 else ""
        url = (BASE_URL + "?function=TIME_SERIES_DAILY_ADJUSTED&apikey=" + API_KEY +
               outputsize +
               "&symbol=" + symbol)
        logger.debug("Retrieving closing stock quote for '%s' on %s (%s)" % (symbol, date,
                                                                             url))
        page_av = urllib.request.urlopen(url).read()
        r_json = json.loads(page_av.decode("utf-8"))
        cache[symbol] = r_json
    elif cache[symbol]["Time Series (Daily)"].__len__() <= date_difference:
        url = (BASE_URL + "?function=TIME_SERIES_DAILY_ADJUSTED&apikey=" + API_KEY +
               "&outputsize=full&symbol=" + symbol)
        logger.debug("Retrieving full closing stock quote for '%s' on %s (%s)" % (symbol, date,
                                                                                  url))
        page_av = urllib.request.urlopen(url).read()
        r_json = json.loads(page_av.decode("utf-8"))
        cache[symbol] = r_json
    else:
        logger.debug("Retrieving stock quote for '%s' on %s from cache" %
                     (symbol, date))
        r_json = cache[symbol]

    value_daily_close = float(r_json["Time Series (Daily)"][str(date)]["4. close"])
    logger.debug("Closing stock quote for '%s' on %s: %s" % (symbol, date, value_daily_close))
    if value_daily_close == 0.0:  # Change date and try again
        date += datetime.timedelta(days=-1)
        if date.isoweekday() in set((6, 7)):
            date += datetime.timedelta(days=(8 - date.isoweekday()))
            stock_quote(symbol, date)
        else:
            stock_quote(symbol, date)
        # raise InvalidValueError("Stock Quote from alphavantage is invalid (0) "
        #                         "data: %s" %
        #                         r_json["Time Series (Daily)"][str(date)]
        #                         ["4.  close"])

    return value_daily_close


def getPageAlpha(search):
    url = BASE_SEARCH_URL + search + '&apikey=' + API_KEY
    response = urllib.request.urlopen(url)
    logger.debug("Retrieving search for '%s' on %s" % (search,
                                                       url))
    json_response_page = response.read().decode('utf-8')
    return json_response_page


def findCurrency(json_response_page, currency=None, region=None):
    if currency is None:
        currency = 'EUR'
    if region is None:
        region = "Frankfurt"
    loaded_json = json.loads(json_response_page)
    try:
        loaded_json = loaded_json["bestMatches"]
        for data in loaded_json:
            if currency in data["8. currency"] and region in data["4. region"]:
                return data["1. symbol"]
                break
            else:
                continue
        return None
    except KeyError as err:
        return None


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    # r = stock_quote("VOW.DE", (datetime.datetime.now() -
    #                            datetime.timedelta(days=99)))
    # r = stock_quote("VOW.DE", (datetime.datetime.now() -
    #                            datetime.timedelta(days=101)))
