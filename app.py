from flask import Flask, request, jsonify, abort, redirect, url_for
#from flask_limiter import Limiter
#from flask_limiter.util import get_remote_address
from flask_caching import Cache
import requests
from datetime import datetime
from dataclasses import dataclass
from typing import Optional

app = Flask(__name__)

# Configure Flask-Caching
app.config['CACHE_TYPE'] = 'simple'
cache = Cache(app)

# Configure Flask-Limiter
#limiter = Limiter(get_remote_address, app=app)


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
        #XXX seems buggy if t['ValidTo'] is None

        if start >= t['ValidFrom'] and start < t['ValidTo']:
            return t

    return None

def date_from_reqparam(param):
    date_format = '%Y-%m-%d'
    return datetime.strptime(param, date_format).date()

@dataclass
class GridCompany:
    name: str
    gln_Number: str
    chargeTypeCode: str
    gridCompanyNumber: str
    priceArea: Optional[str] = "DK1"

#Painfully manually extracted from https://www.energidataservice.dk/tso-electricity/DatahubPricelist
gridCompanies = [
    GridCompany("N1 A/S", "5790000611003", "T-C-F-T-TD", "344", "DK1"),
    GridCompany("Zeanet A/S", "5790001089375", "43110", "860", "DK2"),
    GridCompany("NOE Net A/S", "5790000395620", "30030", "347", "DK1"),
    GridCompany("Radius Elnet A/S", "5790000705689", "DT_C_01", "791", "DK2"),
    GridCompany("Netselskabet Elværk A/S - 331", "5790000681358", "5NCFF", "331", "DK1"),
    GridCompany("TREFOR El-Net Øst A/S", "5790000706686", "46", "911", "DK2"),
    GridCompany("Sunds Net A.m.b.a", "5790001095444", "SEF-NT-05", "396", "DK1"),
    GridCompany("Elnet Midt A/S", "5790001100520", "T3001", "154", "DK1"),
    GridCompany("Vores Elnet A/S", "5790000610976", "TNT1011", "543", "DK1"),
    GridCompany("Netselskabet Elværk A/S - 042", "5790000681075", "0NCFF", "042", "DK1"),
    GridCompany("NKE-Elnet A/S", "5790001088231", "94TR_C_ET", "854", "DK2"),
    GridCompany("Hurup Elværk Net A/S", "5790000610839", "HEV-NT-01T", "381", "DK1"),
    GridCompany("Elektrus A/S", "5790000836239", "6000091", "757", "DK2"),
    GridCompany("Aal El-Net A M B A", "5790001095451", "AAL-NT-05", "370", "DK1"),
    GridCompany("Nord Energi Net A/S", "5790000610877", "TAC", "031", "DK1"),
    GridCompany("RAH Net A/S", "5790000681327", "RAH-C", "348", "DK1"),
    GridCompany("Videbæk Elnet A/S", "5790000610822", "VE-ON-11", "385", "DK1"), #maybe also need to add "VE-NT-01"
    GridCompany("Ravdex A/S", "5790000836727", "NT-C", "531", "DK1"),
    GridCompany("Midtfyns Elforsyning A.m.b.A", "5790001089023", "TNT15000", "584", "DK1"),
    GridCompany("FLOW Elnet A/S", "5790000392551", "FE2 NT-01", "533", "DK1"),
    GridCompany("Veksel A/S", "5790001088217", "NT-10", "532", "DK1"),
    GridCompany("TREFOR El-net A/S", "5790000392261", "C", "244", "DK1"),
]

elafgift = 0.761

#https://energinet.dk/el/elmarkedet/tariffer/aktuelle-tariffer/
energinet_nettarif = 0.074
energinet_systemtarif = 0.051

moms = 1.25 #percentage


#TODO: support address lookup by https://api.elnet.greenpowerdenmark.dk/api/supplierlookup/Ringstedgade%2066,%204000%20Roskilde


@app.route('/elpris')
def elpris():
    startDate = request.args.get('start', datetime.now().date(), type=date_from_reqparam)
    priceArea = request.args.get('PriceArea', 'DK1')
    gln_Number = request.args.get('GLN_Number', '5790000611003')
    gridCompany = next((c for c in gridCompanies if c.gln_Number == gln_Number), None)

    chargeTypeCode = request.args.get('ChargeTypeCode')
    if not chargeTypeCode:
        chargeTypeCode = gridCompany.chargeTypeCode

    spotprices = get_spotprices(startDate, priceArea)
    tariffs = get_tariffs_for_date(startDate, gln_Number, chargeTypeCode)


    prices = []
    for (p, hour) in zip(spotprices['records'], range(len(spotprices['records']))):
        pout = {
            'HourDK': p['HourDK'],
            'HourUTC': p['HourUTC'],
            'SpotPrice': p['SpotPriceDKK'] / 1000.0, # MWh to KWh

            'ElAfgift': elafgift,
            'EnergiNetNetTarif': energinet_nettarif,
            'EnergiNetSystemTarif': energinet_systemtarif,

            'NetselskabTarif': tariffs['Price%d' % (hour % 24 + 1)]
        }
        pout['TotalExMoms'] = pout['SpotPrice'] + pout['ElAfgift'] + \
                pout['EnergiNetNetTarif'] + pout['EnergiNetSystemTarif'] + \
                pout['NetselskabTarif']
        pout['Moms'] = pout['TotalExMoms'] * 0.25
        pout['Total'] = pout['TotalExMoms'] + pout['Moms']
        prices.append(pout)

    
    return jsonify(locals())

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)

