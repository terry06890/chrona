import unittest
import tempfile, os

from tests.common import createTestDbTable, readTestDbTable
from hist_data.enwiki.gen_img_data import getInputPageIdsFromDb, genData

TEST_DUMP_FILE = os.path.join(os.path.dirname(__file__), 'sample_enwiki_pages_articles.xml.bz2')

class TestGetInputPageIdsFromDb(unittest.TestCase):
	def test_get(self):
		with tempfile.TemporaryDirectory() as tempDir:
			# Create temp history db
			dbFile = os.path.join(tempDir, 'data.db')
			createTestDbTable(
				dbFile,
				'CREATE TABLE events (id INT PRIMARY KEY, title TEXT UNIQUE, ' \
					'start INT, start_upper INT, end INT, end_upper INT, fmt INT, ctg TEXT)',
				'INSERT INTO events VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
				{
					(1, 'Belgium', 2389729, None, None, None, 2, 'country'),
					(2, 'George Washington', 2353711, None, 2378478, None, 2, 'human'),
					(3, 'Douglas Adams', 2434082, None, 2452040, None, 2, 'human'),
					(4, 'World War II', 2429507, None, 2431700, None, 2, 'event'),
					(5, 'Marie Curie', 2403277, None, 2427622, None, 2, 'human'),
				}
			)
			# Create temp dump-index db
			indexDb = os.path.join(tempDir, 'dump_index.db')
			createTestDbTable(
				indexDb,
				'CREATE TABLE offsets (title TEXT PRIMARY KEY, id INT UNIQUE, offset INT, next_offset INT)',
				'INSERT INTO offsets VALUES (?, ?, ?, ?)',
				{
					('Belgium',10,0,-1),
					('George Washington',20,0,-1),
					('Douglas Adams',30,0,-1),
					('Marie Curie',50,0,-1),
					('Autism',25,0,-1),
				}
			)
			# Run
			pageIds = getInputPageIdsFromDb(dbFile, indexDb)
			# Check
			self.assertEqual(pageIds, {10, 20, 30, 50})

class TestGenData(unittest.TestCase):
	def test_gen(self):
		with tempfile.TemporaryDirectory() as tempDir:
			# Create temp dump-index db
			indexDb = os.path.join(tempDir, 'dump_index.db')
			createTestDbTable(
				indexDb,
				'CREATE TABLE offsets (title TEXT PRIMARY KEY, id INT UNIQUE, offset INT, next_offset INT)',
				'INSERT INTO offsets VALUES (?, ?, ?, ?)',
				{
					('AccessibleComputing',10,0,-1),
					('AfghanistanHistory',13,0,-1),
					('Autism',25,0,-1),
				}
			)
			# Run
			imgDb = os.path.join(tempDir, 'imgData.db')
			genData({10, 25}, TEST_DUMP_FILE, indexDb, imgDb)
			# Check
			self.assertEqual(
				readTestDbTable(imgDb, 'SELECT page_id, title, img_name from page_imgs'),
				{
					(10, None, None),
					(25, 'Autism', 'Autism-stacking-cans 2nd edit.jpg'),
				}
			)
			# Run with updated page-ids set
			genData({13, 10}, TEST_DUMP_FILE, indexDb, imgDb)
			# Check
			self.assertEqual(
				readTestDbTable(imgDb, 'SELECT page_id, title, img_name from page_imgs'),
				{
					(10, None, None),
					(13, None, None),
					(25, 'Autism', 'Autism-stacking-cans 2nd edit.jpg'),
				}
			)
