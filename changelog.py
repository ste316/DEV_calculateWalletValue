#
#                           TO DO
# TODO [calculateWalletValue] add option to (not) save plt image
# TODO [all] adjust pic size
# TODO [calculateWalletValue] adapt to cg_api changes
# TODO [cryptoBalanceReport] add special keyword to see stablecoin aggretated
# TODO [walletBalanceReport, cryptoBalanceReport] add special keyword to choose date range (ytd ecc)
# TODO [walletBalanceReport, cryptoBalanceReport] add possibility to rerun without exit the program
# TODO [cryptoBalanceReport] implement date range
# TODO [cryptoBalanceReport, walletBalanceReport] implement volatility
# TODO [all] comment new code
# TODO [lib] compare volatility with btc and eth volatility or other crypto index
#            DONE [calculateWalletValue] add report.json support
# TODO [new] watch defillama api https://defillama.com/docs/api
# TODO [new] get defi vault data https://nanoly.com/api
# TODO [calculateWalletValue] add support for CG api key
# TODO [main] see cmc fiat conversion
#             https://coinmarketcap.com/api/documentation/v1/#operation/getV2ToolsPriceconversion
#
#                           CHANGELOG
#  DONE [calculateWalletValue] PLT rename asset with weight < %5 to OTHER 
#  DONE [calculateWalletValue] implement https://www.coingecko.com/api/pricing https://github.com/man-c/pycoingecko to retrieve price
#  DONE [calculateWalletValue] create cronologic wallet value overview with chart and save it as {date}.png
#  DONE [calculateWalletValue] save json file with wallet value over time
#  DONE [main] add path to save file/img to settings.json
#  DONE [new] [walletBalanceReport] create total value report over the time 
#  DONE [walletBalanceReport] select the last one update
#  DONE [new] convert crypto.csv to walletValue.json
#  DONE [main] add optparse D:\python\script\network\change-MAC-addy_OPT_PARSE
#  DONE [calculateWalletValue] add option: crypto and total balance
#  DONE [walletBalanceReport] add support for D:\crypto\walletGeneralOverview.json
#  DONE [main] gen plt from settings['json_path'] file
#  DONE [main] improve grafic of plt
#             https://towardsdatascience.com/a-simple-guide-to-beautiful-visualizations-in-python-f564e6b9d392
#  DONE [main] clean and comment new code
#  DONE [main] publish on github 
#  DONE [github] add image of pie chart
#  DONE [github] rewrite README.md
#  DONE [github] add wallet to donate
#  DONE [new] [cryptoBalanceReport] add crypto balance(btc, eth) report over time
#  DONE [cryptoBalanceReport, walletBalanceReport] improve date managment
#  DONE [main] refactor and comment code
#  DONE [calculateWalletValue] add alternative api
#                              https://coinmarketcap.com/api/pricing/
#                              https://coinmarketcap.com/api/documentation/v1/#operation/getV1CryptocurrencyListingsLatest
#  DONE [calculateWalletValue] implement cmc api
#  DONE [calculateWalletValue] fix calc total using CMC
#  DONE [cryptoBalanceReport] add fiat value of a single crypto over time
#  DONE [cryptoBalanceReport] divide into 2 subplots to show fiat value and amount together
#                            https://stackoverflow.com/questions/14762181/adding-a-y-axis-label-to-secondary-y-axis-in-matplotlib
#  DONE [calculateWalletValue] [crypto] add percentage increase/decrease on total spent and total value
#                                      https://www.omnicalculator.com/math/percentage-increase
# DONE [calculateWalletValue] use one file to dump both total and crypto
#                             include total_value and crypto_value fields
#                             the only one difference between running --crypto and --total 
#                             is genPlt()
# DONE [calculateWalletValue] add a flag to do (not) see fiat value in genPlt() img output 
# DONE [calculateWalletValue] check if cmc key is valid https://coinmarketcap.com/alexandria/article/register-for-coinmarketcap-api  
# DONE [walletBalanceReport] adapt to json changes
# DONE [cryptoBalanceReport] adapt to json changes

# DONE [lib] rewrite log logic, add ASK_USER_INPUT color
# DONE [lib] add see portfolio in a date range
# DONE [lib] add volatility index
# DONE [walletBalanceReport] implement date range
# DONE [cg_api] reduce time to get response from CoinGecko api
# DONE [main] move updateJson() from main.py to lib.py
# DONE [lib] improve updateJson() logic, add more use cases
# DONE [api] move cg_api.cachedSymbol to an external json and load it
# DONE [calculateWalletValue] add stablecoin percentage in crypto img
# DONE [calculateWalletValue] fix stablecoin percentage in total calc
# DONE [api][cg_api] fix error 429 coingecko, make onerequest with all id