import unittest
import tempfile, os

from tests.common import createTestDbTable, readTestDbTable
from hist_data.gen_desc_data import genData

class TestGenData(unittest.TestCase):
	def test_gen(self):
		with tempfile.TemporaryDirectory() as tempDir:
			# Create temp enwiki db
			enwikiDb = os.path.join(tempDir, 'enwiki_descs.db')
			createTestDbTable(
				enwikiDb,
				'CREATE TABLE pages (id INT PRIMARY KEY, title TEXT UNIQUE)',
				'INSERT INTO pages VALUES (?, ?)',
				{
					(1, 'I'),
					(3, 'III'),
					(4, 'IV'),
					(5, 'V'),
				}
			)
			createTestDbTable(
				enwikiDb,
				'CREATE TABLE redirects (id INT PRIMARY KEY, target TEXT)',
				'INSERT INTO redirects VALUES (?, ?)',
				{
					(5, 'IV'),
				}
			)
			createTestDbTable(
				enwikiDb,
				'CREATE TABLE descs (id INT PRIMARY KEY, desc TEXT)',
				'INSERT INTO descs VALUES (?, ?)',
				{
					(1, 'One'),
					(3, 'Three'),
					(4, 'Four'),
					(5, 'Five'),
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
					(10, 'I', 100, None, None, None, 0, 'event'),
					(20, 'II', 200, None, None, None, 0, 'discovery'),
					(30, 'III', 300, None, 350, None, 0, 'event'),
					(50, 'V', 5, 10, None, None, 1, 'human'),
				}
			)
			# Run
			genData(enwikiDb, dbFile)
			# Check
			self.assertEqual(
				readTestDbTable(dbFile, 'SELECT id, wiki_id, desc from descs'),
				{
					(10, 1, 'One'),
					(30, 3, 'Three'),
					(50, 5, 'Four'),
				}
			)
