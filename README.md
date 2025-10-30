# 🪙 ETH Telegram Bot — Ethereum ETF & Market Report

This project is a **Telegram bot** that sends concise, real-time reports on the Ethereum market.  
It combines live data from **CoinGecko** (price, 24h volume, change) and **Farside** (ETF inflows/outflows), caches responses, and delivers formatted updates directly in Telegram.

---

## ⚙️ Key Features

- Fetches the **current ETH/USD price**
- Displays **24-hour trading volume**
- Shows **percentage price change**
- Parses **ETF inflow/outflow data** from [Farside.co.uk](https://farside.co.uk/ethereum-etf-flow-all-data/)
- Generates a formatted summary message
- **Kyiv timezone** support
- **5-minute caching** for CoinGecko API calls
- **FastAPI webhook** compatible with Render.com deployment

---

## 🧩 Tech Stack

- **Python 3.10+**
- **FastAPI** — web framework for the server
- **python-telegram-bot v20+** — Telegram bot library
- **BeautifulSoup + cloudscraper** — HTML parsing
- **requests** — for REST API requests
- **dotenv** — environment variable management
- **CoinGecko API** — ETH market data
- **Render.com** — cloud deployment (auto port configuration)

---

## 📁 Project Structure

All logic is contained in one file (`main.py`):

| Section | Description |
|----------|--------------|
| **Configuration** | Loads `.env`, timezone, tokens |
| **Utilities** | Functions for formatting time, money, percentages |
| **CoinGecko** | Fetches ETH price, volume, and change |
| **Farside Parser** | Scrapes ETF data from Farside |
| **`build_message()`** | Composes the report text |
| **Telegram Bot** | Handles `/start` and `/now` commands |
| **FastAPI** | Provides `/` and `/webhook` endpoints |
| **Main** | Starts FastAPI + webhook on Render |

---

## 🧰 Environment Setup

Create a `.env` file in your project root:

```bash
TELEGRAM_BOT_TOKEN=123456789:ABC_your_token_here
BASE_URL=https://your-app.onrender.com
PORT=10000
