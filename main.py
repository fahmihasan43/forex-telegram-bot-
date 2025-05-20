import nest_asyncio
import asyncio
import pandas as pd
import yfinance as yf
import feedparser
import logging
from datetime import datetime
from ta.trend import EMAIndicator
from ta.momentum import StochRSIIndicator
from ta.volatility import AverageTrueRange
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

nest_asyncio.apply()

# === KONFIGURASI ===
TOKEN = "ISI_TOKEN_BOT_KAMU"
AUTHORIZED_USERS = {7866728515}
ADMIN_ID = 7866728515
SYMBOLS = ['EURUSD=X', 'GC=F', 'USDJPY=X']
LOOP_DELAY = 60

logging.basicConfig(level=logging.INFO)

def write_log(msg):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now}] {msg}")

def get_forex_news():
    try:
        rss = feedparser.parse("https://nfs.faireconomy.media/ff_calendar_thisweek.xml")
        return [e['title'] for e in rss.entries if "USD" in e['title']][:3]
    except:
        return ["Berita gagal"]

def analyze(df):
    try:
        df = df.copy()
        close = df['Close']
        high = df['High']
        low = df['Low']
        open_ = df['Open']
        volume = df['Volume']
        ema5 = EMAIndicator(close, window=5).ema_indicator()
        ema20 = EMAIndicator(close, window=20).ema_indicator()
        stoch = StochRSIIndicator(close).stochrsi_k()
        atr = AverageTrueRange(high, low, close).average_true_range()

        recent_high = high[-20:].max()
        recent_low = low[-20:].min()
        avg_vol = volume.rolling(14).mean()
        vol_spike = volume.iloc[-1] > 1.5 * avg_vol.iloc[-1]
        close_now = close.iloc[-1]
        close_prev = close.iloc[-2]
        open_now = open_.iloc[-1]
        high_now = high.iloc[-1]
        low_now = low.iloc[-1]
        marubozu = abs(close_now - open_now) > 0.7 * (high_now - low_now)

        breakout_up = close_now > recent_high and close_prev <= recent_high and vol_spike and marubozu
        breakout_down = close_now < recent_low and close_prev >= recent_low and vol_spike and marubozu

        if len(close) >= 11:
            drop_pct = (close_now - close[-11]) / close[-11]
            if drop_pct < -0.02 and vol_spike:
                sl = high[-11:].max()
                tp = close_now - 2 * atr.iloc[-1]
                return {'signal': 'JUNAM SELL', 'sl': round(sl, 5), 'tp': round(tp, 5)}

        if ema5.iloc[-1] > ema20.iloc[-1] and stoch.iloc[-1] < 0.2 and breakout_up:
            sl = recent_low - atr.iloc[-1]
            tp = close_now + 2 * atr.iloc[-1]
            return {'signal': 'BREAKOUT BUY', 'sl': round(sl, 5), 'tp': round(tp, 5)}

        if ema5.iloc[-1] < ema20.iloc[-1] and stoch.iloc[-1] > 0.8 and breakout_down:
            sl = recent_high + atr.iloc[-1]
            tp = close_now - 2 * atr.iloc[-1]
            return {'signal': 'BREAKOUT SELL', 'sl': round(sl, 5), 'tp': round(tp, 5)}

        return None
    except Exception as e:
        return f"ANALYSIS_ERROR: {e}"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cid = update.message.chat_id
    if cid not in AUTHORIZED_USERS:
        await update.message.reply_text("Akses ditolak.")
        return
    await update.message.reply_text("Bot aktif. Tunggu sinyal...")

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)

async def send_signal(app, message):
    for uid in AUTHORIZED_USERS:
        try:
            await app.bot.send_message(chat_id=uid, text=message, parse_mode='Markdown')
        except:
            pass

async def analysis_loop(app):
    while True:
        news = get_forex_news()
        news_text = "\n".join(f"- {n}" for n in news)

        for symbol in SYMBOLS:
            try:
                df = yf.download(tickers=symbol, interval='1m', period='1d', progress=False)
                df.dropna(inplace=True)
                result = analyze(df)
                if isinstance(result, dict):
                    label = "⚠️ JUNAM DETECTED ⚠️\n" if "JUNAM" in result['signal'] else ""
                    msg = (
                        f"{label}**SINYAAL M1**\nPair: {symbol}\n"
                        f"Sinyal: {result['signal']}\nSL: {result['sl']} | TP: {result['tp']}\n"
                        f"Time: {datetime.now()}\n\nBerita:\n{news_text}"
                    )
                    await send_signal(app, msg)
                    write_log(msg)
                elif isinstance(result, str) and result.startswith("ANALYSIS_ERROR"):
                    write_log(f"[ERROR] {symbol}: {result}")
            except Exception as e:
                write_log(f"[ERROR] {symbol}: {e}")
        await asyncio.sleep(LOOP_DELAY)

async def start_bot():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
    asyncio.create_task(analysis_loop(app))
    write_log("Bot aktif & polling dimulai")
    await app.run_polling()
