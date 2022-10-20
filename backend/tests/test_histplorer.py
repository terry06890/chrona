import unittest
import tempfile, os

from tests.common import createTestDbTable
from histplorer import handleReq, HistDate, Event, ImgInfo, EventInfo, SuggResponse

def initTestDb(dbFile: str) -> None:
	createTestDbTable(
		dbFile,
		'CREATE TABLE events (id INT PRIMARY KEY, title TEXT UNIQUE, ' \
			'start INT, start_upper INT, end INT, end_upper INT, fmt INT, ctg TEXT)',
		'INSERT INTO events VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
		{
			(1, 'event one', 1900, None, None, None, 0, 'event'),
			(2, 'event two', 2452594, None, 2455369, None, 3, 'human'), # 2/11/2002 to 21/06/2010
			(3, 'event three', 2448175, 2451828, None, None, 2, 'discovery'), # 10/10/1990 to 10/10/2000
			(4, 'event four', 991206, None, 1721706, None, 1, 'event'), # 10/10/-2000 to 10/10/1
			(5, 'event five', 2000, None, 2001, None, 0, 'event'),
		}
	)
	createTestDbTable(
		dbFile,
		'CREATE TABLE pop (id INT PRIMARY KEY, pop INT)',
		'INSERT INTO pop VALUES (?, ?)',
		{
			(1, 11),
			(2, 21),
			(3, 0),
			(4, 1000),
			(5, 51),
		}
	)
	createTestDbTable(
		dbFile,
		'CREATE TABLE event_imgs (id INT PRIMARY KEY, img_id INT)',
		'INSERT INTO event_imgs VALUES (?, ?)',
		{
			(1, 10),
			(2, 20),
			(3, 30),
			(4, 20),
			(5, 50),
		}
	)
	createTestDbTable(
		dbFile,
		'CREATE TABLE images (id INT PRIMARY KEY, url TEXT, license TEXT, artist TEXT, credit TEXT)',
		'INSERT INTO images VALUES (?, ?, ?, ?, ?)',
		{
			(10, 'example.com/1', 'cc0', 'artist one', 'credits one'),
			(20, 'example.com/2', 'cc-by', 'artist two', 'credits two'),
			(30, 'example.com/3', 'cc-by-sa 3.0', 'artist three', 'credits three'),
			(50, 'example.com/5', 'cc-by', 'artist five', 'credits five'),
		}
	)
	createTestDbTable(
		dbFile,
		'CREATE TABLE descs (id INT PRIMARY KEY, wiki_id INT, desc TEXT)',
		'INSERT INTO descs VALUES (?, ?, ?)',
		{
			(1, 100, 'desc one'),
			(2, 200, 'desc two'),
			(3, 300, 'desc three'),
			(4, 400, 'desc four'),
			(5, 500, 'desc five'),
		}
	)

class TestHandleReq(unittest.TestCase):
	def setUp(self):
		self.maxDiff = None
		self.tempDir = tempfile.TemporaryDirectory()
		self.dbFile = os.path.join(self.tempDir.name, 'data.db')
		initTestDb(self.dbFile)
	def tearDown(self):
		self.tempDir.cleanup()
	def test_events_req(self):
		response = handleReq(self.dbFile, {'QUERY_STRING': 'type=events&range=-1999.2002-11-1&incl=3&limit=2'})
		self.assertEqual(response, [
			Event(5, 'event five', HistDate(True, 2000, 1, 1), None, HistDate(True, 2001, 1, 1), None,
				'event', 50, 51),
			Event(3, 'event three', HistDate(True, 1990, 10, 10), HistDate(True, 2000, 10, 10), None, None,
				'discovery', 30, 0),
		])
		response = handleReq(self.dbFile, {'QUERY_STRING': 'type=events&range=.1999-11-27&excl=1&ctg=event'})
		self.assertEqual(response, [
			Event(4, 'event four', HistDate(False, -2000, 10, 10), None, HistDate(False, 1, 10, 10), None,
				'event', 20, 1000),
		])
	def test_info_req(self):
		response = handleReq(self.dbFile, {'QUERY_STRING': 'type=info&event=3'})
		self.assertEqual(response,
			EventInfo('desc three', 300, ImgInfo('example.com/3', 'cc-by-sa 3.0', 'artist three', 'credits three')))
		response = handleReq(self.dbFile, {'QUERY_STRING': 'type=info&event=4'})
		self.assertEqual(response,
			EventInfo('desc four', 400, ImgInfo('example.com/2', 'cc-by', 'artist two', 'credits two')))
	def test_sugg_req(self):
		response = handleReq(self.dbFile, {'QUERY_STRING': 'type=sugg&input=event t'})
		self.assertEqual(response, SuggResponse(['event two', 'event three'], False))
		response = handleReq(self.dbFile, {'QUERY_STRING': 'type=sugg&input=o&ctg=event'})
		self.assertEqual(response, SuggResponse(['event four', 'event one'], False))
		response = handleReq(self.dbFile, {'QUERY_STRING': 'type=sugg&input=event&ctg=event&limit=1'})
		self.assertEqual(response, SuggResponse(['event four'], True))
