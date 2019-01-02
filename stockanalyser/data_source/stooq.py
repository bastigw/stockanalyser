import json
import logging

from stockanalyser.data_source import common

logger = logging.getLogger(__name__)

with open('./html_site', 'r') as myfile:
    HTML_PAGE = myfile.read()
data = {}


def get_all_symbols(country=None):
    XPATH__len__ = '/html/body/table[1]/tr[2]/td[2]/table/tr/td/table/tr/td/table[6]/tr/td/table/tr/td[1]/table[1]/tr/td[2]/a[2]/@href'
    XPATH_cur = '/html/body/table[1]/tr[2]/td[2]/table/tr/td/table/tr/td/table[6]/tr/td/table/tr[2]/td[3]/div[12]/a/@href'
    # XPATH__len__ = '//*[@id="f13"]'
    if not country:
        country = "germany"
    URL = "https://stooq.com/t/?i={}".format(switch_country(country))
    URL_2 = "https://stooq.com/t/?i={}&v=0&l=".format(switch_country(country))
    # response_str = common.url_to_str(URL)
    # response = common.url_to_etree(URL)
    response = common.str_to_etree(response_read=HTML_PAGE)
    # len = response.xpath(XPATH__len__)[0].encode("utf-8").decode("utf-8")
    cur = response.xpath(XPATH_cur)[0].encode("utf-8").decode("utf-8")
    # print(lxml.etree.tostring(cur, pretty_print=True))
    # len = int(len[15:])
    cur = int(cur[26:])
    logger.debug("Current Page: {}".format(cur))
    data = find_all_symbols_on_page(response)

    # # for i in range(2, len):
    #     # this_url = URL_2 + str(i)
    #     # response = common.url_to_etree(this_url)
    # new_data = find_all_symbols_on_page(response)
    # data.update(new_data)
    # logger.debug("Got new Data. Progress: {}/{}".format(1, len))

    return data


def find_all_symbols_on_page(lxml_response):
    XPATH_table = '/html/body/table[1]/tr[2]/td[2]/table/tr/td/table/tr/td/table[6]/tr/td/table/tr[2]/td[1]/table[2]/tbody/tr'
    data_list = {}

    table = lxml_response.xpath(XPATH_table)
    for elem in table:
        symbol = elem.xpath('./td[1]/b/a')[0].text_content().encode("utf-8").decode("utf-8")
        name = elem.xpath('./td[2]')[0].text_content().encode("utf-8").decode("utf-8")
        data_list[name] = symbol
    return data_list


def switch_country(country):
    country_to_number = {
        "germany": 521,
        "us": 518
    }
    return country_to_number[country.lower()]


def save_dict(dict, name):
    DIR_PATH = '../../data/symbols_json/{}.json'.format(name)
    with open(DIR_PATH, 'r') as input:
        old_data = json.loads(input.read())
        len_old_data = len(old_data)
    with open(DIR_PATH, 'w') as output:
        if old_data:
            old_data.update(dict)
            json.dump(old_data, output, indent=4)
        else:
            json.dump(dict, output, indent=4)
    if len_old_data < len(old_data):
        logger.debug("Worked! Old len: {} vs New len: {}".format(len_old_data, len(old_data)))
    else:
        logger.debug("ERROR! Old len: {} vs New len: {}, dif: {}".format(len_old_data, len(old_data), (len_old_data - len(old_data))))


logging.basicConfig(level=logging.DEBUG)

name = 'us'
data = get_all_symbols()
save_dict(data, name)
