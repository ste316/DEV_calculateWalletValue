from lib_tool import lib
from typing import Any
from time import sleep, time
from pandas_datareader import _utils
from yfinance import download, Ticker
from requests import get, Response, post
from json import dumps, loads

class cg_api_n():
    def __init__(self, currency: str) -> None:
        self.currency = currency.lower()
        self.baseurl = 'https://api.coingecko.com/api/v3/'

        ''' CoinGecko price oracle do NOT work with ticker(eg. $eth, $btc) but with its own id
            it may happen that one ticker have multiple id:
            eg. {'symbol': 'eth', 'id': ['ethereum', 'ethereum-wormhole']}
            usually id with "-" in it is a wrapped token or similar
            BUT sometimes isn't the case, so when you encounter that price is incorrect 
            you may add the right one in cached symbol 
            To find the right one just ctrl/cmd + F on cached_id_CG.json file
            and search the right one by looking at name field'''

        # create cache file
        files = lib.createCacheFile()
        if not files: exit()

        self.cacheFile = 'cached_id_CG.json'
        self.all_id_path = 'all_id_CG.json'
        cg_cache = lib.loadJsonFile(self.cacheFile)
        self.fixedSymbol = cg_cache['fixed']
        self.usedSymbol = cg_cache['used']
        
        try:
            with open(self.all_id_path, 'r') as f:
                if len(f.read()) == 0:
                    f.close()
                    self.fetchID()
        except FileNotFoundError: 
            self.fetchID()
        except Exception as e:
            lib.printFail(str(e))
            exit()

    # fetch all id, symbol and name from CoinGecko, run only once in a while to update it
    def fetchID(self) -> None: 
        path = 'coins/list'
        coin = get(self.baseurl+path).json()

        with open('all_id_CG.json', 'w') as f:
            f.write(dumps(coin, indent=4))
        lib.printOk('Coin list successfully fetched and saved')

    # convert 'find' to CoinGecko id
    # @param find crypto ticker eg. "ETH" "eth"
    # @return dict eg. {'eth': 'ethereum', }
    def convertSymbol2ID(self, find: list[str]) -> dict[str: str] | set: 
        res = {'error': False}
        # make all string lower and remove all empty string (including '\n' '\t' ' ')
        find =  [x.lower() for x in find if x.replace(' ', '') != '']
        checkSet = set(find)

        # check if items in find list are already cached in cached_id_CG.json['used]
        # if so pop it from find list
        for crypto in find.copy():
            if crypto in self.usedSymbol.keys():
                res[crypto] = self.usedSymbol[crypto]
                find.pop(find.index(crypto))

        # retrieve all possible id from all_id_CG.json file
        temp = dict()
        with open(self.all_id_path, 'r') as f:
            filedata = loads(f.read())

            for crypto in filedata:
                if crypto['symbol'] in find:
                    # add if new, append if other possible valid id were found 
                    if crypto['symbol'] not in temp.keys():
                        temp[crypto['symbol']] = [crypto['id']]
                    else:
                        temp[crypto['symbol']].append(crypto['id'])

        # extract correct id using cached_id_CG.json['fixed'], otherwise print error
        err_count = 0
        for (symbol, ids) in temp.items():
            if len(ids) == 1: # if only one id were found -> i assume it's the correct one
                res[symbol] = ids[0]
                continue
            else:
                for id in ids:
                    if id in self.fixedSymbol: # if id in cached_id_CG.json['fixed']
                        res[symbol] = id # add it to response
                        ids = [id] # make id the only item in ids
                        # if after this loop ids have more than one item print an error
                        break
 
            if len(ids) > 1:
                err_count +=1
                lib.printFail(f'CoinGecko error, multiple ids has been found {lib.WARNING_YELLOW}({ids}){lib.ENDC} for symbol {lib.WARNING_YELLOW}"{symbol}"{lib.ENDC}')

        if err_count > 0:
            lib.printFail(f'Add the correct one in {lib.WARNING_YELLOW}{self.cacheFile}{lib.ENDC} in fixed field')
            res['error'] = True
        
        # update self.usedSymbol and dump it to cached_id_CG.json['used']
        self.usedSymbol.update(res)
        self.dumpUsedId()
        return res, checkSet-set(res.keys())

    # dump self.usedSymbol in cached_id_CG.json
    # note this function read and write cached_id_CG.json file 
    # BUT 'fixed' obj in NOT modified
    def dumpUsedId(self) -> None:
        with open(self.cacheFile, 'r') as f:
            # load 'fixed' and 'used' json object
            temp = loads(f.read())
        
        # update 'used' json object
        temp['used'] = self.usedSymbol
        temp['used'] = self.deleteControlItem(temp['used'])

        # dump json obj and write the new file
        with open(self.cacheFile, 'w') as f:
            f.write(dumps(temp, indent=4))

    # delete item in listToBeDeleted from a dict with str as key and any type of data as value
    def deleteControlItem(self, response: dict[str, Any]) -> dict[str, Any]:
        listToBeDeleted = ['error']
        for item in listToBeDeleted:
            if item in response.keys():
                # delete items
                del response[item]
        return response

    def getPriceOf(self, find: list[str]) -> dict[str, float]:
        path = 'simple/price'
        id, missingCryptoFromConvert = self.convertSymbol2ID(find=find)
        id = self.deleteControlItem(id)
        priceToReturn = dict()
        checkSet = set(id.keys())
        param = {
            'ids': ','.join(id.values()),
            'vs_currencies': self.currency,
            'precision': 2
        }

        # make request and retrieve a dict from json obj
        res = self.makeRequest(url=self.baseurl+path, param=param).json()
        # format data correctly
        for item in res:
            index = [i for i in id if id[i] == item][0]
            if res[item] == {}:
                # data price not available, most likely coin is 'Preview Only'
                priceToReturn[index] = 0
            else: # all good
                priceToReturn[index] = res[item][self.currency]

        missingCryptoFromPrice = checkSet-set(priceToReturn.keys())
        if len(missingCryptoFromConvert) > 0:
                lib.printFail(f'The following crypto(s) are NOT available in CoinGecko or do NOT exist: {lib.WARNING_YELLOW}{list(missingCryptoFromConvert)}{lib.ENDC}')
                lib.printWarn(f'Make sure to fetch all new CoinGecko ids by setting {lib.WARNING_YELLOW}fetchSymb{lib.ENDC} param equals to true in your {lib.WARNING_YELLOW}settings.json{lib.ENDC} file')
        if len(missingCryptoFromPrice) > 0:
                lib.printFail(f'The following crypto(s) price(s) are NOT retrivable from CoinGecko: {lib.WARNING_YELLOW}{list(missingCryptoFromPrice)}{lib.ENDC}')

        return priceToReturn, missingCryptoFromConvert, missingCryptoFromPrice

    def makeRequest(self, url: str, param: dict[str, Any]) -> Response:
        error_count = 0
        sleep_time = 0
        msg = ''

        while True:
            res = get(url=url, params=param)
            if res.status_code == 200: # all good
                return res

            elif res.status_code == 429: # rate limit
                sleep_time = 110
                error_count +=1
                msg = 'you have been rate limited'

            elif str(res.status_code)[0] == '5': # server errors
                error_count +=1
                sleep_time = 20
                msg = 'server error'

            else: # all other possible errors
                error_count +=1
                sleep_time = 30

            if error_count > 5:
                lib.printFail("CoinGecko api may be down, please visit https://status.coingecko.com/")
            lib.printWarn(f'Error {res.status_code}, {msg}{", " if msg != "" else ""}retrying after {sleep_time} seconds')
            sleep(sleep_time)

