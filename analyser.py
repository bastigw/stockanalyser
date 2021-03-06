# !/usr/bin/env python3

import argparse
import logging

from stockanalyser import logger as colorlog
from stockanalyser.analysis.levermann import Levermann

colorlog.setup_logger()
logger = logging.getLogger(__name__)


def configure_argparse():
    parser = argparse.ArgumentParser(description="Levermann Stock analyser")
    parser.add_argument("-d", "--debug", action='store_true')

    subparsers = parser.add_subparsers()

    # show_parser = subparsers.add_parser("list")
    # show_parser.add_argument("-v", "--verbose", action='store_true')
    # show_parser.add_argument("-o", "--outdated",
    #                          help="show list of stocks with outdated"
    #                               " figure release date", action='store_true')
    # show_parser.set_defaults(func=list)
    #
    # add_parser = subparsers.add_parser("add")
    # add_parser.add_argument("ISIN", help="Stock ISIN")
    # add_parser.set_defaults(func=add)
    #
    # update_parser = subparsers.add_parser("update")
    # update_parser.add_argument("STOCK_SYMBOL", help="Stock Symbol", nargs="?")
    # update_parser.add_argument("-f", "--force", help="enforce update",
    #                            action="store_true")
    # update_parser.set_defaults(func=update)

    # set_parser = subparsers.add_parser("set")
    # set_parser.add_argument("stock_symbol", help="Stock Symbol with"
    #                                              " country ending")
    # set_parser.set_defaults(func=set)

    args = vars(parser.parse_args())

    configure_logger(args.debug)

    if "func" not in args:
        parser.print_help()

    args.func(args)

    # logger.debug("Argparse arguments: %s" % args)
    # if args.add:
    #    add_stock()
    # elif args.show:
    #    show(args.verbose)
    # else:


def configure_logger(debug):
    if debug:
        level = logging.DEBUG
    else:
        level = logging.INFO

    logging.getLogger().setLevel(level)


def show_outdated(levermann_objs):
    outdated = []
    for l in levermann_objs:
        if l.stock._is_quarterly_figures_release_date_outdated():
            outdated.append("%s (%s): %s" %
                            (l.stock.name, l.stock.symbol,
                             l.stock.last_quarterly_figures_release_date()))
    print("For the following stocks the last figure release date is outdated:\n",
          "\n".join(outdated))
    print("-" * 80)


def main(isin):
    if isinstance(isin, list):
        for idx, stock in enumerate(isin, 1):
            # print(idx, stock)
            Levermann(isin=stock)
            logger.info(
                "Finished stock with ISIN: {}! {}/{} stock finished".format(stock, idx, len(isin)))
    elif isinstance(isin, str):
        print("str")
        # Levermann(isin=isin)


if __name__ == "__main__":
    main(isin=["DE0005313704", "DE000CBK1001"])
