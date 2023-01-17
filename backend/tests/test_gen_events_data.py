import unittest
import tempfile, os, json, bz2, pickle, indexed_bzip2
# Local imports
from tests.common import readTestDbTable
from hist_data.gen_events_data import genData

def runGenData(wikiItemArray: str, preGenOffsets: bool, nProcs: int):
	""" Sets up wikidata file to be read by genData(), runs it, and returns the output database's contents.
		If 'preGenOffsets' is True, generates a bz2 offsets file before running genData(). """
	with tempfile.TemporaryDirectory() as tempDir:
		# Create temp wikidata file
		wikidataFile = os.path.join(tempDir, 'dump.json.bz2')
		with bz2.open(wikidataFile, mode='wb') as file:
			file.write(b'[\n')
			for i in range(len(wikiItemArray)):
				file.write(json.dumps(wikiItemArray[i], separators=(',',':')).encode())
				if i < len(wikiItemArray) - 1:
					file.write(b',')
				file.write(b'\n')
			file.write(b']\n')
		# Create temp offsets file if requested
		offsetsFile = os.path.join(tempDir, 'offsets.dat')
		if preGenOffsets:
			with indexed_bzip2.open(wikidataFile) as file:
				with open(offsetsFile, 'wb') as file2:
					pickle.dump(file.block_offsets(), file2)
		# Run genData()
		dbFile = os.path.join(tempDir, 'events.db')
		genData(wikidataFile, offsetsFile, dbFile, nProcs)
		# Read db
		return readTestDbTable(dbFile, 'SELECT * FROM events')

