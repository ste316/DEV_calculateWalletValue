# Feature: Rebalancer Execution Modes

This document provides an overview of the Rebalancer Execution Modes feature implemented in the `kucoinAutoBalance` class (`src/rebalancer.py`).

## Goal

To provide users with control over how the automatic portfolio rebalancer executes trades on KuCoin, enhancing safety and flexibility.

## Modes

Three execution modes are available:

1.  **`simulation`**:
    *   Calculates all required sell and buy orders, including necessary intermediate swaps.
    *   Logs all intended actions (e.g., "Would place SELL order...", "Would place BUY order...").
    *   **Does NOT execute any actual trades** via the KuCoin API.
    *   Useful for previewing the rebalancing plan without any risk.

2.  **`interactive`**:
    *   Calculates the complete rebalancing plan.
    *   Displays the overall plan (proposed sells, buys, potential issues).
    *   **Prompts the user for confirmation (y/n) BEFORE each individual trade** (including preparatory swaps).
    *   Only executes a trade if the user explicitly confirms with 'y'.
    *   Provides a balance between automation and user control. This is the recommended default for safety.

3.  **`yolo` ("You Only Live Once")**:
    *   Calculates the complete rebalancing plan.
    *   Proceeds to **automatically execute all calculated trades** (sells, buys, swaps) via the KuCoin API without asking for confirmation.
    *   Use with caution, as it involves real trades and potential costs/losses.

## Configuration

The execution mode can be set in two ways:

1.  **`settings.json` File:**
    *   Add or modify the key `"rebalance_mode"` within your `settings.json`.
    *   Example: `"rebalance_mode": "interactive"`
    *   If the key is missing, the application defaults to `"interactive"`.

2.  **Command-Line Argument (Overrides `settings.json`):**
    *   Use the `--rebalance-mode` flag when running `main.py` with `--calc`.
    *   Example: `python main.py --calc --crypto --rebalance-mode simulation`
    *   Allowed values: `simulation`, `interactive`, `yolo`.
    *   If this argument is provided, it takes precedence over the value in `settings.json`.

## Implementation Details

*   The final execution mode is determined in `src/calc_wallet.py` (checking the CLI argument first, then `settings.json`).
*   This mode is passed directly to the `kucoinAutoBalance` constructor in `src/rebalancer.py`.
*   The `marketOrder` method within `kucoinAutoBalance` contains the core logic to handle behavior based on `self.execution_mode`.
*   Preparatory swaps are planned in `prepareBuyOrders` and executed just-in-time during `executeBuyOrders` to maintain context, allowing for individual confirmation in interactive mode.