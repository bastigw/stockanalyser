from stockanalyser.database import aktieninformation, aktien_data_jaehrlich, \
    aktie_levermann_result, aktie_levermann_values
import logging

logger = logging.getLogger(__name__)


def save_information(stock_object):
    lines_changed: int = aktieninformation.insert_data(
        stock_object=stock_object)
    logger.debug("{} lines where changed!".format(lines_changed))


def save_yearly(stock_object):
    lines_changed: int = aktien_data_jaehrlich.save_yearly(
        stock_object=stock_object)
    logger.debug("{} lines where changed!".format(lines_changed))


def save_points(levermann_result_object):
    lines_changed: int = aktie_levermann_result.save_points(
        levermann_result=levermann_result_object)
    logger.debug("{} lines where changed!".format(lines_changed))


def save_values(levermann_object):
    lines_changed: int = aktie_levermann_values.save_points(
        levermann=levermann_object)
    logger.debug("{} lines where changed!".format(lines_changed))


def find_entry_in_aktieninformation(field: str) -> dict:
    return aktieninformation.find_data_entry(field)
