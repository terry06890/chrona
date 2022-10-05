#!/usr/bin/python3

"""
Delete extraneous events from the database that have no image (and consequently no description)
"""

import argparse
import sqlite3

DB_FILE = 'data.db'

def reduceData(dbFile: str) -> None:
	dbCon = sqlite3.connect(dbFile)
	dbCur = dbCon.cursor()
	#
	print('Getting events to delete')
	eventsToDel = set()
	query = 'SELECT events.id FROM events LEFT JOIN event_imgs ON events.id = event_imgs.id WHERE event_imgs.id IS NULL'
	for (eventId,) in dbCur.execute(query):
		eventsToDel.add(eventId)
	#
	print('Deleting events')
	iterNum = 0
	for eventId in eventsToDel:
		iterNum += 1
		if iterNum % 1e5 == 0:
			print(f'At iteration {iterNum}')
		#
		dbCur.execute('DELETE from events where id = ?', (eventId,))
		dbCur.execute('DELETE from pop where id = ?', (eventId,))
	#
	dbCon.commit()
	dbCon.close()

if __name__ == '__main__':
	parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
	args = parser.parse_args()
	#
	reduceData(DB_FILE)
