import calendar
import datetime
import logging
import pickle
from datetime import date, timedelta
from enum import Enum, unique

from stockanalyser import fileutils
from stockanalyser.analysis import levernann_result
from stockanalyser.config import *
from stockanalyser.data_source import alphavantage
from stockanalyser.exceptions import NotSupportedError
from stockanalyser.stock import Cap
from stockanalyser.stock import Stock

logger = logging.getLogger(__name__)

THIS_YEAR = date.today().year
LAST_YEAR = date.today().year - 1


def is_weekday(adate):
    if adate.weekday() in (5, 6):
        return False

    return True


def prev_weekday(adate):
    _offsets = (3, 1, 1, 1, 1, 1, 2)
    return adate - timedelta(days=_offsets[adate.weekday()])


def closest_weekday(adate):
    if adate.weekday() == 6:
        return adate + timedelta(days=1)
    elif adate.weekday() == 5:
        return adate - timedelta(days=1)
    return adate


def last_weekday_of_month(adate):
    last_day = calendar.monthrange(adate.year, adate.month)[1]
    d = date(adate.year, adate.month, last_day)

    if not is_weekday(d):
        return prev_weekday(d)
    return d


def prev_month(adate):
    return date(adate.year, adate.month, 1) - timedelta(days=1)


class CriteriaRating(object):
    def __init__(self, value, points):
        self.value = value
        self.points = points


@unique
class Recommendation(Enum):
    BUY = 1
    HOLD = 2
    SELL = 3


def levermann_pickle_path(symbol, dir=DATA_PATH):
    filename = fileutils.to_pickle_filename(symbol + ".levermann")
    path = os.path.join(dir, filename)
    return path


def unpickle_levermann_sym(symbol, dir=DATA_PATH):
    path = levermann_pickle_path(symbol)
    return unpickle_levermann(path)


def unpickle_levermann(path):
    l = pickle.load(open(path, "rb"))
    logger.debug("Unpickled Levermann Analysis for Stock: {} from '{}'".format(l.stock.symbol, path))
    return l


class EvaluationResult(object):
    def __init__(self, points, eval_date):
        self.points = points
        self.date = eval_date


