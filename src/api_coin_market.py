try:
    from src.lib_tool import lib
except:
    from lib_tool import lib
from time import sleep
from json import dumps, loads
from requests import Session
from requests.exceptions import ConnectionError, Timeout, TooManyRedirects
from random import randrange
from os.path import join
from os import getcwd

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
        cwd = getcwd()
        self.cacheFile = join(cwd, 'cache', 'cached_id_CMC.json')
        self.all_id_path = join(cwd, 'cache', 'all_id_CMC.json')
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
        res = self.session.get(self.baseurl+url) # add error handling TODO
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
            data = loads(open(self.all_id_path, 'r').read())['data'] # once in a while run fetchID() to update it

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