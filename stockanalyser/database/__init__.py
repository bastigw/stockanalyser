"""Database package

Main File: Database_Interface_

Database must be created locally. Database is not shipped with this project.
Database straucture and shema can be found in individual file.

Four Tables are used to Store the data:

+------------------------------------------------------------------------------------------------------------------------------+
|                                                       Tables                                                                 |
+=======================+======================================================================================================+
| Aktieninformation_    | is used for storing never changing data such as aktie_id, urls, isin, symbol, name, etc.             |
|                       |                                                                                                      |
|                       |                                                                                                      |
|                       |                                                                                                      |
|                       |                                                                                                      |
+-----------------------+------------------------------------------------------------------------------------------------------+
| AktienDataJaehrlich_  | is used for storing yearly data such as ebit (Earning before interests and taxes),                   |
|                       | roe  (Return on Equity), per (Price Earning Ratio), etc.                                             |
|                       |                                                                                                      |
|                       |                                                                                                      |
+-----------------------+------------------------------------------------------------------------------------------------------+
| AktieLevermannValues_ | is used for storing values of each analysis such as quarterly figures reaction, analyst              |
|                       | ratings, momentum, 6 and 12 month price-change, etc. For complete Levermann Score explanation visit: |
|                       | Levermann-Score_                                                                                     |
|                       |                                                                                                      |
|                       |                                                                                                      |
+-----------------------+------------------------------------------------------------------------------------------------------+
| AktieLevermannResult_ | is used for storing points of analysis. Contains all points form analysis as -1, 0 or 1 and the      |
|                       | sum of points. With the sum of the points you can evaluate the recommendation.                       |
|                       |                                                                                                      |
|                       |                                                                                                      |
|                       |                                                                                                      |
+-----------------------+------------------------------------------------------------------------------------------------------+



.. _Database_Interface: database.html#database.database_interface
.. _Aktieninformation: database.html#module-database.aktieninformation
.. _AktienDataJaehrlich: database.html#module-database.aktien_data_jaehrlich
.. _AktieLevermannValues: database.html#module-database.aktie_levermann_values
.. _AktieLevermannResult: database.html#module-database.aktie_levermann_result
.. _levermann-score: https://levermann24.com/levermann-strategie/?lang=en


"""
