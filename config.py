import os
basedir = os.path.abspath(os.path.dirname(__file__))
from ccxt import binance

API_KEY = os.environ['kat_API_KEY']
API_SECRET = os.environ['kat_API_SECRET']
PASSPHRASE = os.environ['kat_PASSPHRASE']
DatabaseURL = 'sqlite:///' + os.path.join(basedir,'db.sqlite')
exchange = binance({
   "apiKey": API_KEY, 
   "secret": API_SECRET,
   "enableRateLimit": True,
})

