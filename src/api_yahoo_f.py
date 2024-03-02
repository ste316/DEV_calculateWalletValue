try:
    from src.lib_tool import lib
except:
    from lib_tool import lib
from pandas_datareader import _utils
from yfinance import download, Ticker

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
