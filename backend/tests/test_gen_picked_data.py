import unittest
from unittest.mock import patch
import tempfile, os, shutil

from tests.common import createTestFile, createTestDbTable, readTestDbTable
from hist_data.gen_picked_data import genData

TEST_IMG = os.path.join(os.path.dirname(__file__), 'test_img.png')

class TestGenImgs(unittest.TestCase):
	@patch('hist_data.gen_imgs.convertImage', autospec=True)
	def test_gen(self, convertImageMock):
		with tempfile.TemporaryDirectory() as tempDir:
			convertImageMock.side_effect = lambda imgPath, outPath: shutil.copy(imgPath, outPath)
			# Create picked-event file
			pickedDir = os.path.join(tempDir, 'picked')
			os.mkdir(pickedDir)
			pickedEvtFile = os.path.join(pickedDir, 'events.json')
			createTestFile(pickedEvtFile, '''
				[{
					"title": "COVID-19 Pandemic",
					"start": 2458919,
					"start_upper": null,
					"end": null,
					"end_upper": null,
					"fmt": 2,
					"ctg": "event",
					"image": {
						"file": "covid.jpg",
						"url": "https://en.wikipedia.org/wiki/File:Covid-19_SP_-_UTI_V._Nova_Cachoeirinha.jpg",
						"license": "cc-by-sa 4.0",
						"artist": "Gustavo Basso",
						"credit": ""
					},
					"desc": "Global pandemic caused by the virus SARS-CoV-2",
					"pop": 100
				},{
					"id": 2,
					"title": "foo",
					"start": -100,
					"start_upper": null,
					"ctg": "discovery",
					"image": {
						"file": "foo.jpg",
						"url": "https://example.com/foo_img",
						"license": "cc-by",
						"artist": "Fibble Wesky",
						"credit": "Plosta Grimble and Hoska Ferlento"
					}
				},{
					"title": "event three"
				}]
			''')
			# Create picked images
			shutil.copy(TEST_IMG, os.path.join(pickedDir, 'covid.jpg'))
			shutil.copy(TEST_IMG, os.path.join(pickedDir, 'foo.jpg'))
			# Create temp history db
			dbFile = os.path.join(tempDir, 'data.db')
			createTestDbTable(
				dbFile,
				'CREATE TABLE events (id INT PRIMARY KEY, title TEXT UNIQUE, ' \
					'start INT, start_upper INT, end INT, end_upper INT, fmt INT, ctg TEXT)',
				'INSERT INTO events VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
				{
					(1, 'event one', 100, 1000, None, None, 0, 'event'),
					(2, 'event two', 200, 2000, None, None, 0, 'event'),
					(3, 'event three', 300, 3000, None, None, 0, 'event'),
				}
			)
			createTestDbTable(
				dbFile,
				'CREATE TABLE images (id INT PRIMARY KEY, url TEXT, license TEXT, artist TEXT, credit TEXT)',
				'INSERT INTO images VALUES (?, ?, ?, ?, ?)',
				{
					(10, 'http://example.com/img1', 'cc0', 'Spofta Klurry', ''),
				}
			)
			createTestDbTable(
				dbFile,
				'CREATE TABLE event_imgs (id INT PRIMARY KEY, img_id INT)',
				'INSERT INTO event_imgs VALUES (?, ?)',
				{
					(1, 10),
					(2, 10),
				}
			)
			createTestDbTable(
				dbFile,
				'CREATE TABLE descs (id INT PRIMARY KEY, wiki_id INT, desc TEXT)',
				'INSERT INTO descs VALUES (?, ?, ?)',
				{
					(1, 100, 'desc one'),
					(3, 200, 'desc three'),
				}
			)
			createTestDbTable(
				dbFile,
				'CREATE TABLE pop (id INT PRIMARY KEY, pop INT)',
				'INSERT INTO pop VALUES (?, ?)',
				{
					(1, 99),
					(2, 35),
					(3, 1),
				}
			)
			# Create existing event images
			imgOutDir = os.path.join(tempDir, 'imgs')
			os.mkdir(imgOutDir)
			shutil.copy(TEST_IMG, os.path.join(imgOutDir, '10.jpg'))
			# Run
			genData(pickedDir, pickedEvtFile, dbFile, imgOutDir)
			# Check
			self.assertEqual(set(os.listdir(imgOutDir)), {
				'10.jpg',
				'-1.jpg',
				'-2.jpg',
			})
			self.assertEqual(
				readTestDbTable(dbFile, 'SELECT id, title, start, start_upper, end, end_upper, fmt, ctg FROM events'),
				{
					(1, 'event one', 100, 1000, None, None, 0, 'event'),
					(2, 'foo', -100, None, None, None, 0, 'discovery'),
					(-1, 'COVID-19 Pandemic', 2458919, None, None, None, 2, 'event'),
				}
			)
			self.assertEqual(
				readTestDbTable(dbFile, 'SELECT id, url, license, artist, credit FROM images'),
				{
					(10, 'http://example.com/img1', 'cc0', 'Spofta Klurry', ''),
					(-1, 'https://en.wikipedia.org/wiki/File:Covid-19_SP_-_UTI_V._Nova_Cachoeirinha.jpg',
						'cc-by-sa 4.0', 'Gustavo Basso', ''),
					(-2, 'https://example.com/foo_img', 'cc-by', 'Fibble Wesky', 'Plosta Grimble and Hoska Ferlento'),
				}
			)
			self.assertEqual(
				readTestDbTable(dbFile, 'SELECT id, img_id FROM event_imgs'),
				{
					(1, 10),
					(2, -2),
					(-1, -1),
				}
			)
			self.assertEqual(
				readTestDbTable(dbFile, 'SELECT id, wiki_id, desc from descs'),
				{
					(1, 100, 'desc one'),
					(-1, -1, 'Global pandemic caused by the virus SARS-CoV-2'),
				}
			)
			self.assertEqual(
				readTestDbTable(dbFile, 'SELECT id, pop from pop'),
				{
					(1, 99),
					(2, 35),
					(-1, 100),
				}
			)