class TestGenData(unittest.TestCase):
	def setUp(self):
		self.maxDiff = None # Remove output-diff size limit
		self.testWikiItems = [
			{
				'id': 'Q1',
				'claims': {
					'P31': [{'mainsnak': {'datavalue': {'value': {'id': 'Q1656682'}}}}], # 'instance of' 'event'
					'P585': [{'mainsnak': {'datavalue': {'type': 'time', 'value': { # 'point in time'
						'time':'+1950-12-00T00:00:00Z',
						'timezone':0,
						'before':0,
						'after':0,
						'precision':10, # month precision
						'calendarmodel':'http://www.wikidata.org/entity/Q1985727' # 'proleptic gregorian calendar'
					}}}}],
					'P141': [{'mainsnak': {'datavalue': {'value': {'id': 'Q211005'}}}}], # Other random property
				},
				'sitelinks': {'enwiki': {'title': 'event one'}},
			},
			{
				'id': 'Q2',
				'claims': {
					'P31': [{'mainsnak': {'datavalue': {'value': {'id': 'Q5'}}}}], # 'instance of' 'human'
					'P569': [{'mainsnak': {'datavalue': {'type': 'time', 'value': { # 'date of birth'
						'time':'+2002-11-02T00:00:00Z',
						'precision':11, # day precision
						'calendarmodel':'http://www.wikidata.org/entity/Q1985786' # 'proleptic julian calendar'
					}}}}],
					'P570': [{'mainsnak': {'datavalue': {'type': 'time', 'value': { # 'date of death'
						'time':'+2010-06-21T00:00:01Z',
						'timezone':1,
						'precision':11,
						'calendarmodel':'http://www.wikidata.org/entity/Q1985727' # 'proleptic gregorian calendar'
					}}}}],
				},
				'sitelinks': {'enwiki': {'title': 'Human One'}},
			},
			{
				'id': 'Q3',
				'claims': {
					'P31': [{'mainsnak': {'datavalue': {'value': {'id': 'Q7275'}}}}], # 'instance of' 'state'
					'P580': [{'mainsnak': {'datavalue': {'type': 'time', 'value': { # 'start time'
						'time':'-1001-00-00T00:00:00Z',
						'precision':9, # year precision
						'calendarmodel':'http://www.wikidata.org/entity/Q1985727'
					}}}}],
					'P582': [{'mainsnak': {'datavalue': {'type': 'time', 'value': { # 'end time'
						'time':'-99-00-00T00:00:01Z',
						'precision':9,
						'calendarmodel':'http://www.wikidata.org/entity/Q1985786'
					}}}}],
				},
				'sitelinks': {'enwiki': {'title': 'country one'}},
			},
			{
				'id': 'Q4',
				'claims': {
					'P31': [{'mainsnak': {'datavalue': {'value': {'id': 'Q6256'}}}}], # 'instance of' 'country'
					'P7584': [{'mainsnak': {'datavalue': {'type': 'quantity', 'value': {
						# 'age estimated by a dating method'
						"amount":"+10.9",
						"unit":"http://www.wikidata.org/entity/Q3013059", # kiloannum
						"lowerBound":"+9",
						"upperBound":"+11",
					}}}}],
				},
				'sitelinks': {'enwiki': {'title': 'country two'}},
			},
			{
				'id': 'Q5',
				'claims': {
					'P31': [{'mainsnak': {'datavalue': {'value': {'id': 'Q11019'}}}}], # 'instance of' 'machine'
					'P575': [{'mainsnak': {'datavalue': {'type': 'time', 'value': { # 'time of discovery or invention'
						'time':'+0101-00-00T00:00:01Z',
						'precision':6, # millenium precision
						'calendarmodel':'http://www.wikidata.org/entity/Q1985786'
					}}}}],
				},
				'sitelinks': {'enwiki': {'title': 'discovery one'}},
			},
			{
				'id': 'Q6',
				'claims': {
					'P31': [{'mainsnak': {'datavalue': {'value': {'id': 'Q7725634'}}}}], # 'instance of' 'literary work'
					'P170': [{'mainsnak': {'datavalue': {'value': {'id': 'Q180'}}}}], # 'creator'
					'P1319': [{'mainsnak': {'datavalue': {'type': 'time', 'value': { # 'earliest date'
						'time':'-0020-08-01T00:00:00Z',
						'precision':11, # day precision
						'calendarmodel':'http://www.wikidata.org/entity/Q1985786' # 'proleptic julian calendar'
					}}}}],
					'P1326': [{'mainsnak': {'datavalue': {'type': 'time', 'value': { # 'latest date'
						'time':'-0020-09-01T00:00:00Z',
						'precision':11,
						'calendarmodel':'http://www.wikidata.org/entity/Q1985786' # 'proleptic julian calendar'
					}}}}],
				},
				'sitelinks': {'enwiki': {'title': 'media one'}},
			},
			{
				'id': 'Q7',
				'claims': {
					'P31': [{'mainsnak': {'datavalue': {'value': {'id': 'Q11424'}}}}], # 'instance of' 'film'
					'P136': [{'mainsnak': {'datavalue': {'value': {'id': 'Q157394'}}}}], # 'genre'
					'P577': [{'mainsnak': {'datavalue': {'type': 'time', 'value': { # 'publication date'
						'time':'-2103-00-00T00:00:00Z',
						'precision':7, # century precision
						'calendarmodel':'http://www.wikidata.org/entity/Q1985727'
					}}}}],
				},
				'sitelinks': {'enwiki': {'title': 'media two'}},
			},
			{
				'id': 'Q8',
				'claims': {
					'P31': [{'mainsnak': {'datavalue': {'value': {'id': 'Q16521'}}}}], # 'instance of' 'taxon'
					'P571': [{'mainsnak': {'datavalue': {'type': 'time', 'value': { # 'inception'
						'time':'-400000000-00-00T00:00:01Z',
						'precision':1, # hundred million years precision
						'calendarmodel':'http://www.wikidata.org/entity/Q1985727' # 'proleptic gregorian calendar'
					}}}}],
				},
				'sitelinks': {'enwiki': {'title': 'organism one'}},
			},
		]
		self.expectedRows = {
			(1, 'event one', 2433617, 2433647, None, None, 1, 'event'),
			(2, 'Human One', 2452594, None, 2455369, None, 3, 'person'),
			(3, 'country one', -1001, None, -99, None, 0, 'place'),
			(4, 'country two', -11000, -9000, None, None, 0, 'place'),
			(5, 'discovery one', 1, 1000, None, None, 0, 'discovery'),
			(7, 'media two', -2199, -2100, None, None, 0, 'work'),
			(8, 'organism one', -400000000, -300000001, None, None, 0, 'organism'),
		}
	def test_wikiItems(self):
		rows = runGenData(self.testWikiItems, False, 1)
		self.assertEqual(rows, self.expectedRows)
	def test_empty_dump(self):
		rows = runGenData([{}], False, 1)
		self.assertEqual(rows, set())
	def test_multiprocessing(self):
		rows = runGenData(self.testWikiItems, False, 4)
		self.assertEqual(rows, self.expectedRows)
	def test_existing_offsets(self):
		rows = runGenData(self.testWikiItems, True, 3)
		self.assertEqual(rows, self.expectedRows)
