# Features

- save/load stock data from databse
- get stock data (prices, etc) from yahoo or other websites
- recalculate stock rating periodically
- save old stock ratings

## TODO:

- [ ] minimize requests
- [ ] implement nicer code, e.g. property decorators
- [ ] write the documentation
- [ ] if there are no new quarterly figures, use old ones (try to extract
      them from database)
- [ ] add support to update data in database if new information is
      available
- [ ] change argparse to use subcommand e.g: "./stockananalyser add \[-d
      \<SYM\> \<URL\>\]" "./stockananalyser show \[-v -d\]"
- [ ] add a refresh function to CLI, recalculates the score of a saved
      stock and ask for the quarterly figure release date if it makes
      sense
- [ ] show rating of all saved stocks in an overview, show the difference
      between the current and the last calculated store (last calculated
      score should be at least X days old, doesn't make sense to show the
      score that was calculated 20seconds ago to compare it with the
      current one)
- [ ] allow to show data/scores of all stores stocks
- [ ] ask for quarterly release date when showin
- [ ] get current stock quote from onvista page instead of from yahoo

<!-- end list -->

- [ ] \- add CLI:

  - [ ] allow to enter new STocks with symbol
  - [ ] offer to load stock data if it already exist
    - [ ] check which values are outdated and have to be entered again

<!-- end list -->

- [ ] check also main.py with pylint
- [ ] add support for non-Dax Stocks
- [ ] write more tests, ensure functions are also working correctly in
      corner cases (getting quotes on weekend days, year breaks, etc)
- [ ] only ask for stock data that is outdated on the CLI
- [ ] Store portfolio
- [ ] store data in a local or remote database
- [ ] Rename input module, to not clash with the naming of the input()
      function
- [ ] make levermann evaluation threaded to speed it up (YQL queries take
      lot of time)

\- todo: verify, do we also need the timezone for the quarterly figures
release date?? \# could it happen that when the date for the quarterly
figures is in a \# differnt timezone than the stock exchange, that we
compare the wrong \# dates? \# is it ensured that the quarterly figures
are released during the time the \# exchange is open? or could it be
released outside of their opening hours \# and we would have to check
the following day instead?
