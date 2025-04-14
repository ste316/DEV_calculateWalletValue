try:
    from src.api_yahoo_f import *
    from src.lib_tool import lib
    from src.api_coin_market import cmc_api
    from src.api_coin_gecko import cg_api_n
    from src.api_kucoin import kc_api
    from src.rebalancer import kucoinAutoBalance
except:
    from api_yahoo_f import *
    from lib_tool import lib
    from api_coin_market import cmc_api
    from api_coin_gecko import cg_api_n
    from api_kucoin import kc_api
    from rebalancer import kucoinAutoBalance

from pandas import read_csv, concat
from datetime import datetime
from numpy import array
from math import isnan
from matplotlib.pyplot import figure, pie, legend, title, savefig, show
from seaborn import set_style
from json import dumps, loads
from os.path import join
from os import getcwd
from typing import Tuple

# 
# Calculate your wallet value 
# add your crypto and fiat in input.csv
# fill currency, provider and path in settings.json
# specify type: crypto or total
# type affect only the visualization of the data
# wallet data is calculated the same way with both crypto and total type
# 
class calculateWalletValue:
    # Initialization variable and general settings
    def __init__(self, type_: str, load = False, privacy = False, rebalance_mode_override: str | None = None) -> None:
        """Initialize the wallet calculator with general settings and configurations.
        
        Args:
            type_ (str): Type of wallet calculation ('crypto' or 'total')
            load (bool, optional): Option to load data from JSON. Defaults to False.
            privacy (bool, optional): Enable privacy mode to hide total values. Defaults to False.
            rebalance_mode_override (str | None, optional): Override rebalancer mode from CLI. Defaults to None.
        """
        self.settings = lib.getSettings()
        self.config = lib.getConfig()
        self.rebalance_mode_override = rebalance_mode_override
        self.invalid_sym = []
        self.provider = ''
        self.version = self.config['version']
        self.supportedFiat = self.config['supportedFiat']
        self.supportedStablecoin = self.config['supportedStablecoin']
        self.load = load # option to load data from json, see calculateWalletValue.genPltFromJson()
        self.privacy = privacy
        self.wallet = {
            # { asset: [[symbol,qta,value, ('crypto' | 'stable' | 'fiat')],] , total_invested: 0, currency: ''}
            # { asset: [['ATOM', 2, 30, 'crypto'], ['USDC', 21.4, 21.4, 'fiat']]}
            'asset' : dict(),
            'total_invested': 0,
            'currency': self.settings['currency'],
            'kucoin_asset': dict()
        }
        self.wallet_liquid_stake = set() # list of asset that are liquid staked asset, see calculateWalletValue.handle_liquid_stake()
        lib.printWelcome(f'Welcome to Calculate Wallet Value!')
        lib.printWarn(f'Currency: {self.wallet["currency"]}')
        lib.printWarn(f'Privacy: {"ON" if self.privacy else "OFF"}')

        # if path is not specified in settings.json
        if not len(self.settings['path'] ) > 0:
            lib.printFail('Specify path in settings.json file')
            exit()
        else: basePath = self.settings['path']

        # create working files
        files = lib.createWorkingFile(basePath)
        if not files: exit()
        self.settings['grafico_path'], self.settings['wallet_path'], self.settings['report_path'] = files

        # create input.csv file
        lib.createFile(f'input.csv', 'symbol,qta,label', False)

        # set price provider
        if self.settings['provider'] == 'cg':
            lib.printWarn('Api Provider: CoinGecko')
            self.provider = 'cg'
            self.cg = cg_api_n(self.wallet["currency"])
            lib.createFile(self.cg.all_id_path)
        elif self.settings['provider'] == 'cmc':
            lib.printWarn('Api Provider: CoinMarketCap')
            self.provider = 'cmc'
            self.cmc = cmc_api(self.wallet["currency"], self.settings['CMC_key'])
            lib.createFile(self.cmc.all_id_path)
        else:
            lib.printFail("Specify a correct price provider")
            exit()

        # fetch all crypto symbol and name from CoinGecko or CoinMarketCap
        # run once or if there is any new crypto
        if self.settings['fetch_symb'] == True: 
            if self.provider == 'cg':
                self.cg.fetchID()
            if self.provider == 'cmc':
                self.cmc.fetchID()

        # set type
        if type_ in ['crypto', 'total']: 
            self.type = type_
            lib.printWarn(f'Report type: {self.type} wallet')
        else:
            lib.printFail('Unexpected error, pass the correct argument, run again with option --help')
            exit()
        
        if self.settings['retrieve_kc_balance']:
            try:
                self.kc = kc_api(self.wallet['currency'])
                if self.kc.error:
                    raise Exception
                if not self.kc.getBalance(): # try to update balance, if fail raise Exception
                    raise Exception
            except Exception as e:
                self.settings['retrieve_kc_balance'] = False
                lib.printFail(f'Failed to update Kucoin balance, reason: {e}')

    def loadCSV(self) -> list:
        """Acquire data from input CSV file and convert it to a list.
        
        If Kucoin balance retrieval is enabled, also reads from input_kc.csv and concatenates the data.
        If custom input path is specified in settings.json, it will be used instead of input.csv
        
        Returns:
            list: List of values from the CSV file(s)
        """
        from os.path import isfile
        lib.printWarn('Loading value from input.csv...')
        input_file = f'input.csv'
        if self.settings['input_custom'] and isfile(self.settings['input_path']):
            input_file = self.settings['input_path']
        df = read_csv(input_file, parse_dates=True) # pandas.read_csv()
        if self.settings['retrieve_kc_balance']:        
            df_kc = read_csv(f'input_kc.csv') # read kucoin asset
            df = concat([df, df_kc], axis=0, ignore_index=True)
        return df.values.tolist() # convert dataFrame to list []

    # CoinGecko retrieve price of a single crypto
    # return a float
    def CGgetPriceOf(self, symbol: list[str]) -> dict: 
        """Retrieve price of crypto symbols from CoinGecko.
        
        Args:
            symbol (list[str]): List of crypto symbols to get prices for
            
        Returns:
            dict: Dictionary of prices with symbols as keys
            
        Raises:
            SystemExit: If incorrect price provider is specified
        """
        if self.provider == 'cg': # coingecko
            price, missingSet1, missingSet2 = self.cg.getPriceOf(symbol)
            if len(missingSet1) > 0:
                self.invalid_sym.append(list(missingSet1))
            if len(missingSet2) > 0:
                self.invalid_sym.append(list(missingSet2))
            return price

        lib.printFail('Unexpected error, incorrect price provider')
        exit()

    # CoinMarketCap retrieve price of multiple crypto
    # return a dict with symbol as key and price as value
    def CMCgetPriceOf(self, symbol: list) -> dict:
        """Retrieve price of multiple crypto symbols from CoinMarketCap.
        
        Args:
            symbol (list): List of crypto symbols to get prices for
            
        Returns:
            dict: Dictionary with symbols as keys and prices as values
            
        Raises:
            SystemExit: If incorrect price provider is specified or unable to retrieve prices
        """
        if self.provider == 'cmc': #CoinMarketCap
            symbol = [x.upper() for x in symbol] 
            temp = self.cmc.getPriceOf(symbol)
            if not temp[1]: # if temp[1] is false, it means that one or more prices are missing, see api.py for more info
                (dict, _, missing, _) = temp
                self.invalid_sym.extend(list(missing))
                if len(dict) <= 0: # check if all price are missing
                    lib.printFail('Unexpected error, unable to retrieve price data')
                    exit()
            else:
                (dict, _) = temp
            return dict
        lib.printFail('Unexpected error, incorrect price provider')
        exit()
    
    def getCryptoIndex(self) -> float:
        """Get NCIS (crypto index) price.
        
        Used to compare volatility of portfolio vs volatility of NCIS.
        
        Returns:
            float: Current NCIS price
        """
        date_format = '%Y-%m-%d'
        current_date = lib.getCurrentDay(date_format)
        return getTicker(
            ticker="^NCIS", 
            start=lib.getPreviousDay(current_date, date_format), 
            end=current_date
        )

    def showInvalidSymbol(self) -> None:
        """Print invalid pairs or incorrect symbols that were encountered."""
        if len(self.invalid_sym) > 0:
            lib.printFail('The following pair(s) cannot be found:')
            for ticker in self.invalid_sym:
                print(f'\t{ticker}-{self.wallet["currency"]}', end=' ')
            print('')

    def checkInput(self, crypto: list, load: bool = False) -> dict:
        """Validate and sort input data into crypto, stable and fiat assets.
        
        Args:
            crypto (list): List of crypto data from input CSV
            load (bool, optional): Whether data is being loaded from saved JSON. Defaults to False.
            
        Raises:
            SystemExit: If input data is empty or invalid
            ValueError: If symbol or quantity values are invalid
        """
        lib.printWarn('Validating data...')
        if len(crypto) == 0:
            lib.printFail(f'Input.csv is empty, fill it with your crypto...')
            exit()
        
        if load and self.settings['convert_liquid_stake']:
            pass
            # inject liquid_stake to crypto variable

        err = 0
        # value variable refer to 'label' column in input.csv
        # when self.load is true INSTEAD value variable refer to fiat value in the 
        # list 'crypto' walletValue.json inside and it is used
        for (symbol, qta, value, liquid_stake) in crypto:
            try:
                if type(symbol) == float or (type(symbol) == 'str' and symbol.replace(" ", "") == ""): raise ValueError
                if isnan(float(qta)): raise ValueError
                qta = float(qta) # convert str to float
            except ValueError:
                lib.printFail(f'Error parsing value of {symbol}')
                if not str(symbol) == 'nan': self.invalid_sym.append(str(symbol))
                err +=1
                continue

            if not load and value == 'kucoin': 
                # when reading csv files <value> refer to label column in csv 
                if symbol not in self.wallet['kucoin_asset'].keys():
                    self.wallet['kucoin_asset'][symbol] = qta
                else:
                    self.wallet['kucoin_asset'][symbol] += qta

            # add total_invested from csv to self.wallet['total_invested']
            if symbol == 'total_invested':
                self.wallet['total_invested'] = qta
                continue
            
            # add liquid stake asset to the list
            # so in genPlt() it can be visualizzed as the base asset
            if self.settings['convert_liquid_stake']:
                if str(liquid_stake).replace(' ', '').lower() == 'yes':
                    self.wallet_liquid_stake.add(symbol)

            # this block of 3 if statement sort the symbol 
            # in fiat, stablecoin crypto
            if symbol.lower() in self.supportedFiat:  # FIAT
                if symbol.upper() in self.getAssetFromWallet(['fiat']):
                    # when symbol is already in wallet
                    # add new qta (+=)
                    self.wallet['asset'][str(symbol).upper()][0] += qta
                else: 
                    # when symbol is NOT in wallet
                    if self.load:
                        # when self.load is true add qta and value directly
                        # without += operator since, it get wallet data 
                        # from walletValue.json record
                        # this implies that qta and value is correct
                        self.wallet['asset'][str(symbol).upper()] = [qta, value, 'fiat']
                    else: 
                        # add qta, value will be calculated later
                        self.wallet['asset'][str(symbol).upper()] = [qta, 0.0, 'fiat']

            elif symbol.lower() in self.supportedStablecoin: # STABLE
                if symbol.upper() in self.getAssetFromWallet(['stable']):
                    self.wallet['asset'][str(symbol).upper()][0] += qta
                else: 
                    if self.load:
                        self.wallet['asset'][str(symbol).upper()] = [qta, value, 'stable']
                    else: self.wallet['asset'][str(symbol).upper()] = [qta, 0.0, 'stable']

            else: # CRYPTO
                if symbol.upper() in self.getAssetFromWallet(['crypto']):
                    self.wallet['asset'][str(symbol).upper()][0] += qta
                else: 
                    if self.load:
                        self.wallet['asset'][str(symbol).upper()] = [qta, value, 'crypto']
                    else: self.wallet['asset'][str(symbol).upper()] = [qta, 0.0, 'crypto']
        
        if self.wallet['asset'] == {}:
            lib.printFail('File input.csv is empty or have some columns missing')
            exit()
        if err > 0:
            lib.printFail("Check your input.csv file, some value is missing")

    def getAssetFromWallet(self, typeOfAsset: list, fullItem = False, getQta = False, getValue = False) -> list[list]:
        """Get assets from wallet filtered by type.
        
        Args:
            typeOfAsset (list): List of asset types to filter by ('crypto', 'stable', 'fiat', 'all')
            fullItem (bool, optional): Return full item details [symbol, qta, value, type]. Defaults to False.
            getQta (bool, optional): Include quantity in return data. Defaults to False.
            getValue (bool, optional): Include value in return data. Defaults to False.
            
        Returns:
            list[list]: Filtered list of assets in requested format
        """
        if set(typeOfAsset).intersection(set(['crypto', 'stable', 'fiat', 'all'])): # empty set are evaluated False
            listOfAsset = list()
            isAll = False

            if 'all' in typeOfAsset: isAll = True
            for item in self.wallet['asset'].items():
                
                item = list(item)
                item = [item[0]]+item[1]
                # final result
                # item=['ATOM', 1.0, 12.5, 'crypto']
                #       symbol, qta,    value,  type
                if item[3] in typeOfAsset or isAll: 
                    if fullItem: listOfAsset.append(item); continue
                    elif getQta and getValue: listOfAsset.append([item[0], item[1], item[2]]); continue
                    elif getQta: listOfAsset.append([item[0], item[1]]); continue
                    elif getValue: listOfAsset.append([item[0], item[2]]); continue
                    else: listOfAsset.append(item[0]); continue

            return listOfAsset

        else: return []

    def aggregateAssetValue(self, stable: bool = False, crypto: bool = False, fiat: bool = False, custom: list = []):
        """Aggregate asset values by type.
        
        Args:
            stable (bool, optional): Include stablecoins. Defaults to False.
            crypto (bool, optional): Include cryptocurrencies. Defaults to False.
            fiat (bool, optional): Include fiat currencies. Defaults to False.
            custom (list, optional): Custom list of assets to include. Defaults to empty list.
            
        Returns:
            dict: Dictionary containing list of assets and their total value
        """
        if not isinstance(custom, list): return {}

        data = []
        if stable: data.extend(self.getAssetFromWallet(['stable'], getValue=True))
        if crypto: data.extend(self.getAssetFromWallet(['crypto'], getValue=True))
        if fiat: data.extend(self.getAssetFromWallet(['fiat'], getValue=True))
        if len(custom) > 0: 
            for c in custom:
                if c in self.wallet['asset'].keys() and c not in data:
                    data.extend([[c, self.wallet['asset'][c][1]]])

        total_value = 0
        asset = []
        for symbol, value in data:
            symbol = symbol.upper()
            if symbol not in asset: #to avoid duplicate, in case of using custom list
                total_value += value
                asset.append(symbol)  
        return {"asset": asset, 'total_value': total_value}
        
    def CMCcalcValue(self):
        """Calculate asset values using CoinMarketCap prices.
        
        Retrieves current prices for crypto and stable assets from CoinMarketCap.
        Calculates fiat values using Yahoo Finance exchange rates.
        Updates wallet with calculated values and totals.
        """
        tot = 0.0
        tot_crypto_stable = 0.0
        lib.printWarn('Retriving current price...')

        # get prices of crypto and stable
        cryptoList = self.getAssetFromWallet(['crypto'])
        stableList = self.getAssetFromWallet(['stable'])
        rawData = self.CMCgetPriceOf(cryptoList+stableList)

        # unpack value and divide it back to crypto and stable
        for (symbol, price) in rawData.items():
            value = round(price * self.wallet['asset'][symbol][0] ,2) # price * qta
            self.wallet['asset'][symbol][1] = value
            tot += value
            tot_crypto_stable += value

        for symbol, qta in self.getAssetFromWallet(['fiat'], getQta=True):
            # if symbol is the main currency -> return the qta
            if symbol.upper() == self.wallet["currency"]:
                value = round(qta, 2)
                tot += value
                self.wallet['asset'][symbol][1] = value

            # you want to exchange the other fiat currency into the currency in settings
            elif symbol.lower() in self.supportedFiat:
                price = yahooGetPriceOf(f'{self.wallet["currency"]}{symbol}=X')
                value = round(price * qta, 2)
                self.wallet['asset'][symbol][1] = value
                tot += value 
            else:
                self.invalid_sym.append(symbol)

        self.wallet['total_value'] = round(tot, 2)
        self.wallet['total_crypto_stable'] = round(tot_crypto_stable, 2)
        self.wallet['date'] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    def CGcalcValue(self):
        """Calculate asset values using CoinGecko prices.
        
        Retrieves current prices for crypto and stable assets from CoinGecko.
        Calculates fiat values using Yahoo Finance exchange rates.
        Updates wallet with calculated values and totals.
        """
        tot = 0.0
        tot_crypto_stable = 0.0
        lib.printWarn('Retriving current price...')

        cryptoList = self.getAssetFromWallet(['crypto'])
        stableList = self.getAssetFromWallet(['stable'])

        rawData = self.CGgetPriceOf(cryptoList+stableList)
        for symbol, value in rawData.items():
            value = round(value * self.wallet['asset'][symbol.upper()][0] ,2)
            self.wallet['asset'][symbol.upper()][1] = value
            tot += value
            tot_crypto_stable += value

        for symbol, qta in self.getAssetFromWallet(['fiat'], getQta=True):
            # if symbol is the main currency, just return the qta
            if symbol.upper() == self.wallet["currency"]:
                price = 1
            elif symbol.lower() in self.supportedFiat:
                # you want to exchange the other fiat currency into the currency in settings
                price = yahooGetPriceOf(f'{self.wallet["currency"]}{symbol}=X')
            else:
                self.invalid_sym.append(symbol)
                continue

            value = round(price*qta, 2)
            self.wallet['asset'][symbol][1] = value
            tot += value

        self.wallet['total_value'] = round(tot, 2)
        self.wallet['total_crypto_stable'] = round(tot_crypto_stable, 2)
        self.wallet['date'] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    def handleLiquidStake(self) -> dict:
        """Handle liquid staked assets and their base tokens.
        
        Returns:
            dict: Dictionary mapping liquid staked assets to their base token names
        """
        base_asset = {}
        # if enabled in settings.json
        if self.settings['convert_liquid_stake']:
            # load all cached liquid stake asset
            cached_ls = lib.loadLiquidStakeCache()
            for asset in self.wallet_liquid_stake:
                if asset in cached_ls["asset"]:
                    # add the base token relative to liquid staked asset
                    base_asset.update({asset: cached_ls[asset]})
     
        return base_asset
    
    def handleDataPlt(self) -> Tuple[list, dict]:
        """Format data for pie chart visualization.
        
        For crypto type:
            - Aggregates crypto values <= 2% into 'other' category
            - Optionally aggregates stablecoins
            - Handles liquid staked assets
            
        For total type:
            - Aggregates into just 'Crypto' and 'Fiat' categories
            
        Returns:
            Tuple[list, dict]: Tuple containing:
                - List of [symbol, value] pairs for visualization
                - Dictionary of data for Kucoin rebalancer (if enabled)
        """
        symbol_to_visualize = list()  # [ [symbol, value], ...]
        kucoin_rebalancer_data = dict() 
        lib.printWarn('Preparing data...')

        ############### CRYPTO HANDLING ###############
        if self.type == 'crypto':
            # Handle stablecoins aggregation
            if self.settings['aggregate_stablecoin']:
                stable = self.getAssetFromWallet(['stable'], getValue=True)
                stable_value = 0
                for symbol, value in stable:
                    stable_value += value
                
                temp = self.getAssetFromWallet(['crypto'], getValue=True)
                temp.append(['STABLEs', stable_value])
            else: 
                temp = self.getAssetFromWallet(['stable', 'crypto'], getValue=True)

            # Process liquid staking assets first
            value_to_add = {}
            ls_asset = self.handleLiquidStake()
            for ls, base in ls_asset.items():
                # add as key: base token relative to its liquid stake
                # add as value: liquid stake asset's value
                base = base.upper()
                if base in value_to_add:
                    value_to_add[base] += self.wallet['asset'][ls.upper()][1]
                else:
                    value_to_add[base] = self.wallet['asset'][ls.upper()][1]

            # Handle Kucoin rebalancer data if enabled
            if self.settings['kucoin_enable_autobalance']:
                kucoin_rebalancer_data = self.getAssetFromWallet(['stable', 'crypto'], getValue=True)
                # remove debt positions (if any) and 0 value crypto (if any)
                kucoin_rebalancer_data = {symbol: value for symbol, value in kucoin_rebalancer_data if value > 0}
                
                # add Liquid Staked asset values to base asset counting
                avoid_double_sum = []
                for symbol, _ in kucoin_rebalancer_data.items():
                    if symbol.lower() in ls_asset.keys():
                        base_symbol = ls_asset[symbol.lower()].upper()
                        if base_symbol in avoid_double_sum: continue
                        avoid_double_sum.append(base_symbol)
                        kucoin_rebalancer_data[base_symbol] += value_to_add[base_symbol]

                # delete liquid staked asset
                kucoin_rebalancer_data = {k: v for k, v in kucoin_rebalancer_data.items() if k.lower() not in ls_asset.keys()}

            # Combine base assets with their liquid staked values
            combined_assets = {}
            for symbol, value in temp:
                if symbol == 'other' or (self.settings['convert_liquid_stake'] and symbol.lower() in ls_asset.keys()):
                    continue
                
                total_value = value
                if self.settings['convert_liquid_stake'] and symbol in value_to_add:
                    total_value += value_to_add[symbol]
                
                combined_assets[symbol] = total_value

            # Now handle the "other" category based on combined values
            symbol_to_visualize = [['other', 0.0]] if any(value / self.wallet['total_crypto_stable'] <= self.settings['minimum_pie_slice'] for value in combined_assets.values()) else []
            
            for symbol, value in combined_assets.items():
                if value / self.wallet['total_crypto_stable'] <= self.settings['minimum_pie_slice']:
                    symbol_to_visualize[0][1] += value
                else:
                    symbol_to_visualize.append([symbol, value])

            return symbol_to_visualize, kucoin_rebalancer_data

        ############### TOTAL HANDLING ###############
        elif self.type == 'total':
            symbol_to_visualize = [
                ['Crypto', 0.0], ['Fiat', 0.0]
            ]
            temp = self.getAssetFromWallet(['all'], getValue=True)
            for symbol, value in temp:
                if symbol.lower() not in self.supportedFiat and symbol.lower() not in self.supportedStablecoin:
                    # crypto
                    symbol_to_visualize[0][1] += value
                else: 
                    # stable and fiat
                    symbol_to_visualize[1][1] += value
            return symbol_to_visualize, kucoin_rebalancer_data
        else:
            lib.printFail('Unexpected error on wallet type, choose crypto or total')
            exit()

    def genPlt(self, symbol_to_visualize: list) -> None:
        """Create, save and display a pie chart visualization of the wallet.
        
        Creates a pie chart showing asset distribution with percentages.
        Includes total balance, stablecoin percentage, and optional privacy mode.
        For crypto type with total_invested, shows percentage change.
        
        Args:
            symbol_to_visualize (list): List of [symbol, value] pairs to visualize
        """
        lib.printWarn('Creating pie chart...')
        mylabels = [] # symbols
        val = [] # value in currency of symbols

        for (symb, value) in sorted(symbol_to_visualize):
            mylabels.append(symb)
            val.append(value)

        y = array(val)# numpy.array()

        # grafic settings
        set_style('whitegrid')
        #sns.color_palette('pastel')
        # define size of the image
        figure(figsize=(7, 6), tight_layout=True)
        # create a pie chart with value in 'xx.x%' format
        pie(y, labels = mylabels, autopct='%.2f', startangle=90, shadow=False)

        # add legend and title to pie chart
        legend(title = "Symbols:")
        stable_percentage = self.getStableCoinPercentage()
        title_stablePercentage = f'Stablecoin Percentage: {" " if stable_percentage < 0 else stable_percentage}%'
        if self.privacy:
            # do not show total value
            title(f'{self.type.capitalize()} Balance: ***** {self.wallet["currency"]} | {self.wallet["date"]}\n{title_stablePercentage}', fontsize=13, weight='bold')
 
        elif self.type == 'crypto' and self.wallet['total_invested'] > 0:
            # if type == crypto AND total_invested > 0
            # show total value and percentage of change given total_invested
            increasePercent = round((self.wallet['total_crypto_stable'] - self.wallet['total_invested'])/self.wallet['total_invested'] *100, 2)
            title(f'{self.type.capitalize()} Balance: {self.wallet["total_crypto_stable"]} {self.wallet["currency"]} ({increasePercent}% {"↑" if increasePercent>0 else "↓"}) | {self.wallet["date"]}\n{title_stablePercentage}', fontsize=13, weight='bold')
        else:
            # if type == total OR
            # if type == crypto AND total_invested <= 0
            if self.type == 'crypto':
                total = self.wallet['total_crypto_stable']
            elif self.type == 'total':
                total = self.wallet['total_value']
            else: exit()

            # show total value
            title(f'{self.type.capitalize()} Balance: {total} {self.wallet["currency"]} | {self.wallet["date"]}\n{title_stablePercentage}', fontsize=13, weight='bold')

        # format filename using current date
        filename = self.wallet['date'].replace("/",'_').replace(':','_').replace(' ',' T')+'.png'

        if not self.load:
            # when load is enabled it get data from past record from walletValue.json
            # so you do NOT need to save the img and do NOT need to update json file
            if self.settings['save_img']:
                path_ = join(self.settings["grafico_path"], f'{"C_" if self.type == "crypto" else "T_" if self.type == "total" else ""}{filename}')
                savefig(path_) # save image
                lib.printOk(f'Pie chart image successfully saved in {path_}')
            self.updateWalletValueJson()
            
            #self.updateReportJson()
            # It's useless until, volatility is implemented
            # search 'def getCryptoIndex'

        show()

    def getWalletAsList(self) -> list:
        """Convert wallet data to a list format.
        
        Returns:
            list: List of [symbol, qta, value] for all assets in wallet
        """
        li = list()
        temp = self.getAssetFromWallet(['all'], getQta=True, getValue=True) # merge dict
        for symbol, qta, value in temp:
            li.append([symbol, qta, value]) # convert dict to list
        return li
    
    def getStableCoinPercentage(self) -> float:
        """Calculate stablecoin percentage of portfolio.
        
        Returns:
            float: Percentage of portfolio value in stablecoins or -1.0 if error
            
        Raises:
            SystemExit: If wallet type is invalid
        """
        tot_stable = 0
        for _ , value in self.getAssetFromWallet(['stable'], getValue=True):
            tot_stable += value

        if self.type == 'crypto':
            return round(tot_stable/self.wallet['total_crypto_stable'] * 100, 2)
        elif self.type == 'total':
            return round(tot_stable/self.wallet['total_value'] * 100, 2)
        else:
            lib.printFail('Unexpected error')
            return -1.0

    def updateReportJson(self):
        """Update report JSON file with current wallet data.
        
        Saves date, currency, and NCIS index value to report file.
        Prints success/failure message.
        """
        temp = dumps({
            'date': self.wallet['date'],
            'currency': self.wallet['currency'],
            'NCIS': round(self.getCryptoIndex(), 2), # Nasdaq Crypto Index Settlement
        })
        res = lib.updateJson(self.settings['report_path'], self.wallet['date'], temp)
        if res[0]:
            lib.printOk(f'Data successfully saved in {self.settings["report_path"]}')            
        else:
            lib.printFail(f"Failed to update {self.settings['wallet_path']}")   

    def updateWalletValueJson(self):
        """Update wallet value JSON file with current wallet state.
        
        Saves complete wallet data including:
        - Date, total values, currency
        - Price provider used
        - List of all crypto holdings
        
        Overwrites any existing record for the same date.
        Prints success/failure message.
        """
        temp = dumps({ # data to be dumped
            'date': self.wallet['date'],
            'total_value': self.wallet['total_value'],
            'total_crypto_stable': self.wallet['total_crypto_stable'],
            'total_invested': self.wallet['total_invested'],
            'currency': self.wallet['currency'],
            'price_provider': f"{'coinMarkerCap' if self.provider == 'cmc' else 'coinGecko' if self.provider == 'cg' else ''}",
            'crypto': [['COIN, QTA, VALUE IN CURRENCY']]+self.getWalletAsList(), # all symbols
            }
        )
        res = lib.updateJson(self.settings['wallet_path'], self.wallet['date'], temp)
        if res[0]:
            lib.printOk(f'Data successfully saved in {self.settings["wallet_path"]}')            
        else:
            lib.printFail(f"Failed to update {self.settings['wallet_path']}")

    def genPltFromJson(self):
        """Generate pie chart from historical wallet data.
        
        Loads historical records from wallet JSON file.
        Allows user to select a date and visualization type.
        Creates pie chart visualization of historical wallet state.
        
        Raises:
            SystemExit: On keyboard interrupt
        """
        lib.printWelcome('Select one of the following date to load data from.')
        record = []

        # load records of json file
        with open(self.settings['wallet_path'], 'r') as f:
            for line in f:
                record.append(loads(line))
        # print all date of records
        for (i, rec) in enumerate(record):
            print(f"[{i}] {rec['date']}", end='\n')

        # get user inputs 
        lib.printWarn('Type one number...')
        gotIndex = False
        while not gotIndex:
            try:
                index = int(input())
                if index >= 0 and index <= len(record):
                    gotIndex = True
                else: lib.printFail('Insert an in range number...')
            except KeyboardInterrupt:
                exit()
            except:
                lib.printFail('Insert a valid number...')
        record = record[index]

        lib.printWarn('Choose between crypto and total visualization:')
        gotType = False
        type = ''
        while not gotType:
            try:
                type = input().lower()
                if type in ['crypto', 'total']:
                    self.load = True
                    self.type = type
                    gotType = True
                else: lib.printFail('Insert a valid option("crypto" or "total")...')
            except KeyboardInterrupt:
                exit()
            except:
                lib.printFail('Insert a valid string...')

        # set variable to use genPlt()
        self.wallet['total_crypto_stable'] = record['total_crypto_stable']
        self.wallet['total_value'] = record['total_value']
        self.wallet['date'] = record['date']
        self.wallet['currency'] = record['currency']

        self.checkInput(record['crypto'][1:], True) # skip the first element, it's ["COIN, QTA, VALUE IN CURRENCY"]
        newdict = self.handleDataPlt()
        # if total invested is in the input.csv
        if 'total_invested' in record.keys():
            self.wallet['total_invested'] = record['total_invested']
        else: self.wallet['total_invested'] = 0

        self.genPlt(newdict)

    def run(self) -> None:
        """Main execution method for wallet calculation and visualization.
        
        Either:
        1. Loads historical data and generates visualization (if load=True)
        2. Or processes current wallet:
            - Loads CSV data
            - Validates input
            - Calculates values using selected provider
            - Generates visualization
            - Optionally runs Kucoin auto-balance
        """
        if self.load:
            self.genPltFromJson()
        else:
            rawCrypto = self.loadCSV()
            self.checkInput(rawCrypto)
            if self.provider == 'cg':
                self.CGcalcValue()
            if self.provider == 'cmc':
                self.CMCcalcValue()
            if self.invalid_sym:
                self.showInvalidSymbol()
            
            crypto, wallet_for_kc = self.handleDataPlt()
            self.genPlt(crypto)
            if self.settings['kucoin_enable_autobalance']: 
                data = {
                    'kucoin_asset': self.wallet['kucoin_asset'], 
                    'total_crypto_stable': self.wallet['total_crypto_stable'],  
                    'currency': self.wallet['currency'],
                    'asset': wallet_for_kc # custom struct
                }
                
                # Determine final execution mode
                final_rebalance_mode = self.settings.get('rebalance_mode', 'interactive') # Default from settings
                if self.rebalance_mode_override:
                    final_rebalance_mode = self.rebalance_mode_override
                    lib.printWarn(f"Using rebalance mode '{final_rebalance_mode}' from command line argument.")
                
                # Pass determined mode to kucoinAutoBalance
                auto = kucoinAutoBalance(
                    wallet=data, 
                    kucoin_api_obj=self.kc, 
                    ls_asset=self.handleLiquidStake(), 
                    debug_mode=True, # Consider making debug_mode configurable too
                    execution_mode=final_rebalance_mode # Pass the final mode here
                )
                auto.run()
