#!/usr/bin/python3

"""
Adds data from the wiki dump index-file into a database
"""
import sys, os, re
import bz2
import sqlite3

INDEX_FILE = 'enwiki-20220501-pages-articles-multistream-index.txt.bz2' # Had about 22e6 lines
DB_FILE = 'dump_index.db'

def genData(indexFile: str, dbFile: str) -> None:
	""" Reads the index file and creates the db """
	if os.path.exists(dbFile):
		raise Exception(f'ERROR: Existing {dbFile}')
	print('Creating database')
	dbCon = sqlite3.connect(dbFile)
	dbCur = dbCon.cursor()
	dbCur.execute('CREATE TABLE offsets (title TEXT PRIMARY KEY, id INT UNIQUE, offset INT, next_offset INT)')
	print('Iterating through index file')
	lineRegex = re.compile(r'([^:]+):([^:]+):(.*)')
	lastOffset = 0
	lineNum = 0
	entriesToAdd: list[tuple[str, str]] = []
	with bz2.open(indexFile, mode='rt') as file:
		for line in file:
			lineNum += 1
			if lineNum % 1e5 == 0:
				print(f'At line {lineNum}')
			#
			match = lineRegex.fullmatch(line.rstrip())
			assert match is not None
			offsetStr, pageId, title = match.group(1,2,3)
			offset = int(offsetStr)
			if offset > lastOffset:
				for t, p in entriesToAdd:
					try:
						dbCur.execute('INSERT INTO offsets VALUES (?, ?, ?, ?)', (t, int(p), lastOffset, offset))
					except sqlite3.IntegrityError as e:
						# Accounts for certain entries in the file that have the same title
						print(f'Failed on title "{t}": {e}', file=sys.stderr)
				entriesToAdd = []
				lastOffset = offset
			entriesToAdd.append((title, pageId))
	for title, pageId in entriesToAdd:
		try:
			dbCur.execute('INSERT INTO offsets VALUES (?, ?, ?, ?)', (title, int(pageId), lastOffset, -1))
		except sqlite3.IntegrityError as e:
			print(f'Failed on title "{t}": {e}', file=sys.stderr)
	print('Closing database')
	dbCon.commit()
	dbCon.close()

if __name__ == '__main__':
	import argparse
	parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
	parser.parse_args()
	#
	genData(INDEX_FILE, DB_FILE)
