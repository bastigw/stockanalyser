import datetime
import urllib.request
import numpy as np
import pathlib

import lxml.etree
import lxml.html
import logging

logger = logging.getLogger(__name__)


def url_to_etree(url):
    return str_to_etree(request_url_to_str(url))


def request_url_to_str(url):
    req = urllib.request.Request(url)
    req.add_header('User-Agent', get_random_ua())
    logger.debug("Fetching webpage '%s'" % url)
    resp = urllib.request.urlopen(req).read()
    return resp


def str_to_etree(response_read):
    logger.debug("Parsing string to etree")
    return lxml.html.fromstring(response_read)


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


def get_random_ua():
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


def date_difference(date_start, date_end=None):
    """
    Calculate date difference between dates

    :param date_start: Older date
    :param date_end: If None = Today, else newer date
    :return: int of date difference
    """
    if date_start.isoweekday() not in (6, 7):
        # print(date_start.weekday)
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


def is_weekday(adate):
    if adate.weekday() in (5, 6):
        return False
    return True


def prev_weekday(adate):
    _offsets = (3, 1, 1, 1, 1, 1, 2)
    return adate - datetime.timedelta(days=_offsets[adate.weekday()])


def closest_weekday(adate):
    if adate.weekday() == 6:
        return adate + datetime.timedelta(days=1)
    elif adate.weekday() == 5:
        return adate - datetime.timedelta(days=1)
    return adate


def prev_month(adate):
    if adate.month == 1:
        new_date = datetime.date(year=datetime.date.today().year - 1, month=12,
                        day=prev_weekday(datetime.date(year=datetime.date.today().year - 1, month=12, day=22)).day)  # New Years Chaos, takes day before Christmas
    else:
        new_date = datetime.date(adate.year, adate.month, 1) - datetime.timedelta(days=1)
    return new_date
