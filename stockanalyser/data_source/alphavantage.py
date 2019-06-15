import datetime
import json
import urllib.request

from stockanalyser.data_source import common
import logging

logger = logging.getLogger(__name__)

API_KEY = "7MU4HCSA2Y0BWMJP"
BASE_URL = "http://www.alphavantage.co/query"
BASE_SEARCH_URL = 'https://www.alphavantage.co/query?function=SYMBOL_SEARCH&keywords='
cache = {}


# todo get rid of me DONE

class EmptyStockDataResponse(Exception):
    pass


def stock_quote(symbol, date):
    if not common.is_weekday(date):
        date = common.prev_weekday(date)
    full_output: bool = False if (common.date_difference(date) * 251 / 365) < 100 else True
    date = date.strftime("%Y-%m-%d")
    if symbol not in cache:
        _get_stock_json(symbol, full_output=False)
    elif full_output is True and cache[symbol]['Time Series (Daily)'].__len__() <= 100:
        _get_stock_json(symbol, full_output=True)
    else:
        logger.debug("Retrieving stock quote for '%s' on %s from cache" %
                     (symbol, date))
        r_json = cache[symbol]

    value_daily_close = float(r_json["Time Series (Daily)"][str(date)]["4. close"])
    logger.debug("Closing stock quote for '%s' on %s: %s" % (symbol, date, value_daily_close))
    if value_daily_close == 0.0:  # Change date and try again
        date += datetime.timedelta(days=-1)
        if date.isoweekday() in {6, 7}:
            date += datetime.timedelta(days=(8 - date.isoweekday()))
            stock_quote(symbol, date)
        else:
            stock_quote(symbol, date)
        # raise InvalidValueError("Stock Quote from alphavantage is invalid (0) "
        #                         "data: %s" %
        #                         r_json["Time Series (Daily)"][str(date)]
        #                         ["4.  close"])

    return round(value_daily_close, 2)


def _get_stock_json(symbol: str, full_output=False):
    outputsize = "&outputsize=full" if full_output is True else ""
    url = (BASE_URL + "?function=TIME_SERIES_DAILY_ADJUSTED&apikey=" + API_KEY + outputsize + "&symbol=" + symbol)
    logger.debug("Retrieving closing stock quote for '{}'".format(symbol))
    page_av = common.request_url_to_str(url)
    r_json = json.loads(page_av.decode("utf-8"))
    cache[symbol] = r_json


def getPagmmeAlpha(search):
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
    r = stock_quote("VOW.DE", (datetime.datetime.now()))
    x = stock_quote("VOW.DE", (datetime.datetime.now() - datetime.timedelta(days=140)))  # -
    #                            datetime.timedelta(days=99)))
    # r = stock_quote("VOW.DE", (datetime.datetime.now() -
    #                            datetime.timedelta(days=101)))
    pass
