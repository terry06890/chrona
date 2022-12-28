import unittest
import tempfile, os

from tests.common import createTestDbTable, readTestDbTable
from hist_data.reduce_event_data import reduceData

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
					(2, 'event two', 2452594, None, 2455369, None, 3, 'human'), # 2/11/2002 to 21/06/2010
					(3, 'event three', 2448175, 2451828, None, None, 2, 'discovery'), # 10/10/1990 to 10/10/2000
				}
			)
			createTestDbTable(
				dbFile,
				'CREATE TABLE pop (id INT PRIMARY KEY, pop INT)',
				'INSERT INTO pop VALUES (?, ?)',
				{
					(1, 11),
					(2, 21),
				}
			)
			createTestDbTable(
				dbFile,
				'CREATE TABLE event_imgs (id INT PRIMARY KEY, img_id INT)',
				'INSERT INTO event_imgs VALUES (?, ?)',
				{
					(1, 10),
				}
			)
			createTestDbTable(
				dbFile,
				'CREATE TABLE images (id INT PRIMARY KEY, url TEXT, license TEXT, artist TEXT, credit TEXT)',
				'INSERT INTO images VALUES (?, ?, ?, ?, ?)',
				{
					(10, 'example.com/1', 'cc0', 'artist one', 'credits one'),
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
			reduceData(dbFile)
			# Check
			self.assertEqual(
				readTestDbTable(dbFile, 'SELECT id, title, start, start_upper, end, end_upper, fmt, ctg FROM events'),
				{
					(1, 'event one', 1900, None, None, None, 0, 'event'),
				}
			)
			self.assertEqual(
				readTestDbTable(dbFile, 'SELECT id, pop from pop'),
				{
					(1, 11),
				}
			)
