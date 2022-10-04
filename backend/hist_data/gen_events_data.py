#!/usr/bin/python3

"""
Reads a Wikidata JSON dump, looking for entities usable as historical events.  For each such
entity, finds a start date (may be a range), optional end date, and event category (eg: normal
event, person with birth/death date, country, etc).  Writes the results into a database.

The JSON dump contains an array of objects, each of which describes a Wikidata item item1,
and takes up it's own line.
- Getting item1's Wikidata ID: item1['id'] (eg: "Q144")
- Checking for a property: item1['claims'][prop1] == array1
- Getting a property statement value: item1['claims'][prop1][idx1]['mainsnak']['datavalue']
	'idx1' indexes an array of statements

Value objects have a 'type' and 'value' field.
Info about objects with type 'time' can be found at: https://www.wikidata.org/wiki/Help:Dates
	An example:
		{"value":{
			"time":"+1830-10-04T00:00:00Z", # The year is always signed and padded to 4-16 digits (-0001 means 1 BCE)
			"timezone":0, # Unused
			"before":0,   # Unused
			"after":0,    # Unused
			"precision":11,
			"calendarmodel":"http://www.wikidata.org/entity/Q1985727"
		}, "type":"time"}
	'precision' can be one of:
		0  - billion years (timestamp eg: -5000000000-00-00T00:00:00Z)
		1  - hundred million years
		...
		6  - millenium (warning: represents ranges from *1 to *0, eg: 1001-2000)
		7  - century (warning: represents ranges from *1 to *0, eg: 1801-1900)
		8  - decade (represents ranges from *0 to *9, eg: 2010-2019)
		9  - year
		10 - month
		11 - day
	'calendarmodel' can be one of:
		"http://www.wikidata.org/entity/Q1985727" - proleptic Gregorian calendar
		"http://www.wikidata.org/entity/Q1985786" - proleptic Julian calendar
Info about objects with type 'quantity' can be found at: https://www.wikidata.org/wiki/Help:Data_type#Quantity
	An example:
		{"value":{
			"amount":"+10.9",
			"unit":"http://www.wikidata.org/entity/Q20764",
			"lowerBound":"+170.1", # May be absent
			"upperBound":"+470", # May be absent
		}, "type":"quantity"}
	'unit' can be one of:
		"http://www.wikidata.org/entity/Q577"      - year
		"http://www.wikidata.org/entity/Q24564698" - years old
		"http://www.wikidata.org/entity/Q3013059"  - kiloannum (1e3 yrs)
		"http://www.wikidata.org/entity/Q20764"    - megaannum (1e6 yrs)
		"http://www.wikidata.org/entity/Q524410"   - gigaannum (1e9 yrs)
"""

# On Linux, running on the full dataset seems to make the processes hang when done. This was resolved by:
# - Storing subprocess results in temp files. Apparently passing large objects through pipes can cause deadlock.
# - Using set_start_method('spawn'). Apparently 'fork' can cause unexpected copying of lock/semaphore/etc state.
#   Related: https://bugs.python.org/issue6721
# - Using pool.map() instead of pool.imap_unordered(), which seems to hang in some cases (was using python 3.8).
#   Possibly related: https://github.com/python/cpython/issues/72882

# Enable unit testing code to, when running this script, resolve imports of modules within this directory
import os, sys
parentDir = os.path.dirname(os.path.realpath(__file__))
sys.path.append(parentDir)

import io, math, re, argparse
import bz2, json, sqlite3
import multiprocessing, indexed_bzip2, pickle, tempfile
# Modules in this directory
from cal import gregorianToJdn, julianToJdn

WIKIDATA_FILE = os.path.join('wikidata', 'latest-all.json.bz2')
DUMP_YEAR = 2022 # Used for converting 'age' values into dates
OFFSETS_FILE = os.path.join('wikidata', 'offsets.dat')
DB_FILE = 'data.db'
N_PROCS = 6

