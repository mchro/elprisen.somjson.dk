# test_app.py
import unittest
import datetime
from flask import Flask, jsonify
import app

class TestApp(unittest.TestCase):
    def setUp(self):
        # Set up a test client
        self.client = app.app.test_client()

    def test_spotprices(self):
        startDate = app.date_from_reqparam("2024-02-23")
        spotprices = app.get_spotprices(startDate, "DK1")

        hour0 = spotprices['records'][0]
        self.assertEqual(hour0['HourDK'], '2024-02-23T00:00:00')
        self.assertEqual(hour0['PriceArea'], 'DK1')
        self.assertEqual(hour0['SpotPriceDKK'], 68.800003)

    def test_get_tariffs(self):
        startDate = app.date_from_reqparam("2024-02-23")
        gln_Number = '5790000611003'
        chargeTypeCode = app.default_chargeType_perGLN[gln_Number]

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

if __name__ == '__main__':
    unittest.main()
