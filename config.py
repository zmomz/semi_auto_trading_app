import os
from ccxt import binance

API_KEY = os.environ['API_KEY']
API_SECRET = os.environ['API_SECRET']
PASSPHRASE = os.environ['PASSPHRASE']
DatabaseURL = 'postgresql+psycopg2:'+(os.environ['DATABASE_URL']).split(':')[1]
exchange = binance({
   "apiKey": API_KEY, 
   "secret": API_SECRET,
   "enableRateLimit": True,
})
