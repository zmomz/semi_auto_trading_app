import os
from ccxt import binance

API_KEY = os.environ.APIKEY
API_SECRET = os.environ.env.APISECRET
PASSPHRASE = os.environ.env.PASSPHRASE

exchange = binance({
   "apiKey": API_KEY, 
   "secret": API_SECRET,
   "enableRateLimit": True,
})
