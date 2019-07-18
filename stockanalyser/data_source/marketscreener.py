import json
import logging
import re
import numpy as np

from stockanalyser.data_source import common
from stockanalyser import exceptions

logger = logging.getLogger(__name__)


class MarketScreenerScraper(object):
    def __init__(self, ms_id=None, ms_url=None, isin=None, name=None):
        logger.info("Initializing {}".format(type(self).__name__))
        self.ISIN = isin
        self.name = name

        self.BASE_SEARCH_URL = "https://de.marketscreener.com/suchen/firmen/?aComposeInputSearch=s_"
        self.URL = ms_url
        if not self.URL:
            self.URL = self._lookup_url()

        self.URL_revisions = self.URL + "reviews-revisions/"
        self.URL_consensus = self.URL + "analystenerwartungen/"

        self.codeZB = ms_id
        if not self.codeZB:
            self.codeZB = self._lookup_codeZB()

        self._data_consensus: dict = {}
        self._data_revision_cy: dict = {}
        self._data_revision_ny: dict = {}

    @property
    def consensus_data(self):
        if not self._data_consensus:
            self._set_consensus()
        return self._data_consensus

    @property
    def revisions(self):
        if not (self._data_revision_cy and self._data_revision_ny):
            self._set_revision()
        return self._data_revision_cy, self._data_revision_ny

    def _lookup_url(self):
        if self.ISIN:
            url = self.BASE_SEARCH_URL + self.ISIN
        else:
            url = self.BASE_SEARCH_URL + self.name
        lxml_html = common.url_to_etree(url)
        xpath = '//*[@id="ALNI0"]'
        children = lxml_html.xpath(xpath)[0].getchildren()
        for child in children:
            child = common.str_to_etree(common.tostring(child))
            src = dict(child
                       .xpath("//td/div[1]/table/tr/td[1]/img")[0]
                       .attrib
                       )['src']
            if src.endswith("de.png"):
                return "https://de.marketscreener.com" + dict(child
                                                              .xpath("//*/td/div[1]/table/tr/td[2]/a")[0]
                                                              .attrib
                                                              )['href']
        raise exceptions.MissingDataError("Couldn't find link to stock")

    def _lookup_codeZB(self):
        return self.URL.split('/')[-2].split('-')[-1]

    def _set_revision(self):
        url = "https://de.marketscreener.com//reuters_charts/afDataFeed.php?&codeZB={}&t=rev&sub_t=bna&iLang=1".format(
            self.codeZB)
        revisions_data = json.loads(common.request_url_to_str(url))
        eps_four_weeks_cy = revisions_data[0][0][-20][1]
        date_four_weeks_cy = revisions_data[0][0][-20][0]
        date_four_weeks_cy = common.unixtime_to_datetime(
            date_four_weeks_cy, milliseconds=True)

        eps_today_cy = revisions_data[0][0][-1][1]
        date_today_cy = revisions_data[0][0][-1][0]
        date_today_cy = common.unixtime_to_datetime(
            date_today_cy, milliseconds=True)
        change_cy = (eps_today_cy / eps_four_weeks_cy) * 100 - 100
        change_cy = round(change_cy, 2)

        eps_four_weeks_ny = revisions_data[0][1][-20][1]
        date_four_weeks_ny = revisions_data[0][1][-20][0]
        date_four_weeks_ny = common.unixtime_to_datetime(
            date_four_weeks_ny, True)

        eps_today_ny = revisions_data[0][1][-1][1]
        date_today_ny = revisions_data[0][0][-1][0]
        date_today_ny = common.unixtime_to_datetime(date_today_ny, True)

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
        url = "https://de.marketscreener.com/reuters_charts/afDataFeed.php?codeZB={}&t=dcons&iLang=3".format(
            self.codeZB
        )
        consensus_data = json.loads(common.request_url_to_str(url))

        if consensus_data[3] is False:
            raise ValueError("Did not respond correctly (404)")
        consensus_weighted = []
        consensus_weighted.append(10 * consensus_data[0]["reco_BUY"])
        consensus_weighted.append(7.5 * consensus_data[0]["reco_OUTPERFORM"])
        consensus_weighted.append(5 * consensus_data[0]["reco_HOLD"])
        consensus_weighted.append(2.5 * consensus_data[0]["reco_UNDERPERFORM"])
        consensus_weighted.append(0 * consensus_data[0]["reco_SELL"])

        number_of_analysts = consensus_data[0]["reco_BUY"]
        number_of_analysts += consensus_data[0]["reco_OUTPERFORM"]
        number_of_analysts += consensus_data[0]["reco_HOLD"]
        number_of_analysts += consensus_data[0]["reco_UNDERPERFORM"]
        number_of_analysts += consensus_data[0]["reco_SELL"]

        self._data_consensus["consensus"] = round(sum(consensus_weighted) / number_of_analysts, 2)
        self._data_consensus["n_analysts"] = number_of_analysts
