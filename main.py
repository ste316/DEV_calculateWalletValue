from src.lib_tool import lib
from argparse import ArgumentParser

# parse arguments
def get_args(): 
    parser = ArgumentParser()
    parser.add_argument('--crypto', dest='crypto', action="store_true", help='view balance of crypto assets')
    parser.add_argument('--total', dest='total',action="store_true", help='view balance of fiat vs crypto assets')
    parser.add_argument('--calc', dest='calc',action="store_true", help='calculate wallet value')
    parser.add_argument('--report', dest='report',action="store_true", help='view wallet value over time')
    parser.add_argument('--privacy', dest='privacy', action='store_true', help='obscure total value when used combined with --calc')
    parser.add_argument('--load', dest='load', action='store_true', help='load one past date and view it')
    parser.add_argument('--singleCrypto', dest='singleCrypto', action='store_true', help='view balance of a crypto over time')
    parser.add_argument('--version', dest='version', action='store_true', help='')
    parser.add_argument(
        '--rebalance-mode',
        dest='rebalance_mode',
        choices=['simulation', 'interactive', 'yolo'],
        default=None,
        help='Specify the KuCoin rebalancer execution mode (overrides settings.json)'
    )
    option = parser.parse_args()
    return option

if __name__ == '__main__':
    option = get_args()
    run = False
    rebalance_mode_arg = option.rebalance_mode

    if option.calc:
        from src.calc_wallet import calculateWalletValue
        if option.load:
            if option.privacy: 
                main = calculateWalletValue('crypto', privacy=True, load=True, rebalance_mode_override=rebalance_mode_arg)
                run = True
            else:
                main = calculateWalletValue('crypto', privacy=False, load=True, rebalance_mode_override=rebalance_mode_arg)
                run = True

        elif option.crypto:
            if option.privacy:
                main = calculateWalletValue('crypto', privacy=True, load=False, rebalance_mode_override=rebalance_mode_arg)
                run = True
            else:
                main = calculateWalletValue('crypto', privacy=False, load=False, rebalance_mode_override=rebalance_mode_arg)
                run = True
        elif option.total:
            if option.privacy:
                main = calculateWalletValue('total', privacy=True, load=False, rebalance_mode_override=rebalance_mode_arg)
                run = True
            else:
                main = calculateWalletValue('total', privacy=False, load=False, rebalance_mode_override=rebalance_mode_arg)
                run = True

    elif option.report:
        if option.crypto:
            from src.report_wallet import walletBalanceReport
            main = walletBalanceReport('crypto')
            run = True
        elif option.total:
            from src.report_wallet import walletBalanceReport
            main = walletBalanceReport('total')
            run = True
        elif option.singleCrypto:
            from src.report_crypto import cryptoBalanceReport
            main = cryptoBalanceReport()
            run = True
    elif option.version:
        print(lib.getConfig()['version'])
    if run:
        main.run()