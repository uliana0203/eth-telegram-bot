import os
import re
import requests
from datetime import datetime
from pytz import timezone
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import cloudscraper
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from flask import Flask, request
import asyncio

# ==========================
# Конфіг
# ==========================
load_dotenv()
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
BASE_URL = os.environ.get("BASE_URL")           # https://<your-app>.onrender.com
PORT = int(os.environ.get("PORT", 10000))       # Render підставить свій порт
KYIV_TZ = timezone("Europe/Kyiv")

if not TELEGRAM_BOT_TOKEN:
    raise RuntimeError("Вкажи TELEGRAM_BOT_TOKEN у змінних середовища або .env")

# ==========================
# Утиліти
# ==========================
def now_str():
    return datetime.now(KYIV_TZ).strftime("%Y-%m-%d %H:%M")

def fmt_money(x):
    if x is None: return "N/A"
    units = ["", "K", "M", "B", "T"]
    v = float(x); k = 0
    while abs(v) >= 1000 and k < len(units) - 1:
        v /= 1000.0; k += 1
    return f"${v:,.2f}{units[k]}"

def pct_delta(new, old):
    try:
        if new is None or old is None or float(old) == 0: return "N/A"
        d = (float(new) - float(old)) / float(old) * 100.0
        return f"{'+' if d >= 0 else ''}{d:.2f}%"
    except:
        return "N/A"

# ==========================
# CoinGecko
# ==========================
CG_BASE = "https://api.coingecko.com/api/v3"
HEADERS_JSON = {"accept": "application/json"}

def get_eth_price_and_volume():
    r = requests.get(
        f"{CG_BASE}/coins/ethereum",
        params={"localization":"false","tickers":"false","market_data":"true",
                "community_data":"false","developer_data":"false","sparkline":"false"},
        headers=HEADERS_JSON, timeout=20
    )
    r.raise_for_status()
    data = r.json()
    price = float(data["market_data"]["current_price"]["usd"])
    vol_24h = float(data["market_data"]["total_volume"]["usd"])
    price_chg_pct = float(data["market_data"]["price_change_percentage_24h"])

    r2 = requests.get(
        f"{CG_BASE}/coins/ethereum/market_chart",
        params={"vs_currency":"usd","days":"2","interval":"daily"},
        headers=HEADERS_JSON, timeout=20
    )
    r2.raise_for_status()
    vols = r2.json().get("total_volumes", [])
    vol_prev = vols[-2][1] if len(vols) >= 2 else None
    vol_delta_pct = pct_delta(vol_24h, vol_prev)

    return price, vol_24h, price_chg_pct, vol_delta_pct

# ==========================
# Farside
# ==========================
FARSIDE_URL = "https://farside.co.uk/ethereum-etf-flow-all-data/"

def fetch_text(url: str) -> str:
    try:
        scraper = cloudscraper.create_scraper(
            browser={"browser": "chrome", "platform": "windows", "mobile": False}
        )
        r = scraper.get(url, timeout=25)
    except Exception:
        r = requests.get(url, timeout=25, headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "text/html",
        })
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    for t in soup(["script", "style", "noscript"]):
        t.extract()
    text = soup.get_text(separator="\n")
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    return "\n".join(lines)

