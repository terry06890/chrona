#!/usr/bin/python3

"""
Adds additional manually-picked events to the database
"""

# Code used in unit testing (for resolving imports of modules within this directory)
import os, sys
parentDir = os.path.dirname(os.path.realpath(__file__))
sys.path.append(parentDir)
# Standard imports
import argparse
import json, sqlite3
# Local imports
from gen_imgs import convertImage

PICKED_DIR = 'picked'
PICKED_EVT_FILE = 'events.json'
DB_FILE = 'data.db'
IMG_OUT_DIR = 'img'

def genData(pickedDir: str, pickedEvtFile: str, dbFile: str, imgOutDir: str) -> None:
	dbCon = sqlite3.connect(dbFile)
	dbCur = dbCon.cursor()
	#
	with open(os.path.join(pickedDir, pickedEvtFile)) as f:
		eventsToAdd = json.load(f)
	nextId = -1
	for event in eventsToAdd:
		row = dbCur.execute('SELECT id from events where title = ?', (event['title'],)).fetchone()
		if row is not None:
			print(f'WARNING: Event "{event["title"]}" already exists, and will be skipped')
			continue
		print(f'Adding event {event["title"]}')
		print("- Updating 'events'")
		dbCur.execute('INSERT INTO events VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
			(nextId, event['title'], event['start'], event['start_upper'], event['end'], event['end_upper'],
				event['fmt'], event['ctg']))
		print('- Converting image file')
		image = event['image']
		success = convertImage(os.path.join(pickedDir, image['file']), os.path.join(imgOutDir, str(nextId) + '.jpg'))
		if not success:
			break
		print("- Updating 'images'")
		dbCur.execute('INSERT INTO images VALUES (?, ?, ?, ?, ?)',
			(nextId, image['url'], image['license'], image['artist'], image['credit']))
		print("- Updating 'event_imgs'")
		dbCur.execute('INSERT INTO event_imgs VALUES (?, ?)', (nextId, nextId))
		print("- Updating 'descs'")
		dbCur.execute('INSERT INTO descs VALUES (?, ?, ?)', (nextId, nextId, event['desc']))
		print("- Updating 'pop'")
		dbCur.execute('INSERT INTO pop VALUES (?, ?)', (nextId, event['pop']))
		#
		nextId -= 1
	#
	dbCon.commit()
	dbCon.close()

if __name__ == '__main__':
	parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
	args = parser.parse_args()
	#
	genData(PICKED_DIR, PICKED_EVT_FILE, DB_FILE, IMG_OUT_DIR)
