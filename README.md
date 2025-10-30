🪙 ETH Telegram Bot — Ethereum ETF & Market Report

This project is a Telegram bot that sends concise daily reports on the Ethereum market.
It combines live data from CoinGecko (price, volume, 24h change) and Farside (ETF inflows/outflows), caches responses, and delivers formatted updates via Telegram commands.

⚙️ Key Features

Get the current ETH/USD price

Show 24h trading volume

Display percentage price change

Parse ETF inflow/outflow data from Farside.co.uk

Generate a clean, human-readable summary

Kyiv timezone support

5-minute caching for CoinGecko requests

FastAPI-based webhook for Telegram integration

Fully deployable on Render.com

🧩 Tech Stack

Python 3.10+

FastAPI – web server

python-telegram-bot v20+ – Telegram API framework

BeautifulSoup + cloudscraper – HTML parsing

requests – HTTP client

dotenv – environment variable loader

CoinGecko API – ETH price & volume data

Render.com – hosting environment (auto PORT assignment)

📁 File Overview

Everything is contained in a single Python file:

Configuration: tokens, base URL, timezone setup

Utilities: currency formatting, percentage changes, timestamps

CoinGecko API: fetches ETH price, volume, and 24h change

Farside Parser: retrieves and parses ETF flow data

build_message(): composes the final message

Telegram Bot: handles /start and /now commands

FastAPI Endpoints: / and /webhook for Render deployment

Main Runner: starts webhook and server concurrently

🧰 Environment Setup

Create a .env file in your project root:

TELEGRAM_BOT_TOKEN=123456789:ABC_your_token_here
BASE_URL=https://your-app.onrender.com
PORT=10000


BASE_URL should match your Render app domain
(e.g., https://eth-report-bot.onrender.com)

▶️ Run Locally

Install dependencies:

pip install fastapi uvicorn python-telegram-bot python-dotenv requests beautifulsoup4 cloudscraper pytz


Run the app:

python main.py


Open Telegram and send /start to your bot.

⚠️ For local webhook testing, use ngrok or a similar tunneling service:

ngrok http 10000


Then update BASE_URL in .env to your ngrok URL.

☁️ Deploying to Render

Create a new Web Service on Render
.

Set Build Command:

pip install -r requirements.txt


Set Start Command:

python main.py


Add environment variables:

TELEGRAM_BOT_TOKEN

BASE_URL

Render automatically assigns the PORT.

Once deployed, the log should show:

Webhook set!

🧾 Example Output
ETH Report — 2025-10-30 12:10 (Kyiv)
1) Price: $3,412.56 (+0.84%)
2) Volume (24h): $8.91B (N/A)
3) Major Funds (spot ETH ETF — 29 Oct 2025 vs 28 Oct 2025):
• BlackRock (IBIT): +12.4M $ (inflow, +5.1 vs yesterday)
• Fidelity (FETH): –4.6M $ (outflow, –2.1 vs yesterday)
• ...
Sources: CoinGecko, Farside.

🧠 Notes

CoinGecko results are cached for 5 minutes to reduce API calls.

If CoinGecko or Farside is unavailable, the bot gracefully falls back to N/A.

Farside parsing may need updates if the site’s structure changes.
