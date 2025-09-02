import os
import re
import time
import requests
from datetime import datetime
from pytz import timezone
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import cloudscraper

from fastapi import FastAPI, Request
import uvicorn

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

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
# CoinGecko з кешем
# ==========================
CG_BASE = "https://api.coingecko.com/api/v3"
HEADERS_JSON = {"accept": "application/json"}

_last_fetch = {"ts": 0, "data": None, "error": None}

def get_eth_price_and_volume():
    global _last_fetch
    now = time.time()

    # кеш 5 хвилин
    if now - _last_fetch["ts"] < 300 and (_last_fetch["data"] or _last_fetch["error"]):
        if _last_fetch["error"]:
            raise RuntimeError(_last_fetch["error"])
        return _last_fetch["data"]

    try:
        r = requests.get(
            f"{CG_BASE}/coins/ethereum",
            params={
                "localization": "false",
                "tickers": "false",
                "market_data": "true",
                "community_data": "false",
                "developer_data": "false",
                "sparkline": "false"
            },
            headers=HEADERS_JSON,
            timeout=20
        )
        r.raise_for_status()
        data = r.json()

        price = float(data["market_data"]["current_price"]["usd"])
        vol_24h = float(data["market_data"]["total_volume"]["usd"])
        price_chg_pct = float(data["market_data"]["price_change_percentage_24h"])

        # CoinGecko не дає попередній обсяг напряму → залишимо N/A
        vol_delta_pct = "N/A"

        result = (price, vol_24h, price_chg_pct, vol_delta_pct)
        _last_fetch = {"ts": now, "data": result, "error": None}
        return result

    except Exception as e:
        err_msg = f"CoinGecko недоступний: {e}"
        _last_fetch = {"ts": now, "data": None, "error": err_msg}
        raise RuntimeError(err_msg)

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

    # шукаємо фонди
    si = lines.index("Blackrock")
    fund_names = lines[si:si+9]

    fee_i = lines.index("Fee", si)
    tickers = [x for x in lines[si+10:fee_i] if re.fullmatch(r"[A-Z]{3,6}\*?", x)]
    tickers = tickers[:9]

    labels = [f"{n} ({t})" for n, t in zip(fund_names, tickers)] + ["Total"]

    val_token = re.compile(r"\(?-?\d[\d,]*\.?\d*\)?|-$")

    def parse_val(s: str) -> float:
        s = s.strip()
        if s == "-":
            return 0.0
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

    # беремо лише ті блоки, де є реальні дані (не всі "-")
    def has_real_fund_data(vals):
        return any(v.strip() not in ["-", "0"] for v in vals[:9])

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
        if vy > 0:
            status = "приплив"
        elif vy < 0:
            status = "відтік"
        else:
            status = "без змін"

        if status == "без змін":
            out.append(f"{label}: {vy:.1f} млн $ ({status})")
        else:
            sign = "+" if diff >= 0 else "–"
            out.append(f"{label}: {vy:.1f} млн $ ({status}, {sign}{abs(diff):.1f} vs учора)")

    return date_y, date_p, out

# ==========================
# Формування повідомлення
# ==========================
def build_message():
    try:
        price, vol, price_chg_pct, vol_delta_pct = get_eth_price_and_volume()
        line1 = f"1) Ціна: ${price:,.2f} ({'+' if price_chg_pct >= 0 else ''}{price_chg_pct:.2f}%)"
        line2 = f"2) Об'єм (24h): {fmt_money(vol)} ({vol_delta_pct})"
    except Exception as e:
        line1 = "1) CoinGecko недоступний"
        line2 = str(e)

    try:
        txt = fetch_text(FARSIDE_URL)
        dy, dp, lines_out = parse_eth_farside_yesterday(txt)
        funds_block = "\n".join(f"• {ln}" for ln in lines_out)
        line3 = f"3) Великі фонди (spot ETH ETF — {dy} vs {dp}):\n{funds_block}"
    except Exception as e:
        line3 = f"3) Великі фонди (spot ETH ETF): N/A — {e}"

    header = f"ETH звіт — {now_str()} (Kyiv)"
    footer = "Джерела: CoinGecko, Farside."
    return f"{header}\n{line1}\n{line2}\n{line3}\n{footer}"

# ==========================
# Telegram + FastAPI
# ==========================
app = FastAPI()
tg_app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.reply_text(build_message(), disable_web_page_preview=True)
    except Exception as e:
        await update.message.reply_text(f"Помилка: {e}")

tg_app.add_handler(CommandHandler("start", cmd_start))
tg_app.add_handler(CommandHandler("now", cmd_start))

@app.get("/")
async def home():
    return {"status": "Bot is running!"}

@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, tg_app.bot)
    await tg_app.process_update(update)
    return {"ok": True}

# ==========================
# Запуск на Render
# ==========================
if __name__ == "__main__":
    import asyncio

    async def main():
        await tg_app.initialize()
        await tg_app.start()
        await tg_app.bot.set_webhook(url=f"{BASE_URL}/webhook")
        print("Webhook set!")

        config = uvicorn.Config(app, host="0.0.0.0", port=PORT)
        server = uvicorn.Server(config)
        await server.serve()

        await tg_app.stop()

    asyncio.run(main())
