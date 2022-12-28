#!/usr/bin/python3

"""
Adds data about event distribution and scores to the database.
"""

# Enable unit testing code to, when running this script, resolve imports of modules within this directory
import os, sys
parentDir = os.path.dirname(os.path.realpath(__file__))
sys.path.append(parentDir)

import sqlite3
from cal import gregorianToJdn, jdnToGregorian

MONTH_SCALE = -1;
DAY_SCALE = -2;
SCALES: list[int] = [int(x) for x in [1e9, 1e8, 1e7, 1e6, 1e5, 1e4, 1e3, 100, 10, 1, MONTH_SCALE, DAY_SCALE]];
MAX_DISPLAYED_PER_UNIT = 4
#
DB_FILE = 'data.db'

def genData(dbFile: str, scales: list[int], maxDisplayedPerUnit: int) -> None:
	dbCon = sqlite3.connect(dbFile)
	dbCur = dbCon.cursor()
	#
	print('Reading through events')
	scaleUnitToCounts: dict[tuple[int, int], list[int]] = {}
		# Maps scale and unit to two counts (num events in that unit, num events displayable for that unit)
		# Only includes events with popularity values
	idAndScaleToScore: dict[tuple[int, int], int] = {} # Maps event id and scale to score
	iterNum = 0
	query = 'SELECT events.id, start, fmt, pop FROM events INNER JOIN pop ON events.id = pop.id ORDER BY pop.pop DESC'
	for eventId, eventStart, fmt, pop in dbCur.execute(query):
		iterNum += 1
		if iterNum % 1e3 == 0:
			print(f'At iteration {iterNum}')
		# For each scale
		for scale in scales:
			# Get unit
			unit: int
			if scale >= 1:
				unit = (eventStart if fmt == 0 else jdnToGregorian(eventStart)[0]) // scale
			elif scale == MONTH_SCALE:
				if fmt == 0:
					unit = gregorianToJdn(eventStart, 1, 1)
				else:
					year, month, day = jdnToGregorian(eventStart)
					unit = eventStart if day == 1 else gregorianToJdn(year, month, 1)
			else: # scale == DAY_SCALE
				unit = eventStart if fmt != 0 else gregorianToJdn(eventStart, 1, 1)
			# Update maps
			counts: list[int]
			if (scale, unit) in scaleUnitToCounts:
				counts = scaleUnitToCounts[(scale, unit)]
				counts[0] += 1
			else:
				counts = [1, 0]
			if counts[1] < maxDisplayedPerUnit:
				counts[1] += 1
				idAndScaleToScore[(eventId, scale)] = pop
			scaleUnitToCounts[(scale, unit)] = counts
	#
	print('Writing to db')
	dbCur.execute('CREATE TABLE dist (scale INT, unit INT, count INT, PRIMARY KEY (scale, unit))')
	dbCur.execute('CREATE TABLE scores (id INT, scale INT, score INT, PRIMARY KEY (id, scale))')
	for (scale, unit), (count, _) in scaleUnitToCounts.items():
		dbCur.execute('INSERT INTO dist VALUES (?, ?, ?)', (scale, unit, count))
	for (eventId, scale), score in idAndScaleToScore.items():
		dbCur.execute('INSERT INTO scores VALUES (?, ?, ?)', (eventId, scale, score))
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
