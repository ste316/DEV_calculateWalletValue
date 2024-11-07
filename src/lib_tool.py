from json import load, loads, decoder, dumps
from datetime import datetime, timedelta
from os import environ, path, getcwd, mkdir, name
from pandas import DataFrame
from numpy import log
from numpy import sqrt
from typing import Union

class lib:
    """Utility library providing common functionality for file operations, logging, and data handling.
    
    Contains static methods for:
    - Console output with color support
    - JSON file operations
    - Date handling and formatting
    - User input processing
    - File system operations
    
    Attributes:
        OKGREEN (str): ANSI color code for green text
        WARNING_YELLOW (str): ANSI color code for yellow text
        FAIL_RED (str): ANSI color code for red text
        ENDC (str): ANSI code to reset text color
        WELCOME_BLUE (str): ANSI color code for blue text
        ASK_USER_INPUT_PURPLE (str): ANSI color code for purple text
        bool_term_program (bool): Whether terminal supports ANSI colors
        dir_sep (str): Directory separator for current OS
    """

    # this color below works only on unixlike shell
    # unsupported OS will use plain text without color
    OKGREEN = '\033[92m'
    WARNING_YELLOW = '\033[93m'
    FAIL_RED = '\033[91m'
    ENDC = '\033[0m'
    WELCOME_BLUE = '\033[94m'
    ASK_USER_INPUT_PURPLE = '\033[95m'

    # affect log visualization: colors
    bool_term_program = False 
    if 'TERM_PROGRAM' in environ.keys(): bool_term_program = True
    
    # if os.name == windows use \\ as dir separator
    dir_sep = '/'
    if name == 'nt': dir_sep = '\\'

    @staticmethod
    def logConsole(text: str, color: str, end: str):
        """Print colored text to console if supported, plain text otherwise.
        
        Args:
            text (str): Text to print
            color (str): ANSI color code
            end (str): String to append at end (like print's end parameter)
        """
        if lib.bool_term_program:
            print(f'{color}{text} {lib.ENDC}', end=end)
        else:
            print(text, end=end)

    @staticmethod
    def printOk(text: str, end = "\n"):
        """Print success message in green.
        
        Args:
            text (str): Message to print
            end (str, optional): String to append at end. Defaults to newline.
        """
        lib.handlePrint(text, color=lib.OKGREEN, symbol="[+]", end=end)

    @staticmethod
    def printWarn(text: str, end = "\n"):
        """Print warning message in yellow.
        
        Args:
            text (str): Message to print
            end (str, optional): String to append at end. Defaults to newline.
        """
        lib.handlePrint(text, color=lib.WARNING_YELLOW, symbol="[+]", end=end)

    @staticmethod
    def printFail(text: str, end = "\n"):
        """Print failure/error message in red.
        
        Args:
            text (str): Message to print
            end (str, optional): String to append at end. Defaults to newline.
        """
        lib.handlePrint(text, color=lib.FAIL_RED, symbol="[-]", end=end)

    @staticmethod
    def printWelcome(text: str, end = "\n"):
        """Print welcome message in blue with double symbols.
        
        Args:
            text (str): Message to print
            end (str, optional): String to append at end. Defaults to newline.
        """
        lib.handlePrint(text, color=lib.WELCOME_BLUE, symbol="[*]", end=end, doubleSymbol=True)

    @staticmethod
    def printAskUserInput(text: str, end= "\n"):
        """Print user input prompt in purple.
        
        Args:
            text (str): Message to print
            end (str, optional): String to append at end. Defaults to newline.
        """
        lib.handlePrint(text, color=lib.ASK_USER_INPUT_PURPLE, symbol="[!]", end=end)

    @staticmethod
    def handlePrint(text: str, color: str, symbol: str, end = "\n", doubleSymbol = False):
        """Format and print text with optional symbols and color.
        
        Args:
            text (str): Text to print
            color (str): ANSI color code
            symbol (str): Symbol to prepend (e.g., "[+]")
            end (str, optional): String to append at end. Defaults to newline.
            doubleSymbol (bool, optional): Whether to add symbol at end too. Defaults to False.
        """
        temp = lib.formatInput(text)
        for item in temp[0]:
            if lib.ENDC in item:
                item = item.replace(lib.ENDC, lib.ENDC+color)
            lib.logConsole(f'{symbol} {item} {symbol if doubleSymbol else ""}', color=color, end=end)

    @staticmethod
    def formatInput(text: str):
        """Split input text into lines if it contains newlines.
        
        Args:
            text (str): Input text to format
            
        Returns:
            tuple: ([lines], bool) - List of lines and whether text was split
        """
        if "\n" in text:
            text = text.split('\n') 
            return text, True
        return [text], False

    @staticmethod
    def getSettings() -> dict:
        """Load settings from settings.json file.
        
        Returns:
            dict: Settings dictionary
        """
        return lib.loadJsonFile(f'settings.json')

    @staticmethod
    def getConfig() -> dict:
        """Load configuration from config.json file.
        
        Returns:
            dict: Configuration dictionary
        """
        return lib.loadJsonFile(f'config.json')

    @staticmethod
    def loadJsonFile(file: str) -> dict:
        """Load and parse JSON file.
        
        Args:
            file (str): Path to JSON file
            
        Returns:
            dict: Parsed JSON content
            
        Raises:
            SystemExit: If file cannot be read
        """
        with open(file,'r') as f:
            if(f.readable()):
                return load(f) # json.load settings in a dict
            else: 
                lib.printFail(f'Error while reading {file}')
                exit()

    @staticmethod
    def getNextDay(day: str, format = '%d/%m/%Y') -> datetime:
        """Get datetime object for day after given date.
        
        Args:
            day (str): Date string
            format (str, optional): Date format. Defaults to '%d/%m/%Y'.
            
        Returns:
            datetime: Next day as datetime object
        """
        return lib.parse_formatDate(day, format) + timedelta(days=1)
    
    @staticmethod
    def getNextHour(day: str, format = '%d/%m/%Y') -> datetime:
        """Get datetime object for hour after given date/time.
        
        Args:
            day (str): Date string
            format (str, optional): Date format. Defaults to '%d/%m/%Y'.
            
        Returns:
            datetime: Next hour as datetime object
        """
        return lib.parse_formatDate(day, format) + timedelta(hours=1)
    
    @staticmethod
    def getPreviousDay(day: str, format = '%d/%m/%Y') -> datetime:
        """Get datetime object for day before given date.
        
        Args:
            day (str): Date string
            format (str, optional): Date format. Defaults to '%d/%m/%Y'.
            
        Returns:
            datetime: Previous day as datetime object
        """
        return lib.parse_formatDate(day, format) - timedelta(days=1)
    
    @staticmethod
    def getCurrentDay(format = '%d/%m/%Y') -> str:
        """Get current date as formatted string.
        
        Args:
            format (str, optional): Date format. Defaults to '%d/%m/%Y'.
            
        Returns:
            str: Current date string
        """
        return datetime.today().date().strftime(format)
    
    @staticmethod
    def parse_formatDate(day: str, format = '%d/%m/%Y', splitBy = ' ') -> datetime:
        """Parse date string into datetime object.
        
        Args:
            day (str): Date string or datetime object
            format (str, optional): Date format. Defaults to '%d/%m/%Y'.
            splitBy (str, optional): Split character for date string. Defaults to space.
            
        Returns:
            datetime: Parsed datetime object
        """
        if type(day) == datetime:
            return day
        return datetime.strptime(day.split(splitBy)[0], format)

    @staticmethod
    def calcAvgVolatility(total_value: list, avg_period: int = 30):
        """Calculate average volatility over a period.
        
        Uses log returns and rolling standard deviation to compute annualized volatility.
        
        Args:
            total_value (list): List of price values
            avg_period (int, optional): Period for rolling calculation. Defaults to 30.
                Must be > 1 and < len(total_value)
            
        Returns:
            float: Average annualized volatility
            None: If avg_period is invalid
        """
        if avg_period == 1 or avg_period > len(total_value): 
            lib.printFail(f"Specify a correct avg_period when calling {lib.calcAvgVolatility.__name__}")
            return None

        dataset = DataFrame(total_value) # pandas DF
        dataset = log(dataset/dataset.shift(1)) # numpy.log()
        dataset.fillna(0, inplace = True)

        # window/avg_period tells us how many days out you want
        # ddof in variance formula is x parameter .../(N - x)
        # ddof = 0 means you CALCULATE variance, any other number means you are ESTIMATE it.
        # you want to estimate it when you don't have all the necessary data to calc it.
        #
        # 365 in np.sqrt(365) is the number of trading day in a year, 
        # specifically in crypto market, trading days = year-round
        volatility = dataset.rolling(window=avg_period).std(ddof=0)*sqrt(365) # numpy.sqrt()

        # avarage volatily
        avg_volatility = volatility.mean(axis=0).get(0)
        
        return avg_volatility

    @staticmethod
    def isValidDate(date: str, format = '%d/%m/%Y'):
        """Check if string is a valid date in given format.
        
        Args:
            date (str): Date string to validate
            format (str, optional): Expected date format. Defaults to '%d/%m/%Y'.
            
        Returns:
            bool: True if valid date, False otherwise
        """
        try:
            lib.parse_formatDate(date, format)
        except:
            return False
        return True

    @staticmethod
    def getIndexOfDate(dateToFind: str, list: list):
        """Find index of date in list of dates.
        
        Args:
            dateToFind (str): Date to search for
            list (list): List of date strings
            
        Returns:
            tuple: (index, found) - Index of date and whether it was found
        """
        found = False
        index = 0
        for (i, item) in enumerate(list):
            if lib.parse_formatDate(item) == lib.parse_formatDate(dateToFind):
                found = True; index = i
                break
        return index, found

    @staticmethod
    def getUserInputDate(listOfDate):
        """Get valid date input from user.
        
        Prompts user until valid date is entered or empty input (default) received.
        
        Args:
            listOfDate: List of valid dates
            
        Returns:
            Union[str, int]: 'default' for empty input or index of selected date
            
        Raises:
            SystemExit: On keyboard interrupt
        """
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
        """Get input from user with keyboard interrupt handling.
        
        Returns:
            str: User input
            
        Raises:
            SystemExit: On keyboard interrupt
        """
        while True:
            try:
                return input()
            except KeyboardInterrupt:
                lib.printWarn('^C detected, aborting...')
                exit()

    @staticmethod
    def updateJson(file_path: str, date_to_update: str, new_record: str) -> tuple[bool, str]:
        """Update JSON file with new record at specific date.
        
        Handles insertion at beginning, middle, or end based on date order.
        
        Args:
            file_path (str): Path to JSON file
            date_to_update (str): Date for new record
            new_record (str): JSON record to insert
            
        Returns:
            tuple: (success, error_content) - Success flag and content on error
        """
        new_file = ''
        date_to_update = date_to_update.split(':')[0]
        formated_date_to_update = datetime.strptime(date_to_update,  '%d/%m/%Y %H')
        date_file_line = datetime(1970, 1, 1)
        isFirst = True

        with open(file_path, 'r') as f:
            for (_, line) in enumerate(f):
                try:
                    date = loads(line)
                except decoder.JSONDecodeError as e: # sometimes it throw error on line 2
                    lib.printFail(f'Json error, {file_path=} {e}')
                    pass

                # parse date and convert to dd/mm/yyyy
                date_file_line = datetime.strptime(date['date'].split(':')[0], '%d/%m/%Y %H')
                if isFirst: 
                    if formated_date_to_update < date_file_line: 
                        # if date_to_update is before the first line's date
                        # add new_record at the beginning of file_path
                        new_file = new_record + str(open(file_path, 'r').read())
                        isFirst = False
                        break

                if date_file_line == formated_date_to_update:
                    new_file += new_record+'\n' # insert new_record instead of old record(line variable)
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
    def createCacheFile():
        """Create cache directory and files for ID mappings.
        
        Creates:
        - cached_id_CG.json for CoinGecko
        - cached_id_CMC.json for CoinMarketCap
        - cached_liquid_stake.json for liquid staking
        
        Returns:
            tuple: Paths to created CoinGecko and CoinMarketCap cache files
            False: If creation fails
        """
        cwd = getcwd() # current working directory
        cachePath = path.join(cwd, 'cache')

        try:
            if not path.isdir(cachePath): mkdir(cachePath) 
        except FileExistsError: pass
        
        cg = path.join(cachePath, 'cached_id_CG.json')
        cmc = path.join(cachePath, 'cached_id_CMC.json')
        cachedLSPath = path.join(cachePath, 'cached_liquid_stake.json')
        
        lib.createFile(cachedLSPath, dumps({"asset": []}, indent=4), False)
        lib.createFile(cg, dumps({"fixed": [], "used": {}}, indent=4), False)
        lib.createFile(cmc, '{}', False)
        
        return cg, cmc

    @staticmethod
    def createWorkingFile(dirPath: str):
        """Create working directory structure and files.
        
        Creates:
        - /grafico directory
        - walletValue.json
        - report.json
        
        Args:
            dirPath (str): Base directory path
            
        Returns:
            tuple: Paths to created directory and files
            False: If creation fails
        """
        try:
            if not path.isdir(dirPath): mkdir(dirPath) 
        except FileExistsError: pass
        except FileNotFoundError: lib.printFail('Error on init, check path in settings.json'); return False
        
        graficoPath = path.join(dirPath, 'grafico') 
        walletJsonPath = path.join(dirPath, 'walletValue.json')
        reportJsonPath = path.join(dirPath, 'report.json')

        try:
            if not path.isdir(graficoPath): mkdir(graficoPath) 
        except FileExistsError: pass
        except FileNotFoundError: lib.printFail('Error on init, check path in settings.json'); return False
        
        lib.createFile(walletJsonPath)
        lib.createFile(reportJsonPath)

        return graficoPath, walletJsonPath, reportJsonPath

    @staticmethod
    def createFile(filepath: str, content: str = '', overide: bool = False):
        """Create file with content or update if empty/override allowed.
        
        Args:
            filepath (str): Path to file
            content (str, optional): Content to write. Defaults to empty.
            overide (bool, optional): Whether to override existing content. Defaults to False.
            
        Raises:
            SystemExit: If file creation fails
        """
        try:
            if not path.exists(filepath):
                with open(filepath, 'w') as f:
                    f.write(content)
                return
            else:
                f = open(filepath, 'r')
                if len(f.read()) == 0 or overide:
                    f.close()
                    f = open(filepath, 'w')
                    f.write(content)
                return
        except Exception as e:
            lib.printFail(f'Failed to create file: {filepath}')
            lib.printFail('lib.createFile: '+str(e))
            exit()

if __name__ == '__main__':
    # print(lib.calcAvgVolatility([1383,1371,1373,1341]), 2)
    pass