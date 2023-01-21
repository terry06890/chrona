import unittest
import tempfile
import os

from tests.common import createTestDbTable, readTestDbTable
from hist_data.gen_pop_data import genData

class TestGenData(unittest.TestCase):
	def test_gen(self):
		with tempfile.TemporaryDirectory() as tempDir:
			# Create temp pageviews db
			pageviewsDb = os.path.join(tempDir, 'pageview_data.db')
			createTestDbTable(
				pageviewsDb,
				'CREATE TABLE views (title TEXT PRIMARY KEY, id INT, views INT)',
				'INSERT INTO views VALUES (?, ?, ?)',
				{
					('one', 1, 10),
					('two', 2, 20),
					('three', 3, 30),
				}
			)

			# Create temp history db
			dbFile = os.path.join(tempDir, 'data.db')
			createTestDbTable(
				dbFile,
				'CREATE TABLE events (id INT PRIMARY KEY, title TEXT UNIQUE, ' \
					'start INT, start_upper INT, end INT, end_upper INT, fmt INT, ctg TEXT)',
				'INSERT INTO events VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
				{
					(11, 'one', 100, None, None, None, 0, 'event'),
					(33, 'three', 100, None, None, None, 0, 'event'),
				}
			)

			# Run
			genData(pageviewsDb, dbFile)

			# Check
			self.assertEqual(
				readTestDbTable(dbFile, 'SELECT id, pop from pop'),
				{
					(11, 10),
					(33, 30)
				}
			)
