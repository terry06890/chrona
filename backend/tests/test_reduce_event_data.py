import unittest
import tempfile, os

from tests.common import createTestDbTable, readTestDbTable
from hist_data.reduce_event_data import reduceData
from hist_data.cal import gregorianToJdn, julianToJdn, MONTH_SCALE, DAY_SCALE

class TestReduceData(unittest.TestCase):
	def test_reduce(self):
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
					(2, 'event two', 2452594, None, 2455369, None, 3, 'human'), # 2/11/2002
					(3, 'event three', 2448175, 2448200, None, None, 1, 'discovery'), # 10/10/1990
					(4, 'event four', 1900, None, None, None, 0, 'event'), # Copy of 1
					(5, 'event five', 2452595, None, 2455369, None, 3, 'human'), # Day after 2
				}
			)
			createTestDbTable(
				dbFile,
				'CREATE TABLE pop (id INT PRIMARY KEY, pop INT)',
				'INSERT INTO pop VALUES (?, ?)',
				{
					(1, 10),
					(2, 20),
					(3, 30),
					(4, 40),
					(5, 50),
				}
			)
			createTestDbTable(
				dbFile,
				'CREATE TABLE dist (scale INT, unit INT, count INT, PRIMARY KEY (scale, unit))',
				'INSERT INTO dist VALUES (?, ?, ?)',
				{
					(1, 1900, 2),
					(1, 1990, 1),
					(1, 2002, 2),
					(MONTH_SCALE, gregorianToJdn(1900, 1, 1), 2),
					(MONTH_SCALE, gregorianToJdn(1990, 10, 1), 1),
					(MONTH_SCALE, julianToJdn(2002, 11, 1), 2),
					(DAY_SCALE, gregorianToJdn(1900, 1, 1), 2),
					(DAY_SCALE, gregorianToJdn(1990, 10, 10), 1),
					(DAY_SCALE, 2452594, 1),
					(DAY_SCALE, 2452595, 1),
				}
			)
			createTestDbTable(
				dbFile,
				'CREATE TABLE event_disp (id INT, scale INT, PRIMARY KEY (id, scale))',
				'INSERT INTO event_disp VALUES (?, ?)',
				{
					(1, 1),
					(1, MONTH_SCALE),
					(1, DAY_SCALE),
					(2, 1),
					(2, MONTH_SCALE),
					(2, DAY_SCALE),
					(3, 1),
					(3, MONTH_SCALE),
					(3, DAY_SCALE),
					(4, 1),
					(4, MONTH_SCALE),
					(4, DAY_SCALE),
					(5, 1),
					(5, MONTH_SCALE),
					(5, DAY_SCALE),
				}
			)
			createTestDbTable(
				dbFile,
				'CREATE TABLE event_imgs (id INT PRIMARY KEY, img_id INT)',
				'INSERT INTO event_imgs VALUES (?, ?)',
				{
					(1, 11),
					(2, 21),
				}
			)
			createTestDbTable(
				dbFile,
				'CREATE TABLE images (id INT PRIMARY KEY, url TEXT, license TEXT, artist TEXT, credit TEXT)',
				'INSERT INTO images VALUES (?, ?, ?, ?, ?)',
				{
					(11, 'example.com/1', 'cc0', 'artist one', 'credits one'),
					(21, 'example.com/1', 'cc0', 'artist two', 'credits two'),
				}
			)
			createTestDbTable(
				dbFile,
				'CREATE TABLE descs (id INT PRIMARY KEY, wiki_id INT, desc TEXT)',
				'INSERT INTO descs VALUES (?, ?, ?)',
				{
					(1, 100, 'desc one'),
				}
			)
			# Run
			reduceData(dbFile, [1, MONTH_SCALE, DAY_SCALE])
			# Check
			self.assertEqual(
				readTestDbTable(dbFile, 'SELECT * FROM events'),
				{
					(1, 'event one', 1900, None, None, None, 0, 'event'),
					(2, 'event two', 2452594, None, 2455369, None, 3, 'human'),
				}
			)
			self.assertEqual(
				readTestDbTable(dbFile, 'SELECT * from pop'),
				{
					(1, 10),
					(2, 20),
				}
			)
			self.assertEqual(
				readTestDbTable(dbFile, 'SELECT * from dist'),
				{
					(1, 1900, 1),
					(1, 2002, 1),
					(MONTH_SCALE, gregorianToJdn(1900, 1, 1), 1),
					(MONTH_SCALE, julianToJdn(2002, 11, 1), 1),
					(DAY_SCALE, gregorianToJdn(1900, 1, 1), 1),
					(DAY_SCALE, 2452594, 1),
				}
			)
			self.assertEqual(
				readTestDbTable(dbFile, 'SELECT * from event_disp'),
				{
					(1, 1),
					(1, MONTH_SCALE),
					(1, DAY_SCALE),
					(2, 1),
					(2, MONTH_SCALE),
					(2, DAY_SCALE),
				}
			)
