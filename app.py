from flask import Flask, request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_caching import Cache
import requests
from datetime import datetime



app = Flask(__name__)

# Configure Flask-Caching
app.config['CACHE_TYPE'] = 'simple'  # You can choose a different caching type based on your needs
cache = Cache(app)

# Configure Flask-Limiter
limiter = Limiter(get_remote_address, app=app)


@app.route('/')
def maindoc():
    return 'Hello, Docker and Nginx!'


@cache.memoize(timeout=60)
def get_spotprices(start, priceArea):
    params = {
        "start": start.isoformat(),
        "filter": '{"PriceArea":"%s"}' % priceArea,
        "sort": "HourUTC asc",
    }
    response = requests.get('https://api.energidataservice.dk/dataset/elspotprices', params=params)
    if response.status_code == 200:
        return response.json()
    else:
        return None

@cache.memoize(timeout=60)
def get_tariffs(start, gln_Number, chargeTypeCode):
    params = {
        "start": start.isoformat(),
        "filter": '{"GLN_Number":"%s"}' % gln_Number,
        #"sort": "HourUTC asc",
    }
    response = requests.get('https://api.energidataservice.dk/dataset/DatahubPriceList', params=params)
    if response.status_code == 200:
        return response.json()
    else:
        return None

def date_from_reqparam(param):
    date_format = '%Y-%m-%d'
    return datetime.strptime(param, date_format).date()

    

@app.route('/elpris')
def elpris():
    startDate = request.args.get('start', datetime.now().date(), type=date_from_reqparam)
    priceArea = request.args.get('PriceArea', 'DK1')
    gln_Number = request.args.get('GLN_Number', '5790000611003')
    chargeTypeCode = request.args.get('ChargeTypeCode', 'T-C-F-T-TD')

    spotprices = get_spotprices(startDate, priceArea)
    tariffs = get_tariffs(startDate, gln_Number, chargeTypeCode)

    

    return jsonify(locals())

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)

