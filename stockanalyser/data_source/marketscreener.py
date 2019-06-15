import json

from stockanalyser.data_source import common
import logging

logger = logging.getLogger(__name__)


class MarketScreenerScraper(object):
    def __init__(self, ms_id=None, ms_url=None, isin=None, name=None, exchange=("xetra", "deutsche boerse ag")):
        logger.info("Initializing {}".format(type(self).__name__))
        self.ISIN = isin
        self.name = name
        self.exchange = exchange

        self.BASE_SEARCH_URL = "https://de.marketscreener.com/indexbasegauche.php?lien=recherche&type_recherche=1&mots="
        self.URL = ms_url
        if not self.URL:
            self.URL = self._lookup_url()

        self.URL_revisions = self.URL + "reviews-revisions/"
        self.URL_consensus = self.URL + "analystenerwartungen/"

        self.id = ms_id
        if not self.id:
            self.id = self._lookup_id()

        self._data_consensus: dict = {}
        self._data_revision_cy: dict = {}
        self._data_revision_ny: dict = {}

    @property
    def consensus(self):
        if not self._data_consensus:
            self._set_consensus()
        return self._data_consensus

    @property
    def revisions(self):
        if not (self._data_revision_cy and self._data_revision_ny):
            self._set_revison()
        return self._data_revision_cy, self._data_revision_ny

    def _lookup_url(self):
        xpath = '//*[@id="ALNI0"]/tr'
        if self.ISIN:
            url = self.BASE_SEARCH_URL + self.ISIN
        else:
            url = self.BASE_SEARCH_URL + self.name
        lxml_html = common.url_to_etree(url)
        for elem in lxml_html.xpath(xpath)[1:]:
            # Name from marketscraper.net website
            # symb = elem.xpath('./td[1]')[0].text_content().encode("utf-8").decode("utf-8")
            # country = elem.xpath('./td[2]/img/@title')[0].encode("utf-8").decode("utf-8")
            href = "https://de.marketscreener.com" + elem.xpath('./td[3]/a/@href')[0].encode("utf-8").decode("utf-8")
            exchange = elem.xpath('./td[7]')[0].text_content().encode("utf-8").decode("utf-8")
            if exchange.lower() in self.exchange:
                logger.debug("Got URL: {}!".format(href))
                return href

    def _lookup_id(self):
        xpath = '//*[@id="zbCenter"]/div/span/table[4]/tr/td[1]/table[1]/tr[2]/td/div[2]/a/@href'
        url = self.URL_revisions
        lxml_html = common.url_to_etree(url)
        link = lxml_html.xpath(xpath)[0]
        id_marketscreener = link.split("&")[1][-5:]
        return id_marketscreener

    def _set_revison(self):
        url = "https://de.marketscreener.com//reuters_charts/afDataFeed.php?repNo={}&codeZB=&t=rev&sub_t=bna&iLang=1".format(
            self.id)
        data = json.loads(common.request_url_to_str(url))
        eps_four_weeks_cy = data[0][0][-3][1]
        date_four_weeks_cy = data[0][0][-3][0]
        date_four_weeks_cy = common.german_date_to_normal(date_four_weeks_cy, "%b %Y")

        eps_today_cy = data[0][0][-1][1]
        date_today_cy = data[0][0][-1][0]
        date_today_cy = common.german_date_to_normal(date_today_cy, "%d.%m.%Y")
        change_cy = (eps_today_cy / eps_four_weeks_cy) * 100 - 100
        change_cy = round(change_cy, 2)

        eps_four_weeks_ny = data[0][1][-3][1]
        date_four_weeks_ny = data[0][1][-3][0]
        date_four_weeks_ny = common.german_date_to_normal(date_four_weeks_ny, "%b %Y")

        eps_today_ny = data[0][1][-1][1]
        date_today_ny = data[0][0][-1][0]
        date_today_ny = common.german_date_to_normal(date_today_ny, "%d.%m.%Y")

        change_ny = (eps_today_ny / eps_four_weeks_ny) * 100 - 100
        change_ny = round(change_ny, 2)

        self._data_revision_cy[date_today_cy] = eps_today_cy
        self._data_revision_cy[date_four_weeks_cy] = eps_four_weeks_cy
        self._data_revision_cy["Change current Year"] = change_cy
        self._data_revision_ny[date_today_ny] = eps_today_ny
        self._data_revision_ny[date_four_weeks_ny] = eps_four_weeks_ny
        self._data_revision_ny["Change next Year"] = change_ny
        # return self._data_revision_cy, self._data_revision_ny

    def _set_consensus(self):
        xpath = '//*[@id="zbCenter"]/div/span/table[4]/tr/td[3]/div[2]/div[2]/table/tr'
        url_resonse = common.url_to_etree(self.URL_consensus)
        self._data_consensus["consensus"] = url_resonse.xpath(xpath + "[1]/td[2]")[0].text_content().replace(" ", "").replace("\n", "").replace("\r", "")
        self._data_consensus["n_of_analysts"] = url_resonse.xpath(xpath + "[2]/td[2]")[0].text_content().replace(" ", "").replace("\n", "").replace("\r", "")
        self._data_consensus["price_target_average"] = float(
            url_resonse.xpath(xpath + "[3]/td[2]")[0].text_content().replace(" ", "").replace("\n", "").replace("\r", "").replace(',', '.').replace(u'\xa0', u'').strip("€"))
        # return self._data_consensus


if __name__ == '__main__':
    ms = MarketScreenerScraper(isin="DE000A1DAHH0")
    # print(ms.consensus)
    print(ms.URL)
    # ms._set_consensus()
    # print(ms.data_consensus)
    # for x, y in ms.data_consensus.items():
    #     print(x)
    #     print(y)
