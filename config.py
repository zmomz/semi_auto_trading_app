import os
from ccxt import binance

API_KEY = os.environ.API_KEY
API_SECRET = os.environ.env.API_SECRET
PASSPHRASE = os.environ.env.PASSPHRASE

exchange = binance({
   "apiKey": API_KEY, 
   "secret": API_SECRET,
   "enableRateLimit": True,
})