class Levermann(object):
    def __init__(self, stock):
        self.stock = stock
        self.evaluation_results = []

        if self.stock.cap_type == Cap.LARGE:
            self.reference_index = "^GDAXI"
        elif self.stock.cap_type == Cap.MID:
            self.reference_index = "^MDAXI"
        elif self.stock.cap_type == Cap.SMALL:
            self.reference_index = "^SDAXI"
        else:
            raise NotSupportedError("Only DAX Stocks are supported."
                                    " The stock symbol has to end in .de")

    def evaluate(self):
        logger.info("Creating Levermann Analysis for {}".format(self.stock.symbol))
        result = levernann_result.LevermannResult(name=self.stock.name)

        result.roe = self.eval_roe()
        result.ebit_margin = self.eval_ebit_margin()
        result.equity_ratio = self.eval_equity_ratio()
        result.price_earnings_ratio = self.eval_price_earnings_ratio()
        result.five_years_price_earnings_ratio = self.eval_five_years_price_earnings_ratio()
        result.analyst_rating = self.eval_analyst_rating()
        result.quarterly_figures_reaction = self.eval_quarterly_figures_reaction()

        result.quote_chg_6month = self.eval_quote_chg_6month()
        result.quote_chg_1year = self.eval_quote_chg_1year()
        result.momentum = self.eval_momentum(result.quote_chg_6month.points,
                                             result.quote_chg_1year.points)

        result.three_month_reversal = self.eval_three_month_reversal()
        result.earning_growth = self.eval_earning_growth()
        result.earning_revision = self.eval_earning_revision()

        if self.evaluation_results:
            last = self.evaluation_results[-1]
            if ((last.timestamp > (datetime.datetime.now() -
                                   datetime.timedelta(days=7))) and last.score == result.score):
                logger.debug("Old Levermann analysis:\n%s\n"
                             "New Levermann anylsis: \n%s" %
                             (str(last), str(result)))
                logger.info("Previous Levermann analysis is younger than 1"
                            " week and\nLevermann score hasn't changed."
                            "New analysis data is not stored.")
                return False

        self.evaluation_results.append(result)

        return result, True

    def outdated(self):
        if not self.evaluation_results:
            return True

        last = self.evaluation_results[-1]
        if (last.timestamp < (datetime.datetime.now() -
                              datetime.timedelta(days=3))):
            return True
        return False

    def eval_earning_growth(self):
        logger.debug("Evaluating earning growth")
        # Sorted! Uses dict to get amount

        eps_cur_year = self.stock.eps[THIS_YEAR]
        eps_next_year = self.stock.eps[THIS_YEAR + 1]

        chg = ((eps_next_year.amount / eps_cur_year.amount) - 1) * 100
        logger.debug("EPS current year: %s\n"
                     "EPS next year: %s\n"
                     "Change: %s%%" % (eps_cur_year, eps_next_year, chg))

        if chg >= -5 and chg <= 5:
            logger.debug("Earning growth change >=-5%%, <=5% => 0 Points")
            points = 0
        elif eps_cur_year < eps_next_year:
            logger.debug("Earning growth change EPS next year > EPS current"
                         " year => 1 Points")
            points = 1
        elif eps_cur_year > eps_next_year:
            logger.debug("Earning growth change EPS next year < EPS current"
                         " year => -1 Points")
            points = -1

        return CriteriaRating(chg, points)

    def _calc_ref_index_comp(self, date):
        # compare quote of stock with the quote of the reference index at the
        # last day of the month
        d = last_weekday_of_month(date)
        prev_month_date = last_weekday_of_month(prev_month(date))

        quote = alphavantage.stock_quote(self.stock.symbol, d)
        prev_quote = alphavantage.stock_quote(self.stock.symbol, prev_month_date)
        q_diff = ((quote / prev_quote) - 1) * 100

        ref_quote = alphavantage.stock_quote(self.reference_index, d)
        prev_ref_quote = alphavantage.stock_quote(self.reference_index,
                                                  prev_month_date)
        ref_q_diff = ((ref_quote / prev_ref_quote) - 1) * 100

        logger.debug("Comparing Stock with reference index. "
                     "(%s vs %s) Stock: %s vs %s = %s%%,"
                     "Ref. Index.: %s vs %s = %s%%" %
                     (d, prev_month_date, quote, prev_quote, q_diff,
                      ref_quote, prev_ref_quote, ref_q_diff))

        return q_diff - ref_q_diff

    def eval_three_month_reversal(self):
        logger.debug("Evaluating 3 month reversal")

        if self.stock.cap_type != Cap.LARGE:
            return CriteriaRating((None, None, None), 0)
        d = prev_month(date.today())
        m1_diff = self._calc_ref_index_comp(d)

        d = prev_month(d)
        m2_diff = self._calc_ref_index_comp(d)

        d = prev_month(d)
        m3_diff = self._calc_ref_index_comp(d)

        if m1_diff > 0 and m2_diff > 0 and m3_diff > 0:
            points = -1
        elif (m1_diff < 0 and m2_diff < 0 and m3_diff < 0):
            points = 1
        else:
            points = 0

        return CriteriaRating((m1_diff, m2_diff, m3_diff), points)

    def eval_momentum(self, points_6month_chg, points_1year_chg):
        if points_6month_chg == 1 and (points_1year_chg <= 0):
            points = 1
        elif points_6month_chg == -1 and (points_1year_chg >= 0):
            points = -1
        else:
            points = 0

        return CriteriaRating((points_6month_chg, points_1year_chg), points)

    def _calc_quite_chg_points(self, chg):
        if chg >= -5 and chg <= 5:
            return 0
        elif chg < -5:
            return -1
        elif chg > 5:
            return 1

    def _eval_quote_chg_daydiff(self, days_diff):
        before_date = closest_weekday(date.today() - timedelta(days=days_diff))
        before_quote = alphavantage.stock_quote(self.stock.symbol, before_date)

        chg = ((float(self.stock.quote.amount) / before_quote) - 1) * 100
        return (chg, self._calc_quite_chg_points(chg))

    def eval_quote_chg_6month(self):
        chg, points = self._eval_quote_chg_daydiff(182)

        return CriteriaRating(chg, points)

    def eval_quote_chg_1year(self):
        chg, points = self._eval_quote_chg_daydiff(365)

        return CriteriaRating(chg, points)

    def _calc_earning_rev_points(self, chg):
        if -5 <= chg <= 5:
            return 0
        elif chg > 5:
            return 1
        elif chg < -5:
            return -1

    def eval_earning_revision(self):
        cur_year_eps = self.stock.eval_earning_revision_cy
        next_year_eps = self.stock.eval_earning_revision_ny

        cur_year_chg = cur_year_eps['Change current Year']
        next_year_chg = next_year_eps['Change next Year']

        cur_year_points = self._calc_earning_rev_points(cur_year_chg)
        next_year_points = self._calc_earning_rev_points(next_year_chg)

        psum = cur_year_points + next_year_points

        if cur_year_points == 0 and next_year_points == 0:
            points = 0
        elif psum >= 1:
            points = 1
        elif psum <= -1:
            points = -1

        return CriteriaRating((cur_year_points, next_year_points), points)

    def eval_quarterly_figures_reaction(self):
        logger.debug("Evaluating stock reaction on"
                     "quarterly figures")
        qf_date = self.stock.last_quarterly_figures_release_date()
        qf_prev_day = prev_weekday(self.stock.last_quarterly_figures_release_date())

        qf_previous_day_quote = alphavantage.stock_quote(self.stock.symbol,
                                                         qf_prev_day)
        qf_day_quote = alphavantage.stock_quote(self.stock.symbol, qf_date)
        qf_reaction = ((qf_day_quote / qf_previous_day_quote) - 1) * 100

        ref_index_quote = alphavantage.stock_quote(self.reference_index, qf_date)
        ref_previous_index_quote = alphavantage.stock_quote(self.reference_index,
                                                            qf_prev_day)
        ref_index_chg = (((ref_index_quote / ref_previous_index_quote) - 1) *
                         100)

        rel_qf_reaction = qf_reaction - ref_index_chg

        logger.debug("Quarterly figure reaction %s vs %s: "
                     "%s: %s vs %s => %s, %s: %s vs %s => %s," %
                     (qf_date, qf_prev_day, self.stock.symbol, qf_day_quote,
                      qf_previous_day_quote, qf_reaction, self.reference_index,
                      ref_index_quote, ref_previous_index_quote,
                      ref_index_chg))

        if rel_qf_reaction >= -1 and rel_qf_reaction < 1:
            logger.debug("Relative Stock reaction to quarterly figure release"
                         " is %s%%" ", >= -1%%, <1%% => 0 Points" %
                         rel_qf_reaction)
            points = 0
        elif rel_qf_reaction >= 1:
            logger.debug("Relative Stock reaction to quarterly figure release"
                         " is %s%%" ", >1%% => 1 Points" % rel_qf_reaction)
            points = 1
        else:
            logger.debug("Relative Stock reaction to quarterly figure release"
                         " is %s%%" ", <-1%% => -1 Points" % rel_qf_reaction)
            points = -1

        return CriteriaRating(rel_qf_reaction, points)

    def eval_analyst_rating(self):

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
            points = -1
        elif score == 3:
            points = 0
        elif score == 4 or score == 5:
            points = 1
        else:
            raise ValueError("Wrong Type")

        if number_of_analysts >= 5:
            points = points * -1

        return CriteriaRating(score, points)

    def eval_five_years_price_earnings_ratio(self):
        per = self.stock.price_earnings_ratio_5year().amount
        logger.debug("Evaluating 5year PER: %s" % (per))

        if per > 0 and per < 12:
            logger.debug("5 year PER <12: 1 Points")
            points = 1
        elif per >= 12 and per <= 16:
            logger.debug("5 year PER >=12, <=16: 0 Points")
            points = 0
        else:
            logger.debug("5 year PER >16: -1 Points")
            points = -1

        return CriteriaRating(per, points)

    def eval_price_earnings_ratio(self):
        per = self.stock.price_earnings_ratio().amount
        logger.debug("Evaluating PER: %s" % (per))

        if per > 0 and per < 12:
            logger.debug("PER <12: 1 Points")
            points = 1
        elif per >= 12 and per <= 16:
            logger.debug("PER >=12, <=16: 0 Points")
            points = 0
        else:
            logger.debug("PER >16: -1 Points")
            points = -1

        return CriteriaRating(per, points)

    def eval_roe(self):
        year = LAST_YEAR
        if year not in self.stock.roe:
            year -= 1
            logger.debug("ROE for year year %s"
                         " not set. Evaluation RoE "
                         " of year %s instead" % (LAST_YEAR, year))
        roe = self.stock.roe[year]

        logger.debug("Evaluating RoE (%s): %s%%" % (year, roe))
        if roe < 10:
            logger.debug("ROE <10%: -1 Points")
            points = -1
        elif roe >= 10 and roe <= 20:
            logger.debug("ROE >=10%, <=20%: 0 Points")
            points = 0
        elif roe > 20:
            logger.debug("ROE >20%: 1 Point")
            points = 1

        return CriteriaRating(roe, points)

    def eval_equity_ratio(self):
        last_year = LAST_YEAR

        if last_year not in self.stock.equity_ratio:
            last_year -= 1
            logger.debug("Equity ratio for year year %s"
                         " not set. Evaluation Equity Ratio"
                         " of year %s instead" % (LAST_YEAR, last_year))

        equity_ratio = self.stock.equity_ratio[last_year]

        logger.debug("Evaluating equity ratio (%s): %s%%" % (last_year,
                                                             equity_ratio))
        if equity_ratio < 15:
            logger.debug("Equity Ratio <10%: -1 Points")
            points = -1
        elif equity_ratio >= 15 and equity_ratio <= 25:
            logger.debug("Equity Ratio >=15%, <=25%: 0 Points")
            points = 0
        elif equity_ratio > 25:
            logger.debug("Equity Ratio >25%: 1 Point")
            points = 1

        return CriteriaRating(equity_ratio, points)

    def eval_ebit_margin(self):
        last_year = LAST_YEAR
        if last_year not in self.stock.ebit_margin:
            last_year -= 1
            logger.debug("Ebit margin for year %s unknown."
                         " Evaluating margin of year %s"
                         " instead" % (LAST_YEAR, last_year))

        ebit_margin = self.stock.ebit_margin[last_year]

        logger.debug("Evaluating EBIT-Margin %s" % ebit_margin)
        if ebit_margin < 6:
            logger.debug("EBIT-Margin <6%: -1 Points")
            points = -1
        elif ebit_margin >= 6 and ebit_margin <= 12:
            logger.debug("EBIT-Margin >=6%, <=12%: 0 Points")
            points = 0
        elif ebit_margin > 12:
            logger.debug("EBIT-Margin >12%: 1 Points")
            points = 1

        return CriteriaRating(ebit_margin, points)

    def save(self, dir=DATA_PATH):
        path = levermann_pickle_path(self.stock.symbol, dir)
        with open(path, "wb") as f:
            pickle.dump(self, f)

    def short_summary_header(self):
        s = ("| {:<25} | {:<14} | {:<14} | {:<6} |".format("Name", "Prev Score (Date)", "Last Score (Date)", "Advise"))
        s += "\n"
        s += "-" * 78
        return s

    def short_summary_footer(self):
        return "-" * 78

    def short_summary(self):
        r = self.evaluation_results[-1]
        r_prev = None
        r_prev_ts = "N/A"
        r_prev_score = "N/A"
        if len(self.evaluation_results) > 1:
            r_prev = self.evaluation_results[-2]
            r_prev_ts = r_prev.timestamp.strftime("%x")
            r_prev_score = r_prev.score

        r_ts = r.timestamp.strftime("%x")

        s = ("| {:<25} | {:<6} ({:<8}) | {:<6} ({:<8}) | {:<6} |".format(self.stock.name, r_prev_score, r_prev_ts, r.score, r_ts, self.recommendation().name))

        return s

    def __str__(self):
        if not self.evaluation_results:
            return "No Analysis exist"

        r = self.evaluation_results[-1]

        s = str(self.stock)
        s += str(r)
        return s

    def recommendation(self):
        if (len(self.evaluation_results) >= 2 and
                (self.evaluation_results[-1].score -
                 self.evaluation_results[-2].score) <= -2):
            return Recommendation.SELL

        if self.stock.cap_type == Cap.LARGE:
            if self.evaluation_results[-1].score <= 2:
                return Recommendation.SELL
            if self.evaluation_results[-1].score >= 4:
                return Recommendation.BUY
            return Recommendation.NONE

        if self.evaluation_results[-1].score <= 4:
            return Recommendation.SELL
        if self.evaluation_results[-1].score >= 7:
            return Recommendation.BUY

        return Recommendation.NONE


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    s = Stock(name="rational")
    # # s.onvista_fundamental_url = "http://www.onvista.de/aktien/Volkswagen-ST-Aktie-DE0007664005"
    # # s.finanzen_net_url = "http://www.finanzen.net/termine/Volkswagen"
    s.update_stock_info()
    leverman = Levermann(stock=s)
    # leverman.evaluate()
    result = leverman.evaluate()[0]
    print(result)

    # print(s)
    # s = Stock(symbol="SIE.DE", isin="DE0007236101")
    # # s.onvista_fundamental_url = "http://www.onvista.de/aktien/Siemens-Aktie-DE0007236101"
    # # s.finanzen_net_url = "http://www.finanzen.net/termine/Siemens"
    # s.update_stock_info()
    # print(s)
    # leverman = Levermann(stock=s)
    # pprint(leverman.evaluate())
    # print(leverman)

    # s2 = Stock("MUV2.DE")
    # s2.onvista_fundamental_url = "http://www.onvista.de/aktien/Muenchener-Rueck-Aktie-DE0008430026"
    # s2.update_stock_info()
