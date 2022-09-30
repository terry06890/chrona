#!/usr/bin/python3

"""
Reads a wikidata JSON dump, looking for entities usable as historical events.
Writes results into a database.

The JSON dump contains an array of objects, each of which describes a
Wikidata item item1, and takes up it's own line.
- Getting item1's Wikidata ID: item1['id'] (eg: "Q144")
- Checking for a property: item1['claims'][prop1] == array1
- Getting a property statement value: item1['claims'][prop1][idx1]['mainsnak']['datavalue']
	'idx1' indexes an array of statements
"""

# On Linux, running on the full dataset seems to make the processes hang when done. This was resolved by:
# - Using set_start_method('spawn'). Apparently 'fork' can cause unexpected copying of lock/semaphore/etc state.
#   Related: https://bugs.python.org/issue6721
# - Using pool.map() instead of pool.imap_unordered(), which seems to hang in some cases (was using python 3.8).
#   Possibly related: https://github.com/python/cpython/issues/72882

import os, io, re, argparse
import bz2, json, sqlite3
import multiprocessing, indexed_bzip2, pickle, tempfile

WIKIDATA_FILE = 'latest-all.json.bz2'
OFFSETS_FILE = 'offsets.dat'
DB_FILE = 'events.db'
N_PROCS = 6

# For handling Wikidata entity IDs
INSTANCE_OF = 'P31'
EVENT_CTG: dict[str, dict[str, str]] = {
	# Map from event-categories to dicts that map event-indicative entity names to their IDs
		# If the ID starts with 'Q', it expects entities to be an 'instance of' that ID
		# If the ID starts with 'P', it expects entities to have a property with that ID
	'event': {
		'occurrence': 'Q1190554',
		'time interval': 'Q186081',
		'historical period': 'Q11514315',
		'era': 'Q6428674',
		'event': 'Q1656682',
		'recurring event': 'Q15275719',
		'event sequence': 'Q15900616',
		'incident': 'Q18669875',
	},
	'human': {
		'human': 'Q5',
	},
	'country': {
		'country': 'Q6256',
		'state': 'Q7275',
		'sovereign state': 'Q3624078',
	},
	'discovery': {
		'time of discovery or invention': 'P575',
	},
	'media': {
		'work of art': 'Q4502142',
		'literary work': 'Q7725634',
		'comic book series': 'Q14406742',
		'painting': 'Q3305213',
		'musical work/composition': 'Q105543609',
		'film': 'Q11424',
		'animated film': 'Q202866',
		'television series': 'Q16401',
		'anime television series': 'Q63952888',
		'video game': 'Q7889',
		'video game series': 'Q7058673',
	},
}
ID_TO_CTG = {id: ctg for ctg, nmToId in EVENT_CTG.items() for name, id in nmToId.items()}
EVENT_PROP: dict[str, str] = { # Maps event-start/end-indicative property names to their IDs
	'start time': 'P580',
	'end time': 'P582',
	'point in time': 'P585',
	'inception': 'P571',
	'age estimated by a dating method': 'P7584',
	'temporal range start': 'P523',
	'temporal range end': 'P524',
	'earliest date': 'P1319',
	'latest date': 'P1326',
	'date of birth': 'P569',
	'date of death': 'P570',
	'time of discovery or invention': 'P575',
	'publication date': 'P577',
}
PROP_RULES: list[tuple[str] | tuple[str, str] | tuple[str, str, bool]] = [
	# Indicates how event start/end data should be obtained from EVENT_PROP props
		# Each tuple starts with a start-time prop to check for, followed by an optional
		# end-time prop, and an optional 'both props must be present' boolean indicator
	('start time', 'end time'),
	('point in time',),
	('inception',),
	('age estimated by a dating method',),
	('temporal range start', 'temporal range end'),
	('earliest date', 'latest date', True),
	('date of birth', 'date of death'),
	('time of discovery or invention',),
	('publication date',),
]
# For filtering lines before parsing JSON
TYPE_ID_REGEX = re.compile(
	('"id":(?:"' + '"|"'.join([id for id in ID_TO_CTG if id.startswith('Q')]) + '")').encode())
PROP_ID_REGEX = re.compile(
	('(?:"' + '"|"'.join([id for id in ID_TO_CTG if id.startswith('P')]) + '"):\[{"mainsnak"').encode())

