# pokemon-etb-bot

Monitor-only Pokémon ETB stock checker built with Python and Playwright.

This repo checks product pages for stock indicators on Pokémon Center, Target, Walmart, and Amazon. It does not add items to cart or attempt checkout.

When stock is detected, the script logs a clear alert, sounds a terminal bell, and keeps monitoring instead of exiting.

## Requirements

- Python 3.10 or newer
- pip
- Playwright for Python

## Setup

Clone the repo, then install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
playwright install chromium
```

## Usage

Run the monitor continuously with one or more product URLs:

```bash
python monitor_etb.py PASTE_PRODUCT_URL_1 PASTE_PRODUCT_URL_2
```

The script checks each URL, prints the current status, and then waits the configured interval before checking again. If it finds stock, it logs a stock alert and sounds a terminal bell, but it does not stop.

Change the polling interval with `--interval`:

```bash
python monitor_etb.py --interval 300 PASTE_PRODUCT_URL_1 PASTE_PRODUCT_URL_2
```

Use a text file with one URL per line:

```bash
python monitor_etb.py --urls-file urls.txt
```

Run a single pass only, then exit:

```bash
python monitor_etb.py --once PASTE_PRODUCT_URL_1 PASTE_PRODUCT_URL_2
```

## Notes

- The monitor keeps running until you stop it manually with Ctrl+C.
- The script exits with code 2 only when `--once` is used and stock is detected.
- Retailer page layouts can change, so selectors may need occasional updates.
- For best results, monitor the exact ETB product page you care about.
