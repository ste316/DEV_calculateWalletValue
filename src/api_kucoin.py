try:
    from src.lib_tool import lib
except:
    from lib_tool import lib
from time import time
from requests import get, post
from json import dumps, loads
from base64 import b64encode
from hashlib import sha256
from time import time
from hmac import new
from pandas import DataFrame
from kucoin.client import Trade, User
from os.path import join
from os import getcwd

class kc_api:
    def __init__(self, currency: str) -> None:
        """Initialize Kucoin API wrapper with authentication and configuration.
        
        Loads API credentials from kc_info.json and initializes Trade and User clients.
        Validates API credentials and sets up base configuration.
        
        Args:
            currency (str): Base currency for price quotes (e.g., 'USD', 'EUR')
            
        Attributes:
            error (bool): True if initialization failed (e.g., missing API credentials)
        """
        _kc_info = 'kc_info.json'
        self.kc_info = lib.loadJsonFile(_kc_info)
        self.api_key: str = self.kc_info['key']
        self.api_secret: str = self.kc_info['secret']
        self.api_passphrase: str = self.kc_info['passphrase']
        self.symbol_blacklist: list[str] = self.kc_info['symbol_blacklist']
        self.base = 'https://api.kucoin.com'
        self.error = False
        self.currency = currency.upper()
        # KC client to make orders
        self.client = Trade(key=self.api_key, secret=self.api_secret, passphrase=self.api_passphrase, is_sandbox=False, url='')
        self.user = User(key=self.api_key, secret=self.api_secret, passphrase=self.api_passphrase, is_sandbox=False, url='')
        # self.kcMarket = Market(key=self.api_key, secret=self.api_secret, passphrase=self.api_passphrase, is_sandbox=False, url='')

        checklist = [len(x.replace(' ', ''))>0 for x in [self.api_key, self.api_passphrase, self.api_secret] ]
        if not all(checklist): # if any api info is empty -> error
            lib.printFail(f'Kucoin: failed to load Kucoin API data from {_kc_info}')
            self.error = True
    
    def __isKucoinApiUp(self) -> bool:
        """Check if Kucoin API is accessible.
        
        Returns:
            bool: True if API responds with success code, False otherwise
        """
        endpoint = '/api/v1/timestamp'
        url = self.base + endpoint
        res = get(url)
        body = loads(res)

        if res.status_code == 200 and body['code'] == '200000': return True
        return False

    def __prepareHeader(self, str_to_sign: str):
        """Prepare authentication signatures for API requests.
        
        Creates base64 encoded signatures for both the request and API passphrase.
        
        Args:
            str_to_sign (str): String to be signed for authentication
            
        Returns:
            tuple: (signature, passphrase) - Base64 encoded authentication values
        """
        signature = b64encode(new(self.api_secret.encode('utf-8'), str_to_sign.encode('utf-8'), sha256).digest())
        passphrase = b64encode(new(self.api_secret.encode('utf-8'), self.api_passphrase.encode('utf-8'), sha256).digest())
        return signature, passphrase
    
    def __getHeader(self, endpoint: str, now: int, json_data: dict = {}, post: bool = False): # see https://www.kucoin.com/docs/basic-info/connection-method/authentication/signing-a-message
        # gen http header to auth
        # param:
        #       endpoint: api route
        #       now: unix-time in seconds
        #       post: use post method
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

    def getBalance(self):
        """Retrieve Kucoin balance and save to input_kc.csv.
        
        Fetches account balances, transfers any main account assets to trading account,
        formats data and saves to CSV. Handles blacklisted symbols and filters zero balances.
        
        Returns:
            bool: True if successful, False if error occurred
        """
        def handleCurrency2Transfer(df: DataFrame):
            currency = df['currency'].to_list()
            balance = df['balance'].to_list()
            return {symbol: value for symbol, value in zip(currency, balance) if symbol not in self.symbol_blacklist}

        def transfer2TradingAcc(need_to_transfer: dict):
            for symbol, amt in need_to_transfer.items():
                self.user.inner_transfer(currency=symbol, from_payer='main', to_payee='trade', amount=amt)
        
        if self.error:
            return False
        
        endpoint = '/api/v1/accounts'
        url = self.base+endpoint
        now = int(time() * 1000)
        res = get(url, headers=self.__getHeader(endpoint, now))
        body = loads(res.text) # load response body data
        try:
            if res.status_code == 200 or body['code'] != '200000':
                df = DataFrame.from_records(body['data'], exclude=['available','holds', 'id'])
                # assets that are in 'main' account, with balance more than 0
                # needs to be transfered to 'trading' account, in order to be available for trading
                need_to_transfer = handleCurrency2Transfer(df[ (df['type'] == 'main') & (df['balance'].values.astype(float) > 0) ])
                transfer2TradingAcc(need_to_transfer)

                df.drop(['type'], axis=1, inplace=True)
                # rename column, convert qta to float, delete rows with qta <= 0
                df.rename({'currency': 'symbol', 'balance': 'qta'}, axis=1, inplace=True)
                # filter using the blacklist, can be edit in kc_info.json
                df = df[~df['symbol'].isin(self.symbol_blacklist)]
                convert_dict = {'symbol': str, 'qta': float }
                df = df.astype(convert_dict)
                df = df[df['qta'] > 0]
                
                # add missing columns to match input.csv columns
                df['label'] = 'kucoin'
                df['liquid_stake'] = 'no'
                df['symbol'] = df['symbol'].str.lower()

                df.to_csv('input_kc.csv', sep=',', index=False)
                return True
            else: 
                raise Exception
        except Exception as e:
            lib.printFail(f'Kucoin: failed to retrieve KC balance, error msg: {body["msg"] if "msg" in body else e}')
            return False

    def getSymbols(self):
        """Retrieve all tradable pairs from Kucoin.
        
        Downloads and saves trading pair information to cache/kucoin_symbol.csv.
        
        Returns:
            bool: True if successful, False if error occurred
        """
        endpoint = '/api/v2/symbols'
        url = self.base + endpoint
        
        res = get(url)
        body = loads(res.text)

        if res.status_code == 200 and body['code'] == '200000':
            data = body['data']
            df = DataFrame.from_records(data, 
                exclude=['market', 'quoteMinSize', 'name',
                        'baseMaxSize', 'quoteMaxSize',
                        'priceIncrement', 'priceLimitRate', 'isMarginEnabled'])
            
            df.to_csv(join(getcwd(), 'cache', 'kucoin_symbol.csv'), sep=',', index=False)
            return True
        
        lib.printFail(f'Kucoin: unable to download symbols error: {body["msg"]}')
        return False

    def getFiatPrice(self, numerator_assets: list[str], currency: str = '', include_currency: bool = False) -> dict[str, float]:
        """Get Kucoin's prices for specified assets.
        
        Note: Should not be used as price oracle like CoinGecko, as prices are specific to Kucoin markets.
        
        Args:
            numerator_assets (list[str]): List of assets to get prices for (e.g., ['btc', 'eth'])
            currency (str, optional): Override default currency. Defaults to self.currency.
            include_currency (bool, optional): Include currency in response. Defaults to False.
            
        Returns:
            dict[str, float]: Asset symbols mapped to their prices
        """
        numerator_assets = [c.upper() for c in set(numerator_assets)]
        endpoint = '/api/v1/prices'
        url = self.base + endpoint
        param = {
            'currencies': ','.join(numerator_assets).upper(), # CURRENCIES refer to the asset at numerator -> 1/3
            # comma separated cryptocurrencies to be converted into fiat, e.g.: BTC,ETH
            'base': currency if currency != '' else self.currency # BASE refer to the asset at denominator 1/3 <-
        }

        res = get(url, params=param)
        body = loads(res.text)
        
        if res.status_code == 200 and body['code'] == '200000':
            data: dict = body['data']

            if len(data) != len(numerator_assets) and len(data) > 0:
                # NOT all fine, NOT all good broda
                missing = list(set(numerator_assets)-set(data.keys()))
                lib.printFail(f'Kucoin: unable to retrieve all fiat prices, missing: [{len(missing)}] {missing}')
            elif len(data) == 0:
                lib.printFail(f'Kucoin: error while retrieving fiat prices for {numerator_assets}')
                return {}

            data = {symb: float(value) for symb, value in data.items()} # convert all fiat prices in float number
            if include_currency: data['currency'] = self.currency
            return data
        
        lib.printFail(f'Kucoin: error while retrieving fiat prices..., {body["msg"]}')
        return {}

    def getMarketData(self, symbol: str):
        """Get market data for a specific trading pair.
        
        Args:
            symbol (str): Trading pair symbol (e.g., 'ETH-USDT')
            Note: Use getSymbols() to see available trading pairs
            
        Returns:
            dict: Market data including last price and trading volume, empty dict if error
        """
        if '-' not in symbol: 
            lib.printFail(f'Kucoin: getMarketData: incorrect symbol {symbol}')
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

    def placeOrder(self, symbol: str, side: str, size: float) -> str: 
        """Place a market order on Kucoin.
        
        For buy orders, size must be in quote currency (e.g., USDC)
        For sell orders, size must be in base currency (e.g., SOL)
        
        Args:
            symbol (str): Trading pair symbol (e.g., 'SOL-USDC')
            side (str): 'buy' or 'sell'
            size (float): Order size in appropriate currency
            
        Returns:
            str: Order ID if successful, empty string if failed
        """
        if self.error or side.lower() not in ['buy', 'sell']:
            return False

        try:
            if side == 'buy':
                order_id = self.client.create_market_order(symbol, side, funds=str(size))    
            else: #    'sell'
                order_id = self.client.create_market_order(symbol, side, size=str(size))
        except Exception as e :
            temp = str(e).split('-', 2)
            status_code, msg = temp[0], temp[1]
            msg = loads(msg)
            lib.printFail(f'Kucoin: symbol: {symbol} {side} size: {size} {symbol.split("-")[1] if side=="buy" else symbol.split("-")[0]} status code: {status_code}, body: {msg["msg"]} KC error: {msg["code"]}')
            return ''
        
        return order_id

    def getOrders(self):
        """Retrieve order history from Kucoin.
        
        Note: Currently unimplemented
        
        Raises:
            SystemExit: Always exits as function is unimplemented
        """
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
    
if __name__ == '__main__':
    pass
    # a = kc_api('EUR')
    # a.getBalance()
    # a.transfer2TradingAcc()
    # print(a.placeOrder('TIA-USDT', 'buy', 1))
    # print(a.placeOrder('ETH-USDT', 'sell', 0.0001))
    # d = a.getFiatPrice(['usdc'])
    # print(d)
    # print(a.getFiatPrice(['BTC','eth']))