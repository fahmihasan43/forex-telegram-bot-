from flask import Flask
from threading import Thread
import asyncio
from main import start_bot

app = Flask('')

@app.route('/')
def home():
    return "Forex bot aktif!"

@app.route('/start')
def trigger():
    Thread(target=asyncio.run, args=(start_bot(),)).start()
    return "Bot dimulai!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    Thread(target=run).start()

if __name__ == '__main__':
    keep_alive()
    asyncio.run(start_bot())
