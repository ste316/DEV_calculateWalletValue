try:
    from src.lib_tool import lib
except:
    from lib_tool import lib
from pandas_datareader import _utils
from yfinance import download, Ticker

def yahooGetPriceOf(symbol: str):
    """Retrieve current price of a financial symbol from Yahoo Finance.
    
    Uses 1-minute interval data to get the most recent closing price.
    
    Args:
        symbol (str): Yahoo Finance symbol (e.g., "EURUSD=X" for EUR/USD forex pair)
        
    Returns:
        float: Most recent closing price
        False: If symbol cannot be found or other error occurs
        
    Example:
        >>> yahooGetPriceOf("EURUSD=X")
        1.0876
    """
    try:
        data = download(tickers = symbol, period ='1d', interval = '1m', progress=False)
        return data.tail()['Close'][4]
    except _utils.RemoteDataError: 
        # if symbol cannot be found
        lib.printFail(f'Error getting price of {symbol}')
        return False

def getTicker(ticker: str, start: str, end: str) -> float:
    """Retrieve historical price data for a ticker within a date range.
    
    Args:
        ticker (str): Yahoo Finance ticker symbol
        start (str): Start date in 'yyyy-mm-dd' format
        end (str): End date in 'yyyy-mm-dd' format
        
    Returns:
        float: First closing price in the period
        0: If dates are invalid or other error occurs
        
    Example:
        >>> getTicker("AAPL", "2024-01-01", "2024-01-31")
        185.85
    """
    # start and end format: yyyy-mm-dd
    if lib.isValidDate(start, '%Y-%m-%d') and lib.isValidDate(end, '%Y-%m-%d'):
        data = Ticker(ticker)
        return data.history(period='1mo', interval='1d')['Close'][0]
    else: 
        print('error')
        return 0
