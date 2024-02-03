from src.api_kucoin import kc_api
from src.lib_tool import lib
from pandas import read_csv, DataFrame
from os.path import exists

# DOING rewrite(?) and comment this class
class kucoinAutoBalance:

        # TODO 
        # - DOING comunicate which assets are not tradable on kucoin    ;
        # - TODO use isPairValid 
        # - TODO add security 
        # - TODO add chron
        # - TODO report executed ones
        # 
        # DONE
        # - find the best market on kucoin to trade it                  ; see searchBestTradingPairs()
        # - make the orders                                             ; see kc_api.placeOrder()
        # - you need to check that the assets to buy/sell are on kucoin ; see calcBuyPower()
    
    def __init__(self, wallet: dict, kucoin_api_obj: kc_api, ls_asset: dict = {}, debug_mode: bool = False):
        # load variables, files and settings
        self.wallet = wallet # calculateWalletValue wallet data struct
        self.kc = kucoin_api_obj
        self.debug_mode = debug_mode
        self.config = lib.getConfig() # load config.json file

        ########################################################################
        # Every data structures that are part of the class are defined down here
        self.BUY = 'buy'
        self.SELL = 'sell'
        self.portfolio_pct_wallet = dict(
            # key: asset
            # value: asset value in percentage in the wallet
        )
        self.portfolio_pct_target = lib.loadJsonFile(
            # key: asset
            # value: asset percentage target using: 
            'portfolio_pct.json' # file
        )
        self.min_rebalance_pct = self.portfolio_pct_target['min_rebalance'] # min pct to perform a rebalance
        del self.portfolio_pct_target['min_rebalance']
        self.kc_info = lib.loadJsonFile(
            # load api data (key, secret, passphrase) 
            # and Kucoin settings(
            #       symbol_blacklist: do not buy/sell/getBalance of this symbol, 
            #       tradable_counterpart_whitelist: 
            #               asset allowed to be used as quote currency in trading pairs
            #               e.g. USDC, USDT, BTC ecc
            #     )
            'kc_info.json'
        ) # load necessary files
        self.error = dict(
            # key: symbol to trade, not tradable for every reason
            # value: amount to trade, currency, type ['buy' or 'sell']
            # e.g. {'btc': [150.21, 'EUR', 'sell'], 
            #       'eth': [29.02,  'EUR', 'buy']}
        )
        self.orders = {
            # tot_buy_size is the total amount of self.wallet['currency'] (EUR) that is needed to execute the rebalancing
            # tot_buy_size takes into account also the sell orders
            'tot_buy_size': 0,
            'currency': self.wallet['currency'],
            self.SELL: dict(
                # key: asset
                # value: amount to rebalance according to self.portfolio_pct_target
            ),
            self.BUY: dict(
                # same as sell
            )
        }
        # this 2 data structures will be respctivelly 
        # utilized in executeSellOrders and executeBuyOrders
        self.price_asset2sell = {
            # key: asset
            # value: asset price pulled from KuCoin api
        } 
        self.price_asset2buy = {
            # same as self.price_asset2sell
        }
        self.buy_power = { # self.wallet['currency'] buy power
            'normal': dict(
                # key: asset from self.kc_info['tradable_counterpart_whitelist']
                # value: value denominated in self.wallet['currency] 
            ),
            'sell_orders': dict(
                # same as 'normal'
                # buy power from sell orders, not yet executed
            ),
            'tot_buy_power': 0 # total buy power
        } 
        ########################################################################
        self.handleLS(ls_asset)

    # add value of Liquid Staked Asset to base Asset and 
    # delete the LSA from self.portfolio_pct_wallet, self.wallet['asset']
    #
    # ls_asset has to be from calculateWalletValue.handleLiquidStake()
    def handleLS(self, ls_asset: dict):
        # HANDLE LIQUID STAKED ASSET
        # sum their value to the base token and delete the liquid staked asset from portfolio_pct_wallet
        value_to_add = {}
        for ls, base in ls_asset.items():
            # add as key: base token relative to its liquid stake
            # add as value: 
            #     a list containing:
            #        * liquid stake asset's value
            #        * liquid stake asset's name
            if base.upper() in value_to_add.keys(): 
                value_to_add[base.upper()][0] += self.wallet['asset'][ls.upper()][1]
                value_to_add[base.upper()][1].append(ls.upper())
            else: value_to_add.update({base.upper(): [self.wallet['asset'][ls.upper()][1], [ls.upper()]]})

        to_delete = []
        for (symb, [_, value, _]) in self.wallet['asset'].items():
            # calc each asset weight in the portfolio
            self.portfolio_pct_wallet[symb] = round(value / self.wallet['total_crypto_stable'] * 100, 4)
            if symb in value_to_add.keys(): # if symb has a liquid stake version in the porfolio
                self.portfolio_pct_wallet[symb] += round(value_to_add[symb][0] / self.wallet['total_crypto_stable'] * 100, 4)
                to_delete.extend(value_to_add[symb][1])
                self.wallet['asset'][symb][1] += value_to_add[symb][0]
                # sum its value and delete the ticker
        for symb in to_delete: del self.portfolio_pct_wallet[symb]; del self.wallet['asset'][symb]

    def loadOrders(self):
        for symb in self.wallet['asset'].keys():
            if symb.lower() in self.config['supportedStablecoin']: continue

            # default is set to 0% for every asset, 
            # if symb exist in portfolio_pct_target update it
            expected_pct = 0
            if symb == self.wallet['currency']: 
                # skip if symb is the currency (eur, usd, ecc),  
                # this is an autorebalancer for cryptos
                continue
            if symb in self.portfolio_pct_target:
                expected_pct = self.portfolio_pct_target[symb]
            
            expected_value = expected_pct/100*self.wallet["total_crypto_stable"] 
            actual_value = self.portfolio_pct_wallet[symb]/100*self.wallet["total_crypto_stable"]
            # buy_size is the amount to be sold/bought to rebalance the portfolio
            buy_size = round(expected_value-actual_value, 10)
            buy_size_pct = round(buy_size / self.wallet["total_crypto_stable"] * 100, 10) # buy_size in percentage

            # if order size percentage > minimum rebalance percentage
            if abs(buy_size_pct) >= abs(self.min_rebalance_pct):
                buy_size = abs(buy_size)
                if buy_size_pct < 0:
                    self.orders[self.SELL][symb] = buy_size
                    self.orders['tot_buy_size'] -= buy_size
                else:
                    self.orders[self.BUY][symb] = buy_size
                    self.orders['tot_buy_size'] += buy_size

    def calcBuyPower(self):
        # if eur (or wallet['currency']) is whitelisted to buy assets and it's available on kucoin:
        # add its value to buy power
        if self.wallet['currency'] in self.kc_info['tradable_counterpart_whitelist'] \
            and self.wallet['currency'] in self.wallet['kucoin_asset'].keys(): 
            self.buy_power['normal'][self.wallet['currency']] = self.wallet['kucoin_asset'].pop(self.wallet['currency'].lower())
            self.buy_power['tot_buy_power'] += self.buy_power['normal'][self.wallet['currency']]

        to_delete = [] # if encounter any error delete this item
        for symbol, amount in self.orders[self.SELL].items():
            # for each sell order: check Kucoin availability
            #   calc the available value on KC
            #   check if order amount is less or equal than available one
            #       add it to buy power
            symbol = symbol.lower()
            if symbol in self.wallet['kucoin_asset']:
                asset_price = self.kc.getFiatPrice([symbol])[symbol.upper()] 
                self.price_asset2sell[symbol.upper()] = asset_price
                available_value = self.wallet['kucoin_asset'][symbol] * asset_price
                diff = round(available_value, 10) - round(amount, 10)
                # if the difference between kucoin availble asset and the amount I need to sell to rebalance
                # is equal o greater than 0:
                #           add amount to sell order
                # is less than 0:
                #           add available_value on kucoin and
                #           notify the remaining difference to be deposited / sold
                if diff >= 0:
                    self.buy_power['sell_orders'][symbol.upper()] = amount
                else:
                    self.buy_power['sell_orders'][symbol.upper()] = available_value
                    # FUTURE create the deposit address and show it to deposit it straightaway
                    lib.printFail(f'REBALANCER: deposit {round(diff, 2)} {self.orders["currency"]} worth of {symbol.upper()} to execute SELL order')
                    self.error[symbol] = [amount, self.wallet['currency'], self.SELL]
                    to_delete.append(symbol)
            else: 
                # asset has 0.0 balance on KC
                lib.printFail(f'REBALANCER: deposit {round(amount, 2)} {self.orders["currency"]} worth of {symbol.upper()} to execute SELL order')
                self.error[symbol] = [amount, self.wallet['currency'], self.SELL]
                to_delete.append(symbol)

        for symbol in to_delete: del self.orders[self.SELL][symbol.upper()]

        tradable_asset = set(self.kc_info['tradable_counterpart_whitelist']).intersection([x.upper() for x in self.wallet['kucoin_asset'].keys()])
        # tradable asset is the available asset on Kucoin balance that are also in 'tradable_counterpart_whitelist'
        tradable_asset_kc_price = self.kc.getFiatPrice(list(tradable_asset))
        print(tradable_asset_kc_price)
        # calc the actual buy power on kucoin denominated in self.wallet['currency']
        isAdded = []
        for symbol, price in tradable_asset_kc_price.items():
            isAdded.append(symbol)
            self.price_asset2buy[symbol.upper()] = price
            self.buy_power['normal'][symbol] = price * self.wallet["kucoin_asset"][symbol.lower()] 
            self.buy_power['tot_buy_power'] += self.buy_power['normal'][symbol]

        for symbol in set(self.buy_power['sell_orders'].keys())-set(isAdded): # add the remaining symbols
            self.buy_power['tot_buy_power'] += self.buy_power['sell_orders'][symbol]

        del isAdded
        
        if self.debug_mode: print('calcBuyPower: total buy size:', self.orders['tot_buy_size'], self.orders['currency']) 
        if self.debug_mode: print('calcBuyPower: buy power', self.buy_power)

    def retrieveKCSymbol(self):
        filename = 'kucoin_symbol.csv'
        if exists(filename):
            return read_csv(filename)
        else:
            if not self.kc.getSymbols():
                lib.printFail('Error on retrieving Kucoin symbols...')
                exit()

    # return a list with the best trading pair for each crypto based on side (buy or sell)
    # and eventually a list with missing ones
    def searchBestTradingPairs(self, side): # rewrite to automate everything
        
        # this function return the pair precision using the order of magnitude of subset['baseMinSize']
        def getPairPrecision(subset: DataFrame):
            from math import log, floor
            return abs(floor(log(subset['baseMinSize'].iloc[0], 10)))

        if side not in [self.BUY, self.SELL]:
            return [], []
        
        return_dict = dict()
        missing_list = []
        kucoin_symbol_df = self.retrieveKCSymbol()
        orders = self.orders[self.BUY] if side == self.BUY else self.orders[self.SELL]
        for symbol, amount in orders.items():
            if self.debug_mode: print(f'searchBestTradingPairs: searching pairs to {(side+"ing").upper()}', symbol, 'for', self.wallet['currency'], round(amount, 2))
            temp = [x.upper() for x in self.buy_power['normal'].keys()]
            subset = kucoin_symbol_df[ # in the future, may be it's a good idea to cache this result for every coin
                (kucoin_symbol_df['baseCurrency'] == symbol.upper())
                & (kucoin_symbol_df['enableTrading'] == True)
                & (kucoin_symbol_df['quoteCurrency'].isin(temp))
            ]
            if len(subset) == 0: # coin not found, skipping
                missing_list.append(symbol)
                continue
            
            num_symbol = symbol.upper()
            if len(subset) == 1: # 1 coin found
                pair_precision = getPairPrecision(subset)
                return_dict[symbol] = (f'{num_symbol}-{subset["quoteCurrency"].iloc[0]}', pair_precision)
                continue

            # calc each price subset market pairs
            temp = self.kc.getFiatPrice(subset['baseCurrency'].to_list() + subset['quoteCurrency'].to_list())

            pair_prices = dict()
            for den_symbol, price in temp.items():
                if den_symbol == num_symbol: continue
                pair_prices[f'{num_symbol}-{den_symbol}'] = temp[num_symbol] / price

            # get conversion rate, evaluate them to execute the most convenient trade
            # most of the time the rate will be very similar,
            # if not this is a great deal

            # calc the most convenient, sorting based on value 
            pair_prices = {k: v for k, v in sorted(pair_prices.items(), key=lambda item: item[1])} 
            # search for the minimum price
            if side == self.BUY: 
                best_pair = list(pair_prices.keys())[0]

            # search for the maximum price
            if side == self.SELL: 
                best_pair = list(pair_prices.keys())[-1]
            
            pair_precision = getPairPrecision(subset[subset['quoteCurrency'] == best_pair.split('-')[1]])
            return_dict[symbol] = (best_pair, pair_precision )

        return return_dict, missing_list

    def isPairValid(self, pair: str) -> bool:
        from re import findall
        res = findall('[a-z0-9]{2,8}-[a-z0-9]{2,8}', pair.lower())
        if len(res) == 1:
            return True
        return False

    def getBaseCurrency(self, pair: str) -> str: 
        if self.isPairValid(pair):
            return pair.split('-')[0]
        return ''
    
    def getQuoteCurrency(self, pair: str) -> str: 
        if self.isPairValid(pair):
            return pair.split('-')[1]
        return ''

    # given searchBestTradingPairs result, find out if there's enough
    # liquidity, if not: swap accordingly to self.orders amounts
    def prepareBuyOrders(self):
        # execute intermidiary order to match bestTradingPairs
        # E.G. eth-usdc is the best one
        # you only got usdt, swap usdt->usdc, execute the final order
        available_pairs, not_available = self.searchBestTradingPairs(self.BUY)
        for symbol in not_available:
            self.error[symbol] = [self.orders[self.BUY][symbol], self.wallet['currency'], self.BUY]
            del self.orders[self.BUY][symbol]
            lib.printFail(f'Cannot BUY {symbol.upper()} on Kucoin, no trading pair available!')
        
        for symbol, (pair, _) in available_pairs.items():
            quote_asset_needed = self.getQuoteCurrency(pair)
            quote_asset_available = sorted(self.buy_power['normal'])[-1] # the most liquid available to trade
            # if you already got the liquidity skip to the next one
            if quote_asset_needed == quote_asset_available: continue
            amount = self.orders[self.BUY][symbol] * self.kc.getFiatPrice([quote_asset_available], self.wallet['currency'], False)[quote_asset_available]
            res = self.marketOrder(f'{quote_asset_needed}-{quote_asset_available}', self.BUY, round(amount, 2))
            if res:
                if self.debug_mode: print(f'prepareBuyOrders: swapped {round(amount, 2)} {self.orders["currency"]} worth of {quote_asset_available} to {quote_asset_needed}')
            else:
                if self.debug_mode: print(f'prepareBuyOrders: {pair} not swapped')
        
        # TODO aggregate buy orders and execute the least number of trades
        return available_pairs

    # To execute a market buy for a crypto Y, you need to input
    # the quantity denominated in quote currency (e.g. for ETH-USDC, USDC) so
    # given searchBestTradingPairs result, 
    # execute orders accordingly to self.price_asset2buy prices
    def executeBuyOrders(self):
        available_pairs = self.prepareBuyOrders() # orders unable to execute on KC

        for symbol, amount in self.orders[self.BUY].items():
            if symbol in available_pairs.keys() and symbol not in self.error.keys():
                amount_in_curr = amount
                convert2 = available_pairs[symbol][0].replace(symbol+'-', '')
                # transform 10€ in quote currency e.g. USDC
                amount_in_quote = round(amount_in_curr/self.price_asset2buy[convert2], available_pairs[symbol][1])
                if self.debug_mode: print('executeBuyOrders:', available_pairs[symbol][0], 'BUYING', amount_in_quote, available_pairs[symbol][0].split('-')[1])

                res: bool = self.marketOrder(available_pairs[symbol][0], self.BUY, amount_in_quote)
                if not res:
                    self.error[available_pairs[symbol][0]] = [amount, self.wallet['currency'], self.BUY]
            else: 
                self.error[symbol] = [amount, self.wallet['currency'], self.BUY]
                lib.printFail(f'Cannot BUY {symbol} on Kucoin, no trading pair available!')

    # To execute a market sell for a crypto Y, you need to input
    # the quantity denominated in crypto Y (e.g. 0.01 btc) so
    # given searchBestTradingPairs result, 
    # execute orders accordingly to self.buy_power['tot_buy_power'] amounts
    # and self.price_asset2sell prices
    def executeSellOrders(self):
        # handle 'a', communicate which asset cannot be sold on KC
        available_pairs, not_available = self.searchBestTradingPairs(self.SELL)
        for symbol in not_available:
            self.error[symbol] = [self.orders[self.SELL][symbol], self.wallet['currency'], self.SELL]
            del self.orders[self.SELL][symbol]
            lib.printFail(f'Cannot SELL {symbol.upper()} on Kucoin, no trading pair available!')

        for symbol, amount_in_curr in self.buy_power['sell_orders'].items():
            if symbol in available_pairs.keys():
                # transform 10€ in base currency e.g. BTC
                amount_in_crypto = round(amount_in_curr/self.price_asset2sell[symbol], available_pairs[symbol][1])
                if self.debug_mode: print('executeSellOrders:', available_pairs[symbol][0], 'SELLING', amount_in_crypto, symbol) 

                res = self.marketOrder(available_pairs[symbol][0], self.SELL, amount_in_crypto)
                if not res:
                    self.error[available_pairs[symbol][0]] = [amount_in_curr, self.wallet['currency'], self.SELL]
            else: 
                self.error[symbol] = [amount_in_curr, self.wallet['currency'], self.SELL]
                lib.printFail(f'Cannot SELL {symbol} on Kucoin, no trading pair available!')

    # execute market order
    # e.g. pair: SOL-USDC
    # if side == buy , size must be denominated in quotecurrency e.g. USDC
    # if side == sell, size must be denominated in basecurrency e.g. SOL
    def marketOrder(self, pair, side, size):
        if self.isPairValid(pair):
            orderid: str = self.kc.placeOrder(pair, side, size)
            if len(orderid) > 0:
                return True
        return False

    def run(self):
        self.loadOrders()
        self.calcBuyPower()
        self.executeSellOrders()
        self.executeBuyOrders()
        if self.debug_mode: print('ORDERS not executed', self.error) 
        # after execute everything
        # go back to calcWallet to update walletValue.json