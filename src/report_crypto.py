from src.lib_tool import lib
from matplotlib.pyplot import title, show, subplots, xticks, tight_layout
from seaborn import set_style
from json import loads
from os.path import join

# 
# See amount and fiat value of a single crypto over time
# based on previous saved data in walletValue.json
# a crypto ticker will be asked as user input
# 
class cryptoBalanceReport:
    # Initialization variable and general settings
    def __init__(self) -> None: 
        self.settings = lib.getSettings()
        self.config = lib.getConfig()
        self.version = self.config['version']
        self.supportedFiat = self.config['supportedFiat']
        self.supportedStablecoin = self.config['supportedStablecoin']
        lib.printWelcome(f'Welcome to Crypto Balance Report!')
        self.settings['wallet_path'] = join(self.settings['path'], 'walletValue.json')
        self.cryptos = set()
        self.ticker = []
        self.special_ticker = ['stablecoin']
        self.data = {
            'date': [],
            'amount': [],
            'fiat': []
        }

    # retrieve all cryptos ever recorded in json file
    def retrieveCryptoList(self) -> None:
        with open(self.settings['wallet_path'], 'r') as f:
            for line in f:
                crypto_list = loads(line)['crypto'][1:] # skip the first element, it's ["COIN, QTA, VALUE IN CURRENCY"]
                for sublist in crypto_list:
                    self.cryptos.add(sublist[0])
        
        self.cryptos = sorted(list(self.cryptos))

    # ask a crypto from user input given a list
    def getTickerInput(self) -> None:
        for (i, r) in enumerate(self.cryptos):
            print(f"[{i}] {r}", end='\n')
        
        lib.printWarn('Type one number...')
        gotIndex = False

        while not gotIndex:
            try:
                index = int(lib.getUserInput())
                if index >= 0 and index <= len(self.cryptos):
                    gotIndex = True
                else: lib.printFail('Insert an in range number...')
            except Exception as e:
                print(e)
                lib.printFail('Insert a valid number...')
        
        # handle special_ticker
        #if index == 0: # stablecoin
        #    self.ticker = self.supportedStablecoin
        #else: self.ticker = [self.cryptos[index-len(self.special_ticker)].lower()]
        self.ticker = self.cryptos[index]

    # change the dates between which you view the report
    def chooseDateRange(self):
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
                self.data['amount'] = self.data['amount'][firstIndex:lastIndex+1]
                self.data['fiat'] = self.data['fiat'][firstIndex:lastIndex+1]
                break
            else: lib.printFail("Invalid range of date")

    # collect amount, fiat value and date
    # fill amounts of all empty day with the last available
    # similar to walletBalanceReport.loadDatetime
    def retrieveDataFromJson(self) -> None:
        lib.printWarn(f'Loading value from {self.settings["wallet_path"]}...')
        with open(self.settings['wallet_path'], 'r') as file:
            firstI = True # first interaction
            file = list(file) # each element of file is a line
            for index, line in enumerate(file):
                temp = loads(line)
                # parse the whole date + hours
                temp['date'] = lib.parse_formatDate(temp['date'], format='%d/%m/%Y %H', splitBy=':')
                crypto_list = temp['crypto'][1:] # skip the first element, it's ["COIN, QTA, VALUE IN CURRENCY"]
                isfound = False
                for item in crypto_list:
                    # item[0] is the name of the coin
                    if item[0] == self.ticker: # filter using user's input ticker
                        isfound = True
                        if firstI: # first iteration of external loop
                            self.data['amount'].append(item[1])
                            self.data['fiat'].append(item[2])
                            self.data['date'].append(temp['date'])
                            firstI = False
                            continue
                        
                        # calculate the last date in self.data['date'] + 1 hour
                        lastDatePlus1h = lib.getNextHour(self.data['date'][-1])
                        # check if the new date to add is equal to lastDatePlus1h
                        if temp['date'] == lastDatePlus1h:
                            self.data['amount'].append(item[1])
                            self.data['fiat'].append(item[2])
                        else: # maybe there will be a bug if temp['date'] < lastDatePlus1h ???
                            self.data['amount'].append(self.data['amount'][-1])
                            self.data['fiat'].append(self.data['fiat'][-1])
                            file.insert( int(index)+1, line) 
                            # add line again because we added the same amount of the last in list
                            # otherwise it didn't work properly
                        self.data['date'].append(lastDatePlus1h)
                if isfound == False:
                    if firstI:
                        # begin to add values from when self.ticker exist in json file
                        continue

                    # if self.ticker is not found and it's not the first iteration
                    # it means that self.ticker is being sold so amount = 0 and value = 0
                    self.data['amount'].append(0)
                    self.data['fiat'].append(0)     
                    self.data['date'].append(temp['date'])
                    isfound = False

    def genPlt(self) -> None:
        lib.printWarn(f'Creating chart...')
        # set background [white, dark, whitegrid, darkgrid, ticks]
        set_style('darkgrid') 

        # create 2 subplots for amount and value over time
        fig, ax1 = subplots()
        # tight_layout()
        fig.set_size_inches(8, 6)
        ax2 = ax1.twinx()
        ax1.plot(self.data['date'], self.data['amount'], 'g-')
        ax2.plot(self.data['date'], self.data['fiat'], 'r-')
        ax1.set_xlabel('Dates')
        ax1.set_ylabel('Amount', color='g')
        ax2.set_ylabel('Fiat Value', color='r')
        # add title
        title(f'Amount and fiat value of {self.ticker} in {self.settings["currency"]} from {self.data["date"][0].strftime("%d %b %Y")} to {self.data["date"][-1].strftime("%d %b %Y")}', fontsize=12, weight='bold')
        # changing the fontsize and rotation of x ticks
        xticks(fontsize=6.5, rotation = 45)
        show()

    def run(self) -> None:
        while True:
            self.retrieveCryptoList()
            self.getTickerInput()
            self.retrieveDataFromJson()
            self.chooseDateRange()
            self.genPlt()

            lib.printAskUserInput('Do you want to show another graph? (y/N)')
            temp = lib.getUserInput()
            if temp.replace(' ', '') == '' or temp in ['n', 'N']:
                break
            self.__init__()
