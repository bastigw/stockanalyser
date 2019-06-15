import json

from stockanalyser.data_source import common
import logging

logger = logging.getLogger(__name__)


# todo get rid of me DONE

def get_stock_info(symbol: str) -> dict:
    # from https://stackoverflow.com/a/47148296/537958
    url = 'https://finance.yahoo.com/quote/' + symbol
    resp = common.request_url_to_str(url)

    r = resp.decode("utf-8")
    i1 = 0
    i1 = r.find('root.App.main', i1)
    i1 = r.find('{', i1)
    i2 = r.find("\n", i1)
    i2 = r.rfind(';', i1, i2)
    jsonstr = r[i1:i2]

    data = json.loads(jsonstr)
    market_cap = data['context']['dispatcher']['stores']['QuoteSummaryStore']['summaryDetail']['marketCap']['raw']
    prev_close = data['context']['dispatcher']['stores']['QuoteSummaryStore']['summaryDetail']['previousClose']['raw']
    prev_close = round(prev_close, 2)
    currency = data['context']['dispatcher']['stores']['QuoteSummaryStore']['summaryDetail']['currency']
    name = data['context']['dispatcher']['stores']['QuoteSummaryStore']['price']['shortName']

    res = {"Name": name,
           "PreviousClose": round(prev_close, 2),
           "Currency": currency,
           "MarketCapitalization": int(market_cap)
           }

    return res


def lookup_symbol(name: str, loc: str = None) -> tuple:
    """ Finds symbol from Yahoo Search
        :param name: Name of the stock
        :param loc: Location where the stock is listed
    """
    if loc is None:
        loc = 'GER'

    xpath_table = '//*[@id="lookup-page"]/section/div/div/div/div/table/tbody/tr'
    lookup_url = "https://de.finance.yahoo.com/lookup?s=%s" % name
    etree = common.url_to_etree(lookup_url)
    for elem in etree.xpath(xpath_table):
        symbol = elem.xpath('./td[1]')[0].text_content().encode("utf-8").decode("utf-8")
        loc_found = elem.xpath('./td[6]')[0].text_content().encode("utf-8").decode("utf-8")
        name = elem.xpath('./td[2]')[0].text_content().encode("utf-8").decode("utf-8")
        if "vz" in name.lower():
            continue
        if loc_found == loc:
            exchange = __switch_exchange(loc_found)
            logger.debug("Stock symbol for Name '%s': %s" % (name, symbol))
            return symbol, exchange, name


def __switch_exchange(loc_found: str) -> str:
    """ Dictionary that returns exchange
        :param loc_found: Location string
     """
    exchange = {
        'GER': 'XETRA',
        'BER': 'Berlin',
        'FRA': 'Frankfurt',
        'HAM': 'Hamburg'
    }
    if loc_found in exchange:
        return exchange[loc_found]
    else:
        logger.debug("Didn't find Exchange for Location: %s " % loc_found)
        return 'XETRA'


if __name__ == "__main__":
    # print(get_stock_info("VOW.DE"))
    s = get_stock_info("VOW.DE")
    print(lookup_symbol(name="volkswagen-ag")[0])
