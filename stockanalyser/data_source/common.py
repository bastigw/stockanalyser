import datetime
import logging
import urllib.request

import lxml.etree
import lxml.html

logger = logging.getLogger(__name__)


def url_to_etree(url):
    req = urllib.request.Request(url)
    # Default User-Agent is rejected from the onvista webserver with 404
    req.add_header('User-Agent', "Bla")
    logger.debug("Fetching webpage '%s'" % url)
    resp = urllib.request.urlopen(req).read()

    return lxml.html.fromstring(resp)


def str_to_etree(response=None, response_read=None):
    if response:
        logger.debug("Parsing {} to etree".format(response.url))
        return lxml.html.fromstring(response.read())
    if response_read:
        logger.debug("Parsing string to etree")
        return lxml.html.fromstring(response_read)


def url_to_str(url):
    req = urllib.request.Request(url)
    # Default User-Agent is rejected from the onvista webserver with 404
    req.add_header('User-Agent', "Foo the Man")
    logger.debug("Fetching webpage '%s'" % url)
    resp = urllib.request.urlopen(req).read().decode()
    return resp


def _date_difference(date_start, date_end=None):
    assert date_start.weekday() not in (6, 7)
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