def parse_eth_farside_yesterday(txt: str):
    lines = [l.strip() for l in txt.splitlines() if l.strip()]

    try:
        si = lines.index("Blackrock")
    except ValueError:
        raise ValueError("Не знайдено 'Blackrock' у таблиці.")

    fund_names = lines[si:si+9]

    try:
        fee_i = lines.index("Fee", si)
    except ValueError:
        raise ValueError("Не знайдено 'Fee' після фондів.")

    tickers = []
    for x in lines[si+10:fee_i]:
        if re.fullmatch(r"[A-Z]{3,6}\*?", x):
            tickers.append(x)
    tickers = tickers[:9]
    if len(tickers) != 9:
        raise ValueError(f"Очікувалось 9 тікерів, знайдено: {tickers}")

    labels = [f"{n} ({t})" for n, t in zip(fund_names, tickers)] + ["Total"]

    val_token = re.compile(r"\(?\d[\d,]*\.?\d*\)?|-$")
    def parse_val(s: str) -> float:
        s = s.strip()
        if s == "-": return 0.0
        neg = s.startswith("(") and s.endswith(")")
        v = float(s.strip("()").replace(",", ""))
        return -v if neg else v

    date_pat = re.compile(r"^\d{1,2} [A-Z][a-z]{2} \d{4}$")
    blocks = []
    for i, l in enumerate(lines):
        if date_pat.match(l):
            vals = lines[i+1:i+11]
            if len(vals) == 10 and all(val_token.fullmatch(v) for v in vals):
                blocks.append((i, l, vals))

    if len(blocks) < 2:
        raise ValueError("Недостатньо дат з даними.")

    def has_real_fund_data(vals):
        return any(v.strip() != "-" for v in vals[:9])

    real_blocks = [(i, d, vals) for (i, d, vals) in blocks if has_real_fund_data(vals)]
    if len(real_blocks) < 2:
        raise ValueError("Немає двох днів з реальними даними.")

    y_idx, date_y, vals_y_raw = real_blocks[-1]
    p_idx, date_p, vals_p_raw = real_blocks[-2]

    vals_y = [parse_val(v) for v in vals_y_raw]
    vals_p = [parse_val(v) for v in vals_p_raw]

    out = []
    for label, vy, vp in zip(labels, vals_y, vals_p):
        diff = vy - vp
        sign = "+" if diff >= 0 else ""
        out.append(f"{label}: {vy:.1f} ({sign}{diff:.1f})")

    return date_y, date_p, out

# ==========================
# Формування повідомлення
# ==========================
def build_message():
    price, vol, price_chg_pct, vol_delta_pct = get_eth_price_and_volume()

    try:
        txt = fetch_text(FARSIDE_URL)
        dy, dp, lines_out = parse_eth_farside_yesterday(txt)
        funds_block = "\n".join(f"• {ln}" for ln in lines_out)
        line3 = f"3) Великі фонди (spot ETH ETF — {dy} vs {dp}):\n{funds_block}"
    except Exception as e:
        line3 = f"3) Великі фонди (spot ETH ETF): N/A — {e}"

    line1 = f"1) Ціна: ${price:,.2f} ({'+' if price_chg_pct >= 0 else ''}{price_chg_pct:.2f}%)"
    line2 = f"2) Об'єм (24h): {fmt_money(vol)} ({vol_delta_pct})"

    header = f"ETH звіт — {now_str()} (Kyiv)"
    footer = "Джерела: CoinGecko, Farside."
    return f"{header}\n{line1}\n{line2}\n{line3}\n{footer}"

# ==========================
# Telegram + Flask
# ==========================
app = Flask(__name__)
tg_app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

# 🔑 Ініціалізуємо Application вручну
asyncio.get_event_loop().run_until_complete(tg_app.initialize())

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.reply_text(build_message(), disable_web_page_preview=True)
    except Exception as e:
        await update.message.reply_text(f"Помилка: {e}")

tg_app.add_handler(CommandHandler("start", cmd_start))
tg_app.add_handler(CommandHandler("now", cmd_start))

@app.route("/")
def home():
    return "Bot is running!", 200

@app.route("/webhook", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), tg_app.bot)
    tg_app.update_queue.put_nowait(update)
    return "OK", 200



# ==========================
# Запуск на Render
# ==========================
if __name__ == "__main__":
    async def set_webhook():
        await tg_app.bot.set_webhook(url=f"{BASE_URL}/webhook")
    asyncio.get_event_loop().run_until_complete(set_webhook())

    app.run(host="0.0.0.0", port=PORT)
