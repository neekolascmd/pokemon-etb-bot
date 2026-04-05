# pokemon-etb-bot

Monitor-only Pokémon ETB stock checker built with Python and Playwright.

This repo checks product pages for stock indicators on Pokémon Center, Target, Walmart, and Amazon. It does not add items to cart or attempt checkout.

## Requirements

- Python 3.10 or newer
- pip
- Playwright for Python

## Setup

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

Run a one-time check:

```bash
python monitor_etb.py --once PASTE_PRODUCT_URL_1 PASTE_PRODUCT_URL_2
```

Run continuously and check every 5 minutes:

```bash
python monitor_etb.py --interval 300 PASTE_PRODUCT_URL_1 PASTE_PRODUCT_URL_2
```

Or keep the URLs in a file, one per line:

```bash
python monitor_etb.py --once --urls-file urls.txt
```

## Notes

- The script exits with code 2 when it detects stock on any monitored page.
- Retailer page layouts can change, so selectors may need occasional updates.
- For best results, monitor the exact ETB product page you care about.
