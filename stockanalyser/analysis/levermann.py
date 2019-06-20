import datetime
import logging
from datetime import date, timedelta
from enum import Enum, unique

from stockanalyser.analysis import levernann_result
from stockanalyser.exceptions import NotSupportedError
from stockanalyser.stock import Cap, Stock
from stockanalyser.data_source import common
from database import database_interface

logger = logging.getLogger(__name__)

THIS_YEAR = date.today().year
LAST_YEAR = date.today().year - 1


class CriteriaRating(object):
    """
    Savaes value and point of a rating
    """

    def __init__(self, value, point):
        self._value = value
        self._points = point

    def __str__(self):
        string = "Value: {} | Points: {} ".format(self._value, self._points)
        return string

    @property
    def value(self):
        return self._value

    @property
    def points(self):
        return self._points


@unique
class Recommendation(Enum):
    BUY = 1
    HOLD = 2
    SELL = 3
    NONE = 0


# def levermann_pickle_path(symbol, path=DATA_PATH):
#     filename = fileutils.to_pickle_filename(symbol + ".levermann")
#     path = os.path.join(path, filename)
#     return path
#
#
# def unpickle_levermann_sym(symbol):
#     path = levermann_pickle_path(symbol)
#     return unpickle_levermann(path)
#
#
# def unpickle_levermann(path):
#     levermann_object = pickle.load(open(path, "rb"))
#     logger.debug("Unpickled Levermann Analysis for Stock: {} from '{}'".format(levermann_object.stock.symbol, path))
#     return levermann_object


class EvaluationResult(object):
    def __init__(self, points_all, eval_date):
        self.points = points_all
        self.date = eval_date


