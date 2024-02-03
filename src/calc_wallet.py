from src.api_yahoo_f import *
from src.lib_tool import lib

from pandas import read_csv, concat
from datetime import datetime
from numpy import array
from math import isnan
from matplotlib.pyplot import figure, pie, legend, title, savefig, show
from seaborn import set_style
from json import dumps, loads

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
    def __init__(self, type_: str, load = False, privacy = False) -> None:
        self.settings = lib.getSettings()
        self.config = lib.getConfig()
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
        lib.createFile(f'..{lib.dir_sep}input.csv', 'symbol,qta,label', False)

        # set price provider
        if self.settings['provider'] == 'cg':
            lib.printWarn('Api Provider: CoinGecko')
            from src.api_coin_gecko import cg_api_n
            self.provider = 'cg'
            self.cg = cg_api_n(self.wallet["currency"])
            lib.createFile(f'..{lib.dir_sep}cache{lib.dir_sep}all_id_CG.json')
        elif self.settings['provider'] == 'cmc':
            lib.printWarn('Api Provider: CoinMarketCap')
            from src.api_coin_market import cmc_api
            self.provider = 'cmc'
            self.cmc = cmc_api(self.wallet["currency"], self.settings['CMC_key'])
            lib.createFile(f'..{lib.dir_sep}cache{lib.dir_sep}all_id_CMC.json')
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
            from api_kucoin import kc_api
            try:
                self.kc = kc_api(self.wallet['currency'])
                if self.kc.error:
                    raise Exception
                if not self.kc.getBalance(): # try to update balance, if fail raise Exception
                    raise Exception
            except Exception as e:
                self.settings['retrieve_kc_balance'] = False
                lib.printFail(f'Failed to update Kucoin balance, reason: {e}')

    # acquire csv data and convert it to a list
    # return a list
    def loadCSV(self) -> list:
        from os.path import isfile
        lib.printWarn('Loading value from input.csv...')
        input_file = f'..{lib.dir_sep}input.csv'
        if self.settings['custom_input'] and isfile(self.settings['input_path']):
            input_file = self.settings['input_path']
        df = read_csv(input_file, parse_dates=True) # pandas.read_csv()
        if self.settings['retrieve_kc_balance']:        
            df_kc = read_csv(f'..{lib.dir_sep}input_kc.csv') # read kucoin asset
            df = concat([df, df_kc], axis=0, ignore_index=True)
        return df.values.tolist() # convert dataFrame to list []

    # CoinGecko retrieve price of a single crypto
    # return a float
    def CGgetPriceOf(self, symbol: list[str]) -> dict: 
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
    
    # get NCIS (crypto index) price
    # will be used to compare volatility of portfolio vs volatility of NCIS
    def getCryptoIndex(self) -> float:
        return getTicker(
            ticker="^NCIS", 
            start=lib.getPreviousDay(lib.getCurrentDay('%Y-%m-%d'), '%Y-%m-%d'), 
            end=lib.getCurrentDay('%Y-%m-%d')
        )

    # print invalid pairs or incorrect symbol
    def showInvalidSymbol(self) -> None:
        if len(self.invalid_sym) > 0:
            lib.printFail('The following pair(s) cannot be found:')
            for ticker in self.invalid_sym:
                print(f'\t{ticker}-{self.wallet["currency"]}', end=' ')
            print('')

    # check data and sort assets in crypto, stable and fiat
    def checkInput(self, crypto: list, load: bool = False) -> dict:
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

    # get assets from self.wallet, specify typeOfAsset('crypto' or 'stable' or 'fiat' or 'all')
    # default return: list of symbol filtered by type
    # pass fullItem=True to get a list of [symbol, qta, value, type]
    # pass getQta or getValue to get a list of [symbol, ?qta, ?value]
    def getAssetFromWallet(self, typeOfAsset: list, fullItem = False, getQta = False, getValue = False) -> list[list]:
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
        
    # CoinMarketCap calculate the value of crypto and format data to be used in handleDataPlt()
    def CMCcalcValue(self):
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

    # CoinGecko calculate the value of crypto and format data to be used in handleDataPlt()
    def CGcalcValue(self):
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

    # return a dict containing liquid staked asset and 
    # their base token name
    def handleLiquidStake(self) -> dict:
        base_asset = {}
        # if enabled in settings.json
        if self.settings['convert_liquid_stake']:
            # load all cached liquid stake asset
            cached_ls = lib.loadJsonFile(f'..{lib.dir_sep}cache{lib.dir_sep}cached_liquid_stake.json')
            for asset in self.wallet_liquid_stake:
                if asset in cached_ls["asset"]:
                    # add the base token relative to liquid staked asset
                    base_asset.update({asset: cached_ls[asset]})
     
        return base_asset
    
    # format data to generate PLT
    # for crypto:
    #   if value of a certain crypto is <= 2%
    #   add special symbol 'other' and sum all crypto whose value is <= 2%
    # 
    # for total:
    #   there are only 2 symbols: crypto and fiat
    #   crypto value is the total sum of cryptos
    #   fiat value is the total sum of fiat and stablecoins converted in self.wallet["currency"]
    def handleDataPlt(self) -> list:
        symbol_to_visualize = list()  # [ [symbol, value], ...]
        lib.printWarn('Preparing data...')
        if self.type == 'crypto':
            if self.settings['aggregate_stablecoin']:
                stable = self.getAssetFromWallet(['stable'], getValue=True)
                stable_value = 0
                stable_list = []
                for symbol, value in stable:
                    stable_value += value
                    stable_list.append(symbol)  
                
                temp = self.getAssetFromWallet(['crypto'], getValue=True)
                temp.append(['STABLEs', stable_value])
            else: 
                temp = self.getAssetFromWallet(['stable', 'crypto'], getValue=True) # merge into one dict

            # do not show liquid stake asset, 
            # instead add the relative value to the base asset
            value_to_add = {}
            ls_asset = self.handleLiquidStake()
            for ls, base in ls_asset.items():
                # add as key: base token relative to its liquid stake
                # add as value: liquid stake asset's value
                # in case base asset is already added, sum it to the previous value
                if base.upper() in value_to_add.keys(): value_to_add[base.upper()] += self.wallet['asset'][ls.upper()][1]
                else: value_to_add.update({base.upper(): self.wallet['asset'][ls.upper()][1]})

            for symbol, value in temp:
                if symbol == 'other': continue

                # do not show liquid stake asset, 
                # instead add the relative value to the base asset
                if self.settings['convert_liquid_stake'] and symbol.lower() in ls_asset.keys(): continue
                
                # group together all element whose value is <= than minimum_pie_slice param, specified in settings.json
                if value / self.wallet['total_crypto_stable'] <= self.settings['minimum_pie_slice']:
                    if symbol_to_visualize[0][0] != 'other':
                        # add 'other' as first element
                        symbol_to_visualize = [['other', 0.0], *symbol_to_visualize]
                    # increment value of symbol 'other'
                    symbol_to_visualize[0][1] += value
                else: 
                    if self.settings['convert_liquid_stake'] and symbol in value_to_add.keys():
                        # do not show liquid stake asset, 
                        # instead add the relative value to the base asset
                        value += value_to_add[symbol] 

                    symbol_to_visualize.append([symbol, value])

            return symbol_to_visualize
        
        elif self.type == 'total':
            symbol_to_visualize = [
                ['Crypto', 0.0], ['Fiat', 0.0]
            ]
            temp = self.getAssetFromWallet(['all'], getValue=True) # merge into one dict
            for symbol, value in temp:
                if symbol.lower() not in self.supportedFiat and symbol.lower() not in self.supportedStablecoin:
                    # crypto
                    symbol_to_visualize[0][1] += value
                else: 
                    # stable and fiat
                    symbol_to_visualize[1][1] += value
            return symbol_to_visualize
        else:
            lib.printFail('Unexpected error on wallet type, choose crypto or total')
            exit()

    # create a pie chart, save it(unless self.load is checked) and show it
    def genPlt(self, symbol_to_visualize: list, ) -> None:
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
                savefig(f'{self.settings["grafico_path"]}{lib.dir_sep}{"C_" if self.type == "crypto" else "T_" if self.type == "total" else ""}{filename}') #save image
                lib.printOk(f'Pie chart image successfully saved in {self.settings["grafico_path"]}{lib.dir_sep}{"C_" if self.type == "crypto" else "T_" if self.type == "total" else ""}{filename}')
            self.updateWalletValueJson()
            
            #self.updateReportJson()
            # It's useless until, volatility is implemented
            # search 'def getCryptoIndex'

        show()

    # return a list containing all asset in self.wallet
    # the list is composed of other list that are composed so:
    # [symbol, qta, value]
    def getWalletAsList(self) -> list:
        li = list()
        temp = self.getAssetFromWallet(['all'], getQta=True, getValue=True) # merge dict
        for symbol, qta, value in temp:
            li.append([symbol, qta, value]) # convert dict to list
        return li
    
    # calculate stablecoin percentage of portfolio
    def getStableCoinPercentage(self) -> float:
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

    # append the record in walletValue.json
    # it overwrite the record with the same date of today
    def updateWalletValueJson(self):
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

    # given a past date and json data from walletValue.json file, 
    # create a pie chart
    def genPltFromJson(self):
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

    # main 
    def run(self) -> None: 
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
            
            crypto = self.handleDataPlt()
            self.genPlt(crypto)
            if self.settings['kucoin_enable_autobalance']: 
                from rebalancer import kucoinAutoBalance
                auto = kucoinAutoBalance(self.wallet, self.kc, self.handleLiquidStake(), True)
                auto.run()