def genData(wikidataFile: str, offsetsFile: str, dbFile: str, nProcs: int) -> None:
	""" Reads the dump and writes info to db """
	# Check db
	if os.path.exists(dbFile):
		print('ERROR: Database already exists')
		return
	# Read dump, and write to db
	print('Writing to db')
	dbCon = sqlite3.connect(dbFile)
	dbCon.execute('CREATE TABLE events (' \
		'id INT PRIMARY KEY, title TEXT, start TEXT, end TEXT, time_type TEXT, ctg TEXT)')
	dbCon.commit()
	dbCon.close()
	if nProcs == 1:
		dbCon = sqlite3.connect(dbFile)
		dbCur = dbCon.cursor()
		with bz2.open(wikidataFile, mode='rb') as file:
			for lineNum, line in enumerate(file, 1):
				if lineNum % 1e4 == 0:
					print(f'At line {lineNum}')
				entry = readDumpLine(line)
				if entry:
					dbCur.execute('INSERT INTO events VALUES (?, ?, ?, ?, ?, ?)', entry)
		dbCon.commit()
		dbCon.close()
	else:
		if not os.path.exists(offsetsFile):
			print('Creating offsets file') # For indexed access for multiprocessing (creation took about 6.7 hours)
			with indexed_bzip2.open(wikidataFile) as file:
				with open(offsetsFile, 'wb') as file2:
					pickle.dump(file.block_offsets(), file2)
		print('Allocating file into chunks')
		fileSz: int # About 1.4 TB
		with indexed_bzip2.open(wikidataFile) as file:
			with open(offsetsFile, 'rb') as file2:
				file.set_block_offsets(pickle.load(file2))
				fileSz = file.seek(0, io.SEEK_END)
		chunkSz = fileSz // nProcs
		chunkIdxs = [-1] + [chunkSz * i for i in range(1, nProcs)] + [fileSz-1]
			# Each adjacent pair specifies a start+end byte index for readDumpChunk()
		print(f'- Chunk size: {chunkSz:,}')
		print('Starting processes to read dump')
		dbCon = sqlite3.connect(dbFile)
		dbCur = dbCon.cursor()
		with tempfile.TemporaryDirectory() as tempDirName:
			with multiprocessing.Pool(processes=nProcs, maxtasksperchild=1) as pool:
				# Used maxtasksperchild=1 to free resources on task completion
				for outFile in pool.map(readDumpChunkOneParam,
					((i, wikidataFile, offsetsFile, os.path.join(tempDirName, f'{i}.pickle'),
						chunkIdxs[i], chunkIdxs[i+1]) for i in range(nProcs))):
					# Add entries from subprocess output file
					with open(outFile, 'rb') as file:
						for e in pickle.load(file):
							dbCur.execute('INSERT INTO events VALUES (?, ?, ?, ?, ?, ?)', e)
		dbCon.commit()
		dbCon.close()
def readDumpLine(lineBytes: bytes) -> tuple[int, str, str, str, str, str] | None:
	# Check with regex
	if TYPE_ID_REGEX.search(lineBytes) is None and PROP_ID_REGEX.search(lineBytes) is None:
		return None
	# Decode
	try:
		line = lineBytes.decode('utf-8').rstrip().rstrip(',')
		jsonItem = json.loads(line)
	except json.JSONDecodeError:
		print(f'Unable to parse line {line} as JSON')
		return None
	if 'claims' not in jsonItem:
		return None
	claims = jsonItem['claims']
	# Get event category
	eventCtg: str | None = None
	if INSTANCE_OF not in claims:
		return None
	for statement in claims[INSTANCE_OF]:
		try:
			itemType = statement['mainsnak']['datavalue']['value']['id']
		except KeyError:
			return None
		if itemType in ID_TO_CTG:
			eventCtg = ID_TO_CTG[itemType]
			break
	if not eventCtg:
		for prop in claims:
			if prop in ID_TO_CTG:
				eventCtg = ID_TO_CTG[prop]
		if not eventCtg:
			return None
	# Check for event props
	start: str
	end: str | None
	timeType: str
	found = False
	for props in PROP_RULES:
		startProp: str = EVENT_PROP[props[0]]
		endProp = None if len(props) < 2 else EVENT_PROP[props[1]] # type: ignore
		needBoth = False if len(props) < 3 else props[2] # type: ignore
		if startProp not in claims:
			continue
		try:
			start = json.dumps(claims[startProp][0]['mainsnak']['datavalue'], separators=(',', ':'))
			end = None
			if endProp and endProp in claims:
				end = json.dumps(claims[endProp][0]['mainsnak']['datavalue'], separators=(',', ':'))
			if needBoth and end == None:
				continue
		except (KeyError, ValueError):
			continue
		timeType = props[0]
		found = True
		break
	if not found:
		return None
	# Get wikidata ID, enwiki title
	try:
		itemId = int(jsonItem['id'][1:]) # Skip initial 'Q'
		itemTitle: str = jsonItem['sitelinks']['enwiki']['title']
	except (KeyError, ValueError):
		return None
	# Return result
	return (itemId, itemTitle, start, end, timeType, eventCtg) # type: ignore
def readDumpChunkOneParam(params: tuple[int, str, str, str, int, int]) -> str:
	""" Forwards to readDumpChunk() (for use with pool.map()) """
	return readDumpChunk(*params)
def readDumpChunk(procId: int, wikidataFile: str, offsetsFile: str, outFile: str, startByte: int, endByte: int) -> str:
	""" Reads lines in the dump that begin after a start-byte, and not after an end byte.
		If startByte is -1, start at the first line. """
	# Read dump
	entries = []
	with indexed_bzip2.open(wikidataFile) as file:
		# Load offsets file
		with open(offsetsFile, 'rb') as file2:
			offsets = pickle.load(file2)
			file.set_block_offsets(offsets)
		# Seek to chunk
		if startByte != -1:
			file.seek(startByte)
			file.readline()
		else:
			startByte = 0 # Used for progress calculation
		# Read lines
		count = 0
		while file.tell() <= endByte:
			count += 1
			if count % 1e4 == 0:
				perc = (file.tell() - startByte) / (endByte - startByte) * 100
				print(f'Thread {procId}: {perc:.2f}%')
			entry = readDumpLine(file.readline())
			if entry:
				entries.append(entry)
		# Output results into file
		with open(outFile, 'wb') as file:
			pickle.dump(entries, file)
		return outFile

if __name__ == '__main__':
	parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
	args = parser.parse_args()
	#
	multiprocessing.set_start_method('spawn')
	genData(WIKIDATA_FILE, OFFSETS_FILE, DB_FILE, N_PROCS)