# For getting Wikidata entity IDs
INSTANCE_OF = 'P31'
EVENT_CTG: dict[str, dict[str, str]] = {
	# Maps event-categories to dicts that map event-indicative entity names to their IDs
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
EVENT_PROP: dict[str, str] = {
	# Maps event-start/end-indicative property names to their IDs
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
UNIT_TO_SCALE: dict[str, int] = { # Maps 'unit' values (found in type=quantity value objects) to numbers of years
	'http://www.wikidata.org/entity/Q577':          1, # 'year'
	'http://www.wikidata.org/entity/Q24564698':     1, # 'years old'
	'http://www.wikidata.org/entity/Q3013059':  10**3, # 'kiloannum' (1e3 yrs)
	'http://www.wikidata.org/entity/Q20764':    10**6, # 'megaannum' (1e6 yrs)
	'http://www.wikidata.org/entity/Q524410':   10**9, # 'gigaannum' (1e9 yrs)
}

# For filtering lines before parsing JSON
TYPE_ID_REGEX = ('"id":(?:"' + '"|"'.join([id for id in ID_TO_CTG if id.startswith('Q')]) + '")').encode()
PROP_ID_REGEX = ('(?:"' + '"|"'.join([id for id in ID_TO_CTG if id.startswith('P')]) + '"):\[{"mainsnak"').encode()

def genData(wikidataFile: str, offsetsFile: str, dbFile: str, nProcs: int) -> None:
	""" Reads the dump and writes to db """
	# Check db
	if os.path.exists(dbFile):
		print('ERROR: Database already exists')
		return
	# Read dump, and write to db
	print('Writing to db')
	dbCon = sqlite3.connect(dbFile)
	dbCur = dbCon.cursor()
	dbCur.execute('CREATE TABLE events (id INT PRIMARY KEY, title TEXT UNIQUE, ' \
		'start INT, start_upper INT, end INT, end_upper INT, fmt INT, ctg TEXT)')
	if nProcs == 1:
		with bz2.open(wikidataFile, mode='rb') as file:
			for lineNum, line in enumerate(file, 1):
				if lineNum % 1e4 == 0:
					print(f'At line {lineNum}')
				entry = readDumpLine(line)
				if entry:
					dbCur.execute('INSERT OR IGNORE INTO events VALUES (?, ?, ?, ?, ?, ?, ?, ?)', entry)
						# The 'OR IGNORE' is for a few entries that share the same title (and seem like redirects)
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
		with tempfile.TemporaryDirectory() as tempDirName:
			with multiprocessing.Pool(processes=nProcs, maxtasksperchild=1) as pool:
				# Used maxtasksperchild=1 to free resources on task completion
				for outFile in pool.map(readDumpChunkOneParam,
					[(i, wikidataFile, offsetsFile, os.path.join(tempDirName, f'{i}.pickle'),
						chunkIdxs[i], chunkIdxs[i+1]) for i in range(nProcs)]):
					# Add entries from subprocess output file
					with open(outFile, 'rb') as file:
						for entry in pickle.load(file):
							dbCur.execute('INSERT OR IGNORE INTO events VALUES (?, ?, ?, ?, ?, ?, ?, ?)', entry)
	dbCon.commit()
	dbCon.close()

# For data extraction
def readDumpLine(lineBytes: bytes) -> tuple[int, str, int, int | None, int | None, int | None, int, str] | None:
	""" Parses a Wikidata dump line, returning an entry to add to the db """
	# Check with regex
	if re.search(TYPE_ID_REGEX, lineBytes) is None and re.search(PROP_ID_REGEX, lineBytes) is None:
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
	# Get wikidata ID, enwiki title
	try:
		itemId = int(jsonItem['id'][1:]) # Skip initial 'Q'
		itemTitle: str = jsonItem['sitelinks']['enwiki']['title']
	except (KeyError, ValueError):
		return None
	# Get event category
	eventCtg: str | None = None
	if INSTANCE_OF in claims: # Check types
		for statement in claims[INSTANCE_OF]:
			try:
				itemType = statement['mainsnak']['datavalue']['value']['id']
			except KeyError:
				return None
			if itemType in ID_TO_CTG:
				eventCtg = ID_TO_CTG[itemType]
				break
	if not eventCtg:
		for prop in claims: # Check props
			if prop in ID_TO_CTG:
				eventCtg = ID_TO_CTG[prop]
		if not eventCtg:
			return None
	# Check for event-start/end props
	startVal: str
	endVal: str | None
	timeType: str
	found = False
	for props in PROP_RULES:
		startProp: str = EVENT_PROP[props[0]]
		endProp = None if len(props) < 2 else EVENT_PROP[props[1]]
		needBoth = False if len(props) < 3 else props[2]
		if startProp not in claims:
			continue
		try:
			startVal = claims[startProp][0]['mainsnak']['datavalue']
			endVal = None
			if endProp and endProp in claims:
				endVal = claims[endProp][0]['mainsnak']['datavalue']
			elif needBoth:
				continue
		except (KeyError, ValueError):
			continue
		timeType = props[0]
		found = True
		break
	if not found:
		return None
	# Convert time values
	timeData = getTimeData(startVal, endVal, timeType)
	if timeData is None:
		return None
	start, startUpper, end, endUpper, timeFmt = timeData
	#
	return (itemId, itemTitle, start, startUpper, end, endUpper, timeFmt, eventCtg)
def getTimeData(startVal, endVal, timeType: str) -> tuple[int, int | None, int | None, int | None, int] | None:
	""" Obtains event start+end data from value objects with type 'time', according to 'timeType' """
	# Values to return
	start: int
	startUpper: int | None = None
	end: int | None = None
	endUpper: int | None = None
	timeFmt: int
	#
	if timeType == 'age estimated by a dating method':
		if 'type' not in startVal or startVal['type'] != 'quantity':
			return None
		# Get quantity data
		try:
			value = startVal['value']
			amount = math.ceil(float(value['amount']))
			unit = value['unit']
			if 'lowerBound' in value and 'upperBound' in value:
				lowerBound = math.ceil(float(value['lowerBound']))
				upperBound = math.ceil(float(value['upperBound']))
			else:
				lowerBound = None
				upperBound = None
		except (KeyError, ValueError):
			return None
		# Get unit scale
		if unit not in UNIT_TO_SCALE:
			return None
		scale = UNIT_TO_SCALE[unit]
		# Get start+startUpper
		if lowerBound is None:
			start = DUMP_YEAR - amount * scale
		else:
			start = DUMP_YEAR - upperBound * scale
			startUpper = DUMP_YEAR - lowerBound * scale
		# Account for non-existence of 0 CE
		if start <= 0:
			start -= 1
		if startUpper is not None and startUpper <= 0:
			startUpper -= 1
		# Adjust precision
		start = start // scale * scale
		if startUpper is not None:
			startUpper = startUpper // scale * scale
		elif scale > 1:
			startUpper = start + scale - 1
		#
		timeFmt = 0
	elif timeType == 'earliest date':
		# Get start
		startTimeVals = getEventTime(startVal)
		if startTimeVals is None:
			return None
		start, _, timeFmt = startTimeVals
		# Get end
		endTimeVals = getEventTime(endVal)
		if endTimeVals is None:
			return None
		end, _, timeFmt2 = endTimeVals
		if timeFmt != timeFmt2:
			if timeFmt == 1 and timeFmt2 == 2:
				timeFmt = 3
			else:
				return None
	else:
		# Get start+startUpper
		startTimeVals = getEventTime(startVal)
		if startTimeVals is None:
			return None
		start, startUpper, timeFmt = startTimeVals
		# Get end+endUpper
		if endVal is not None:
			endTimeVals = getEventTime(endVal)
			if endTimeVals is None:
				return None
			end, endUpper, timeFmt2 = endTimeVals
			if timeFmt != timeFmt2:
				if timeFmt == 1 and timeFmt2 == 2:
					timeFmt = 3
				else:
					return None
	return start, startUpper, end, endUpper, timeFmt
def getEventTime(dataVal) -> tuple[int, int | None, int] | None:
	""" Obtains event start (or end) data from a value object with type 'time' """
	if 'type' not in dataVal or dataVal['type'] != 'time':
		return None
	# Get time data
	try:
		value = dataVal['value']
		time = value['time']
		match = re.match(r'([+-]\d+)-(\d+)-(\d+)', time)
		if match is None:
			return None
		year, month, day = (int(x) for x in match.groups())
		precision = value['precision']
		calendarmodel = value['calendarmodel']
	except (KeyError, ValueError):
		return None
	# Get start+startUpper
	start: int
	startUpper: int | None = None
	timeFmt: int
	if precision in [10, 11]: # 'month' or 'day' precision
		if year < -4713: # If before 4713 BCE (start of valid julian date period)
			print(f'WARNING: Skipping sub-year-precision date before 4713 BCE: {json.dumps(dataVal)}')
			return None
		day = max(day, 1) # With month-precision, entry may have a 'day' of 0
		if calendarmodel == 'http://www.wikidata.org/entity/Q1985727': # 'proleptic gregorian calendar'
			start = gregorianToJdn(year, month, day)
			if precision == 10:
				startUpper = gregorianToJdn(year, month+1, 0)
			timeFmt = 2
		else: # "http://www.wikidata.org/entity/Q1985786" ('proleptic julian calendar')
			start = julianToJdn(year, month, day)
			if precision == 10:
				startUpper = julianToJdn(year, month+1, 0)
			timeFmt = 1
	elif 0 <= precision < 10: # 'year' to 'gigaannum' precision
		scale: int = 10 ** (9 - precision)
		start = year // scale * scale
		if scale > 1:
			startUpper = start + scale - 1
		if precision in [6, 7]: # Account for century/millenia ranges being from *1 to *0
			start += 1
			if startUpper is not None:
				startUpper += 1
		timeFmt = 0
	else:
		return None
	return start, startUpper, timeFmt

# For using multiple processes
def readDumpChunkOneParam(params: tuple[int, str, str, str, int, int]) -> str:
	""" Forwards to readDumpChunk() (for use with pool.map()) """
	return readDumpChunk(*params)
def readDumpChunk(
		procId: int, wikidataFile: str, offsetsFile: str, outFile: str, startByte: int, endByte: int) -> str:
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
