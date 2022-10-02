#!/usr/bin/python3

"""
Maps events to short descriptions from Wikipedia,
and stores them in the database.
"""

import os, sqlite3

ENWIKI_DB = os.path.join('enwiki', 'desc_data.db')
DB_FILE = 'data.db'

def genData(enwikiDb: str, dbFile: str) -> None:
	print('Creating table')
	dbCon = sqlite3.connect(dbFile)
	dbCur = dbCon.cursor()
	dbCur.execute('CREATE TABLE descs (id INT PRIMARY KEY, wiki_id INT, desc TEXT)')
	#
	print('Getting events with images')
	titleToId: dict[str, int] = {}
	query = 'SELECT events.id, events.title FROM events INNER JOIN event_imgs ON events.id = event_imgs.id'
	for eventId, title in dbCur.execute(query):
		titleToId[title] = eventId
	#
	print('Getting Wikipedia descriptions')
	enwikiCon = sqlite3.connect(enwikiDb)
	enwikiCur = enwikiCon.cursor()
	iterNum = 0
	for title, eventId in titleToId.items():
		iterNum += 1
		if iterNum % 1e4 == 0:
			print(f'At iteration {iterNum}')
		# Get wiki ID
		row = enwikiCur.execute('SELECT id FROM pages WHERE title = ?', (title,)).fetchone()
		if row is None:
			continue
		wikiId = row[0]
		# Check for redirect
		wikiIdToGet = wikiId
		query = \
			'SELECT pages.id FROM redirects INNER JOIN pages ON redirects.target = pages.title WHERE redirects.id = ?'
		row = enwikiCur.execute(query, (wikiId,)).fetchone()
		if row is not None:
			wikiIdToGet = row[0]
		# Get desc
		row = enwikiCur.execute('SELECT desc FROM descs where id = ?', (wikiIdToGet,)).fetchone()
		if row is None:
			continue
		dbCur.execute('INSERT INTO descs VALUES (?, ?, ?)', (eventId, wikiId, row[0]))
	#
	print('Closing databases')
	dbCon.commit()
	dbCon.close()

if __name__ == '__main__':
	import argparse
	parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
	args = parser.parse_args()
	#
	genData(ENWIKI_DB, DB_FILE)