from requests import Session
from requests.exceptions import ConnectionError, Timeout, TooManyRedirects
from random import randrange

#
# CoinMarketCap Api
#
class cmc_api:
    def __init__(self, currency: str, api_key: str) -> None:
        if len(api_key) == 0:
            lib.printFail('CMC API error, no api key provided')
            exit()        
        self.currency = currency
        self.key = api_key
        self.baseurl = f'https://pro-api.coinmarketcap.com/v1/'
        self.cacheFile = 'cached_id_CMC.json'
        self.all_id_path = 'all_id_CMC.json'
        # create cache file
        files = lib.createCacheFile()
        if not files: exit()
        self.cachedSymbol = lib.loadJsonFile(self.cacheFile)    
        
        headers = { 
            'Accepts': 'application/json',
            'Accept-Encoding': 'deflate, gzip',
            'X-CMC_PRO_API_KEY': self.key,
        }

        self.session = Session()
        self.session.headers.update(headers)

        if not self.isKeyValid():
            lib.printFail('CMC API error, api key provided is not valid')
            exit()

        try:
            with open(self.all_id_path, 'r') as f:
                try: 
                    loads(f.read())['data']
                except KeyError: 
                    f.close()
                    self.fetchID()

        except FileNotFoundError: 
            self.fetchID()
        except Exception as e:
            lib.printFail(str(e))
            exit()

    # check that self.key is valid by making a request to CMC endpoint
    # @return True is CMC key is valid, False if not or other error is encoutered
    def isKeyValid(self):
        if self.key.strip() == '' or len(self.key) != 36:
            return False

        path = 'key/info'
        while True:
            res = self.session.get(self.baseurl+path)
            if res.status_code == 200:
                return True
            elif res.status_code == 429:
                lib.printWarn('You have been rate limited, sleeping for 60 second')
                sleep(60)
            elif res.status_code == 500:
                x = randrange(range(50,160))
                lib.printWarn(f'Server error, sleeping for {x}')
                sleep(x)
            else: # all others status code means that key is not valid
                return False

    # fetch all id, symbol and name from CMC, run only once in a while to update it
    def fetchID(self) -> int:
        url = 'cryptocurrency/map'
        res = self.session.get(self.baseurl+url)
        open(self.all_id_path, 'w').write(dumps(res.json(), indent=4))
        lib.printOk('Coin list successfully fetched and saved')

    # convert 'symbols' in CMC ids
    # @param symbols list of crypto tickers ["BTC", "ETH"]
    # @return dict eg. {"BTC": "1", }
    def convertSymbols2ID(self, symbols: list) -> dict:
        id = {}

        # check if there are some cached symbol
        for i, symb in enumerate(symbols):
            if symb in self.cachedSymbol:
                id[symb] = self.cachedSymbol[symb]
                symbols.pop(i) # remove from searching list

        if len(symbols) > 0: 
            found = 0
            data = loads(open('all_id_CMC.json', 'r').read())['data'] # once in a while run fetchID() to update it

            # check for every symbol in data
            for i in range(len(data)):
                if data[i]['symbol'] in symbols:
                    id[data[i]['symbol']] = str(data[i]['id'])
                    found +=1
                    symbols.pop(symbols.index(data[i]['symbol']))

            if found > 0:
                self.cachedSymbol.update(id)
                self.updateUsedSymbol()
                
        return id

    # update used_id_CMC.json
    def updateUsedSymbol(self) -> None:
        with open(self.cacheFile, 'w') as f:
            f.write(dumps(self.cachedSymbol))

    # convert 'symbols' to CMC ids and retrieve their prices
    # @param symbols list of crypto tickers eg. ["BTC", "ETH"]
    # @return (dict, True) if all symbols are found eg. ({"BTC": 20102.0348, "ETH": 1483.31747 }, True), 
    #         (dict, False, set, data) if not all symbols are found eg ({"BTC": 20102.0348}, False, ("ETH"), data)
    #          data is complete http response body loaded in a dict
    def getPriceOf(self, symbols: list):
        path = 'cryptocurrency/quotes/latest'
        convertedSymbol = self.convertSymbols2ID(symbols)
        id = list(convertedSymbol.values())

        toReturn = {}        

        parameters = {
            'id': ','.join(id),
            'convert': self.currency
        }

        try:
            response = self.session.get(self.baseurl+path, params=parameters)
            data = loads(response.text)
            for symb, id in convertedSymbol.items():
                toReturn[symb] = data['data'][id]["quote"][self.currency]["price"] # store only price

        except (ConnectionError, Timeout, TooManyRedirects):
            data = loads(response.text)
        
        # if one or more symbols are not found for any kind of problem 
        # return also the missing one(s) and data
        if (set(convertedSymbol.keys()) & set(toReturn.keys())) != set(symbols):
            return (toReturn, False, set(symbols) - set(toReturn.keys()), data)
        
        return (toReturn, True)

