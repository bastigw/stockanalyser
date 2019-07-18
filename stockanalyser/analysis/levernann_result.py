import datetime
import logging

from stockanalyser.database import database_interface

logger = logging.getLogger(__name__)


class LevermannResult(object):
    def __init__(self, name, isin):
        logger.info("Initializing {}".format(type(self).__name__))
        self.timestamp = datetime.datetime.now()
        self.name = name
        self.isin = isin

        self.roe = None
        self.ebit_margin = None
        self.equity_ratio = None
        self.price_earnings_ratio = None
        self.five_years_price_earnings_ratio = None
        self.analyst_rating = None
        self.quarterly_figures_reaction = None
        self.earning_revision = None
        self.quote_chg_6month = None
        self.quote_chg_1year = None
        self.momentum = None
        self.three_month_reversal = None
        self.earning_growth = None
        self._score = None

        self.THIS_YEAR = datetime.date.today().year

    def __str__(self):
        s = "{:<35} {:<25}\n".format("Last Evaluation Date:", "%s" % self.timestamp)
        s += "\n"
        s = "{:<35} {:<25}\n".format("Analysed Stock", "{}".format(self.name))
        s += "\n"
        s += "{:<35} {:<25} | {} Points\n".format(
            "RoE:", "%s%%" % self.roe.value, self.roe.points
        )
        s += "{:<35} {:<25} | {} Points\n".format(
            "Equity Ratio:", "%s%%" % self.equity_ratio.value, self.equity_ratio.points
        )
        s += "{:<35} {:<25} | {} Points\n".format(
            "EBIT Margin:", "%s%%" % self.ebit_margin.value, self.ebit_margin.points
        )
        s += "{:<35} {:<25} | {} Points\n".format(
            "%s vs. %s Earning growth:" % (self.THIS_YEAR, self.THIS_YEAR + 1),
            "%.2f%%" % self.earning_growth.value,
            self.earning_growth.points,
        )
        if type(self.three_month_reversal.value) is tuple:
            if self.three_month_reversal.value[::-1][0]:
                s += "{:<35} {:<25} | {} Points\n".format(
                    "3 month reversal:",
                    "%.2f%%, %.2f%%, %.2f%%" % self.three_month_reversal.value[::-1],
                    self.three_month_reversal.points,
                )
        s += "{:<35} {:<25} | {} Points\n".format(
            "Stock momentum (6m, 1y chg points):",
            "%s Points, %s Points" % self.momentum.value,
            self.momentum.points,
        )
        s += "{:<35} {:<25} | {} Points\n".format(
            "6 month quote movement:",
            "%.2f%%" % self.quote_chg_6month.value,
            self.quote_chg_6month.points,
        )
        s += "{:<35} {:<25} | {} Points\n".format(
            "1 year quote movement:",
            "%.2f%%" % self.quote_chg_1year.value,
            self.quote_chg_1year.points,
        )
        s += "{:<35} {:<25} | {} Points\n".format(
            "Earning revisions (6m, 1y points):",
            "%s Points, %s Points" % self.earning_revision.value,
            self.earning_revision.points,
        )
        s += "{:<35} {:<25} | {} Points\n".format(
            "Quarterly figures release reaction:",
            "%.2g%%" % self.quarterly_figures_reaction.value,
            self.quarterly_figures_reaction.points,
        )
        s += "{:<35} {:<25} | {} Points\n".format(
            "MarketScreener analyst rating",
            str(self.analyst_rating.value or ""),
            self.analyst_rating.points,
        )
        s += "{:<35} {:<25.2f} | {} Points\n".format(
            "Price earnings ratio",
            self.price_earnings_ratio.value,
            self.price_earnings_ratio.points,
        )
        s += "{:<35} {:<25.2f} | {} Points\n".format(
            "5y price earnings ratio",
            self.five_years_price_earnings_ratio.value,
            self.five_years_price_earnings_ratio.points,
        )
        s += "\n"

        s += "{:<35} {:<25} | {} Points\n".format(
            "Total Levermann Score:", "", self.score
        )
        return s

    @property
    def score(self) -> int:
        if self._score is None:
            self._score = (
                self.roe.points
                + self.equity_ratio.points
                + self.ebit_margin.points
                + self.earning_growth.points
                + self.three_month_reversal.points
                + self.momentum.points
                + self.quote_chg_6month.points
                + self.quote_chg_1year.points
                + self.earning_revision.points
                + self.quarterly_figures_reaction.points
                + self.analyst_rating.points
                + self.five_years_price_earnings_ratio.points
                + self.price_earnings_ratio.points
            )
        return self._score

    def save_points(self) -> int:
        """
        Saves points to database
        :return: amount of changed lines
        """
        lines_changed = database_interface.save_points(self)
        return lines_changed
