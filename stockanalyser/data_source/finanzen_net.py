import logging
import urllib.request
from datetime import datetime

import requests

from stockanalyser.data_source import common

logger = logging.getLogger(__name__)


class FinanzenNetScraper(object):
    def __init__(self, url=None, isin=None, name=None):
        self.URL = url
        self.termine_url = None
        self.ISIN = isin
        self.name = name
        self.BASE_SEARCH_URL = "https://www.finanzen.net/suchergebnis.asp?_search="

    def lookup_url(self):
        # Finanzen.net search with symbol not possible
        if self.ISIN:
            self.__get_url_response(arg=self.ISIN)
        if not self.URL:
            self.__get_url_response(arg=self.name)
        if self.URL is None:
            raise ValueError("Couldn't find URL! Stock's finanzen.net URL is not set ")
        return self.URL

    def __get_url_response(self, arg=None):
        if self.ISIN is arg:
            url = self.BASE_SEARCH_URL + self.ISIN
            url_response = urllib.request.urlopen(urllib.request.Request(url))
            if url is not url_response.url:
                logger.debug("Got redireted! URL: {0}!".format(url_response.url))
                self.URL = url_response.url
                self.name = self.get_name()

        if self.name is arg:
            XPATH = '//*[@id="suggestBESearch"]/div/div[4]/div/table/tr'
            url = self.BASE_SEARCH_URL + self.name
            url_resonse = urllib.request.urlopen(urllib.request.Request(url)).read()

            lxml_html = common.str_to_etree(response_read=url_resonse)
            for elem in lxml_html.xpath(XPATH):
                # Name from finanzen.net website
                ISIN = elem.xpath('./td[2]')[0].text_content().encode("utf-8").decode("utf-8")
                WKN = elem.xpath('./td[3]')[0].text_content().encode("utf-8").decode("utf-8")
                href = "https://www.finanzen.net" + elem.xpath('./td[1]/a/@href')[0].encode("utf-8").decode("utf-8")
                if WKN.endswith('3'):
                    continue
                if ISIN and WKN:
                    logger.debug("Got URL: {0}!".format(href))
                    self.URL = href
                    self.ISIN = ISIN
                    self.name = self.get_name()
                    break

    def get_name(self):
        if not self.URL:
            self.lookup_url()
        name = self.URL.split("/")[-1]
        name = name.replace("-Aktie", "")
        name = name.replace("_", "-")
        return name

    def _get_termine_url(self):
        element = common.url_to_etree(self.URL)
        path = element.xpath('//a[@title][contains(., "Termine")]')[0].attrib['href']
        logger.debug("fetched termine path: %s" % path)

        return requests.compat.urljoin("http://www.finanzen.net/", path)

    def fetch_recent_quarterly_figures_release_date(self):
        # returns a sorted list of all "Quartalszahlen" dates
        if not self.URL:
            self.URL = self.lookup_url()
            if self.URL is None:
                raise ValueError("Stock's finanzen.net URL is not set ")

        termine_url = self._get_termine_url()
        etree = common.url_to_etree(termine_url)
        rows = etree.xpath("//table[@class='table']//tr")
        release_dates = []
        for r in rows:
            if r.xpath("td//text()='Quartalszahlen'"):
                str_date = r.xpath("td[4]")[0].text_content()
                # if the string containts "(e)*" it means it's an estimated
                # date, skip those we want reliable dates
                if "(e)" in str_date:
                    continue
                d = datetime.strptime(str_date, '%d.%m.%Y').date()
                release_dates.append(d)

        release_dates.sort()
        logger.debug("fetched quarterly figures release dates: %s" %
                     release_dates)
        return release_dates


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    f = FinanzenNetScraper(
        # url="http://www.finanzen.net/aktien/Allianz-Aktie",
        isin="DE0008404005",
        # name="Volkswagen"
    )
    print(f.get_name())
    # f.fetch_recent_quarterly_figures_release_date()
    # print(f.fetch_recent_quarterly_figures_release_date())
