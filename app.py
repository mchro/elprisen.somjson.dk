from flask import Flask, request, jsonify, abort, redirect, url_for, render_template, send_from_directory
#from flask_limiter import Limiter
#from flask_limiter.util import get_remote_address
from flask_caching import Cache
import requests
from datetime import datetime
from dataclasses import dataclass
from itertools import zip_longest
from typing import Optional

app = Flask(__name__)

# Configure Flask-Caching
app.config['CACHE_TYPE'] = 'simple'
cache = Cache(app)

# Configure Flask-Limiter
#limiter = Limiter(get_remote_address, app=app)


@app.route('/')
def maindoc():
    return render_template('main.html')

@cache.memoize(timeout=60)
def get_spotprices(start, priceArea):
    params = {
        "start": start.isoformat(),
        "filter": '{"PriceArea":"%s"}' % priceArea,
        "sort": "HourUTC asc",
    }
    response = requests.get('https://api.energidataservice.dk/dataset/elspotprices', params=params, verify="energidataservice.pem")
    if response.status_code == 200:
        return response.json()
    else:
        print ("Error getting spotprices", response)
        return None

@cache.memoize(timeout=60)
def get_co2emissions(start, priceArea):
    params = {
        "start": start.isoformat(),
        "filter": '{"PriceArea":"%s"}' % priceArea,
        "sort": "Minutes5UTC asc",
    }
    response = requests.get('https://api.energidataservice.dk/dataset/CO2EmisProg', params=params, verify="energidataservice.pem")
    if response.status_code == 200:
        return response.json()
    else:
        return None

def hour_from_isotimestamp(ts):
    return ts[:len("YYYY-MM-DDTHH")]

@cache.memoize(timeout=60)
def get_co2emissions_avgperhour(start, priceArea):
    co2emissions = get_co2emissions(start, priceArea)

    perhour = []
    curhour = None
    curvalues = []
    for x in co2emissions['records']:
        xhour = hour_from_isotimestamp(x['Minutes5DK'])
        if curhour is None or curhour != xhour:
            if curvalues != []:
                perhour += [{
                        "HourDK": curhour + ":00:00",
                        "CO2Emission": sum(curvalues) / len(curvalues)
                    }]
            curhour = xhour
            curvalues = []

        curvalues += [x['CO2Emission']]

    #handle last hour
    if curhour:
        perhour += [{
                "HourDK": curhour + ":00:00",
                "CO2Emission": sum(curvalues) / len(curvalues)
            }]

    return {
        'records': perhour,
        }

@cache.memoize(timeout=60*60)
def get_tariffs(gln_Number, chargeTypeCode):
    params = {
        "filter": '{"GLN_Number":"%s", "ChargeType":"D03", "ChargeTypeCode":"%s"}' % (gln_Number, chargeTypeCode),
        #"sort": "HourUTC asc",
        "limit": 0,
    }
    response = requests.get('https://api.energidataservice.dk/dataset/DatahubPriceList', params=params, verify="energidataservice.pem")
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
            #compensate for potentially missing prices, use Price1
            for i in range(2, 25):
                if not t[f'Price{i}']:
                    t[f'Price{i}'] = t['Price1']
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
    GridCompany("Radius Elnet A/S", "5790000705689", "DT_C_01", "790", "DK2"),
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
    GridCompany("Nord Energi Net A/S", "5790000610877", "TAC", "032", "DK1"),
    GridCompany("RAH Net A/S", "5790000681327", "RAH-C", "348", "DK1"),
    GridCompany("Videbæk Elnet A/S", "5790000610822", "VE-ON-11", "385", "DK1"), #maybe also need to add "VE-NT-01"
    GridCompany("Ravdex A/S", "5790000836727", "NT-C", "531", "DK1"),
    GridCompany("Midtfyns Elforsyning A.m.b.A", "5790001089023", "TNT15000", "584", "DK1"),
    GridCompany("FLOW Elnet A/S", "5790000392551", "FE2 NT-01", "533", "DK1"),
    GridCompany("Veksel A/S", "5790001088217", "NT-10", "532", "DK1"),
    GridCompany("TREFOR El-net A/S", "5790000392261", "C", "244", "DK1"),
    GridCompany("Cerius A/S", "5790000705184", "30TR_C_ET", "740", "DK2"),
    GridCompany("Elinord A/S", "5790001095277", "43300", "051", "DK1"),
    GridCompany("Dinel A/S - 232", "5790000610099", "TCL<100_02", "232", "DK1"),
    GridCompany("Dinel A/S - 233", "5790000610099", "TCL<100_02", "233", "DK1"),
    GridCompany("Ikast El Net A/S", "5790000682102", "IEV-NT-05", "342", "DK1"),
    GridCompany("KONSTANT Net A/S", "5790000704842", "151-NT01T", "151", "DK1"),
    GridCompany("KONSTANT Net A/S", "5790000683345", "245-NT01T", "245", "DK1"),
    GridCompany("Hammel El-forsyning Net A/S", "5790001090166", "C-Tarif", "141", "DK1"),
    GridCompany("El-net Kongerslev A/S", "5790002502699", "C-Tarif", "016", "DK1"),
    GridCompany("Tarm Elværk Net A/S", "5790000706419", "TEV-NT-11T", "384", "DK1"),
    GridCompany("L-NET A/S", "5790001090111", "4000", "351", "DK1"),
    GridCompany("Hjerting Transformatorforening", "5790001095376", "C-Tarif", "371", "DK1"),
    GridCompany("Nakskov Elnet A/S", "5790001088460", "92TR_C_ET", "853", "DK2"),
    GridCompany("Læsø Elnet A/S", "5790001103460", "43100", "085", "DK1"),
]

