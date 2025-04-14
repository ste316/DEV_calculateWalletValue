# Calculate Wallet Value is a program to instantly see how your cryptocurrency portfolio is performing.

## Automatic portfolio Rebalancer is currently in beta phase and only support Kucoin exchange APIs.

1. ## Prerequisites:
    * [Download a python interpreter](https://www.python.org/downloads/), suggested python version >= 3.9
    * Download all dependencies
      * move to the folder of the project
      * run: `pip install -r requirements.txt`
    * Insert all your assets and their amount in input.csv
    * Fill settings.json with your preferences
        * currency supported: "EUR" and "USD", needs to be uppercase 
            * other currencies may be supported, have not been tested
        * 🟨🟨🟨NOTE: the first time you run the program make sure to fill fetchSymb with true 🟨🟨🟨
        * <i>path</i> field will be the parent folder where the data will be saved

        * provider can be "cg" for CoinGecko or "cmc" for CoinMarketCap
        * You can choose between CoinGecko and CoinMarketCap api
            * CoinGecko api is free and you do NOT need any api key, see [plan](https://www.coingecko.com/en/api/pricing) and
            [limits](https://www.coingecko.com/en/api/documentation), *Data provided by CoinGecko*
            * CoinMarketCap it's free too, but you need to [sign in](https://pro.coinmarketcap.com/login/) and get an api key

            #### CoinMarketCap is lightning faster and easy to use, but you have less privacy.
            #### CoinGecko is slower and a bit more complicated to use, but you don't have to create any account or fill your information anywhere, yet more privacy.
            #### Both solutions are supported, make your choice.
            in case you choose CoinMarketCap, make sure to fill the api key in <i>CMC_key</i> field
            * If using the KuCoin Rebalancer (Beta):
                * Set `"kucoin_enable_autobalance": true`.
                * Configure KuCoin API credentials in `kc_info.json` (create if it doesn't exist).
                * Optionally set `"rebalance_mode"` to `"simulation"`, `"interactive"` (default), or `"yolo"`.
                * Define your target portfolio percentages in `portfolio_pct.json`.
    * After the first start-up all necessary files will be downloaded or writed

2. ## Usage:
    * ### Preliminary step:
        * `cd <folderOfProject>`

    * ### You can run this command to:
        * 🟨🟨🟨NOTE: both command execute the same code, the only difference is the graphical output. So you will get your wallet data saved in your walletValue.json file anyway.🟨🟨🟨

        * #### instantly see your CRYPTO wallet:
            * `python main.py --calc --crypto`
            * you may want to obscure total value showed in the graphic, run `python main.py --calc --crypto --privacy` 
            * you may want to see your portfolio in a past date(must have been calculated on that date), run `python main.py --calc --crypto --load`
            * **Rebalancer Mode Override:** To run the KuCoin rebalancer with a specific mode (overriding `settings.json`), use `--rebalance-mode`:
                * `python main.py --calc --crypto --rebalance-mode simulation`
                * `python main.py --calc --crypto --rebalance-mode interactive`
                * `python main.py --calc --crypto --rebalance-mode yolo`
        * ![crypto](https://github.com/ste316/calcWalletValue/blob/main/img/crypto.png)

        * #### instantly see your wallet splitted in CRYPTO and FIAT:
            * `--calc --total`
            * 🟨🟨🟨NOTE: stablecoins are counted as FIAT🟨🟨🟨
            * you may want to obscure total value showed in the graphic, run `python main.py --calc --total --privacy` 
            * you may want to see your portfolio in a past date(must have been calculated on that date), run `python main.py --calc --total --load`
            * **Rebalancer Mode Override:** Similar to the crypto view:
                * `python main.py --calc --total --rebalance-mode simulation` 
        * ![total](https://github.com/ste316/calcWalletValue/blob/main/img/total.png)

    * ### You can analyse your portfolio over time, using these commands:
        * 🟨🟨🟨NOTE: to run all this commands you need at least 2 records in walletValue.json🟨🟨🟨

        * #### Show your crypto wallet over time
            * `python main.py --report --crypto`
            * include stablecoins
        * #### Show your total wallet over time
            * `python main.py --report --total`
            * include all assets
        * #### Show fiat value and amout of an asset over time
            * `python main.py --report --singleCrypto`

## KuCoin Auto Rebalancer (Beta)

If `kucoin_enable_autobalance` is set to `true` in `settings.json`, the script will attempt to rebalance your KuCoin portfolio according to the targets defined in `portfolio_pct.json` after calculating and displaying the wallet value.

**Execution Modes:**

*   **`simulation`**: Shows what trades *would* be made without executing them.
*   **`interactive`** (Default): Shows the plan and prompts for confirmation *before each trade*.
*   **`yolo`**: Automatically executes all planned trades without confirmation (Use with caution!).

You can set the mode in `settings.json` using the `"rebalance_mode"` key or override it using the `--rebalance-mode <mode>` command-line argument when using `--calc`.

See `documentation/rebalance_mode_feature.md` for more details.
