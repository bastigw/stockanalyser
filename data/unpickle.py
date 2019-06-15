import pickle
from stockanalyser.stock import Stock, Cap
from database import aktien_data_jaehrlich
from stockanalyser.analysis import levermann

with open(r'./leg.de.pickle', 'rb') as input_file:
    data = pickle.load(input_file)

l = levermann.Levermann(data)
l.evaluate()
print(l)
# aktien_data_jeahrlich.save_yearly(data)
# var = aktien_data_jeahrlich.row_get(1, 2018)

# print(var)

# var = "{:.2f}".format(-5)
# print(var)
# print(type(var))

# for index, (elem, elem_data) in enumerate(data.symbols.items()):
#     if elem_data.exchangeDisplay == "Germany":
#         # if "rational" in elem_data.name.lower():
#             print(elem_data)
# print(index)

# print(data)

#
# def save_yearly(stock_object):
#     aktie_id = 1
#     # aktie_id = aktieninformation.read_value("aktie_id", stock_object.ISIN)
#     eps = stock_object.eps
#     quarterly_figure_dates = stock_object.quarterly_figure_dates
#     ebit = stock_object.ebit_margin
#     roe = stock_object.roe
#     equity_ratio = stock_object.equity_ratio
#     all_data = []
#     data_sql = {'jahr': None,
#                 'q1': None,
#                 'q2': None,
#                 'q3': None,
#                 'q4': None,
#                 'aktie': None,
#                 'ebit': None,
#                 'eigenkapitalquote': None,
#                 'kgv': None,
#                 'return_on_equity': None,
#             }
#
#     for year, value in eps.items():
#         for keys in data_sql.keys():
#             data_sql[keys] = None
#         data_sql['jahr'] = year
#         data_sql['aktie'] = aktie_id
#         # data_sql['kgv'] = value.amount
#         if year in ebit.keys():
#             data_sql['ebit'] = ebit[year]
#         if year in roe.keys():
#             data_sql['return_on_equity'] = roe[year]
#         if year in equity_ratio.keys():
#             data_sql['eigenkapitalquote'] = equity_ratio[year]
#
#         quarterly_figure_dates.sort()
#         this_year_quarterly = []
#         for elem in quarterly_figure_dates:
#             if year == elem.year:
#                 this_year_quarterly.append(elem)
#         for idx, elem in enumerate(this_year_quarterly[::-1]):
#             data_sql['q'+str(4-idx)] = elem.strftime("%Y-%m-%d %H:%M:%S")
#         # print(this_year_quarterly)
#
#         all_data.append(data_sql.copy())
#     return all_data
#
#
# yearly = save_yearly(data)
# # print(yearly)
# for elem in yearly:
#     print(elem)
# # database.aktieninformation.insert_data(data)
