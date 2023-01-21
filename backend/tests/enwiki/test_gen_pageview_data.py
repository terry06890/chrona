import unittest
import tempfile
import os

from tests.common import createTestBz2, createTestDbTable, readTestDbTable
from hist_data.enwiki.gen_pageview_data import genData

class TestGenData(unittest.TestCase):
	def test_gen(self):
		with tempfile.TemporaryDirectory() as tempDir:
			# Create temp pageview files
			pageviewFiles = [os.path.join(tempDir, 'pageviews1.bz2'), os.path.join(tempDir, 'pageviews2.bz2')]
			createTestBz2(pageviewFiles[0], (
				'aa.wikibooks One null desktop 1 W1\n'
				'en.wikipedia Two null mobile-web 10 A9B1\n'
				'en.wikipedia Three null desktop 4 D3\n'
			))
			createTestBz2(pageviewFiles[1], (
				'fr.wikipedia Four null desktop 12 T6U6\n'
				'en.wikipedia Three null desktop 10 E4G5Z61\n'
			))

			# Create temp dump-index db
			dumpIndexDb = os.path.join(tempDir, 'dump_index.db')
			createTestDbTable(
				dumpIndexDb,
				'CREATE TABLE offsets (title TEXT PRIMARY KEY, id INT UNIQUE, offset INT, next_offset INT)',
				'INSERT INTO offsets VALUES (?, ?, ?, ?)',
				{
					('One', 1, 0, -1),
					('Two', 2, 0, -1),
					('Three', 3, 0, -1),
					('Four', 4, 0, -1),
				}
			)

			# Run
			dbFile = os.path.join(tempDir, 'data.db')
			genData(pageviewFiles, dumpIndexDb, dbFile)

			# Check
			self.assertEqual(
				readTestDbTable(dbFile, 'SELECT title, id, views from views'),
				{
					('Two', 2, 5),
					('Three', 3, 7),
				}
			)
