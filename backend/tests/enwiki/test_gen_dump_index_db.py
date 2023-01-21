import unittest
import tempfile
import os

from tests.common import createTestBz2, readTestDbTable
from hist_data.enwiki.gen_dump_index_db import genData

def runGenData(indexFileContents: str):
	""" Sets up index file to be read by genData(), runs it, reads the output database, and returns offset info. """
	with tempfile.TemporaryDirectory() as tempDir:
		# Create temp index file
		indexFile = os.path.join(tempDir, 'index.txt.bz2')
		createTestBz2(indexFile, indexFileContents)

		# Run
		dbFile = os.path.join(tempDir, 'data.db')
		genData(indexFile, dbFile)

		# Read db
		return readTestDbTable(dbFile, 'SELECT title, id, offset, next_offset FROM offsets')

class TestGenData(unittest.TestCase):
	def setUp(self):
		self.maxDiff = None # Remove output-diff size limit

	def test_index_file(self):
		indexFileContents = (
			'100:10:apple\n'
			'100:11:ant\n'
			'300:99:banana ice-cream\n'
			'1000:2030:Custard!\n'
		)
		offsetsMap = runGenData(indexFileContents)
		self.assertEqual(offsetsMap, {
			('apple', 10, 100, 300),
			('ant', 11, 100, 300),
			('banana ice-cream', 99, 300, 1000),
			('Custard!', 2030, 1000, -1),
		})

	def test_emp_index(self):
		offsetsMap = runGenData('')
		self.assertEqual(offsetsMap, set())
		pass
