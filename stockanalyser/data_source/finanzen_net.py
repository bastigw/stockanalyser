from urllib import request, parse
from datetime import datetime
import logging

from stockanalyser.data_source import common

logger = logging.getLogger(__name__)


class FinanzenNetScraper(object):
    def __init__(self, url=None, isin=None, name=None):
        logger.info("Initializing {}".format(type(self).__name__))
        self.URL = url
        self.termine_url = None
        self.ISIN = isin
        self._name = name
        self.BASE_SEARCH_URL = "https://www.finanzen.net/" \
                               "suchergebnis.asp?_search="
        self._benchmark = None
        self._quarterly_figures_dates = None
        self.etree = None

    def lookup_url(self):
        # Finanzen.net search with symbol not possible
        if self.ISIN:
            self._get_url_response(arg=self.ISIN)
        if not self.URL:
            self._get_url_response(arg=self.name)
        if self.URL is None:
            raise ValueError(
                "Couldn't find URL! Stock's finanzen.net URL is not set ")
        return self.URL

    def _get_url_response(self, arg=None):
        if self.ISIN is arg:
            url = self.BASE_SEARCH_URL + self.ISIN
            url_response = request.urlopen(request.Request(url))
            if url is not url_response.url:
                logger.debug(
                    "Got redireted! URL: {0}!".format(url_response.url))
                self.URL = url_response.url
                self.etree = common.str_to_etree(
                    response_read=url_response.read())
                self._name = self.name

        if self.name is arg:
            xpath = '//*[@id="suggestBESearch"]/div/div[4]/div/table/tr'
            url = self.BASE_SEARCH_URL + self.name
            url_response = request.urlopen(
                request.Request(url)).read()

            lxml_html = common.str_to_etree(response_read=url_response)
            self.etree = lxml_html
            for elem in lxml_html.xpath(xpath):
                # Name from finanzen.net website
                isin = elem.xpath('./td[2]')[0].text_content().encode(
                    "utf-8").decode("utf-8")
                wkn = elem.xpath('./td[3]')[0].text_content().encode(
                    "utf-8").decode("utf-8")
                href = "https://www.finanzen.net" + \
                       elem.xpath('./td[1]/a/@href')[0].encode("utf-8").decode(
                           "utf-8")
                if wkn.endswith('3'):
                    continue
                if isin and wkn:
                    logger.debug("Got URL: {0}!".format(href))
                    self.URL = href
                    self.ISIN = isin
                    self._name = self.name
                    break

    def _get_termine_url(self):
        element = self.etree
        path = element.xpath('//a[@title][contains(., "Termine")]')[0].attrib[
            'href']
        logger.debug("fetched termine path: %s" % path)

        return parse.urljoin("http://www.finanzen.net/", path)

    def _fetch_recent_quarterly_figures_release_date(self):
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
                # if the string contains "(e)*" it means it's an estimated
                # date, skip those we want reliable dates
                if "(e)" in str_date:
                    continue
                d = datetime.strptime(str_date, '%d.%m.%Y').date()
                release_dates.append(d)

        release_dates.sort()
        logger.debug("fetched quarterly figures release dates: {}".format(
            release_dates))
        self._quarterly_figures_dates = release_dates

    def _get_benchmark(self):
        if self.etree is None:
            self.lookup_url()
        element = self.etree
        if element is not None:
            benchmark = element.xpath(
                '/html/body/div[2]/div[6]/div[3]/'
                'div[28]/div[3]/div[1]/table/tr')
            for row in benchmark:
                if row[0].text_content() == 'Indizes':
                    benchmark = row[1][0].text_content()
            self._benchmark = benchmark
        else:
            logger.warning("Etree not defined")

    @property
    def benchmark(self):
        if not self._benchmark:
            self._get_benchmark()
        return self._benchmark

    @property
    def quarterly_figure_dates(self):
        if not self._quarterly_figures_dates:
            self._fetch_recent_quarterly_figures_release_date()
        return self._quarterly_figures_dates

    @property
    def name(self):
        if not self.URL:
            self.lookup_url()
        name = self.URL.split("/")[-1]
        name = name.replace("-Aktie", "")
        name = name.replace("_", "-")
        self._name = name
        return self._name


if __name__ == "__main__":
    fin = FinanzenNetScraper(
        # url='https://www.finanzen.net/aktien/Aroundtown-Aktie',
        isin='LU1673108939')
    fin.lookup_url()
    print(fin.quarterly_figure_dates)
    pass
