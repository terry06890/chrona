import unittest
import os
import tempfile

from tests.common import readTestDbTable
from hist_data.enwiki.gen_desc_data import genData

TEST_DUMP_FILE = os.path.join(os.path.dirname(__file__), 'sample_enwiki_pages_articles.xml.bz2')

class TestGenData(unittest.TestCase):
	def test_gen(self):
		with tempfile.TemporaryDirectory() as tempDir:
			# Run
			dbFile = os.path.join(tempDir, 'descData.db')
			genData(TEST_DUMP_FILE, dbFile)

			# Check
			self.assertEqual(
				readTestDbTable(dbFile, 'SELECT id, title FROM pages'),
				{
					(10, 'AccessibleComputing'),
					(13, 'AfghanistanHistory'),
					(25, 'Autism'),
				}
			)
			self.assertEqual(
				readTestDbTable(dbFile, 'SELECT id, target FROM redirects'),
				{
					(10, 'Computer accessibility'),
					(13, 'History of Afghanistan'),
				}
			)
			descsRows = readTestDbTable(dbFile, 'SELECT id, desc FROM descs')
			expectedDescPrefixes = {
				25: 'Kanner autism, or classic autism, is a neurodevelopmental disorder',
			}
			self.assertEqual({row[0] for row in descsRows}, set(expectedDescPrefixes.keys()))
			for id, desc in descsRows:
				self.assertTrue(id in expectedDescPrefixes and desc.startswith(expectedDescPrefixes[id]))
