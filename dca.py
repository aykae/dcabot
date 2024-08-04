import urllib.parse
import hashlib
import hmac
import base64
import os
import time
import requests

def get_kraken_signature(urlpath, data, secret):

    postdata = urllib.parse.urlencode(data)
    encoded = (str(data['nonce']) + postdata).encode()
    message = urlpath.encode() + hashlib.sha256(encoded).digest()

    mac = hmac.new(base64.b64decode(secret), message, hashlib.sha512)
    sigdigest = base64.b64encode(mac.digest())
    return sigdigest.decode()

# Read Kraken API key and secret stored in environment variables
api_url = "https://api.kraken.com"
api_key = os.getenv('API_PUBLIC')
api_sec = os.getenv('API_SECRET')

# Attaches auth headers and returns results of a POST request
def kraken_request(uri_path, data, api_key, api_sec):
    headers = {}
    headers['API-Key'] = api_key
    # get_kraken_signature() as defined in the 'Authentication' section
    headers['API-Sign'] = get_kraken_signature(uri_path, data, api_sec)             
    req = requests.post((api_url + uri_path), headers=headers, data=data)
    return req

###############
###############

MONTHLY_TARGET_NOTIONAL = 1000
MIN_BTC_VOLUME = 0.0001
THIRTY_SECONDS = 30
ONE_HOUR = 60*60

interval = THIRTY_SECONDS
insufficientBalance = True

next_time = time.time() + interval

while True:

    if time.time() < next_time:
        continue

    if insufficientBalance:
        time.sleep(THIRTY_SECONDS)

    # Construct the request and print the result
    ticker = requests.get('https://api.kraken.com/0/public/Ticker?pair=XBTUSD')
    best_ask = float(ticker.json().get('result').get('XXBTZUSD').get('a')[0])
    volume = '{:.8f}'.format(MIN_BTC_VOLUME)
    notional = best_ask * MIN_BTC_VOLUME

    try:
        resp = kraken_request('/0/private/Balance', {
            "nonce": str(int(1000*time.time()))
        }, api_key, api_sec)
    except:
        time.sleep(THIRTY_SECONDS)
        continue

    usd_balance = float(resp.json().get('result').get('ZUSD'))

    if usd_balance < notional:
        insufficientBalance = True
    else:
        insufficientBalance = False

        ## Execute Trade
        try: 
            resp = kraken_request('/0/private/AddOrder', {
                "nonce": str(int(1000*time.time())),
                "ordertype": "market",
                "type": "buy",
                "volume": volume,
                "pair": "XBTUSD",
            }, api_key, api_sec)
        except:
            time.sleep(THIRTY_SECONDS)
            continue

        ## Recompute interval and reset
        interval = MONTHLY_TARGET_NOTIONAL * 12 / 365 / notional * 60 * 60
        next_time = time.time() + interval