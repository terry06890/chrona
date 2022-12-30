#!/usr/bin/python3

"""
Adds data about event distribution to the database, and removes events not eligible for display.
"""

# Enable unit testing code to, when running this script, resolve imports of modules within this directory
import os, sys
parentDir = os.path.dirname(os.path.realpath(__file__))
sys.path.append(parentDir)

import sqlite3
from cal import SCALES, dbDateToHistDate, dateToUnit

MAX_DISPLAYED_PER_UNIT = 4
DB_FILE = 'data.db'

def genData(dbFile: str, scales: list[int], maxDisplayedPerUnit: int) -> None:
	dbCon = sqlite3.connect(dbFile)
	dbCur = dbCon.cursor()
	#
	print('Reading through events')
	scaleUnitToCounts: dict[tuple[int, int], list[int]] = {}
		# Maps scale and unit to two counts (num events in that unit, num events displayable for that unit)
		# Only includes events with popularity values
	idScales: dict[int, list[int]] = {} # Maps event ids to scales they are displayable on
	iterNum = 0
	query = 'SELECT events.id, start, fmt FROM events INNER JOIN pop ON events.id = pop.id ORDER BY pop.pop DESC'
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
				idScales[eventId].append(scale)
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
	query2 = 'SELECT events.id FROM events LEFT JOIN pop ON events.id = pop.id WHERE pop.id IS NULL'
	for (eventId,) in dbCur.execute(query2): # Include events without scores
		eventsToDel.append(eventId)
	print(f'Found {len(eventsToDel)}')
	#
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
	dbCur.execute('CREATE TABLE dist (scale INT, unit INT, count INT, PRIMARY KEY (scale, unit))')
	for (scale, unit), (count, _) in scaleUnitToCounts.items():
		dbCur.execute('INSERT INTO dist VALUES (?, ?, ?)', (scale, unit, count))
	dbCur.execute('CREATE TABLE event_disp (id INT, scale INT, PRIMARY KEY (id, scale))')
	for eventId, scales in idScales.items():
		for scale in scales:
			dbCur.execute('INSERT INTO event_disp VALUES (?, ?)', (eventId, scale))
	#
	print('Closing db')
	dbCon.commit()
	dbCon.close()

if __name__ == '__main__':
	import argparse
	parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
	args = parser.parse_args()
	#
	genData(DB_FILE, SCALES, MAX_DISPLAYED_PER_UNIT)
