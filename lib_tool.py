from json import load, loads, decoder
from datetime import datetime, timedelta
from os import environ

class lib:
    # this color below works only on unixlike shell
    # unsupported OS will use plain text without color
    OKGREEN = '\033[92m'
    WARNING_YELLOW = '\033[93m'
    FAIL_RED = '\033[91m'
    ENDC = '\033[0m'
    WELCOME_BLUE = '\033[94m'
    ASK_USER_INPUT_PURPLE = '\033[95m'

    @staticmethod
    def logConsole(text: str, color: str, end: str):
        if 'SHELL' not in environ.keys():
            print(text, end=end)
        else:
            print(f'{color}{text} {lib.ENDC}', end=end)

    @staticmethod
    def printOk(text: str, end = "\n"):
        lib.handlePrint(text, color=lib.OKGREEN, symbol="[+]", end=end)

    @staticmethod
    def printWarn(text: str, end = "\n"):
        lib.handlePrint(text, color=lib.WARNING_YELLOW, symbol="[+]", end=end)

    @staticmethod
    def printFail(text: str, end = "\n"):
        lib.handlePrint(text, color=lib.FAIL_RED, symbol="[-]", end=end)

    @staticmethod
    def printWelcome(text: str, end = "\n"):
        lib.handlePrint(text, color=lib.WELCOME_BLUE, symbol="[*]", end=end, doubleSymbol=True)

    @staticmethod
    def printAskUserInput(text: str, end= "\n"):
        lib.handlePrint(text, color=lib.ASK_USER_INPUT_PURPLE, symbol="[!]", end=end)

    @staticmethod
    def handlePrint(text: str, color: str, symbol: str, end = "\n", doubleSymbol = False):
        temp = lib.formatInput(text)
        if temp[1]:
            for item in temp[0]:
                if lib.ENDC in item:
                    item = item.replace(lib.ENDC, lib.ENDC+color)
                lib.logConsole(f'{symbol} {item} {symbol if doubleSymbol else ""}', color=color, end=end)
        else: lib.logConsole(f'{symbol} {temp[0]}', color, end)

    @staticmethod
    def formatInput(text: str):
        if "\n" in text:
            text = text.split('\n') 
            return text, True
        return text, False

    @staticmethod
    def getSettings() -> dict:
        return lib.loadJsonFile('settings.json')

    @staticmethod
    def loadJsonFile(file: str) -> dict:
        with open(file,'r') as f:
            if(f.readable):
                return load(f) # json.load settings in a dict
            else: 
                lib.printFail('Error on reading settings')
                exit()

    @staticmethod
    def getNextDay(day: str, format = '%d/%m/%Y') -> datetime: 
        return lib.parse_formatDate(day, format) + timedelta(days=1)
    
    @staticmethod
    def getPreviousDay(day: str, format = '%d/%m/%Y') -> datetime: 
        return lib.parse_formatDate(day, format) - timedelta(days=1)
    
    @staticmethod
    def getCurrentDay(format = '%d/%m/%Y') -> str:
        return datetime.today().date().strftime(format)
    
    @staticmethod
    def parse_formatDate(day: str, format = '%d/%m/%Y') -> datetime:
        if type(day) == datetime:
            return day
        return datetime.strptime(day.split(' ')[0], format)

    @staticmethod
    # given a list of float
    def calcAssetVolatility(total_value: list ):
        volatility = 0
        n = 0
        for i in range(len(total_value)-1):
            if total_value[i+1] == total_value[i]:
                continue

            dayVolatilityPercentage = abs((total_value[i+1]-total_value[i])/ total_value[i])
            volatility += dayVolatilityPercentage
            n +=1
        
        # calc avarage volatility and * 100 to get percentage format
        return round((volatility / n)*100, 4) 

    @staticmethod
    def isValidDate(date: str, format = '%d/%m/%Y'):
        try:
            lib.parse_formatDate(date, format)
        except:
            return False
        return True

    @staticmethod
    def getIndexOfDate(dateToFind: str, list: list):
        for (i, item) in enumerate(list):
            if lib.parse_formatDate(item) == lib.parse_formatDate(dateToFind):
                return i, True
        return 0, False

    @staticmethod
    def getUserInputDate(listOfDate):
        while True:
            try:
                temp = input()
                if len(temp) == 0:
                    return 'default'
                if lib.isValidDate(temp):
                    index = lib.getIndexOfDate(temp, listOfDate)
                    if index[1] == False:
                        raise ValueError
                    return index[0]
                else: raise ValueError
            except ValueError:
                lib.printFail('Invalid date, enter a valid date to continue')

    @staticmethod
    # read json file, update
    def updateJson(file_path: str, date_to_update: str, new_record: str) -> tuple[bool, str]:
        new_file = ''
        formated_date_to_update = datetime.strptime(date_to_update,  '%d/%m/%Y')
        date_file_line = datetime(1970, 1, 1)
        isFirst = True

        with open(file_path, 'r') as f:
            for line in f:
                try:
                    date = loads(line)
                except decoder.JSONDecodeError: # sometimes it throw error on line 2
                    pass

                # parse date and convert to dd/mm/yyyy
                date_file_line = datetime.strptime(date['date'].split(' ')[0], '%d/%m/%Y')
                if isFirst: 
                    if formated_date_to_update < date_file_line: 
                        # if date_to_update is before the first line' date
                        # add new_record at the beginning of file_path
                        new_file = new_record + str(open(file_path, 'r').read())
                        isFirst = False
                        break

                if date_file_line == formated_date_to_update:
                    new_file += new_record # insert new_record instead of old record(line)
                else:
                    new_file += line # add line without modifing it

            if formated_date_to_update > date_file_line:
                # if date_to_update is newer of last file's date 
                # add new record at the end of file
                new_file += new_record
            
        with open(file_path, 'w') as f:
            if f.writable: f.write(new_file)
            else: return False, new_file # return new_file to eventually retry later
        return True, ''
