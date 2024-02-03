from src.lib_tool import lib
from typing import Any
from time import sleep
from requests import get, Response
from json import dumps, loads
from os import getcwd
from os.path import join

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

        cwd = getcwd()
        self.cacheFile = join(cwd, 'cache', 'cached_id_CG.json')
        self.all_id_path = join(cwd, 'cache', 'all_id_CG.json')
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

        with open(self.all_id_path, 'w') as f:
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
            'precision': 10
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