# 🪙 ETH Telegram Bot — Ethereum ETF & Market Report

This project is a **Telegram bot** that sends concise, real-time reports on the Ethereum market.  
It combines live data from **CoinGecko** (price, 24h volume, change) and **Farside** (ETF inflows/outflows), caches responses, and delivers formatted updates directly in Telegram.

---

## 🌐 Live Deployment

This bot is **deployed on Render** and publicly available at:  
👉 [https://eth-telegram-bot-igx3.onrender.com](https://eth-telegram-bot-igx3.onrender.com)

You can also use the Telegram bot directly here:  
💬 [@eth24_price_bot](https://t.me/eth24_price_bot)

---

## ⚙️ Key Features

- Fetches the **current ETH/USD price**
- Displays **24-hour trading volume**
- Shows **percentage price change**
- Parses **ETF inflow/outflow data** from [Farside.co.uk](https://farside.co.uk/ethereum-etf-flow-all-data/)
- Generates a clean, human-readable summary
- **Kyiv timezone** support
- **5-minute caching** for CoinGecko API calls
- **FastAPI webhook** compatible with Render deployment

---

## 🧩 Tech Stack

- **Python 3.10+**
- **FastAPI** — web framework for the server
- **python-telegram-bot v20+** — Telegram bot API wrapper
- **BeautifulSoup + cloudscraper** — for HTML parsing
- **requests** — for REST API requests
- **dotenv** — environment variable management
- **CoinGecko API** — for ETH price and market data
- **Render.com** — for cloud deployment

---

## 📁 Project Structure

All logic is contained in one file (`main.py`):

| Section | Description |
|----------|--------------|
| **Configuration** | Loads `.env`, timezone, tokens |
| **Utilities** | Helper functions for formatting values |
| **CoinGecko** | Fetches ETH price, volume, and % change |
| **Farside Parser** | Scrapes and parses ETF flow data |
| **`build_message()`** | Composes the report text |
| **Telegram Bot** | Handles `/start` and `/now` commands |
| **FastAPI** | Provides `/` and `/webhook` endpoints |
| **Main** | Initializes the Telegram webhook and server |

---

## 🧰 Environment Setup

Create a `.env` file in your project root:

```bash
TELEGRAM_BOT_TOKEN=123456789:ABC_your_token_here
BASE_URL=https://eth-telegram-bot-igx3.onrender.com
PORT=10000
