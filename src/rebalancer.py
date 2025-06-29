try:
    from src.api_kucoin import kc_api
    from src.lib_tool import lib
except:
    from api_kucoin import kc_api
    from lib_tool import lib

from pandas import read_csv, DataFrame
from os.path import exists
from os.path import join
from os import getcwd
from math import ceil, floor, log
from pydantic import BaseModel, validator
from typing import Dict, Union, Literal

# Define the allowed execution modes
ExecutionMode = Literal['simulation', 'interactive', 'yolo']

class PriceAsset(BaseModel):
    """Model for price_asset2sell and price_asset2buy"""
    # key: asset, value: price from KuCoin API
    data: Dict[str, float]

class BuyPower(BaseModel):
    normal: Dict[str, float]  # key: asset from tradable_counterpart_whitelist, value: denominated in currency
    sell_orders: Dict[str, float]
    tot_buy_power: float = 0

class Orders(BaseModel):
    tot_buy_size: float = 0
    currency: str
    sell: Dict[str, float]  # key: asset, value: amount to rebalance
    buy: Dict[str, float]   # key: asset, value: amount to rebalance

class Error(BaseModel):
    """Model for tracking failed trades"""
    # key: symbol, value: [amount, currency, type]
    failed_trades: Dict[str, list[Union[float, str, Literal['buy', 'sell']]]]  

