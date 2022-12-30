#!/usr/bin/python3

"""
Delete events from the database that have no image.
"""

# Enable unit testing code to, when running this script, resolve imports of modules within this directory
import os, sys
parentDir = os.path.dirname(os.path.realpath(__file__))
sys.path.append(parentDir)

import argparse
import sqlite3
from cal import SCALES, dbDateToHistDate, dateToUnit

DB_FILE = 'data.db'

def reduceData(dbFile: str, scales: list[int]) -> None:
	dbCon = sqlite3.connect(dbFile)
	dbCur = dbCon.cursor()
	#
	print('Getting events to delete')
	eventsToDel: list[int] = []
	scaleUnitToDelCount: dict[tuple[int, int], int] = {} # Stores counts to subtract from entries in 'dist'
	query = 'SELECT events.id, events.start, events.fmt FROM events' \
		' LEFT JOIN event_imgs ON events.id = event_imgs.id WHERE event_imgs.id IS NULL'
	iterNum = 0
	for (eventId, start, fmt) in dbCur.execute(query):
		if iterNum % 1e5 == 0:
			print(f'At iteration {iterNum}')
		#
		eventsToDel.append(eventId)
		date = dbDateToHistDate(start, fmt)
		for scale in scales:
			unit = dateToUnit(date, scale)
			if (scale, unit) not in scaleUnitToDelCount:
				scaleUnitToDelCount[(scale, unit)] = 1
			else:
				scaleUnitToDelCount[(scale, unit)] += 1
	print(f'Found {len(eventsToDel)}')
	#
	print('Deleting events')
	iterNum = 0
	for eventId in eventsToDel:
		iterNum += 1
		if iterNum % 1e5 == 0:
			print(f'At iteration {iterNum}')
		#
		dbCur.execute('DELETE FROM events WHERE id = ?', (eventId,))
		dbCur.execute('DELETE FROM pop WHERE id = ?', (eventId,))
		dbCur.execute('DELETE FROM event_disp WHERE id = ?', (eventId,))
	for (scale, unit), delCount in scaleUnitToDelCount.items():
		dbCur.execute('UPDATE dist SET count = count - ? WHERE scale = ? AND unit = ?', (delCount, scale, unit))
	dbCur.execute('DELETE FROM dist WHERE count < 1')
	#
	dbCon.commit()
	dbCon.close()

if __name__ == '__main__':
	parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
	args = parser.parse_args()
	#
	reduceData(DB_FILE, SCALES)
