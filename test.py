# test_app.py
import unittest
from parameterized import parameterized, parameterized_class
import datetime
from flask import Flask, jsonify
import json
from pprint import pprint
import app

class TestApp(unittest.TestCase):
    def setUp(self):
        # Set up a test client
        self.app = app.app.test_client()

    def test_spotprices(self):
        startDate = app.date_from_reqparam("2024-02-23")
        spotprices = app.get_spotprices_legacy(startDate, "DK1")

        hour0 = spotprices['records'][0]
        self.assertEqual(hour0['HourDK'], '2024-02-23T00:00:00')
        self.assertEqual(hour0['PriceArea'], 'DK1')
        self.assertEqual(hour0['SpotPriceDKK'], 68.800003)

    def test_dayaheadprices_against_legacy(self):
        startDate = app.date_from_reqparam("2025-09-19")
        spotprices = app.get_spotprices_legacy(startDate, "DK1")
        dayaheadprices = app.get_spotprices_from_dayahead_prices(startDate, "DK1")

        for sp, dah in zip(spotprices['records'], dayaheadprices['records']):
            self.assertEqual(sp['HourDK'], dah['HourDK'])
            self.assertEqual(sp['HourUTC'], dah['HourUTC'])
            self.assertEqual(sp['SpotPriceDKK'], dah['SpotPriceDKK'])

    def test_co2emissions(self):
        startDate = app.date_from_reqparam("2024-02-23")
        co2emissions = app.get_co2emissions(startDate, "DK1")

        hour0 = co2emissions['records'][0]
        self.assertEqual(hour0['Minutes5DK'], '2024-02-23T00:00:00')
        self.assertEqual(hour0['PriceArea'], 'DK1')
        self.assertEqual(hour0['CO2Emission'], 87.0)

    def test_co2emissions_avgperhour(self):
        startDate = app.date_from_reqparam("2024-02-23")
        co2emissions = app.get_co2emissions_avgperhour(startDate, "DK1")

        hour0 = co2emissions['records'][0]
        self.assertEqual(hour0['HourDK'], '2024-02-23T00:00:00')
        self.assertEqual(hour0['CO2Emission'], 94.25)

        hour1 = co2emissions['records'][1]
        self.assertEqual(hour1['HourDK'], '2024-02-23T01:00:00')
        self.assertEqual(hour1['CO2Emission'], 95.08333333333333)

    def test_co2emissions_aligned_to_timeseries(self):
        startDate = app.date_from_reqparam("2025-09-20")
        endDate = app.date_from_reqparam("2025-09-21")
        timestamps = []
        current_time = datetime.datetime.combine(startDate, datetime.time.min)

        while current_time <= datetime.datetime.combine(endDate, datetime.time.min):
            timestamps.append(current_time)
            current_time += datetime.timedelta(minutes=15)

        co2emissions = app.get_co2emissions_aligned_to_timeseries(startDate, "DK1", timestamps, endDate)

        rec0 = co2emissions['records'][0]
        self.assertEqual(rec0['TimeDK'], '2025-09-20T00:00:00')
        self.assertEqual(rec0['CO2Emission'], (12+11+11)/3)

        rec1 = co2emissions['records'][1]
        self.assertEqual(rec1['TimeDK'], '2025-09-20T00:15:00')
        self.assertEqual(rec1['CO2Emission'], (12+13+13)/3)

        rec95 = co2emissions['records'][95]
        self.assertEqual(rec95['TimeDK'], '2025-09-20T23:45:00')
        #self.assertEqual(rec95['CO2Emission'], (121+121+118)/3)

    def test_get_tariffs(self):
        gridCompany = app.gridCompanies[0]
        self.assertEqual(gridCompany.name, "N1 A/S")
        self.assertEqual(gridCompany.gridCompanyNumber, "344")

        startDate = app.date_from_reqparam("2024-02-23")
        gln_Number = gridCompany.gln_Number
        chargeTypeCode = gridCompany.chargeTypeCode

        tariffs = app.get_tariffs_for_date(startDate, gln_Number, chargeTypeCode)

        self.assertEqual(tariffs['GLN_Number'], gln_Number)
        self.assertEqual(tariffs['ChargeType'], 'D03')
        self.assertEqual(tariffs['ChargeTypeCode'], chargeTypeCode)
        self.assertEqual(tariffs['ValidFrom'], datetime.datetime(2024, 2, 19, 0, 0))
        self.assertEqual(tariffs['ValidTo'], datetime.datetime(2024, 2, 24, 0, 0))
        self.assertEqual(tariffs['Price1'], 0.1101)
        self.assertEqual(tariffs['Price2'], 0.1101)
        self.assertEqual(tariffs['Price3'], 0.1101)
        self.assertEqual(tariffs['Price4'], 0.1101)
        self.assertEqual(tariffs['Price5'], 0.1101)
        self.assertEqual(tariffs['Price6'], 0.1101)
        self.assertEqual(tariffs['Price7'], 0.3303)
        self.assertEqual(tariffs['Price8'], 0.3303)
        self.assertEqual(tariffs['Price9'], 0.3303)
        self.assertEqual(tariffs['Price10'], 0.3303)
        self.assertEqual(tariffs['Price11'], 0.3303)
        self.assertEqual(tariffs['Price12'], 0.3303)
        self.assertEqual(tariffs['Price13'], 0.3303)
        self.assertEqual(tariffs['Price14'], 0.3303)
        self.assertEqual(tariffs['Price15'], 0.3303)
        self.assertEqual(tariffs['Price16'], 0.3303)
        self.assertEqual(tariffs['Price17'], 0.3303)
        self.assertEqual(tariffs['Price18'], 0.991)
        self.assertEqual(tariffs['Price19'], 0.991)
        self.assertEqual(tariffs['Price20'], 0.991)
        self.assertEqual(tariffs['Price21'], 0.991)
        self.assertEqual(tariffs['Price22'], 0.3303)
        self.assertEqual(tariffs['Price23'], 0.3303)
        self.assertEqual(tariffs['Price24'], 0.3303)

    def test_get_tariffs_only1hour(self):
        gridCompany = next(c for c in app.gridCompanies if c.name == 'Elinord A/S')

        startDate = app.date_from_reqparam("2024-02-23")
        gln_Number = gridCompany.gln_Number
        chargeTypeCode = gridCompany.chargeTypeCode

        tariffs = app.get_tariffs_for_date(startDate, gln_Number, chargeTypeCode)

        self.assertEqual(tariffs['GLN_Number'], gln_Number)
        self.assertEqual(tariffs['ChargeType'], 'D03')
        self.assertEqual(tariffs['ChargeTypeCode'], chargeTypeCode)
        self.assertEqual(tariffs['ValidFrom'], datetime.datetime(2023, 4, 1, 0, 0))
        self.assertEqual(tariffs['ValidTo'], datetime.datetime(2024, 3, 1, 0, 0))
        self.assertEqual(tariffs['Price1'], 0.2724)
        self.assertEqual(tariffs['Price2'], 0.2724)
        self.assertEqual(tariffs['Price3'], 0.2724)
        self.assertEqual(tariffs['Price4'], 0.2724)
        self.assertEqual(tariffs['Price5'], 0.2724)
        self.assertEqual(tariffs['Price6'], 0.2724)
        self.assertEqual(tariffs['Price7'], 0.2724)
        self.assertEqual(tariffs['Price8'], 0.2724)
        self.assertEqual(tariffs['Price9'], 0.2724)
        self.assertEqual(tariffs['Price10'], 0.2724)
        self.assertEqual(tariffs['Price11'], 0.2724)
        self.assertEqual(tariffs['Price12'], 0.2724)
        self.assertEqual(tariffs['Price13'], 0.2724)
        self.assertEqual(tariffs['Price14'], 0.2724)
        self.assertEqual(tariffs['Price15'], 0.2724)
        self.assertEqual(tariffs['Price16'], 0.2724)
        self.assertEqual(tariffs['Price17'], 0.2724)
        self.assertEqual(tariffs['Price18'], 0.2724)
        self.assertEqual(tariffs['Price19'], 0.2724)
        self.assertEqual(tariffs['Price20'], 0.2724)
        self.assertEqual(tariffs['Price21'], 0.2724)
        self.assertEqual(tariffs['Price22'], 0.2724)
        self.assertEqual(tariffs['Price23'], 0.2724)
        self.assertEqual(tariffs['Price24'], 0.2724)

    def test_get_info_for_address1(self):
        address = "Ringstedgade 66, 4000 Roskilde"
        info = app.get_info_for_address(address)

        self.assertEqual(info['name'], 'Cerius A/S')
        self.assertEqual(info['def'], '740')

    def test_get_info_for_address2(self):
        address = "Sofiendalsvej 80, 9200 Aalborg"
        info = app.get_info_for_address(address)

        self.assertEqual(info['name'], 'Elnetselskabet N1')
        self.assertEqual(info['def'], '344')

    def test_mainroute(self):
        response = self.app.get('/elpris?start=2025-07-23')

        self.assertEqual(response.status_code, 200)

        hour0 = response.json['records'][0]
        self.assertEqual(hour0['HourDK'], '2025-07-23T00:00:00')
        self.assertEqual(hour0['CO2Emission'], 9.833333333333334)
        self.assertEqual(hour0['SpotPrice'], 0.5672868)
        self.assertEqual(hour0['NetselskabTarif'], 0.0867)
        self.assertEqual(hour0['Total'], 1.8862335)

        hour1 = response.json['records'][1]
        self.assertEqual(hour1['HourDK'], '2025-07-23T01:00:00')
        self.assertEqual(hour1['CO2Emission'], 12.583333333333334)
        self.assertEqual(hour1['SpotPrice'], 0.522501)
        self.assertEqual(hour1['NetselskabTarif'], 0.0867)
        self.assertEqual(hour1['Total'], 1.8302512499999999)

    def test_mainroute_noparams(self):
        response = self.app.get('/elpris')

        self.assertEqual(response.status_code, 200)

    def test_mainroute_detailed_noparams(self):
        response = self.app.get('/elpris-detaljer')

        self.assertEqual(response.status_code, 200)

    def test_mainroute_changeoverdate(self):
        response = self.app.get('/elpris?start=2024-09-30')

        self.assertEqual(response.status_code, 200)

        hour0 = response.json['records'][6]
        self.assertEqual(hour0['HourDK'], '2024-09-30T06:00:00')
        self.assertEqual(hour0['NetselskabTarif'], 0.1652)

        hour1 = response.json['records'][24+6]
        self.assertEqual(hour1['HourDK'], '2024-10-01T06:00:00')
        self.assertEqual(hour1['NetselskabTarif'], 0.3303)

    def test_addressroute1(self):
        response = self.app.get('/adresse/Sofiendalsvej 80, 9200 Aalborg')

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.location, '/elpris?GLN_Number=5790000611003')

    def test_addressroute_detaljer(self):
        response = self.app.get('/adresse/Sofiendalsvej 80, 9200 Aalborg?detaljer=true')

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.location, '/elpris-detaljer?GLN_Number=5790000611003')

    @parameterized.expand([
        ("Åvej 4, 9850 Hirtshals", "5790000610877"),
        ("Kastanievej 9C, 9300 Sæby", "5790001095277"),
        ("Karen Blixens Vej 65, 7430 Ikast", "5790000682102"),
        ("Dusager 22, 8200 Aarhus N", "5790000704842"),
        ("Nyhavevej 12, 8450 Hammel", "5790001090166"),
        ("Solvej 9, 9293 Kongerslev", "5790002502699"),
        ("Kirkegade 10, 6880 Tarm", "5790000706419"),
        ("Nupark 51, 7500 Holstebro", "5790001090111"),
        ("Frejasvej 22, 8464 Galten", "5790000610099"),
        ("Bytoften 8, 6710 Esbjerg", "5790001095376"),
        ("Stavangervej 13, 4900 Nakskov", "5790001088460"),
        ("Doktorvejen 2, 9940 Byrum", "5790001103460"),
        ("Østervej 13, 8592 Anholt", "5790000704842"),
    ])
    def test_addressroute(self, addr, expectedGLN):
        response = self.app.get('/adresse/' + addr)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.location, '/elpris?GLN_Number=' + expectedGLN)

    def test_addressroute_withstartparam(self):
        response = self.app.get('/adresse/Sofiendalsvej 80, 9200 Aalborg?start=2024-01-01')

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.location, '/elpris?GLN_Number=5790000611003&start=2024-01-01')

    def test_gridcompanies(self):
        response = self.app.get('/gridcompanies')

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json[0]['name'])
        self.assertTrue(response.json[0]['gln_Number'])
        self.assertTrue(response.json[0]['priceArea'])
        self.assertTrue(response.json[0]['gridCompanyNumber'])


if __name__ == '__main__':
    unittest.main()