# DOING rewrite(?) and comment this class
class kucoinAutoBalance:

    # - TODO prepareBuyOrders: split the function into smaller, more controllable pieces
    # - TODO log everything to debug later
    # - TODO portfolio_pct.json field permit ',' to aggregate some asset in pct
    # - TODO comunicate which assets are not tradable on kucoin
    # - TODO add chron
    # - TODO report executed ones
    # - TODO add support for LSA to --ca --json load command             
    # 
    # DONE
    # - find the best market on kucoin to trade it                  ; see searchBestTradingPairs()
    # - make the orders                                             ; see kc_api.placeOrder()
    # - you need to check that the assets to buy/sell are on kucoin ; see calcBuyPower()
    # - first define the expected value, second calc the difference between actual and expected value
    # - check if there's crypto on funding -> move it on trading 
    # - use isPairValid 
    # - check prepareBuyOrder logic, not pre-swap if you already got the right token
    # - prepareBuyOrder, swap only needed amount
    # - check symbol_blacklist also when buy/sell
    # - enable to add new tokens
    # - fix increment for buy/sell sizes
    
    def __init__(self, wallet: dict, kucoin_api_obj: kc_api, execution_mode: ExecutionMode, ls_asset: dict = {}, debug_mode: bool = False):
        # load variables, files and settings
        self.wallet = wallet # calculateWalletValue wallet data struct
        self.kc = kucoin_api_obj
        self.debug_mode = debug_mode
        self.config = lib.getConfig() # load config.json file
        self.settings = lib.getSettings()

        # --- Execution Mode Set Directly --- 
        self.execution_mode = execution_mode
        lib.printWarn(f"Rebalancer initialized with mode: '{self.execution_mode}'") # Info log
        # Remove the logic that reads from settings and validates here
        # It's now handled by the caller (calculateWalletValue)
        # --- End Execution Mode Logic ---
        
        ########################################################################
        # Every data structures that are part of the class are defined down here
        self.BUY = 'buy'
        self.SELL = 'sell'
        self.portfolio_pct_wallet: Dict[str, float] = {}  # key: asset, value: percentage in wallet
        
        portfolio_pct = lib.loadJsonFile('portfolio_pct.json')
        self.min_rebalance_pct = portfolio_pct['min_rebalance'] # min pct to perform a rebalance
        self.portfolio_pct_target = {k: v for k, v in portfolio_pct.items() if k != 'min_rebalance'}
        
        # load api data (key, secret, passphrase) 
        # and Kucoin settings(
        #       symbol_blacklist: do not buy/sell/getBalance of this symbol, 
        #       tradable_counterpart_whitelist: 
        #               asset allowed to be used as quote currency in trading pairs
        #               e.g. USDC, USDT, BTC ecc
        #     )
        self.kc_info = lib.loadJsonFile('kc_info.json')
        
        # key: symbol to trade, but not tradable for every reason
        # value: amount to trade, currency, type ['buy' or 'sell']
        # e.g. {'btc': [150.21, 'EUR', 'sell'], 
        #       'eth': [29.02,  'EUR', 'buy']}
        self.error = Error(failed_trades={})
        
        self.orders = Orders(
            # tot_buy_size is the total amount of self.wallet['currency'] (EUR) that is needed to execute the rebalancing
            # tot_buy_size takes into account also the sell orders
            tot_buy_size=0,
            currency=self.wallet['currency'],
            sell={},
            buy={}
        )
        
        # this 2 data structures will be respctivelly 
        # utilized in executeSellOrders and executeBuyOrders
            # key: asset
            # value: asset price pulled from KuCoin api
        self.price_asset2sell = PriceAsset(data={})
        self.price_asset2buy = PriceAsset(data={})
        
        self.buy_power = BuyPower(
            normal={
                # key: asset from self.kc_info['tradable_counterpart_whitelist']
                # value: value denominated in self.wallet['currency] 
            },
            sell_orders={
                # same as 'normal'
                # buy power from sell orders, not yet executed
            },
            tot_buy_power=0
        )
        ########################################################################
        self.getActualPct()

    # get actual wallet asset percentage
    def getActualPct(self):
        for symb, value in self.wallet['asset'].items():
            # calc each asset weight in the portfolio
            self.portfolio_pct_wallet[symb] = round(value / self.wallet['total_crypto_stable'] * 100, 4) / 100

    # get target wallet asset value
    def getExpextedValues(self) -> dict:
        expected_value = dict()
        for symbol, value in self.portfolio_pct_target.items():
            expected_value[symbol] = value/100 * self.wallet['total_crypto_stable']

        return expected_value

    def loadOrders(self):
        wallet_expected_value = self.getExpextedValues()
        
        # Find coins that are in wallet_expected_value but not in current wallet
        new_coins = set(wallet_expected_value.keys()) - set(self.wallet['asset'].keys())
        
        # Process new coins first
        for symb in new_coins:
            # Skip stablecoins and blacklisted symbols
            if symb.lower() in self.config['supportedStablecoin'] or \
               symb.upper() in self.kc_info['symbol_blacklist']: 
                continue
            
            buy_size = wallet_expected_value[symb]
            buy_size_pct = round(buy_size / self.wallet["total_crypto_stable"] * 100, 10)
            
            # if order size percentage > minimum rebalance percentage
            if abs(buy_size_pct) >= abs(self.min_rebalance_pct):
                self.orders.buy[symb] = buy_size
                self.orders.tot_buy_size += buy_size

        # Process existing assets in the wallet
        for symb in self.wallet['asset'].keys():
            # Skip stablecoins and blacklisted symbols
            if symb.lower() in self.config['supportedStablecoin'] or \
               symb.upper() in self.kc_info['symbol_blacklist']: 
                continue

            if symb in wallet_expected_value:
                expected_value = wallet_expected_value[symb]
            else:
                expected_value = 0
            
            actual_value = self.portfolio_pct_wallet[symb]*self.wallet["total_crypto_stable"]
            # buy_size is the amount to be sold/bought to rebalance the portfolio
            buy_size = round(expected_value-actual_value, 10)
            buy_size_pct = round(buy_size / self.wallet["total_crypto_stable"] * 100, 10) # buy_size in percentage

            # if order size percentage > minimum rebalance percentage
            if abs(buy_size_pct) >= abs(self.min_rebalance_pct):
                buy_size = abs(buy_size)
                if buy_size_pct < 0:
                    self.orders.sell[symb] = buy_size
                    self.orders.tot_buy_size -= buy_size
                else:
                    self.orders.buy[symb] = buy_size
                    self.orders.tot_buy_size += buy_size

    # calc buy power take into account:
    #   - availlable liquidity on kc (e.g. usdc, usdt)
    #   - every coin that should be sold
    def calcBuyPower(self):
        # if eur (or wallet['currency']) is whitelisted to buy assets and it's available on kucoin:
        # add its value to buy power
        if self.wallet['currency'] in self.kc_info['tradable_counterpart_whitelist'] \
            and self.wallet['currency'] in self.wallet['kucoin_asset'].keys(): 
            self.buy_power.normal[self.wallet['currency']] = self.wallet['kucoin_asset'].pop(self.wallet['currency'].lower())
            self.buy_power.tot_buy_power += self.buy_power.normal[self.wallet['currency']]

        to_delete = [] # if encounter any error delete this item
        for symbol, amount in self.orders.sell.items():
            # Skip blacklisted symbols
            if symbol.upper() in self.kc_info['symbol_blacklist']:
                self.error.failed_trades[symbol.upper()] = [amount, self.wallet['currency'], self.SELL]
                to_delete.append(symbol)
                lib.printFail(f'REBALANCER: Cannot sell {symbol.upper()} - symbol is blacklisted')
                continue

            # for each sell order: check Kucoin availability
            #   calc the available value on KC
            #   check if order amount is less or equal than available one
            #       add it to buy power
            symbol = symbol.lower()
            if symbol in self.wallet['kucoin_asset']:
                asset_price = self.kc.getFiatPrice([symbol])[symbol.upper()] 
                self.price_asset2sell.data[symbol.upper()] = asset_price
                available_value = self.wallet['kucoin_asset'][symbol] * asset_price
                diff = round(available_value, 10) - round(amount, 10)
                # if the difference between kucoin availble asset and the amount I need to sell to rebalance
                # is equal o greater than 0:
                #           add amount to sell order
                # is less than 0:
                #           add available_value on kucoin and
                #           notify the remaining difference to be deposited / sold
                if diff >= 0:
                    self.buy_power.sell_orders[symbol.upper()] = amount
                else:
                    if available_value >= 1:
                        self.buy_power.sell_orders[symbol.upper()] = available_value
                        
                        partial_sell = amount - available_value
                        lib.printFail(f'{symbol.upper()} will be sold for a partial amount of {partial_sell}')
                        self.error.failed_trades[symbol.upper()] = [partial_sell, self.wallet['currency'], self.SELL]
                    else:
                        self.error.failed_trades[symbol.upper()] = [amount, self.wallet['currency'], self.SELL]
                        to_delete.append(symbol)
                        # FUTURE TODO create the deposit address and show it to deposit straightaway
                        lib.printFail(f'REBALANCER: deposit {round(abs(diff), 2)} {self.orders.currency} worth of {symbol.upper()} to execute SELL order')
                    
                # if amount_in_curr <= 1:
                #    self.error[symbol] = [amount_in_curr, self.wallet['currency'], self.SELL]
                #    lib.printFail(f'Cannot SELL {symbol} on Kucoin, deposit more liquidity!')
            else: 
                # asset has 0.0 balance on KC
                lib.printFail(f'REBALANCER: deposit {round(amount, 2)} {self.orders.currency} worth of {symbol.upper()} to execute SELL order')
                self.error.failed_trades[symbol] = [amount, self.wallet['currency'], self.SELL]
                to_delete.append(symbol)

        for symbol in to_delete: del self.orders.sell[symbol.upper()]

        tradable_asset = set(self.kc_info['tradable_counterpart_whitelist']).intersection([x.upper() for x in self.wallet['kucoin_asset'].keys()])
        if len(tradable_asset) == 0:
            # no tradable asset
            # if you request getFiatPrice with an empty list, it will return all symbols, also the ones you do not have in the account
            return

        # tradable asset is the available asset on Kucoin balance that are also in 'tradable_counterpart_whitelist'
        tradable_asset_kc_price = self.kc.getFiatPrice(list(tradable_asset))
        # calc the actual buy power on kucoin denominated in self.wallet['currency']
        isAdded = []
        for symbol, price in tradable_asset_kc_price.items():
            isAdded.append(symbol)
            self.price_asset2buy.data[symbol.upper()] = price
            self.buy_power.normal[symbol] = price * self.wallet["kucoin_asset"][symbol.lower()] 
            self.buy_power.tot_buy_power += self.buy_power.normal[symbol]

        for symbol in set(self.buy_power.sell_orders.keys())-set(isAdded): # add the remaining symbols
            self.buy_power.tot_buy_power += self.buy_power.sell_orders[symbol]

        del isAdded
        
        if self.debug_mode: print('calcBuyPower: total buy size:', self.orders.tot_buy_size, self.orders.currency) 
        if self.debug_mode: print('calcBuyPower: buy power', self.buy_power)

    def retrieveKCSymbol(self, force_update: bool = False):
        filename = join(getcwd(), 'cache','kucoin_symbol.csv')
        if not exists(filename) or force_update:
            if not self.kc.getSymbols():
                lib.printFail('Error on retrieving Kucoin symbols...')
                exit()
        
        return read_csv(filename)

    # return a list with the best trading pair for each crypto based on side (buy or sell)
    # and eventually a list with missing ones
    def searchBestTradingPairs(self, side): # rewrite to automate everything
        def getIsSell(side: str) -> bool:
            return True if side==self.SELL else False

        # this function return the pair precision using the order of magnitude of subset['baseMinSize']
        def getPairPrecision(subset: DataFrame, side: str):
            if getIsSell(side):
                increment = subset['baseIncrement'].iloc[0]
            else:
                increment = subset['quoteIncrement'].iloc[0]
            
            from math import log, floor
            return abs(floor(log(increment, 10)))

        if side not in [self.BUY, self.SELL]:
            return [], []
        
        return_dict = dict()
        missing_list = []
        kucoin_symbol_df = self.retrieveKCSymbol(force_update=True)
        orders = self.orders.buy if side == self.BUY else self.orders.sell
        for symbol, amount in orders.items():
            if self.debug_mode: print(f'searchBestTradingPairs: searching pairs to {(side+"ing").upper()}', symbol, 'for', self.wallet['currency'], round(amount, 2))
            temp = [x.upper() for x in self.buy_power.normal.keys()]
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
                pair_precision = getPairPrecision(subset, side)
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
            
            pair_precision = getPairPrecision(subset[subset['quoteCurrency'] == best_pair.split('-')[1]], side)
            return_dict[symbol] = (best_pair, pair_precision )

        return return_dict, missing_list

    def isPairValid(self, pair: str) -> bool:
        from re import findall
        res = findall('[a-z0-9]{1,8}-[a-z0-9]{1,8}', pair.lower())
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
        
        # Check for blacklisted symbols first
        for symbol in self.orders.buy.copy():
            if symbol.upper() in self.kc_info['symbol_blacklist']:
                self.error.failed_trades[symbol] = [self.orders.buy[symbol], self.wallet['currency'], self.BUY]
                del self.orders.buy[symbol]
                lib.printFail(f'PREPARE_BUY: Cannot buy {symbol.upper()} - symbol is blacklisted')

        for symbol in not_available:
            self.error.failed_trades[symbol] = [self.orders.buy[symbol], self.wallet['currency'], self.BUY]
            del self.orders.buy[symbol]
            lib.printFail(f'PREPARE_BUY: Cannot BUY {symbol.upper()} on Kucoin, no trading pair available!')
        
        most_liq_asset = sorted(self.buy_power.normal)
        prepare_order = dict() # this will contain the order that are needed to prepare the final swap
        for symbol, (pair, _) in available_pairs.items():
            quote_asset_needed = self.getQuoteCurrency(pair)
            
            # Convert EUR amount to quote currency amount (same pattern as executeBuyOrders)
            amount_quote_asset_needed = self.orders.buy[symbol] / self.price_asset2buy.data[quote_asset_needed]
            if quote_asset_needed in most_liq_asset:
                amount_quote_asset_available = self.wallet["kucoin_asset"][quote_asset_needed.lower()]
                
                if amount_quote_asset_available < amount_quote_asset_needed:
                    # you need more liquidity
                    # find a tradable token with enough counter value
                    quote_asset_available = ''
                    # get all available without the needed (now we are searching for a token to be swapped to the needed)
                    rest_of_available = [item for item in most_liq_asset if item != quote_asset_needed]
                    for avail_asset in rest_of_available:
                        # need to be tested
                        # take the amout of a token, multiply it by its value
                        # compare it to the value needed (converted back to EUR for comparison)
                        avail_liquidity_value = self.wallet['kucoin_asset'][avail_asset.lower()] * self.kc.getFiatPrice([avail_asset], self.wallet['currency'], False)[avail_asset]
                        amount_quote_asset_needed_eur = amount_quote_asset_needed * self.price_asset2buy.data[quote_asset_needed]
                        if avail_liquidity_value >= amount_quote_asset_needed_eur:
                            quote_asset_available = avail_asset

                    if quote_asset_available == '':
                        # if no token were found, this trade can't be made
                        self.error.failed_trades[symbol] = [self.orders.buy[symbol], self.wallet['currency'], self.BUY]
                        del self.orders.buy[symbol]
                        lib.printFail(f'PREPARE_BUY: Cannot buy {symbol.upper()} on Kucoin, there\'s no token with enought liquidity to make the swap')
                        continue
                    
                    # Convert quote asset needed to base asset amount for the swap
                    # amount_quote_asset_needed is already in quote currency, convert to base currency for swap
                    quote_asset_available_price = self.kc.getFiatPrice([quote_asset_available], self.wallet['currency'], False)[quote_asset_available]
                    amount = ceil(amount_quote_asset_needed * self.price_asset2buy.data[quote_asset_needed] / quote_asset_available_price) - self.wallet['kucoin_asset'][quote_asset_needed.lower()]
                    pair = f'{quote_asset_available}-{quote_asset_needed}'
                    if pair not in prepare_order:
                        prepare_order[pair] = amount
                    else:
                        prepare_order[pair] += amount 
            else:
                self.error.failed_trades[symbol] = [self.orders.buy[symbol], self.wallet['currency'], self.BUY]
                del self.orders.buy[symbol]
                lib.printFail(f'PREPARE_BUY: {symbol} cannot be swapped, needed {amount_quote_asset_needed:.2f} {quote_asset_needed}')

        kucoin_symbol_df = self.retrieveKCSymbol() # Ensure symbols are loaded
        adjusted_prepare_order = {}
        for pair, calculated_amount in prepare_order.items():
            asset_to_sell = self.getBaseCurrency(pair).lower()
            # Use upper case for dictionary lookup consistency if needed, but lower() matches wallet keys better
            available_balance = self.wallet['kucoin_asset'].get(asset_to_sell, 0.0)

            # Get precision for the asset being sold (base currency)
            symbol_info = kucoin_symbol_df[kucoin_symbol_df['symbol'] == pair.upper()]
            precision = 8 # Default precision if not found
            if not symbol_info.empty:
                try:
                    # Use baseIncrement for SELL orders (selling the base currency)
                    increment_str = symbol_info['baseIncrement'].iloc[0]
                    if isinstance(increment_str, str): # Check if it's a string before processing
                        if '.' in increment_str:
                            precision = len(increment_str.split('.')[-1].rstrip('0')) # Use rstrip('0') for cases like 0.1000
                        elif 'e-' in increment_str: # Handle scientific notation like 1e-8
                            precision = int(increment_str.split('e-')[-1])
                        elif increment_str == '1': # Handle cases like '1' where precision is 0
                             precision = 0
                        # Add more robust parsing if other formats exist
                    elif isinstance(increment_str, (int, float)): # Handle numeric increments directly if they occur
                         increment_val = float(increment_str)
                         if increment_val == 1:
                              precision = 0
                         elif increment_val < 1:
                              precision = abs(floor(log(increment_val, 10))) # Calculate precision from float
                         # Handle other numeric cases if necessary

                except Exception as e:
                     lib.printWarn(f"PREPARE_BUY: Could not determine precision for {pair} baseIncrement, using default {precision}. Error: {e}")


            adjusted_amount = calculated_amount
            if calculated_amount > available_balance:
                # Format available_balance using the determined precision for the warning message
                available_balance_str = f"{available_balance:.{precision}f}"
                calculated_amount_str = f"{calculated_amount:.{precision}f}"
                lib.printWarn(f"PREPARE_BUY: Swap amount for {pair} ({calculated_amount_str} {asset_to_sell.upper()}) exceeds available balance ({available_balance_str}). Adjusting swap amount.")
                adjusted_amount = available_balance

            # Apply precision flooring AFTER potentially adjusting
            # Ensure adjusted_amount is treated as float before calculation
            adjusted_amount_precise = floor(float(adjusted_amount) * (10**precision)) / (10**precision)

            # Check minimum order size (baseMinSize for SELL)
            min_size = 0.0
            if not symbol_info.empty:
                try:
                    min_size = float(symbol_info['baseMinSize'].iloc[0])
                except Exception as e:
                    lib.printWarn(f"PREPARE_BUY: Could not determine baseMinSize for {pair}, using default {min_size}. Error: {e}")

            if adjusted_amount_precise >= min_size: # Check if adjusted amount meets minimum size
                adjusted_prepare_order[pair] = adjusted_amount_precise
            elif adjusted_amount_precise > 0: # If positive but below minimum
                 lib.printWarn(f"PREPARE_BUY: Adjusted swap amount {adjusted_amount_precise:.{precision}f} for {pair} is below minimum size {min_size:.{precision}f}. Skipping swap.")
            # else: # If zero or negative, implicitly skipped

        prepare_order = adjusted_prepare_order # Replace original with adjusted one

        for pair, amount in prepare_order.items():
             # --- Remove the round(amount, 2) ---
             # res = self.marketOrder(pair, self.SELL, round(amount, 2))
             # --- Use the precise amount calculated above ---
             # Amount here is already precision-adjusted and checked against min size
             res = self.marketOrder(pair, self.SELL, amount) 
             if res:
                 available_asset = self.getBaseCurrency(pair)
                 asset_needed = self.getQuoteCurrency(pair)
                 if self.debug_mode: print(f'prepareBuyOrders: swapped {round(amount, 2)} {self.orders.currency} worth of {available_asset} to {asset_needed}')
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

        for symbol, amount in self.orders.buy.items():
            if symbol in available_pairs.keys() and symbol not in self.error.failed_trades.keys():
                amount_in_curr = amount
                convert2 = available_pairs[symbol][0].replace(symbol+'-', '')
                # transform 10€ in quote currency e.g. USDC
                amount_in_quote = round(amount_in_curr/self.price_asset2buy.data[convert2], available_pairs[symbol][1])
                if self.debug_mode: print('executeBuyOrders:', available_pairs[symbol][0], 'BUYING', amount_in_quote, available_pairs[symbol][0].split('-')[1])

                res: bool = self.marketOrder(available_pairs[symbol][0], self.BUY, amount_in_quote)
                if not res:
                    self.error.failed_trades[available_pairs[symbol][0]] = [amount, self.wallet['currency'], self.BUY]
            else: 
                self.error.failed_trades[symbol] = [amount, self.wallet['currency'], self.BUY]
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
            self.error.failed_trades[symbol] = [self.orders.sell[symbol], self.wallet['currency'], self.SELL]
            del self.orders.sell[symbol]
            lib.printFail(f'Cannot SELL {symbol.upper()} on Kucoin, no trading pair available!')

        for symbol, amount_in_curr in self.buy_power.sell_orders.items():
            if symbol in available_pairs.keys():
                # transform 10€ in base currency e.g. BTC
                amount_in_crypto = floor(amount_in_curr/self.price_asset2sell.data[symbol] * 10**available_pairs[symbol][1]) / 10**available_pairs[symbol][1]
                if amount_in_crypto <= 0: continue
                if self.debug_mode: print('executeSellOrders:', available_pairs[symbol][0], 'SELLING', amount_in_crypto, symbol) 
                
                res = self.marketOrder(available_pairs[symbol][0], self.SELL, amount_in_crypto)
                if not res:
                    self.error.failed_trades[available_pairs[symbol][0]] = [amount_in_curr, self.wallet['currency'], self.SELL]
            else: 
                self.error.failed_trades[symbol] = [amount_in_curr, self.wallet['currency'], self.SELL]
                lib.printFail(f'Cannot SELL {symbol} on Kucoin, no trading pair available!')

    # execute market order
    # e.g. pair: SOL-USDC
    # if side == buy , size must be denominated in quotecurrency e.g. USDC
    # if side == sell, size must be denominated in basecurrency e.g. SOL
    def marketOrder(self, pair, side, size):
        if not self.isPairValid(pair):
            lib.printFail(f"MARKET_ORDER: Invalid pair format '{pair}'")
            return False

        log_prefix = f"[{self.execution_mode.upper()}]"

        # --- Simulation Mode Check (Primary) ---
        if self.execution_mode == 'simulation':
            lib.printWelcome(f"{log_prefix} Would place {side.upper()} order for size {size} on {pair}")
            return True # Return immediately for simulation
        # --- End Simulation Mode Check ---

        # --- Interactive Confirmation (Only if interactive mode) ---
        user_confirmed = True # Default to True (for yolo mode)
        if self.execution_mode == 'interactive':
            lib.printAskUserInput(f"{log_prefix} Confirm {side.upper()} order for size {size} on {pair}? (y/n): ", end='')
            proceed = lib.getUserInput().lower()
            if proceed != 'y':
                user_confirmed = False
                lib.printWarn(f"{log_prefix} Skipped {side.upper()} order for {pair} by user.")
                # Return False if skipped by user in interactive mode
                return False
        # --- End Interactive Confirmation ---

        # Proceed only if in 'yolo' mode OR ('interactive' mode AND user_confirmed is True)
        # Note: user_confirmed check is implicitly handled by the return False above for interactive skips.
        try:
            lib.printWelcome(f"{log_prefix} ATTEMPTING: Placing {side.upper()} order for size {size} on {pair}")
            orderid: str = self.kc.placeOrder(pair, side, size)

            if orderid and len(orderid) > 0:
                lib.printOk(f"{log_prefix} SUCCESS: Placed {side.upper()} order for {pair}. Order ID: {orderid}")
                return True
            else:
                lib.printFail(f"{log_prefix} FAILED: Placing {side.upper()} order for {pair}. API did not return a valid Order ID.")
                return False
        except Exception as e:
            lib.printFail(f"{log_prefix} ERROR: Exception during {side.upper()} order for {pair}: {e}")
            return False

    def run(self):
        self.loadOrders()
        self.calcBuyPower()

        # --- Display Plan --- 
        # Always display the plan regardless of mode for informational purposes
        lib.printWelcome(f"--- Proposed Rebalance Plan ({self.execution_mode} mode) ---") # Changed to printWarn
        lib.printWarn("Sell Orders:") # Changed to printWarn
        if self.orders.sell:
            for symbol, amount in self.orders.sell.items():
                 price = self.price_asset2sell.data.get(symbol.upper(), None)
                 estimated_value = f" (Est. {amount:.2f} {self.orders.currency})" if price else f" ({amount:.2f} {self.orders.currency})"
                 lib.printWarn(f"  - Sell {symbol.upper()}{estimated_value}") # Changed to printWarn
        else:
             lib.printWarn("  - None") # Changed to printWarn

        lib.printWarn("Buy Orders:") # Changed to printWarn
        if self.orders.buy:
            for symbol, amount in self.orders.buy.items():
                 price = self.price_asset2buy.data.get(symbol.upper(), None)
                 estimated_value = f" (Est. {amount:.2f} {self.orders.currency})" if price else f" ({amount:.2f} {self.orders.currency})"
                 lib.printWarn(f"  - Buy {symbol.upper()}{estimated_value}") # Changed to printWarn
        else:
             lib.printWarn("  - None") # Changed to printWarn

        if self.error.failed_trades:
            lib.printFail("Potential Issues/Skipped Trades (Before Execution):") # Changed to printFail
            for symbol, details in self.error.failed_trades.items():
                amount, currency, trade_type = details
                lib.printFail(f"  - Cannot {trade_type.upper()} {symbol}: Amount {amount:.2f} {currency} (Reason logged previously)") # Changed to printFail

        lib.printWarn("--- End Plan ---") # Changed to printWarn

        # --- Execution Start Message --- 
        if self.execution_mode == 'simulation':
             lib.printWelcome("Proceeding with simulation...")
        elif self.execution_mode == 'interactive':
             lib.printWelcome("Proceeding to execute orders interactively...")
        elif self.execution_mode == 'yolo':
             lib.printWelcome("Proceeding to execute orders automatically (YOLO mode!)...")
        # --- End Execution Start Message ---

        self.executeSellOrders()
        self.executeBuyOrders()

        if self.debug_mode: print('ORDERS not executed', self.error.failed_trades)
        # after execute everything
        # go back to calcWallet to update walletValue.json
 
if __name__ == '__main__':
    ''

