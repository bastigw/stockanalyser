"""
common.py

Functions that are used by all modules in this package!

"""

import datetime
import asyncio
import time
import urllib.request
import pathlib
import numpy as np
from typing import Union
from lxml import html
import logging

logger = logging.getLogger(__name__)

SLEEP = 10

url_last = ''

""" All request and HTML-Element handling """


async def request_cooldown():
    await asyncio.sleep(SLEEP)


def url_to_etree(url: str):
    """ Takes url and returns a lxml etree object"""
    return str_to_etree(request_url_to_str(url))


def request_url_to_str(url: str):
    req = urllib.request.Request(url)
    req.add_header('User-Agent', get_random_ua())
    logger.debug("Fetching webpage '%s'" % url)
    try:
        resp = urllib.request.urlopen(req).read()
        return resp
    except (urllib.request.HTTPError) as httperr:
        logger.exception("HTTPError: {}. ".format(httperr.code))
        # logger.exception(httperr)
        logger.warning("Sleeping for {} seconds. Website {} returned with "
                       "error code {}!".format(SLEEP, url.split("/")[2],
                                               httperr.code))
        request_cooldown()
        request_url_to_str(url)


def str_to_etree(response_read):
    logger.debug("Parsing string to etree")
    return html.fromstring(response_read)


def get_random_ua():
    """ Takes random User Agent from file """
    random_ua = ''
    ua_file = pathlib.Path(__file__).parent / 'ua_file.txt'
    try:
        with open(ua_file) as f:
            lines = f.readlines()
        if len(lines) > 0:
            prng = np.random.RandomState()
            index = prng.permutation(len(lines) - 1)
            idx = np.asarray(index, dtype=np.integer)[0]
            random_ua = lines[int(idx)]
            random_ua = random_ua.replace("\n", "")
    except Exception as ex:
        print('Exception in random_ua')
        print(str(ex))
    finally:
        return random_ua


def solve_xpath(etree: html, xpath: str):
    element = etree.xpath(xpath)
    # element = element.
    return element


"""Date calculation and formatting"""


def german_date_to_normal(date, str_format):
    replacements = {
        "ä": "a",
        "i": "y",
        "k": "c",
        "z": "c"
    }

    for old, new in replacements.items():
        date = date.replace(old, new)
    dt = datetime.datetime.strptime(date, str_format)
    return dt


def date_difference(date_start, date_end=None):
    """
    Calculate date difference between dates

    :param date_start: Older date
    :param date_end: If None = Today, else newer date
    :return: int of date difference
    """
    if not is_weekday(date_start):
        date_start = prev_weekday(date_start)
    if not date_end:
        date_end = datetime.datetime.now()
    if isinstance(date_start, datetime.datetime):
        date_end = date_end.date()
        date_start = date_start.date()
        return abs((date_start - date_end).days)
    elif isinstance(date_start, datetime.date):
        date_end = date_end.date()
        return abs((date_start - date_end).days)
    raise ValueError("date_start is not valid: {}".format(date_start))


def is_weekday(adate: Union[str, datetime.datetime, datetime.date]) -> bool:
    """Test if Date is weekday

    :param adate: Date string or datetime object
    """
    adate = convert_to_datetime(adate)
    if adate.isoweekday() not in (6, 7):
        return True
    return False


def prev_weekday(adate: Union[str, datetime.datetime, datetime.date]):
    """ Previous Weekday """
    if adate is not None:
        if isinstance(adate, str):
            adate = convert_to_datetime(adate)
        _offset = (3, 1, 1, 1, 1, 1, 2)[adate.isoweekday() - 1]
        return adate - datetime.timedelta(days=_offset)


def closest_weekday(adate):
    """ Closest Weekday:

            * Saturday -> Friday before
            * Sunday -> Monday after
    :return: datetime
        """
    if adate.isoweekday() == 7:
        return adate + datetime.timedelta(days=1)
    elif adate.isoweekday() == 6:
        return adate - datetime.timedelta(days=1)
    return adate


def convert_to_datetime(adate):
    """ Turns anything (nearly) into datetime obj"""
    if isinstance(adate, str):
        try:
            return datetime.datetime.strptime(adate, "%d.%m.%Y")
        except ValueError as e:
            logger.exception(e)
    if isinstance(adate, (datetime.datetime, datetime.date)):
        return adate


def prev_month(adate):
    if adate.month == 1:
        return datetime.date(year=datetime.date.today().year - 1, month=12,
                             day=prev_weekday(datetime.date(
                                 year=datetime.date.today().year - 1, month=12,
                                 day=22)).day)  # New Years Chaos, takes day before Christmas
    else:
        return datetime.date(adate.year, adate.month, 1) - datetime.timedelta(
            days=1)


if __name__ == '__main__':
    print(closest_weekday(datetime.date.today() - datetime.timedelta(days=4)))
