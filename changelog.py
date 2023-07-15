#
#                           TO DO
# TODO [calculateWalletValue] implement volatility (Realized Volatility)
#                             https://whynance.medium.com/use-python-to-estimate-your-portfolios-volatility-eee22d1a37db 
#                             https://www.learnpythonwithrune.org/calculate-the-volatility-of-historic-stock-prices-with-pandas-and-python/
# TODO [calculateWalletValue] store multiple record on walletValue.json for the same day
#                            ? change walletValue format to csv ? or change to sql db ?
#                            TODO [calculateWalletValue] --load display the last record per day
# TODO [lib] compare portfolio volatility with btc and eth volatility or other crypto index
#            DONE [calculateWalletValue] add report.json support
# TODO [new] add notification on discord/other messaging platform
#            TODO [new] add buy price, send alert to buy when condition meets
# TODO [calculateWalletValue] show liquid staked asset converted as underline asset, es. convert mSol and sum it to Sol
# TODO [api] fix AttributeError: 'list' object has no attribute 'keys', line 49 convertSymbol2ID (coingecko)
# TODO [main] fix arg parser logic for param: --calc --load ('--total' | '--crypto') to run genPltFromJson() with specified type
# TODO [new] airdrop tracker, Track staked tokens
# TODO [cg_api_n, cmc_api] add timeout to requests https://datagy.io/python-requests-timeouts/
# TODO [calculateWalletValue] add boolean option in settings.json to aggregate stable coins in genPlt()
# TODO [cryptoBalanceReport] add special keyword to see stablecoin aggretated
# TODO [walletBalanceReport] add increment percentage of a certain period
# TODO [walletBalanceReport, cryptoBalanceReport] add special keyword to choose date range (ytd ecc)
# TODO [cryptoBalanceReport, walletBalanceReport] implement volatility
# TODO [calculateWalletValue] uniform symbol str structure( all lower )
# TODO [calculateWalletValue] fix handleDataPlt when one asset is a major % of self.wallet['total_crypto_stable']
# TODO [all] comment new code
# TODO [new] watch defillama api https://defillama.com/docs/api
# TODO [new] get defi vault data https://nanoly.com/api
# TODO [calculateWalletValue] add support for CG api key


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
# DONE [calculateWalletValue] adjust pic size
# DONE [api][cg_api] fix getPriceOf() to return the correct item
# DONE [calculateWalletValue] adapt to cg_api changes
# DONE [calculateWalletValue] fix json file naming, handling
# DONE [calculateWalletValue] add option to (not) save plt image
# DONE [walletBalanceReport, cryptoBalanceReport] add possibility to rerun without exit the program
# DONE [lib] add getConfig, add getUserInput, improved leggibility getIndexOfDate, modify getUserInputDate to use getUserInput
# DONE [calculateWalletValue, walletBalanceReport, cryptoBalanceReport] add external config
# DONE [walletBalanceReport, cryptoBalanceReport] fix rerun process
# DONE [lib] fix getUserInputDate, function nested in a while True
# DONE [cryptoBalanceReport] implement date range
# DONE [calculateWalletValue] change internal structure of self.wallet
#                             { crypto: [[symbol,qta,value, ('crypto' | 'stable' | 'fiat')],] , total_invested: 0, currency: ''}
# DONE [calculateWalletValue] adapt to self.wallet changes
# DONE [calculateWalletValue] add function to get asset list from self.wallet
# DONE [all] add input checks and file setup for first run
