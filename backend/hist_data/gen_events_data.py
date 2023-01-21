#!/usr/bin/python3

"""
Reads a Wikidata JSON dump, looking for entities usable as historical events.  For each such
entity, finds a start date (may be a range), optional end date, and event category (eg: discovery,
person with birth/death date, etc).  Writes the results into a database.

The JSON dump contains an array of objects, each of which describes a Wikidata item item1,
and takes up it's own line.
- Getting item1's Wikidata ID: item1['id'] (eg: "Q144")
- Checking for a property: item1['claims'][prop1] == array1
- Getting a property statement value: item1['claims'][prop1][idx1]['mainsnak']['datavalue']
	'idx1' indexes an array of statements

'datavalue' objects have a 'type' and 'value' field.
Info about objects with type 'time' can be found at: https://www.wikidata.org/wiki/Help:Dates
	An example:
		{"value":{
			"time":"+1830-10-04T00:00:00Z", # The year is always signed and padded to 4-16 digits (-0001 means 1 BC)
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

# On Linux, running on the full dataset seems to make the processes hang when done.  This was resolved by:
# - Storing subprocess results in temp files.  Apparently passing large objects through pipes can cause deadlock.
# - Using set_start_method('spawn').  Apparently 'fork' can cause unexpected copying of lock/semaphore/etc state.
#   Related: https://bugs.python.org/issue6721
# - Using pool.map() instead of pool.imap_unordered(), which seems to hang in some cases (was using python 3.8).
#   Possibly related: https://github.com/python/cpython/issues/72882

# Note: Took about 4.5 hours to run

# For unit testing, resolve imports of modules within this directory
import os
import sys
parentDir = os.path.dirname(os.path.realpath(__file__))
sys.path.append(parentDir)

from typing import cast
import argparse
import math
import re
import io
import bz2
import json
import sqlite3

import indexed_bzip2
import pickle
import multiprocessing
import tempfile

from cal import gregorianToJdn, julianToJdn, MIN_CAL_YEAR

# ========== Constants ==========

WIKIDATA_FILE = os.path.join('wikidata', 'latest-all.json.bz2')
OFFSETS_FILE = os.path.join('wikidata', 'offsets.dat')
DB_FILE = 'data.db'
N_PROCS = 6 # Number of processes to use

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
		'project': 'Q170584',
		'number of deaths': 'P1120',
	},
	'place': {
		'country': 'Q6256',
		'state': 'Q7275',
		'sovereign state': 'Q3624078',
		'city': 'Q515',
		'tourist attraction': 'Q570116',
		'heritage site': 'Q358',
		'terrestrial planet': 'Q128207',
		'navigational star': 'Q108171565',
		'G-type main-sequence star': 'Q5864',
	},
	'organism': {
		'taxon': 'Q16521',
	},
	'person': {
		'human': 'Q5',
	},
	'work': {
		'creator': 'P170',
		'genre': 'P136',
	},
	'discovery': {
		'time of discovery or invention': 'P575',
	},
}
ID_TO_CTG = {id: ctg for ctg, nmToId in EVENT_CTG.items() for name, id in nmToId.items()}
BASIC_TIME_PROPS: dict[str, str] = {
	# Maps some time-indicative property names to their IDs
	'start time': 'P580',
	'end time': 'P582',
	'point in time': 'P585',
	'inception': 'P571',
	'age estimated by a dating method': 'P7584',
	'temporal range start': 'P523',
	'temporal range end': 'P524',
	'earliest date': 'P1319',
	'latest date': 'P1326',
}
CTG_TO_TIME_PROPS: dict[str, dict[str, str]] = {
	# Maps event-categories to dicts, which hold usable time-indicative property names and IDs
	'event': BASIC_TIME_PROPS,
	'place': BASIC_TIME_PROPS,
	'organism': BASIC_TIME_PROPS,
	'person': {
		'date of birth': 'P569',
		'date of death': 'P570',
	},
	'work': {
		'publication date': 'P577',
	},
	'discovery': {
		'time of discovery or invention': 'P575',
	},
}
PROP_RULES: list[tuple[str, str | None, bool | None]] = [
	# Indicates how event start/end data should be obtained from props in CTG_TO_TIME_PROPS
		# Each tuple starts with a start-time prop to check for, followed by an optional
		# end-time prop, and an optional 'both props must be present' boolean indicator
	('start time', 'end time', None),
	('point in time', None, None),
	('inception', None, None),
	('age estimated by a dating method', None, None),
	('temporal range start', 'temporal range end', None),
	('earliest date', 'latest date', True),
	('date of birth', 'date of death', None),
	('time of discovery or invention', None, None),
	('publication date', None, None),
]
UNIT_TO_SCALE: dict[str, int] = {
	# Maps 'unit' values (found in 'datavalue' objects with type=quantity) to numbers of years
	'http://www.wikidata.org/entity/Q577':          1, # 'year'
	'http://www.wikidata.org/entity/Q24564698':     1, # 'years old'
	'http://www.wikidata.org/entity/Q3013059':  10**3, # 'kiloannum' (1e3 yrs)
	'http://www.wikidata.org/entity/Q20764':    10**6, # 'megaannum' (1e6 yrs)
	'http://www.wikidata.org/entity/Q524410':   10**9, # 'gigaannum' (1e9 yrs)
}

# For filtering lines before parsing JSON
TYPE_ID_REGEX = ('"id":(?:"' + '"|"'.join([id for id in ID_TO_CTG if id.startswith('Q')]) + '")').encode()
PROP_ID_REGEX = ('(?:"' + '"|"'.join([id for id in ID_TO_CTG if id.startswith('P')]) + '"):\[{"mainsnak"').encode()

# ========== Main function ==========

def genData(wikidataFile: str, offsetsFile: str, dbFile: str, nProcs: int) -> None:
	""" Reads the dump and writes to db """
	if os.path.exists(dbFile):
		print('ERROR: Database already exists')
		return

	print('Opening db')
	dbCon = sqlite3.connect(dbFile)
	dbCur = dbCon.cursor()

	dbCur.execute('CREATE TABLE events (id INT PRIMARY KEY, title TEXT UNIQUE, ' \
		'start INT, start_upper INT, end INT, end_upper INT, fmt INT, ctg TEXT)')
	dbCur.execute('CREATE INDEX events_id_start_idx ON events(id, start)')
	dbCur.execute('CREATE INDEX events_title_nocase_idx ON events(title COLLATE NOCASE)')

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
			print('Creating offsets file') # For indexed access used in multiprocessing (may take about 7 hours)
			with indexed_bzip2.open(wikidataFile) as file:
				with open(offsetsFile, 'wb') as file2:
					pickle.dump(file.block_offsets(), file2)

		print('Allocating file into chunks')
		fileSz: int # Was about 1.4 TB
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
						for item in pickle.load(file):
							dbCur.execute('INSERT OR IGNORE INTO events VALUES (?, ?, ?, ?, ?, ?, ?, ?)', item)

	print('Closing db')
	dbCon.commit()
	dbCon.close()

# ========== For data extraction ==========

def readDumpLine(lineBytes: bytes) -> tuple[int, str, int, int | None, int | None, int | None, int, str] | None:
	""" Parses a Wikidata dump line, returning an entry to add to the db """
	# Check with regexes
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
	usableProps = CTG_TO_TIME_PROPS[eventCtg]
	for rule in PROP_RULES:
		if rule[0] not in usableProps or rule[1] and rule[1] not in usableProps:
			continue
		startProp: str = usableProps[rule[0]]
		endProp = None if not rule[1] else usableProps[rule[1]]
		needBoth = False if not rule[2] else rule[2]
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
		timeType = rule[0]
		found = True
		break
	if not found:
		return None

	# Convert time values
	timeData = getTimeData(startVal, endVal, timeType)
	if timeData is None:
		return None
	start, startUpper, end, endUpper, timeFmt = timeData

	return (itemId, itemTitle, start, startUpper, end, endUpper, timeFmt, eventCtg)

def getTimeData(startVal, endVal, timeType: str) -> tuple[int, int | None, int | None, int | None, int] | None:
	""" Obtains event start+end data from 'datavalue' objects with type 'time', according to 'timeType' """
	# Values to return
	start: int
	startUpper: int | None = None
	end: int | None = None
	endUpper: int | None = None
	timeFmt: int

	if timeType == 'age estimated by a dating method':
		# Note: Ages are interpreted relative to 1 AD. Using a year like 2020 results in
		# 'datedness' and undesirable small offsets to values like '1 billion years old'.
		if 'type' not in startVal or startVal['type'] != 'quantity':
			return None

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

		# Get scale
		if unit not in UNIT_TO_SCALE:
			return None
		scale = UNIT_TO_SCALE[unit]

		# Get start+startUpper
		if lowerBound is None:
			start = -amount * scale
		else:
			start = -cast(int, upperBound) * scale
			startUpper = -lowerBound * scale

		# Adjust precision
		start = start // scale * scale
		if startUpper is not None:
			startUpper = startUpper // scale * scale
		elif scale > 1:
			startUpper = start + scale - 1

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
			if timeFmt == 2 and timeFmt2 == 1:
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
				if timeFmt == 2 and timeFmt2 == 1:
					timeFmt = 3
				else:
					return None
	return start, startUpper, end, endUpper, timeFmt

def getEventTime(dataVal) -> tuple[int, int | None, int] | None:
	""" Obtains event start (or end) data from a 'datavalue' object with type 'time' """
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
		if year < MIN_CAL_YEAR: # If before start of valid julian date period
			print(f'WARNING: Skipping sub-year-precision date before {-MIN_CAL_YEAR} BC: {json.dumps(dataVal)}')
			return None
		day = max(day, 1) # With month-precision, entry may have a 'day' of 0
		if calendarmodel == 'http://www.wikidata.org/entity/Q1985727': # 'proleptic gregorian calendar'
			start = gregorianToJdn(year, month, day)
			if precision == 10:
				startUpper = gregorianToJdn(year, month+1, 0)
			timeFmt = 1
		else: # "http://www.wikidata.org/entity/Q1985786" ('proleptic julian calendar')
			start = julianToJdn(year, month, day)
			if precision == 10:
				startUpper = julianToJdn(year, month+1, 0)
			timeFmt = 2
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

# ========== For using multiple processes ==========

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

# ========== Main block ==========

if __name__ == '__main__':
	parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
	args = parser.parse_args()

	multiprocessing.set_start_method('spawn')
	genData(WIKIDATA_FILE, OFFSETS_FILE, DB_FILE, N_PROCS)
