#!/usr/bin/python3

"""
Adds Wikipedia page view info to the database as popularity values
"""

import os, sqlite3

PAGEVIEWS_DB = os.path.join('enwiki', 'pageview_data.db')
DB_FILE = 'data.db'

def genData(pageviewsDb: str, dbFile: str) -> None:
	dbCon = sqlite3.connect(dbFile)
	dbCur = dbCon.cursor()
	#
	print('Getting event data')
	titleToId: dict[str, int] = {}
	for eventId, title in dbCur.execute('SELECT id, title FROM events'):
		titleToId[title] = eventId
	#
	print('Getting view counts')
	pdbCon = sqlite3.connect(pageviewsDb)
	pdbCur = pdbCon.cursor()
	titleToViews: dict[str, int] = {}
	iterNum = 0
	for title, views in pdbCur.execute('SELECT title, views from views'):
		iterNum += 1
		if iterNum % 1e6 == 0:
			print(f'At iteration {iterNum}')
		#
		if title not in titleToId:
			continue
		titleToViews[title] = views
	pdbCon.close()
	#
	print(f'Result: {len(titleToViews)} out of {len(titleToId)}')
	dbCur.execute('CREATE TABLE pop (id INT PRIMARY KEY, pop INT)')
	dbCur.execute('CREATE INDEX pop_idx ON pop(pop)')
	for title, views in titleToViews.items():
		dbCur.execute('INSERT INTO pop VALUES (?, ?)', (titleToId[title], views))
	#
	dbCon.commit()
	dbCon.close()

if __name__ == '__main__':
	import argparse
	parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
	args = parser.parse_args()
	#
	genData(PAGEVIEWS_DB, DB_FILE)
