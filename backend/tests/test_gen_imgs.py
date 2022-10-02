import unittest
from unittest.mock import patch
import tempfile, os, shutil

from tests.common import createTestDbTable, readTestDbTable
from hist_data.gen_imgs import genImgs

TEST_IMG = os.path.join(os.path.dirname(__file__), 'test_img.png')

class TestGenImgs(unittest.TestCase):
	@patch('hist_data.gen_imgs.convertImage', autospec=True)
	def test_gen(self, convertImageMock):
		with tempfile.TemporaryDirectory() as tempDir:
			convertImageMock.side_effect = lambda imgPath, outPath: shutil.copy(imgPath, outPath)
			# Create temp images
			imgDir = os.path.join(tempDir, 'enwiki_imgs')
			os.mkdir(imgDir)
			shutil.copy(TEST_IMG, os.path.join(imgDir, '100.jpg'))
			shutil.copy(TEST_IMG, os.path.join(imgDir, '200.jpeg'))
			shutil.copy(TEST_IMG, os.path.join(imgDir, '400.png'))
			# Create temp image db
			imgDb = os.path.join(tempDir, 'img_data.db')
			createTestDbTable(
				imgDb,
				'CREATE TABLE page_imgs (page_id INT PRIMARY KEY, title TEXT UNIQUE, img_name TEXT)',
				'INSERT INTO page_imgs VALUES (?, ?, ?)',
				{
					(1, 'first',  'one.jpg'),
					(2, 'second', 'two.jpeg'),
					(3, 'third',  'two.jpeg'),
				}
			)
			createTestDbTable(
				imgDb,
				'CREATE TABLE imgs (id INT PRIMARY KEY, name TEXT UNIQUE, ' \
					'license TEXT, artist TEXT, credit TEXT, restrictions TEXT, url TEXT)',
				'INSERT INTO imgs VALUES (?, ?, ?, ?, ?, ?, ?)',
				{
					(100, 'one.jpg', 'CC BY-SA 3.0', 'author1', 'credits1', '', 'https://upload.wikimedia.org/one.jpg'),
					(200, 'two.jpeg', 'cc-by', 'author2', 'credits2', '', 'https://upload.wikimedia.org/two.jpeg'),
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
					(10, 'first', 100, 1000, None, None, 0, 'event'),
					(20, 'second', 10, 20, None, None, 0, 'event'),
					(30, 'third', 1, 20, 30, 40, 2, 'event'),
				}
			)
			# Run
			outDir = os.path.join(tempDir, 'imgs')
			genImgs(imgDir, imgDb, outDir, dbFile)
			# Check
			self.assertEqual(set(os.listdir(outDir)), {
				'100.jpg',
				'200.jpg',
			})
			self.assertEqual(
				readTestDbTable(dbFile, 'SELECT id, img_id FROM event_imgs'),
				{
					(10, 100),
					(20, 200),
					(30, 200),
				}
			)
			self.assertEqual(
				readTestDbTable(dbFile, 'SELECT id, url, license, artist, credit FROM images'),
				{
					(100, 'https://en.wikipedia.org/wiki/File:one.jpg', 'CC BY-SA 3.0', 'author1', 'credits1'),
					(200, 'https://en.wikipedia.org/wiki/File:two.jpeg', 'cc-by', 'author2', 'credits2'),
				}
			)
