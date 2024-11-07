from src.api_yahoo_f import yahooGetPriceOf
from src.lib_tool import lib
from matplotlib.pyplot import figure, title, show, plot, xticks
from seaborn import set_style
from json import loads

# 
# See value of your crypto/total wallet over time
# based on previous saved data in walletValue.json
# 
class walletBalanceReport:
    """Generate reports and visualizations for historical wallet balances.
    
    Analyzes and visualizes total wallet value over time, supporting both
    crypto-only and total portfolio views. Uses data from walletValue.json.
    """

    def __init__(self, type: str) -> None:
        """Initialize wallet report generator with settings and type.
        
        Args:
            type (str): Report type ('crypto' or 'total')
            
        Raises:
            SystemExit: If invalid report type provided
        """
        self.settings = lib.getSettings()
        self.config = lib.getConfig()
        self.version = self.config['version']
        self.supportedFiat = self.config['supportedFiat']
        self.supportedStablecoin = self.config['supportedStablecoin']
        self.settings['wallet_path'] = self.settings['path']+ '\\walletValue.json'
        self.include_total_invested = False 
        self.data = {
            'date': [],
            'total_invested': [],
            'total_value': [],
            'currency': self.settings['currency']
        }
        lib.printWelcome(f'Welcome to Wallet Balance Report!')
        lib.printWarn(f'Currency: {self.settings["currency"]}')
        # set type
        # N.B. <type> is passed in arguments when you execute the script
        if type in ['crypto', 'total']: 
            self.type = type
            lib.printWarn(f'Report type: {self.type} wallet')
        else:
            lib.printFail('Unexpected error, pass the correct argument, run again with option --help')
            exit()

    def getForexRate(self, line: dict):
        """Get forex rate for currency conversion.
        
        Handles EUR/USD conversions using Yahoo Finance rates.
        
        Args:
            line (dict): Data line containing currency information
            
        Returns:
            float: Exchange rate if conversion needed
            False: If no conversion needed or currencies not supported
        """
        if self.settings["currency"] == 'EUR' and line['currency'] == 'USD':
            # get forex rate using yahoo api
            return yahooGetPriceOf(f'{self.settings["currency"]}{line["currency"]}=X')
        elif self.settings["currency"] == 'USD' and line['currency'] == 'EUR':
            return yahooGetPriceOf(f'{line["currency"]}{self.settings["currency"]}=X')
        else:
            return False

    def chooseDateRange(self):
        """Allow user to select date range for analysis.
        
        Prompts for start and end dates, with defaults being first and last
        recorded dates. Validates that end date is after start date.
        Updates data arrays to contain only values within selected range.
        """
        while True:
            lib.printAskUserInput("Choose a date range, enter dates one by one")
            lib.printAskUserInput(f"{lib.FAIL_RED}NOTE!{lib.ENDC} default dates are the first and last recorded date on walletValue.json\nFirst date")
            lib.printAskUserInput(f'\tinsert a date, press enter to use the default one, {lib.FAIL_RED} format: dd/mm/yyyy {lib.ENDC}')
            firstIndex = lib.getUserInputDate(self.data['date'])
            if firstIndex == 'default':
                firstIndex = 0
            lib.printAskUserInput("Last date:")
            lib.printAskUserInput(f'\tinsert a date, press enter to use the default one, {lib.FAIL_RED} format: dd/mm/yyyy {lib.ENDC}')
            lastIndex = lib.getUserInputDate(self.data['date'])
            if lastIndex == 'default':
                lastIndex = len(self.data['date'])-1
            if lastIndex > firstIndex:
                # to understand why is lastIndex+1 search python list slicing
                self.daterange = tuple([firstIndex, lastIndex+1])
                self.data['date'] = self.data['date'][firstIndex:lastIndex+1]
                self.data['total_value'] = self.data['total_value'][firstIndex:lastIndex+1]
                break
            else: lib.printFail("Invalid range of date")

    def loadDatetime(self) -> None:
        """Load and process historical wallet values from JSON file.
        
        Handles:
        - Loading appropriate values based on report type
        - Currency conversions if needed
        - Filling gaps in time series with previous values
        - Optional inclusion of total invested amounts
        
        Note: Similar to cryptoBalanceReport.retrieveDataFromJson
        """
        lib.printWarn(f'Loading value from {self.settings["wallet_path"]}...')
        lib.printWarn('Do you want to display total invested in line chart?(Y/n)')
        if input().lower() in ['y', 'yes', 'si', '']:
            self.include_total_invested = True
        
        with open(self.settings['wallet_path'], 'r') as f:
            firstI = True # first interaction
            f = list(f) # each element of 'f' is a line
            for i, line in enumerate(f):
                if type(line) != dict:
                    line = loads(line)

                # check field needed
                if 'total_crypto_stable' not in line.keys() and self.type == 'crypto':
                    continue
                if 'total_value' not in line.keys() and self.type == 'total':
                    continue
                if self.include_total_invested:
                    if 'total_invested' not in line.keys():
                        continue

                temp_date = lib.parse_formatDate(line['date'], format='%d/%m/%Y %H', splitBy=':') # parse date format: dd/mm/yyyy hh
                if self.type == 'total':
                    total_value = line['total_value']
                elif self.type == 'crypto':
                    total_value = line['total_crypto_stable']
                else: 
                    lib.printFail('Unexpected error')
                    exit()

                # if currency of json line is different from settings.json currency
                if line['currency'] != self.settings['currency']: 
                    rate = self.getForexRate(line)
                    if not rate:
                        lib.printFail(f'Currency not supported, check {self.settings["wallet_path"]} line: {i+1}')
                        exit()
                    total_value /= rate # convert value using current forex rate

                if firstI:
                    self.data['date'].append(temp_date)
                    self.data['total_value'].append(total_value)
                    if self.include_total_invested: self.data['total_invested'].append(line['total_invested'])
                    firstI = False
                    continue
                
                # calculate the last date in list + 1 hour
                lastDatePlus1h = lib.getNextHour(self.data['date'][-1])
                # check if temp_date (new date to add) is equal to lastDatePlus1h
                if temp_date == lastDatePlus1h:
                    self.data['total_value'].append(total_value)
                    if self.include_total_invested:  self.data['total_invested'].append(line['total_invested'])
                else: # maybe there will be a bug if temp_date < lastDatePlus1h ???
                    self.data['total_value'].append(self.data['total_value'][-1])
                    if self.include_total_invested: self.data['total_invested'].append(self.data['total_invested'][-1])
                    f.insert(int(i)+1, line)
                    # add line again because we added the same amount of the last in list
                    # otherwise it didn't work properly

                self.data['date'].append(lastDatePlus1h)

    def __calcTotalVolatility(self):
        """Calculate total portfolio volatility.
        
        TODO: Currently unimplemented
        
        Raises:
            SystemExit: Always exits as function is unimplemented
        """
        # TODO FIXME 
        if True:
            lib.printFail(f'{self.__name__} Unimplemented function')
            exit()
        # define which assets to calc volatility on
        assets = dict()
        with open(self.settings['wallet_path'], 'r') as f:
            line = loads(list(f)[-1])
            crypto_list = line['crypto'][1:]
            for item in crypto_list:
                if item[0] != self.data['currency']:
                    assets[item[0]] = item[1]/line['total_value']
        
        # group data using date of records
        crypto_data = dict()
        with open(self.settings['wallet_path'], 'r') as f:
            for line in f:
                line = loads(line)
                crypto_list = line['crypto'][1:]
                date = line['date'].split(' ')[0]
                total_val = line['total_value']
                temp = dict()
                for crypto in crypto_list:
                    if crypto[0] in assets.keys():
                        temp[crypto[0]] = crypto[2]/crypto[1]
                
                crypto_data[date] = temp

        #print(f'{crypto_data=}')
        # group data using ticker
        volatility = dict()
        for (date, crypto) in crypto_data.items():
            for (ticker, value) in crypto.items():
                if ticker not in volatility.keys():
                    volatility[ticker] = [value]
                else:
                    volatility[ticker].append(value)

        # TODO fix minor number of record
        #print(f'{volatility["EWT"]=}')
        
        print(assets)
        for (ticker, arr) in volatility.items():
            volatility[ticker] = lib.calcAssetVolatility(arr)
        
        vol = int()
        for (ticker, parz) in volatility.items():
            vol += parz * assets[ticker]

        vol /= sum(assets.values())

        print(volatility, vol)

    def genPlt(self):
        """Generate and display visualization of wallet value over time.
        
        Creates line chart showing:
        - Total wallet value over time (red line)
        - Optional total invested amount (if enabled)
        
        Includes:
        - Title with wallet type and date range
        - Performance metrics
        - Volatility percentage
        - Currency information
        """
        lib.printWarn(f'Creating chart...')
        # set background [white, dark, whitegrid, darkgrid, ticks]
        set_style('darkgrid') 
        # define size of the image
        figure(figsize=(7, 6), tight_layout=True)
        if self.include_total_invested: plot(self.data['date'], self.data['total_invested'])
        plot(self.data['date'], self.data['total_value'], color='red', marker='')

        # calc performance of the selected period
        performance = (self.data["total_value"][-1]-self.data["total_value"][0])/self.data["total_value"][0] * 100
        title(f'{self.type.capitalize()} balance from {self.data["date"][0].strftime("%d %b %Y")} to {self.data["date"][-1].strftime("%d %b %Y")}\nVolatility percentage: {round(self.volatility, 2)}% \nPerformance: {round(performance, 2)}% \nCurrency: {self.settings["currency"]}', fontsize=14, weight='bold')
        # changing the fontsize and rotation of x ticks
        xticks(fontsize=6.5, rotation = 45)
        show()

    def run(self) -> None:
        """Main execution loop for wallet report generation.
        
        Workflow:
        1. Load historical data
        2. Get date range from user
        3. Calculate volatility
        4. Generate visualization
        5. Optionally repeat with different type/date range
        """
        while True:
            self.loadDatetime()
            self.chooseDateRange()
            # self.volatility = lib.calcAssetVolatility(self.data['total_value']) # self.calcTotalVolatility()
            self.volatility = 0
            self.genPlt()

            lib.printAskUserInput('Do you want to show another graph? (y/N)')
            temp = lib.getUserInput()
            if temp.replace(' ', '') == '' or temp in ['n', 'N']:
                break
            
            lib.printWarn('Choose type: crypto or total? ')
            type_ = input()
            self.__init__(type_)