from base64 import b64encode
from hashlib import sha256
from time import time
from hmac import new
from pandas import DataFrame
from uuid import uuid4

class kc_api:
    def __init__(self, currency: str) -> None:
        self.kc_info = lib.loadJsonFile('kc_info.json')
        self.api_key: str = self.kc_info['key']
        self.api_secret: str = self.kc_info['secret']
        self.api_passphrase: str = self.kc_info['passphrase']
        self.symbol_blacklist: list[str] = self.kc_info['symbol_blacklist']
        self.base = 'https://api.kucoin.com'
        self.error = False
        self.currency = currency.upper()

        checklist = [len(x.replace(' ', ''))>0 for x in [self.api_key, self.api_passphrase, self.api_secret] ]
        if not all(checklist): # if any api info is empty -> error
            lib.printFail('Failed to load Kucoin API')
            self.error = True
    
    def __KucoinApiUp(self) -> bool:
        endpoint = '/api/v1/timestamp'
        url = self.base + endpoint
        res = get(url)
        body = loads(res)

        if res.status_code == 200 and body['code'] == '200000':return True
        return False

    def __prepareHeader(self, str_to_sign: str):
        signature = b64encode(new(self.api_secret.encode('utf-8'), str_to_sign.encode('utf-8'), sha256).digest())
        passphrase = b64encode(new(self.api_secret.encode('utf-8'), self.api_passphrase.encode('utf-8'), sha256).digest())
        return signature, passphrase
    
    # gen http header to auth
    # param:
    #       endpoint: api route
    #       now: unix-time in seconds
    #       post: use post method
    def __getHeader(self, endpoint: str, now: int, json_data: dict = {}, post: bool = False): # see https://www.kucoin.com/docs/basic-info/connection-method/authentication/signing-a-message
        str_to_sign = f'{now}{"GET" if not post else "POST"}{endpoint}{dumps(json_data, separators=(",", ":"), ensure_ascii=False) if post else ""}'
        signature, passphrase = self.__prepareHeader(str_to_sign)
        header = {
            "KC-API-SIGN": signature, # The base64-encoded signature
            "KC-API-TIMESTAMP": str(now), # A timestamp for your request
            "KC-API-KEY": self.api_key, # The API key as a string
            "KC-API-PASSPHRASE": passphrase, # The passphrase you specified when creating the API key
            "KC-API-KEY-VERSION": '2', # You can check the version of API key on the page of API Management
        }
        if post:
            header['Content-Type'] = "application/json"
        return header
    
    # retrieve kucoin balance, format and save it in input_kc.csv
    def getBalance(self):
        if self.error:
            return False
        
        endpoint = '/api/v1/accounts'
        url = self.base+endpoint
        now = int(time() * 1000)
        res = get(url, headers=self.__getHeader(endpoint, now))
        body = loads(res.text) # load response body data
        try:
            if res.status_code == 200 or body['code'] != '200000':
                    df = DataFrame.from_records(body['data'], exclude=['available','holds', 'type', 'id'])

                    # rename column, convert qta to float, delete rows with qta <= 0
                    df.rename({'currency': 'symbol', 'balance': 'qta'}, axis=1, inplace=True)
                    convert_dict = {'symbol': str, 'qta': float }
                    df = df.astype(convert_dict)
                    df = df[df['qta'] > 0]
                    
                    # add missing columns to match input.csv columns
                    df['label'] = 'kucoin'
                    df['liquid_stake'] = 'no'

                    # filter using the blacklist, can be edit in kc_info.json
                    df = df[~df['symbol'].isin(self.symbol_blacklist)]
                    df['symbol'] = df['symbol'].str.lower()

                    df.to_csv('input_kc.csv', sep=',', index=False)
                    return True
            else: 
                raise Exception
        except Exception:
            lib.printFail(f'Kucoin: status code: {res.status_code}, error msg: {body["msg"]}')
            return False

    # retrieve all tradable pairs
    def getSymbols(self):
        endpoint = '/api/v2/symbols'
        url = self.base + endpoint
        
        res = get(url)
        body = loads(res.text)

        if res.status_code == 200 and body['code'] == '200000':
            data = body['data']
            df = DataFrame.from_records(data, 
                exclude=['market', 'baseMinSize', 'quoteMinSize', 'name',
                        'baseMaxSize', 'quoteMaxSize', 'baseIncrement', 'quoteIncrement',
                        'priceIncrement', 'priceLimitRate', 'isMarginEnabled'])
            
            df.to_csv('kucoin_symbol.csv', sep=',', index=False)
            return True
        
        lib.printFail(f'Kucoin: unable to download symbols... error:{body["msg"]}')
        return False

    # get Kucoin's prices of currencies list
    # do not use it as price oracle like CoingGecko, as this only refer to Kucoin markets
    def getFiatPrice(self, currencies: list[str]) -> dict[str, float]:
        currencies = [c.upper() for c in currencies]
        endpoint = '/api/v1/prices'
        url = self.base + endpoint
        param = {
            'base': self.currency,
            'currencies': ','.join(currencies)
            # comma separated cryptocurrencies to be converted into fiat, e.g.: BTC,ETH
        }

        res = get(url, params=param)
        body = loads(res.text)
        
        if res.status_code == 200 and body['code'] == '200000':
            data: dict = body['data']

            if len(data) != len(currencies) and len(data) > 0:
                # NOT all fine, NOT all good broda
                missing = set(currencies)-set(data.keys())
                lib.printFail(f'Kucoin: unable to retrieve all fiat prices, missing: [{len(missing)}] {missing}')
            elif len(data) == 0:
                print(body)
                lib.printFail(f'Kucoin: error while retrieving fiat prices...')
                return {}

            data = {symb: float(value) for symb, value in data.items()} # convert all fiat prices in float number
            data['currency'] = self.currency
            return data
        
        lib.printFail(f'Kucoin: error while retrieving fiat prices..., {body["msg"]}')
        return {}

    # get market data of symbol e.g. ETH-USDT
    # if you don't know how symbols are constructed
    # retrieve it all using kc_api.getSymbols function
    def getMarketData(self, symbol: str):
        if '-' not in symbol: 
            lib.printFail(f'Kucoin: uncorrect symbol {symbol}')
            return {}

        endpoint = '/api/v1/market/stats'
        url = self.base + endpoint
        param = {'symbol': symbol}
        res = get(url, params=param)
        body = loads(res.text)

        if res.status_code == 200 and body['code'] == '200000':
            data: dict = body['data']

            # deleting entries in dict
            for n in ['time','changeRate', 'changePrice', 'high', 'low', 'vol', 
                      'volValue', 'averagePrice', 'takerFeeRate',  
                      'makerFeeRate', 'takerCoefficient', 'makerCoefficient']:
                del data[n]

            for key, val in data.items():
                if key == 'symbol': continue
                data[key] = float(val)
            return data
        
        lib.printFail(f'Kucoin: unable to retrieve market data of {symbol}, error: {body["msg"]}')
        return {}

    # https://www.kucoin.com/docs/rest/spot-trading/orders/place-order 
    # https://www.kucoin.com/docs/rest/spot-trading/orders/place-order-test
    def placeOrder(self, symbol: str, side: str, size: float): 
        # FIXME
        if self.error or side.lower() not in ['buy', 'sell']:
            return False

        endpoint = '/api/v1/orders/test' # TODO switch from test endpoint
        url = self.base+endpoint
        now = int(time() * 1000)
        data = {
            'clientOid': str(uuid4()).replace("-",""),
            'side': side,
            'symbol': symbol,
            'type': 'market',
            'size': str(size)
        }
        #endpoint += f'?clientOid={clientOid}&side={side}&symbol={symbol}&type=market&size={size}'
        headers = self.__getHeader(endpoint, now, data, True)

        res = post(url, headers=headers, data=data)
        print(res.status_code, res.json())

    def getOrders(self):
        lib.printFail('Unimplemented...')
        exit()

        if self.error:
            return False
        now = int(time() * 1000)
        endpoint = f'/api/v1/orders?currentPage=1' # 
        url = self.base+endpoint

        res = get(url, headers=self.__getHeader(endpoint, now)) # open('test_kc_api.json', 'w').write(json.dumps(json.loads(res.text), indent=4))

        orders = DataFrame({
            'id': [],

            'asset_in_name': [], 
            'asset_in_amount': [],

            'asset_out_name': [], 
            'asset_out_amount': [], # take fee into account ? 

            # 'to_stablecoin': [], # bool
            'created_at': []
        })
        
        body = loads(res.text)
        if res.status_code == 200 or body['code'] != '200000':
            
            items = body['data']['items'] # list of orders

            for item in items:
                action = item['side']
                symbols: list[str] = item['symbol'].split('-')

                dealSize = item['dealSize']
                dealFunds = item['dealFunds']

                if action == 'sell':
                    order = DataFrame({'id': [item['id']], 'asset_in_name': [symbols[0]], 'asset_in_amount': [dealSize], 'asset_out_name': [symbols[1]], 'asset_out_amount': [dealFunds], 'created_at': [item['created_at']/1000]})
                    # orders = concat([orders, order], axis=0, ignore_index=True)
                    # print(f'{dealSize} {symbols[0]} sold for {dealFunds} {symbols[1]}')
                elif action == 'buy':
                    order = DataFrame({'id': [item['id']], 'asset_in_name': [symbols[1]], 'asset_in_amount': [dealFunds], 'asset_out_name': [symbols[0]], 'asset_out_amount': [dealSize], 'created_at': [item['created_at']/1000]})
                    # orders = concat([orders, order], axis=0, ignore_index=True)
                    # print(f'{dealFunds} {symbols[1]} bought {dealSize} {symbols[0]}')

        else: print(res.status_code); print(body)

        return orders

# retrieve price of 'symbol' 
# @param symbol string eg. "EURUSD=X"
# @return float, False if symbol cannot be found
def yahooGetPriceOf(symbol: str):
    try:
        data = download(tickers = symbol, period ='1d', interval = '1m', progress=False)
        return data.tail()['Close'][4]
    except _utils.RemoteDataError: 
        # if symbol cannot be found
        lib.printFail(f'Error getting price of {symbol}')
        return False

def getTicker(ticker: str, start: str, end: str) -> float:
    # start and end format: yyyy-mm-dd
    if lib.isValidDate(start, '%Y-%m-%d') and lib.isValidDate(end, '%Y-%m-%d'):
        data = Ticker(ticker)
        return data.history(period='1mo', interval='1d')['Close'][0]
    else: 
        print('error')
        return 0

if __name__ == '__main__':
    a = kc_api('EUR')
    # a.placeOrder('ETH-USDT', 'buy', 0.000100)
    d = a.getFiatPrice(['usdc'])
    print(d)
    #a.getMarketData(5)