class Levermann(object):
    """
    Levermann Object:
        - Takes Stock object as input
        - Uses Stock object to evaluate first six points


        Evaluates other points:
            * Quarterly figures reaction
            * 6 and 12 month performance
            * Stock momentum
            * Three month reversal
            * Earning growth and revisions
    """

    def __init__(self, stock: Stock = None, isin: str = None,
                 auto_evaluate: bool = True):
        logger.info("Initializing {}".format(type(self).__name__))
        if stock is not None:
            self.stock = stock
        elif isin is not None:
            self.stock = Stock(isin=isin)
        else:
            logger.critical(
                "To few arguments, Stock object or ISIN are required")
            exit(1)
        self.evaluation_results = []
        self.reference_index = self._set_reference_index()

        if auto_evaluate:
            self.evaluate()

    def _set_reference_index(self) -> str:
        if self.stock.cap_type == Cap.LARGE:
            return "DAX"
        elif self.stock.cap_type == Cap.MID:
            return "MDAX"
        elif self.stock.cap_type == Cap.SMALL:
            return "SDAX"
        else:
            raise NotSupportedError(
                "Only DAX Stocks are supported. The stock symbol has to end "
                "with .de")

    def evaluate(self) -> tuple:
        """
        Evaluates complete Levermann rating
        :return: Levermann Result Object and a boolean:
                                            * True: if ratings are new
                                            * False: if ratings aren't older
                                            than a week
        """

        logger.info(
            "Creating Levermann Analysis for {}".format(self.stock.name))
        levermann_result = levernann_result.LevermannResult(
            name=self.stock.name, isin=self.stock.ISIN)

        try:
            levermann_result.roe = self._eval_roe()
        except Exception as e:
            logging.exception("Exception at {}.".format("self._eval_roe()"))
            logging.exception(e)
        logger.info("Finished evaluating: {}".format("self._eval_roe()"))
        try:
            levermann_result.ebit_margin = self._eval_ebit_margin()
        except Exception as e:
            logging.exception(
                "Exception at {}.".format("self._eval_ebit_margin()"))
            logging.exception(e)
        logger.info(
            "Finished evaluating: {}".format("self._eval_ebit_margin()"))
        try:
            levermann_result.equity_ratio = self._eval_equity_ratio()
        except Exception as e:
            logging.exception(
                "Exception at {}.".format("self._eval_equity_ratio()"))
            logging.exception(e)
        logger.info(
            "Finished evaluating: {}".format("self._eval_equity_ratio()"))
        try:
            levermann_result.price_earnings_ratio = \
                self._eval_price_earnings_ratio()
        except Exception as e:
            logging.exception(
                "Exception at {}.".format("self._eval_price_earnings_ratio()"))
            logging.exception(e)
        logger.info("Finished evaluating: {}".format(
            "self._eval_price_earnings_ratio()"))
        try:
            levermann_result.five_years_price_earnings_ratio = \
                self._eval_five_years_price_earnings_ratio()
        except Exception as e:
            logging.exception("Exception at {}.".format(
                "self._eval_five_years_price_earnings_ratio()"))
            logging.exception(e)
        logger.info("Finished evaluating: {}".format(
            "self._eval_five_years_price_earnings_ratio()"))
        try:
            levermann_result.analyst_rating = self._eval_analyst_rating()
        except Exception as e:
            logging.exception(
                "Exception at {}.".format("self._eval_analyst_rating()"))
            logging.exception(e)
        logger.info(
            "Finished evaluating: {}".format("self._eval_analyst_rating()"))
        try:
            levermann_result.quarterly_figures_reaction = \
                self.eval_quarterly_figures_reaction()
        except Exception as e:
            logging.exception("Exception at {}.".format(
                "self.eval_quarterly_figures_reaction()"))
            logging.exception(e)
        logger.info("Finished evaluating: {}".format(
            "self.eval_quarterly_figures_reaction()"))
        try:
            levermann_result.quote_chg_6month = self.eval_quote_chg_6month()
        except Exception as e:
            logging.exception(
                "Exception at {}.".format("self.eval_quote_chg_6month()"))
            logging.exception(e)
        logger.info(
            "Finished evaluating: {}".format("self.eval_quote_chg_6month()"))
        try:
            levermann_result.quote_chg_1year = self.eval_quote_chg_12month()
        except Exception as e:
            logging.exception(
                "Exception at {}.".format("self.eval_quote_chg_12month()"))
            logging.exception(e)
        logger.info(
            "Finished evaluating: {}".format("self.eval_quote_chg_12month()"))
        try:
            levermann_result.momentum = self._eval_momentum(
                levermann_result.quote_chg_6month.points,
                levermann_result.quote_chg_1year.points)
        except Exception as e:
            logging.exception("Exception at {}.".format(
                "self._eval_momentum(levermann_result.quote_chg_6month.points,"
                " levermann_result.quote_chg_1year.points)"))
            logging.exception(e)
        logger.info("Finished evaluating: {}".format(
            "self._eval_momentum(levermann_result.quote_chg_6month.points,"
            " levermann_result.quote_chg_1year.points)"))
        try:
            levermann_result.three_month_reversal = \
                self._eval_three_month_reversal()
        except Exception as e:
            logging.exception(
                "Exception at {}.".format("self._eval_three_month_reversal()"))
            logging.exception(e)
        logger.info("Finished evaluating: {}".format(
            "self._eval_three_month_reversal()"))
        try:
            levermann_result.earning_growth = self._eval_earning_growth()
        except Exception as e:
            logging.exception(
                "Exception at {}.".format("self._eval_earning_growth()"))
            logging.exception(e)
        logger.info(
            "Finished evaluating: {}".format("self._eval_earning_growth()"))
        try:
            levermann_result.earning_revision = self._eval_earning_revision()
        except Exception as e:
            logging.exception(
                "Exception at {}.".format("self._eval_earning_revision()"))
            logging.exception(e)
        logger.info(
            "Finished evaluating: {}".format("self._eval_earning_revision()"))

        if self.evaluation_results:
            last = self.evaluation_results[-1]
            if (last.timestamp > (datetime.datetime.now() - datetime.timedelta(
                    days=7))) and last.score == levermann_result.score:
                logger.debug("Old Levermann analysis:\n%s\n"
                             "New Levermann anylsis: \n%s" %
                             (str(last), str(levermann_result)))
                logger.info(
                    "Previous Levermann analysis is younger than 1 week and"
                    "\nLevermann score hasn't changed. New analysis data"
                    " is not stored.")
                return last, False

        self.evaluation_results.append(levermann_result)

        # Save data after evaluation finished
        logger.info('<<|{:^30}|>>'.format("Saving all data to database"))
        self.stock.save()
        self.save_levermann_analysis()
        levermann_result.save_points()
        logger.info('<<|{:^30}|>>'.format("Done"))
        logger.info(levermann_result.__str__())

        return levermann_result, True

    def _outdated(self):
        if not self.evaluation_results:
            return True
        last = self.evaluation_results[-1]
        if last.timestamp < (
                datetime.datetime.now() - datetime.timedelta(days=3)):
            return True
        return False

    def _eval_earning_growth(self):
        logger.debug("Evaluating earning growth")
        # Sorted! Uses dict to get amount
        try:
            eps_cur_year = self.stock.eps[THIS_YEAR]
            try:
                eps_next_year = self.stock.eps[THIS_YEAR + 1]
            except KeyError:
                eps_next_year = eps_cur_year
                eps_cur_year = self.stock.eps[THIS_YEAR - 1]

            if not (eps_cur_year and eps_next_year):
                return CriteriaRating(0, 0)

            chg = ((eps_next_year / eps_cur_year) - 1) * 100
            logger.debug("EPS current year: {}\n"
                         "EPS next year: {}\n"
                         "Change: {}%".format(eps_cur_year, eps_next_year,
                                              chg))

            if -5 <= chg <= 5:
                logger.debug("Earning growth change >=-5%%, <=5% => 0 Points")
                _points = 0
            elif eps_cur_year < eps_next_year:
                logger.debug(
                    "Earning growth change EPS next year > EPS current"
                    " year => 1 Points")
                _points = 1
            elif eps_cur_year > eps_next_year:
                logger.debug(
                    "Earning growth change EPS next year < EPS current"
                    " year => -1 Points")
                _points = -1

            return CriteriaRating(chg, _points)

        except (NameError, TypeError, ValueError, AttributeError, KeyError,
                IndexError) as e:
            logging.exception(e)
            return CriteriaRating(0, 0)

    def _calc_ref_index_comp(self, adate):
        # compare quote of stock with the quote of the reference index at the
        # last day of the month
        d = common.closest_weekday(adate)
        prev_month_date = common.closest_weekday(common.prev_month(adate))

        quote = self.stock.OS.get_historic_data(d)
        prev_quote = self.stock.OS.get_historic_data(prev_month_date)
        q_diff = ((quote / prev_quote) - 1) * 100

        ref_quote = self.stock.OS.get_historic_data(d)
        prev_ref_quote = self.stock.OS.get_historic_data(prev_month_date)
        ref_q_diff = ((ref_quote / prev_ref_quote) - 1) * 100

        logger.debug(
            "Comparing Stock with reference index. ({} vs {}) Stock:"
            " {} vs {} = {}%, Ref. Index.: {} vs {} = {}%".format(
                d, prev_month_date, quote, prev_quote, q_diff, ref_quote,
                prev_ref_quote, ref_q_diff))

        return q_diff - ref_q_diff

    def _eval_three_month_reversal(self):
        logger.debug("Evaluating 3 month reversal")
        try:  # TODO change single char variable
            if self.stock.cap_type != Cap.LARGE:
                return CriteriaRating((None, None, None), 0)
            d = common.prev_month(date.today())
            m1_diff = self._calc_ref_index_comp(d)

            d = common.prev_month(d)
            m2_diff = self._calc_ref_index_comp(d)

            d = common.prev_month(d)
            m3_diff = self._calc_ref_index_comp(d)

            if m1_diff > 0 and m2_diff > 0 and m3_diff > 0:
                _points = -1
            elif m1_diff < 0 and m2_diff < 0 and m3_diff < 0:
                _points = 1
            else:
                _points = 0

            return CriteriaRating((m1_diff, m2_diff, m3_diff), _points)
        except (NameError, TypeError, ValueError, AttributeError, KeyError,
                IndexError) as e:
            logging.exception(e)
            return CriteriaRating(0, 0)

    def _eval_quote_chg_daydiff(self, days_diff):
        before_date = common.closest_weekday(
            date.today() - timedelta(days=days_diff))
        before_quote = self.stock.OS.get_historic_data(before_date)

        chg = ((float(self.stock.quote) / before_quote) - 1) * 100
        chg = round(chg, 2)
        return chg, self._calc_quite_chg_points(chg)

    def eval_quote_chg_6month(self):
        try:
            chg, _points = self._eval_quote_chg_daydiff(182)

            return CriteriaRating(chg, _points)
        except (NameError, TypeError, ValueError, AttributeError, KeyError,
                IndexError) as e:
            logging.exception(e)
            return CriteriaRating(0, 0)

    def eval_quote_chg_12month(self):
        try:
            chg, _points = self._eval_quote_chg_daydiff(365)

            return CriteriaRating(chg, _points)
        except (NameError, TypeError, ValueError, AttributeError, KeyError,
                IndexError) as e:
            logging.exception(e)
            return CriteriaRating(0, 0)

    def _eval_earning_revision(self):
        try:
            cur_year_eps = self.stock.eval_earning_revision_cy
            next_year_eps = self.stock.eval_earning_revision_ny

            cur_year_chg = cur_year_eps['Change current Year']
            next_year_chg = next_year_eps['Change next Year']

            cur_year_points = self._calc_earning_rev_points(cur_year_chg)
            next_year_points = self._calc_earning_rev_points(next_year_chg)

            psum = cur_year_points + next_year_points

            if cur_year_points == 0 and next_year_points == 0:
                _points = 0
            elif psum >= 1:
                _points = 1
            elif psum <= -1:
                _points = -1

            return CriteriaRating((cur_year_points, next_year_points), _points)
        except (NameError, TypeError, ValueError, AttributeError, KeyError,
                IndexError) as e:
            logging.exception(e)
            return CriteriaRating(0, 0)

    def eval_quarterly_figures_reaction(self, case: str = ''):
        logger.debug("Evaluating stock reaction on"
                     "quarterly figures")
        try:
            qf_date = self.stock.last_quarterly_figures_release_date()
            qf_prev_day = common.prev_work_day(
                self.stock.last_quarterly_figures_release_date())

            if qf_prev_day is None:
                return CriteriaRating(0, 0)

            qf_previous_day_quote = self.stock.OS.get_historic_data(
                qf_prev_day)
            qf_day_quote = self.stock.OS.get_historic_data(qf_date)
            qf_reaction = ((qf_day_quote / qf_previous_day_quote) - 1) * 100

            ref_index_quote = self.stock.OS.get_historic_data(
                qf_date, index=self.reference_index)
            ref_previous_index_quote = self.stock.OS.get_historic_data(
                qf_prev_day, index=self.reference_index)
            ref_index_chg = (
                ((ref_index_quote / ref_previous_index_quote) - 1) * 100)

            rel_qf_reaction = qf_reaction - ref_index_chg
            logger.debug(
                "Quarterly figure reaction {} vs {}: {}: {} vs {} =>"
                " {}, {}: {} vs {} => {},".format(
                    qf_date, qf_prev_day, self.stock.name, qf_day_quote,
                    qf_previous_day_quote, qf_reaction, self.reference_index,
                    ref_index_quote,
                    ref_previous_index_quote, ref_index_chg))

            if -1 <= rel_qf_reaction < 1:
                _points = 0
            elif rel_qf_reaction >= 1:
                _points = 1
            else:
                _points = -1

            logger.debug(
                "Relative Stock reaction to quarterly figure release is"
                " {}%, => {} Points".format(
                    rel_qf_reaction, _points))

            if case is 'sql_data':
                return qf_reaction, ref_index_chg

            return CriteriaRating(rel_qf_reaction, _points)
        except (NameError, TypeError, ValueError, AttributeError, KeyError,
                IndexError) as e:
            logging.exception(e)
            if case is 'sql_data':
                return 0, 0
            else:
                return CriteriaRating(0, 0)

    def _eval_analyst_rating(self):
        try:
            analyst_ratings = self.stock.consensus_ratings
            if not analyst_ratings:
                return CriteriaRating(None, 0)
            logger.debug("Analyst ratings: %s" % str(analyst_ratings))
            consensus = analyst_ratings["consensus"]
            number_of_analysts = int(analyst_ratings["n_of_analysts"])
            ratings = {
                "KAUFEN": 1,
                "AUFSTOCKEN": 2,
                "HALTEN": 3,
                "REDUZIEREN": 4,
                "VERKAUFEN": 5
            }

            score = ratings[consensus]

            logger.debug("Analyst score: %s" % consensus)

            if score == 2 or score == 1:
                _points = -1
            elif score == 3:
                _points = 0
            elif score == 4 or score == 5:
                _points = 1
            else:
                raise ValueError("Wrong Type")

            if number_of_analysts >= 5:
                _points *= -1

            return CriteriaRating(score, _points)
        except (NameError, TypeError, ValueError, AttributeError, KeyError,
                IndexError) as e:
            logging.exception(e)
            return CriteriaRating(0, 0)

    def _eval_five_years_price_earnings_ratio(self):
        try:
            per = self.stock.price_earnings_ratio_5year()
            logger.debug("Evaluating 5year PER: %s" % per)

            if 0 < per < 12:
                logger.debug("5 year PER <12: 1 Points")
                _points = 1
            elif 12 <= per <= 16:
                logger.debug("5 year PER >=12, <=16: 0 Points")
                _points = 0
            else:
                logger.debug("5 year PER >16: -1 Points")
                _points = -1

            return CriteriaRating(per, _points)
        except (NameError, TypeError, ValueError, AttributeError, KeyError,
                IndexError) as e:
            logging.exception(e)
            return CriteriaRating(0, 0)

    def _eval_price_earnings_ratio(self):
        try:
            per = self.stock.per[THIS_YEAR]
            logger.debug("Evaluating PER: %s" % per)

            if 0 < per < 12:
                logger.debug("PER <12: 1 Points")
                _points = 1
            elif 12 <= per <= 16:
                logger.debug("PER >=12, <=16: 0 Points")
                _points = 0
            else:
                logger.debug("PER >16: -1 Points")
                _points = -1

            return CriteriaRating(per, _points)
        except (NameError, TypeError, ValueError, AttributeError, KeyError,
                IndexError) as e:
            logging.exception(e)
            return CriteriaRating(0, 0)

    def _eval_roe(self):
        try:
            year = LAST_YEAR
            if year not in self.stock.roe or self.stock.roe[year] is None:
                year -= 1
                logger.debug("ROE for year year %s"
                             " not set. Evaluation RoE "
                             " of year %s instead" % (LAST_YEAR, year))
            roe = self.stock.roe[year]

            logger.debug("Evaluating RoE (%s): %s%%" % (year, roe))
            if roe < 10:
                logger.debug("ROE <10%: -1 Points")
                _points = -1
            elif 10 <= roe <= 20:
                logger.debug("ROE >=10%, <=20%: 0 Points")
                _points = 0
            elif roe > 20:
                logger.debug("ROE >20%: 1 Point")
                _points = 1

            return CriteriaRating(roe, _points)
        except (NameError, TypeError, ValueError, AttributeError, KeyError,
                IndexError) as e:
            logging.exception(e)
            return CriteriaRating(0, 0)

    def _eval_equity_ratio(self):
        try:
            last_year = LAST_YEAR

            if last_year not in self.stock.equity_ratio or \
                    self.stock.equity_ratio[last_year] is None:
                last_year -= 1
                logger.debug("Equity ratio for year year %s"
                             " not set. Evaluation Equity Ratio"
                             " of year %s instead" % (LAST_YEAR, last_year))

            equity_ratio = self.stock.equity_ratio[last_year]

            logger.debug("Evaluating equity ratio (%s): %s%%" % (last_year,
                                                                 equity_ratio))
            if equity_ratio < 15:
                logger.debug("Equity Ratio <10%: -1 Points")
                _points = -1
            elif 15 <= equity_ratio <= 25:
                logger.debug("Equity Ratio >=15%, <=25%: 0 Points")
                _points = 0
            elif equity_ratio > 25:
                logger.debug("Equity Ratio >25%: 1 Point")
                _points = 1

            return CriteriaRating(equity_ratio, _points)
        except (NameError, TypeError, ValueError, AttributeError, KeyError,
                IndexError) as e:
            logging.exception(e)
            return CriteriaRating(0, 0)

    def _eval_ebit_margin(self):
        try:
            last_year = LAST_YEAR
            if last_year not in self.stock.ebit_margin or \
                    self.stock.ebit_margin[last_year] is None:
                last_year -= 1
                logger.debug("Ebit margin for year %s unknown."
                             " Evaluating margin of year %s"
                             " instead" % (LAST_YEAR, last_year))

            ebit_margin = self.stock.ebit_margin[last_year]

            logger.debug("Evaluating EBIT-Margin %s" % ebit_margin)
            if ebit_margin < 6:
                logger.debug("EBIT-Margin <6%: -1 Points")
                _points = -1
            elif 6 <= ebit_margin <= 12:
                logger.debug("6% < EBIT-Margin < 12%: 0 Points")
                _points = 0
            elif ebit_margin > 12:
                logger.debug("EBIT-Margin >12%: 1 Points")
                _points = 1

            return CriteriaRating(ebit_margin, _points)
        except (NameError, TypeError, ValueError, AttributeError, KeyError,
                IndexError) as e:
            logging.exception(e)
            return CriteriaRating(0, 0)

    @staticmethod
    def _eval_momentum(points_6month_chg, points_1year_chg):
        try:
            if points_6month_chg == 1 and (points_1year_chg <= 0):
                _points = 1
            elif points_6month_chg == -1 and (points_1year_chg >= 0):
                _points = -1
            else:
                _points = 0

            return CriteriaRating((points_6month_chg, points_1year_chg),
                                  _points)
        except (NameError, TypeError, ValueError, AttributeError, KeyError,
                IndexError) as e:
            logging.exception(e)
            return CriteriaRating(0, 0)

    @staticmethod
    def _calc_quite_chg_points(chg):
        if -5 <= chg <= 5:
            return 0
        elif chg < -5:
            return -1
        elif chg > 5:
            return 1

    @staticmethod
    def _calc_earning_rev_points(chg):
        if -5 <= chg <= 5:
            return 0
        elif chg > 5:
            return 1
        elif chg < -5:
            return -1

    def short_summary_header(self):
        string_short_summary_header = (
            "| {:<25} | {:<14} | {:<14} | {:<6} |".format("Name",
                                                          "Prev Score (Date)",
                                                          "Last Score (Date)",
                                                          "Advise"))
        string_short_summary_header += "\n"
        string_short_summary_header += self.short_summary_footer()
        return string_short_summary_header

    @staticmethod
    def short_summary_footer():
        return "-" * 78

    def short_summary(self):
        r = self.evaluation_results[-1]
        r_prev_ts = "N/A"
        r_prev_score = "N/A"
        if len(self.evaluation_results) > 1:
            r_prev = self.evaluation_results[-2]
            r_prev_ts = r_prev.timestamp.strftime("%x")
            r_prev_score = r_prev.score

        r_ts = r.timestamp.strftime("%x")

        string_output = (
            "| {:<25} | {:<6} ({:<8}) | {:<6} ({:<8}) | {:<6} |".format(
                self.stock.name, r_prev_score, r_prev_ts, r.score, r_ts,
                self.recommendation().name))

        return string_output

    def __str__(self):
        if not self.evaluation_results:
            return "No Analysis exist"

        eva_result = self.evaluation_results[-1]

        string_output = str(self.stock)
        string_output += str(eva_result)
        return string_output

    def recommendation(self):
        """Calculate SELL, HOLD or BUY Action for specific stock

        :return: Recommendation
        """
        if len(self.evaluation_results) >= 2 and (
                self.evaluation_results[-1].score
                - self.evaluation_results[-2].score) <= -2:
            return Recommendation.SELL

        if self.stock.cap_type == Cap.LARGE:
            if self.evaluation_results[-1].score <= 2:
                return Recommendation.SELL
            elif self.evaluation_results[-1].score < 4:
                return Recommendation.HOLD
            elif self.evaluation_results[-1].score >= 4:
                return Recommendation.BUY
            return Recommendation.NONE

        if self.evaluation_results[-1].score <= 4:
            return Recommendation.SELL
        elif self.evaluation_results[-1].score < 7:
            return Recommendation.HOLD
        if self.evaluation_results[-1].score >= 7:
            return Recommendation.BUY

        return Recommendation.NONE

    def save_levermann_analysis(self) -> int:
        """Saves values to database

        :return: amount of changed lines
        """
        return database_interface.save_values(self)


if __name__ == "__main__":
    leverman = Levermann(stock=Stock(isin='DE000A0Z2ZZ5'))
