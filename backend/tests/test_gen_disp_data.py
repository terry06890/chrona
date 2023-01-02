import unittest
import tempfile, os

from tests.common import createTestDbTable, readTestDbTable
from hist_data.gen_disp_data import genData
from hist_data.cal import gregorianToJdn, julianToJdn, MONTH_SCALE, DAY_SCALE

class TestGenData(unittest.TestCase):
	def test_gen(self):
		with tempfile.TemporaryDirectory() as tempDir:
			# Create temp history db
			dbFile = os.path.join(tempDir, 'data.db')
			createTestDbTable(
				dbFile,
				'CREATE TABLE events (id INT PRIMARY KEY, title TEXT UNIQUE, ' \
					'start INT, start_upper INT, end INT, end_upper INT, fmt INT, ctg TEXT)',
				'INSERT INTO events VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
				{
					(1, 'event one', 1900, None, None, None, 0, 'event'),
					(2, 'event two', 2452607, None, 2455369, None, 3, 'human'), # 15/11/2002
					(3, 'event three', 1900, None, 2000, None, 0, 'event'), # version of 1 without pop score
					(4, 'event four', 1901, None, 2000, 2010, 0, 'event'),
					(5, 'event five', 2415307, None, None, None, 2, 'event'), # 01/10/1900
					(6, 'event six', 2415030, None, None, None, 1, 'event'), # 10/01/1900
					(7, 'event seven', 1900, None, None, None, 0, 'event'), # popular version of 1
					(8, 'event eight', 1900, None, None, None, 0, 'event'), # less popular version of 1
					(9, 'event nine', 1900, None, None, None, 0, 'event'), # less popular version of 1
					(10, 'event ten', 2415307, None, None, None, 2, 'event'), # less popular version of 5
					(11, 'event eleven', 2415307, None, None, None, 2, 'event'), # slightly less popular version of 5
				}
			)
			createTestDbTable(
				dbFile,
				'CREATE TABLE pop (id INT PRIMARY KEY, pop INT)',
				'INSERT INTO pop VALUES (?, ?)',
				{
					(1, 11),
					(2, 21),
					(4, 5),
					(5, 50),
					(6, 10),
					(7, 100),
					(8, 1),
					(9, 2),
					(10, 40),
					(11, 45),
				}
			)
			# Run
			genData(dbFile, [10, 1, MONTH_SCALE, DAY_SCALE], 2)
			# Check
			self.assertEqual(
				readTestDbTable(dbFile, 'SELECT * FROM events'),
				{
					(1, 'event one', 1900, None, None, None, 0, 'event'),
					(2, 'event two', 2452607, None, 2455369, None, 3, 'human'),
					(4, 'event four', 1901, None, 2000, 2010, 0, 'event'),
					(5, 'event five', 2415307, None, None, None, 2, 'event'),
					(6, 'event six', 2415030, None, None, None, 1, 'event'),
					(7, 'event seven', 1900, None, None, None, 0, 'event'),
					(11, 'event eleven', 2415307, None, None, None, 2, 'event'), # 01/10/1900
				}
			)
			self.assertEqual(
				readTestDbTable(dbFile, 'SELECT * FROM pop'),
				{
					(1, 11),
					(2, 21),
					(4, 5),
					(5, 50),
					(6, 10),
					(7, 100),
					(11, 45),
				}
			)
			self.assertEqual(
				readTestDbTable(dbFile, 'SELECT scale, unit, count FROM dist'),
				{
					(10, 190, 6),
					(10, 200, 1),
					(1, 1900, 5),
					(1, 1901, 1),
					(1, 2002, 1),
					(MONTH_SCALE, gregorianToJdn(1900, 1, 1), 3),
					(MONTH_SCALE, gregorianToJdn(1901, 1, 1), 1),
					(MONTH_SCALE, julianToJdn(1900, 10, 1), 2),
					(MONTH_SCALE, julianToJdn(2002, 11, 1), 1),
					(DAY_SCALE, gregorianToJdn(1900, 1, 1), 2),
					(DAY_SCALE, gregorianToJdn(1900, 1, 10), 1),
					(DAY_SCALE, julianToJdn(1900, 10, 1), 2),
					(DAY_SCALE, gregorianToJdn(1901, 1, 1), 1),
					(DAY_SCALE, julianToJdn(2002, 11, 15), 1),
				}
			)
			self.assertEqual(
				readTestDbTable(dbFile, 'SELECT id, scale FROM event_disp'),
				{
					(5, 10),
					(7, 10),
					(2, 10),
					(5, 1),
					(7, 1),
					(4, 1),
					(2, 1),
					(1, MONTH_SCALE),
					(7, MONTH_SCALE),
					(4, MONTH_SCALE),
					(5, MONTH_SCALE),
					(11, MONTH_SCALE),
					(2, MONTH_SCALE),
					(1, DAY_SCALE),
					(7, DAY_SCALE),
					(6, DAY_SCALE),
					(4, DAY_SCALE),
					(5, DAY_SCALE),
					(11, DAY_SCALE),
					(2, DAY_SCALE),
				}
			)
