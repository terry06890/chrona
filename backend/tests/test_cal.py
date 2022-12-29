import unittest

from hist_data.cal import \
	gregorianToJdn, julianToJdn, jdnToGregorian, jdnToJulian, \
	julianToGregorian, gregorianToJulian, \
	MONTH_SCALE, DAY_SCALE, HistDate, dbDateToHistDate, dateToUnit

class TestCal(unittest.TestCase):
	def test_gregorian_to_jdn(self):
		self.assertEqual(gregorianToJdn(2010, 11, 3), 2455504)
		self.assertEqual(gregorianToJdn(-4714, 11, 24), 0)
		self.assertEqual(gregorianToJdn(-1, 1, 1), 1721060)
	def test_julian_to_jdn(self):
		self.assertEqual(julianToJdn(2010, 11, 3), 2455517)
		self.assertEqual(julianToJdn(-4713, 1, 1), 0)
		self.assertEqual(julianToJdn(-1, 1, 1), 1721058)
	def test_jdn_to_gregorian(self):
		self.assertEqual(jdnToGregorian(2455504), (2010, 11, 3))
		self.assertEqual(jdnToGregorian(0), (-4714, 11, 24))
		self.assertEqual(jdnToGregorian(1721060), (-1, 1, 1))
	def test_jdn_to_julian(self):
		self.assertEqual(jdnToJulian(2455517), (2010, 11, 3))
		self.assertEqual(jdnToJulian(0), (-4713, 1, 1))
		self.assertEqual(jdnToJulian(1721058), (-1, 1, 1))
	def test_gregorian_to_julian(self):
		self.assertEqual(gregorianToJulian(2022, 9, 30), (2022, 9, 17))
		self.assertEqual(gregorianToJulian(1616, 5, 3), (1616, 4, 23))
	def test_julian_to_gregorian(self):
		self.assertEqual(julianToGregorian(2022, 9, 17), (2022, 9, 30))
		self.assertEqual(julianToGregorian(1616, 4, 23), (1616, 5, 3))
	def test_db_to_hist_date(self):
		self.assertEqual(dbDateToHistDate(2001, 0), HistDate(True, 2001, 1, 1))
		self.assertEqual(dbDateToHistDate(1721455, 1), HistDate(False, 1, 2, 1))
		self.assertEqual(dbDateToHistDate(1356438, 2), HistDate(True, -1000, 9, 13))
		self.assertEqual(dbDateToHistDate(2268942, 3, False), HistDate(False, 1500, 1, 10))
		self.assertEqual(dbDateToHistDate(2268933, 3, True), HistDate(True, 1500, 1, 10))
	def test_date_to_unit(self):
		self.assertEqual(dateToUnit(HistDate(None, 1914, 1, 1), 10), 191)
		self.assertEqual(dateToUnit(HistDate(True, 1500, 10, 5), MONTH_SCALE), 2269197)
		self.assertEqual(dateToUnit(HistDate(False, 1500, 1, 10), DAY_SCALE), 2268942)
