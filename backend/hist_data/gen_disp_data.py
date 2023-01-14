#!/usr/bin/python3

"""
Adds data about event distribution to the database,
and removes events not eligible for display
"""

# Code used in unit testing (for resolving imports of modules within this directory)
import os, sys
parentDir = os.path.dirname(os.path.realpath(__file__))
sys.path.append(parentDir)
# Standard imports
import argparse
import sqlite3
# Local imports
from cal import SCALES, dbDateToHistDate, dateToUnit

MAX_DISPLAYED_PER_UNIT = 4
DB_FILE = 'data.db'

def genData(dbFile: str, scales: list[int], maxDisplayedPerUnit: int, forImageTables: bool) -> None:
	dbCon = sqlite3.connect(dbFile)
	dbCur = dbCon.cursor()
	#
	print('Reading through events')
	scaleUnitToCounts: dict[tuple[int, int], list[int]] = {}
		# Maps scale and unit to two counts (num events in that unit, num events displayable for that unit)
		# Only includes events with popularity values
	idScales: dict[int, list[tuple[int, int]]] = {} # Maps event ids to scales+units they are displayable on
	iterNum = 0
	query = 'SELECT events.id, start, fmt FROM events INNER JOIN pop ON events.id = pop.id' \
		+ ('' if not forImageTables else ' INNER JOIN event_imgs ON events.id = event_imgs.id') \
		+ ' ORDER BY pop.pop DESC'
	for eventId, eventStart, fmt in dbCur.execute(query):
		iterNum += 1
		if iterNum % 1e5 == 0:
			print(f'At iteration {iterNum}')
		# For each scale
		for scale in scales:
			unit = dateToUnit(dbDateToHistDate(eventStart, fmt), scale)
			# Update maps
			counts: list[int]
			if (scale, unit) in scaleUnitToCounts:
				counts = scaleUnitToCounts[(scale, unit)]
				counts[0] += 1
			else:
				counts = [1, 0]
			if counts[1] < maxDisplayedPerUnit:
				counts[1] += 1
				if eventId not in idScales:
					idScales[eventId] = []
				idScales[eventId].append((scale, unit))
			scaleUnitToCounts[(scale, unit)] = counts
	print(f'Results: {len(idScales)} displayable events')
	#
	print('Looking for non-displayable events')
	eventsToDel: list[int] = []
	for eventId, eventStart, fmt in dbCur.execute(query):
		if eventId in idScales:
			continue
		eventsToDel.append(eventId)
		# Remove from data to be added to 'dist'
		for scale in scales:
			unit = dateToUnit(dbDateToHistDate(eventStart, fmt), scale)
			count = scaleUnitToCounts[(scale, unit)][0] - 1
			if count == 0:
				del scaleUnitToCounts[(scale, unit)]
			else:
				scaleUnitToCounts[(scale, unit)][0] = count
	for (eventId,) in dbCur.execute( # Find events without scores
		'SELECT events.id FROM events LEFT JOIN pop ON events.id = pop.id WHERE pop.id IS NULL'):
		eventsToDel.append(eventId)
	print(f'Found {len(eventsToDel)}')
	#
	if not forImageTables:
		print(f'Deleting {len(eventsToDel)} events')
		iterNum = 0
		for eventId in eventsToDel:
			iterNum += 1
			if iterNum % 1e5 == 0:
				print(f'At iteration {iterNum}')
			#
			dbCur.execute('DELETE FROM events WHERE id = ?', (eventId,))
			dbCur.execute('DELETE FROM pop WHERE id = ?', (eventId,))
	#
	print('Writing to db')
	distTable = 'dist' if not forImageTables else 'img_dist'
	dispTable = 'event_disp' if not forImageTables else 'img_disp'
	dbCur.execute(f'CREATE TABLE {distTable} (scale INT, unit INT, count INT, PRIMARY KEY (scale, unit))')
	for (scale, unit), (count, _) in scaleUnitToCounts.items():
		dbCur.execute(f'INSERT INTO {distTable} VALUES (?, ?, ?)', (scale, unit, count))
	dbCur.execute(f'CREATE TABLE {dispTable} (id INT, scale INT, unit INT, PRIMARY KEY (id, scale))')
	dbCur.execute(f'CREATE INDEX {dispTable}_scale_unit_idx ON event_disp(scale, unit)')
	for eventId, scaleUnits in idScales.items():
		for [scale, unit] in scaleUnits:
			dbCur.execute(f'INSERT INTO {dispTable} VALUES (?, ?, ?)', (eventId, scale, unit))
	#
	print('Closing db')
	dbCon.commit()
	dbCon.close()

if __name__ == '__main__':
	parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
	parser.add_argument(
		'type', nargs='?', choices=['event', 'img'], default='event', help='The type of tables to generate')
	args = parser.parse_args()
	#
	genData(DB_FILE, SCALES, MAX_DISPLAYED_PER_UNIT, args.type == 'img')
