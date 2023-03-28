from json import load, loads, decoder, dumps
from datetime import datetime, timedelta
from os import environ, path, getcwd, mkdir

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
        for item in temp[0]:
            if lib.ENDC in item:
                item = item.replace(lib.ENDC, lib.ENDC+color)
            lib.logConsole(f'{symbol} {item} {symbol if doubleSymbol else ""}', color=color, end=end)

    @staticmethod
    def formatInput(text: str):
        if "\n" in text:
            text = text.split('\n') 
            return text, True
        return [text], False

    @staticmethod
    def getSettings() -> dict:
        return lib.loadJsonFile('settings.json')

    @staticmethod
    def getConfig() -> dict:
        return lib.loadJsonFile('config.json')

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
    def calcAssetVolatility(total_value: list):
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
        found = False
        index = 0
        for (i, item) in enumerate(list):
            if lib.parse_formatDate(item) == lib.parse_formatDate(dateToFind):
                found = True; index = i
                break
        return index, found

    @staticmethod
    def getUserInputDate(listOfDate):
        while True:
            try:
                temp = lib.getUserInput().replace(' ', '')
                if len(temp) == 0:
                    return 'default'
                if lib.isValidDate(temp):
                    index, found = lib.getIndexOfDate(temp, listOfDate)
                    if found == False:
                        raise ValueError
                    return index
                else: raise ValueError
            except ValueError:
                lib.printFail('Invalid date, enter a valid date to continue or press ^C')

    @staticmethod
    def getUserInput() -> str:
        while True:
            try:
                return input()
            except KeyboardInterrupt:
                lib.printWarn('^C detected, aborting...')
                exit()

    @staticmethod
    # read json file, update
    def updateJson(file_path: str, date_to_update: str, new_record: str) -> tuple[bool, str]:
        new_file = ''
        formated_date_to_update = datetime.strptime(date_to_update,  '%d/%m/%Y')
        date_file_line = datetime(1970, 1, 1)
        isFirst = True

        with open(file_path, 'r') as f:
            for (i, line) in enumerate(f):
                try:
                    date = loads(line)
                except decoder.JSONDecodeError as e: # sometimes it throw error on line 2
                    lib.printFail(f'Json error, {file_path=} {e}')
                    pass

                # parse date and convert to dd/mm/yyyy
                date_file_line = datetime.strptime(date['date'].split(' ')[0], '%d/%m/%Y')
                if isFirst: 
                    if formated_date_to_update < date_file_line: 
                        # if date_to_update is before the first line's date
                        # add new_record at the beginning of file_path
                        new_file = new_record + str(open(file_path, 'r').read())
                        isFirst = False
                        break

                if date_file_line == formated_date_to_update:
                    new_file += new_record+'\n' # insert new_record instead of old record(line)
                else:
                    new_file += line # add line without modifing it

            if formated_date_to_update > date_file_line:
                # if date_to_update is newer of last file's date 
                # add new record at the end of file
                new_file += new_record+'\n'
            
        with open(file_path, 'w') as f:
            if f.writable: f.write(new_file)
            else: return False, new_file # return new_file to eventually retry later
        return True, ''

    @staticmethod
    def createCacheFile(dirPath: str) -> bool:
        if path.isdir(dirPath):
            cwd = getcwd() # current working directory
            cg = cwd+'\\cached_id_CG.json'
            cmc = cwd+'\\cached_id_CMC.json'

            if not lib.createFile(cg): lib.printFail(f'Failed to create file: {cg}'); return False
            if not lib.createFile(cmc): lib.printFail(f'Failed to create file: {cmc}'); return False
            
            try:
                with open(cg, 'w') as f:
                    if f.writable(): f.write(dumps({"fixed": [], "used": []}, indent=4))
                    else: return False
            except: lib.printFail(f'Failed to write file: {cg}'); return False

            try:    
                with open(cmc, 'w') as f:
                    if f.writable(): f.write('{}')
                    else: return False
            except: lib.printFail(f'Failed to write file: {cmc}'); return False

            return True
        else: lib.printFail(f'The following directory DON\'T exist: {dirPath}'); return False

    @staticmethod
    def createWorkingFile(dirPath: str):
        if path.isdir(dirPath):
            graficoPath = dirPath+'\\grafico'
            walletJsonPath = dirPath+'\\walletValue.json'
            reportJsonPath = dirPath+'\\report.json'

            try:
                if not path.isdir(graficoPath): mkdir(graficoPath) 
            except FileExistsError: pass
            except FileNotFoundError: lib.printFail('Error on init, check path in settings.json'); return False
            
            if not lib.createFile(walletJsonPath): lib.printFail(f'Failed to create file: {walletJsonPath}'); return False
            if not lib.createFile(reportJsonPath): lib.printFail(f'Failed to create file: {reportJsonPath}'); return False

            return graficoPath, walletJsonPath, reportJsonPath
        else: lib.printFail('Specify a correct path in settings.json'); return False
    
    # return True if file exist or is succesfully created
    # False otherwise
    @staticmethod
    def createFile(filepath) -> bool:
        if not path.exists(filepath):
            try:
                open(filepath, 'w').close()
            except:
                return False
        return True 