@app.route('/gridcompanies')
def route_gridcompanies():
    return jsonify(gridCompanies)

elafgift = 0.761

#https://energinet.dk/el/elmarkedet/tariffer/aktuelle-tariffer/
#TODO: get these from the API, or update for 2025
energinet_nettarif = 0.074
energinet_systemtarif = 0.051

moms = 1.25 #percentage

@cache.memoize(timeout=60*60)
def get_info_for_address(address):
    response = requests.get('https://api.elnet.greenpowerdenmark.dk/api/supplierlookup/' + address)

    if response.status_code == 200:
        return response.json()
    else:
        return None

@app.route('/adresse/<address>')
def adresse(address):
    if len(address) > 100:
        abort(400, 'Address too long')

    info = get_info_for_address(address)
    if not info:
        abort(400, 'Address not found in lookup API')

    gridCompanyNumber = info['def']
    gridCompany = next((c for c in gridCompanies if c.gridCompanyNumber == gridCompanyNumber), None)
    if not gridCompany:
        print(f'Gridcompany not found for number {gridCompanyNumber}')
        abort(500, f'Gridcompany not found for number {gridCompanyNumber}')

    startDate = request.args.get('start')
    start = startDate and '&start=' + startDate or ''
    return redirect(url_for('elpris') + "?GLN_Number=" + gridCompany.gln_Number + start)

@app.route('/elpris')
def elpris():
    startDate = request.args.get('start', datetime.now().date(), type=date_from_reqparam)
    gln_Number = request.args.get('GLN_Number', '5790000611003')
    gridCompany = next((c for c in gridCompanies if c.gln_Number == gln_Number), None)

    priceArea = request.args.get('PriceArea', gridCompany.priceArea)
    chargeTypeCode = request.args.get('ChargeTypeCode', gridCompany.chargeTypeCode)
    if not chargeTypeCode:
        chargeTypeCode = gridCompany.chargeTypeCode

    spotprices = get_spotprices(startDate, priceArea)
    co2emissions = get_co2emissions_avgperhour(startDate, priceArea)

    records = []
    for (p, hour, emission) in zip_longest(spotprices['records'], range(len(spotprices['records'])), co2emissions['records']):
        tariffs = get_tariffs_for_date(datetime.fromisoformat(p['HourDK']), gln_Number, chargeTypeCode)

        pout = {
            'HourDK': p['HourDK'],
            'HourUTC': p['HourUTC'],
            'SpotPrice': p['SpotPriceDKK'] / 1000.0, # MWh to KWh

            'ElAfgift': elafgift,
            'EnergiNetNetTarif': energinet_nettarif,
            'EnergiNetSystemTarif': energinet_systemtarif,

            'NetselskabTarif': tariffs['Price%d' % (hour % 24 + 1)],

            'CO2Emission': emission and emission['CO2Emission'] or None,
        }
        pout['TotalExMoms'] = pout['SpotPrice'] + pout['ElAfgift'] + \
                pout['EnergiNetNetTarif'] + pout['EnergiNetSystemTarif'] + \
                pout['NetselskabTarif']
        pout['Moms'] = pout['TotalExMoms'] * 0.25
        pout['Total'] = pout['TotalExMoms'] + pout['Moms']
        records.append(pout)

    
    return jsonify({
        'gridCompany': gridCompany,
        'records': records
        })

@app.route('/apidocs/')
def swagger_ui():
    return render_template('swagger_ui.html')

@app.route('/apispec')
def get_spec():
    return send_from_directory(app.root_path, 'openapi.yaml')


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)

