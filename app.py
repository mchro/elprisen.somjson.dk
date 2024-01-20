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

@cache.memoize(timeout=60*60)
def get_tariffs(gln_Number, chargeTypeCode):
    params = {
        "filter": '{"GLN_Number":"%s", "ChargeType":"D03", "ChargeTypeCode":"%s"}' % (gln_Number, chargeTypeCode),
        #"sort": "HourUTC asc",
        "limit": 0,
    }
    response = requests.get('https://api.energidataservice.dk/dataset/DatahubPriceList', params=params)
    if response.status_code == 200:
        return response.json()['records']
    else:
        return None


@cache.memoize(timeout=60)
def get_tariffs_for_date(start, gln_Number, chargeTypeCode):
    tariffs = get_tariffs(gln_Number, chargeTypeCode)

    start = datetime.combine(start, datetime.min.time())

    for t in tariffs:
        t['ValidFrom'] = datetime.fromisoformat(t['ValidFrom'])
        t['ValidTo'] = t['ValidTo'] and datetime.fromisoformat(t['ValidTo']) or None

        if start >= t['ValidFrom'] and start < t['ValidTo']:
            return t

    #relevant_tariff = filter(lambda x: x['ValidFrom'] , tariffs)
    
    return None

def date_from_reqparam(param):
    date_format = '%Y-%m-%d'
    return datetime.strptime(param, date_format).date()

companyToGLN = {
    "N1 A/S": "5790000611003",
    "Zeanet A/S": "5790001089375",
    "NOE Net A/S": "5790000395620",

}

default_chargeType_perGLN = {
    "5790000611003": "T-C-F-T-TD",
    "5790001089375": "43110",
    "5790000395620": "30030",
}

elafgift = 0.761

#https://energinet.dk/el/elmarkedet/tariffer/aktuelle-tariffer/
nettarif = 0.074
systemtarif = 0.051

moms = 1.25 #percentage



@app.route('/elpris')
def elpris():
    startDate = request.args.get('start', datetime.now().date(), type=date_from_reqparam)
    priceArea = request.args.get('PriceArea', 'DK1')
    gln_Number = request.args.get('GLN_Number', '5790000611003')
    chargeTypeCode = request.args.get('ChargeTypeCode')
    if not chargeTypeCode:
        chargeTypeCode = default_chargeType_perGLN[gln_Number]

    spotprices = get_spotprices(startDate, priceArea)
    tariffs = get_tariffs_for_date(startDate, gln_Number, chargeTypeCode)

    

    return jsonify(locals())

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)

