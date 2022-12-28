import unittest
import tempfile, os

from tests.common import createTestDbTable, readTestDbTable
from hist_data.gen_score_data import genData, MONTH_SCALE, DAY_SCALE
from hist_data.cal import gregorianToJdn

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
					(2, 'event two', 2452594, None, 2455369, None, 3, 'human'), # 15/11/2002 to 21/06/2010
					(3, 'event three', 1900, None, 2000, None, 0, 'event'),
					(4, 'event four', 1901, None, 2000, 2010, 0, 'event'),
					(5, 'event five', 2415294, None, None, None, 1, 'event'), # 01/10/1900
					(6, 'event six', 2415030, None, None, None, 1, 'event'), # 10/01/1900
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
				}
			)
			# Run
			genData(dbFile, [10, 1, MONTH_SCALE, DAY_SCALE], 2)
			# Check
			self.assertEqual(
				readTestDbTable(dbFile, 'SELECT scale, unit, count FROM dist'),
				{
					(10, 190, 4),
					(10, 200, 1),
					(1, 1900, 3),
					(1, 1901, 1),
					(1, 2002, 1),
					(MONTH_SCALE, gregorianToJdn(1900, 1, 1), 2),
					(MONTH_SCALE, gregorianToJdn(1901, 1, 1), 1),
					(MONTH_SCALE, gregorianToJdn(1900, 10, 1), 1),
					(MONTH_SCALE, gregorianToJdn(2002, 11, 1), 1),
					(DAY_SCALE, gregorianToJdn(1900, 1, 1), 1),
					(DAY_SCALE, gregorianToJdn(1900, 1, 10), 1),
					(DAY_SCALE, gregorianToJdn(1900, 10, 1), 1),
					(DAY_SCALE, gregorianToJdn(1901, 1, 1), 1),
					(DAY_SCALE, gregorianToJdn(2002, 11, 15), 1),
				}
			)
			self.assertEqual(
				readTestDbTable(dbFile, 'SELECT id, scale, score FROM scores'),
				{
					(5, 10, 50),
					(1, 10, 11),
					(2, 10, 21),
					(5, 1, 50),
					(1, 1, 11),
					(4, 1, 5),
					(2, 1, 21),
					(1, MONTH_SCALE, 11),
					(6, MONTH_SCALE, 10),
					(4, MONTH_SCALE, 5),
					(5, MONTH_SCALE, 50),
					(2, MONTH_SCALE, 21),
					(1, DAY_SCALE, 11),
					(4, DAY_SCALE, 5),
					(5, DAY_SCALE, 50),
					(6, DAY_SCALE, 10),
					(2, DAY_SCALE, 21),
				}
			)
