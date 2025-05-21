import nest_asyncio
import asyncio
import pandas as pd
import yfinance as yf
import logging
from datetime import datetime
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands, AverageTrueRange
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

nest_asyncio.apply()

TOKEN = "ISI_TOKEN_BOT_KAMU"
AUTHORIZED_USERS = {7866728515}
ADMIN_ID = 7866728515
SYMBOLS = ['EURUSD=X', 'USDJPY=X']
LOOP_DELAY = 60

logging.basicConfig(level=logging.INFO)

def write_log(msg):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now}] {msg}")

def analyze(df):
    try:
        df = df.copy()
        close = df['Close']
        high = df['High']
        low = df['Low']
        rsi = RSIIndicator(close, window=14).rsi()
        bb = BollingerBands(close, window=20, window_dev=2)
        upper = bb.bollinger_hband()
        lower = bb.bollinger_lband()
        atr = AverageTrueRange(high, low, close).average_true_range()
        close_now = close.iloc[-1]
        rsi_now = rsi.iloc[-1]
        upper_now = upper.iloc[-1]
        lower_now = lower.iloc[-1]

        signal = None
        sl, tp = None, None

        # FLY breakout BUY
        if close_now < lower_now and rsi_now < 30:
            signal = "BUY"
            sl = close_now - atr.iloc[-1]
            tp = close_now + 2 * atr.iloc[-1]

        # JUNAM breakout SELL
        elif close_now > upper_now and rsi_now > 70:
            signal = "SELL"
            sl = close_now + atr.iloc[-1]
            tp = close_now - 2 * atr.iloc[-1]

        # Deteksi tambahan FLY/JUNAM
        label = ""
        if len(close) >= 11:
            change = (close_now - close[-11]) / close[-11]
            if change > 0.02:
                label = "🚀 *FLY DETECTED* 🚀"
            elif change < -0.02:
                label = "⚠️ *JUNAM DETECTED* ⚠️"

        if signal:
            return {
                'signal': signal,
                'sl': round(sl, 5),
                'tp': round(tp, 5),
                'label': label
            }
        return None
    except Exception as e:
        return f"ANALYSIS_ERROR: {e}"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cid = update.message.chat_id
    if cid not in AUTHORIZED_USERS:
        await update.message.reply_text("Akses ditolak.")
        return
    await update.message.reply_text("Bot aktif. Menunggu sinyal BB/RSI...")

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)

async def send_signal(app, msg):
    for uid in AUTHORIZED_USERS:
        try:
            await app.bot.send_message(chat_id=uid, text=msg, parse_mode='Markdown')
        except Exception as e:
            write_log(f"Send error: {e}")

async def analysis_loop(app):
    while True:
        for symbol in SYMBOLS:
            try:
                df = yf.download(tickers=symbol, interval='1m', period='1d', progress=False)
                df.dropna(inplace=True)
                result = analyze(df)
                if isinstance(result, dict):
                    msg = (
                        f"{result['label']}\n" if result['label'] else ""
                    ) + f"""**SINYAL M1**\nPair: {symbol}
Sinyal: {result['signal']}
SL: {result['sl']} | TP: {result['tp']}
Waktu: {datetime.now()}"""
                    await send_signal(app, msg)
                    write_log(f"{symbol} {result['signal']} sent.")
            except Exception as e:
                write_log(f"[ERROR] {symbol}: {e}")
        await asyncio.sleep(LOOP_DELAY)

async def start_bot():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
    asyncio.create_task(analysis_loop(app))
    write_log("Bot aktif. Menunggu sinyal...")
    await app.run_polling()
