#
#   TO PUSH
#  cryptoBalanceReport.retrieveDataFromJson() fixed some issue
#
#                           TO DO
# TODO [main version 2.0]:
#                             DONE [calculateWalletValue] use one file to dump both total and crypto
#                                                         include total_value and crypto_value fields
#                                                         the only one difference between running --crypto and --total 
#                                                         is genPlt()
#                             DONE [calculateWalletValue] add a flag to (do not) see fiat value in genPlt() img output 
#                             DONE [calculateWalletValue] check if cmc key is valid https://coinmarketcap.com/alexandria/article/register-for-coinmarketcap-api  
#                             DONE [calculateWalletValue] add lib.printwarn with privacy settings
#                             DONE [walletBalanceReport] adapt to json changes
#                             DONE [cryptoBalanceReport] adapt to json changes
#                             TODO [new] ? use openAI to give information about cryptocurrency, pricing, trading strategies
#                                        https://openai.com/api/pricing/
#                                        https://beta.openai.com/docs/guides/embeddings/what-are-embeddings
#                             DONE [main] clean and comment new code
#                             TODO [json] merge walletGeneralOverview.json into walletValue.json
#                             TODO [main] clean and comment new code
#
# TODO [walletBalanceReport] add volatility index https://www.youtube.com/watch?v=xzmRQgo8ZXs https://www.youtube.com/watch?v=cXqGMS2HAU0
# TODO [new] get defi vault data https://nanoly.com/api
# TODO [calculateWalletValue] add support for CG api key
# TODO [main] see cmc fiat conversion
#             https://coinmarketcap.com/api/documentation/v1/#operation/getV2ToolsPriceconversion
# TODO [calculateWalletValue] retrieve value of lp position
# TODO [calculateWalletValue] implement address to retrieving balance of crypto

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
