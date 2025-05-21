from flask import Flask
from threading import Thread
import asyncio
from main import start_bot

app = Flask('')

@app.route('/')
def home():
    return "Bot aktif di Railway!"

@app.route('/start')
def trigger():
    Thread(target=asyncio.run, args=(start_bot(),)).start()
    return "Bot dimulai!"

def run():
    app.run(host='0.0.0.0', port=8080)

if __name__ == '__main__':
    run()
