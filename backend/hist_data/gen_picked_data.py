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
		eventId = event['id'] if 'id' in event else None
		title = event['title'] if 'title' in event else None
		if eventId is None and title is None:
			print(f'ERROR: Entry with no ID or title: {event}')
			break
		#
		doAdd = eventId is None and len(event) > 1
		doModify = eventId is not None and len(event) > 1
		doDelete = not doModify and not doAdd
		if doAdd:
			print(f'Adding event with title "{title}"')
			dbCur.execute('INSERT INTO events VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
				(nextId, event['title'], event['start'], event['start_upper'], event['end'], event['end_upper'],
					event['fmt'], event['ctg']))
			if 'image' in event:
				print('> Adding image')
				image = event['image']
				outFile = os.path.join(imgOutDir, str(nextId) + '.jpg')
				success = convertImage(os.path.join(pickedDir, image['file']), outFile)
				if not success:
					print('ERROR: Conversion failed')
					break
				dbCur.execute('INSERT INTO images VALUES (?, ?, ?, ?, ?)',
					(nextId, image['url'], image['license'], image['artist'], image['credit']))
				dbCur.execute('INSERT INTO event_imgs VALUES (?, ?)', (nextId, nextId))
			if 'desc' in event:
				dbCur.execute('INSERT INTO descs VALUES (?, ?, ?)', (nextId, nextId, event['desc']))
			dbCur.execute('INSERT INTO pop VALUES (?, ?)', (nextId, event['pop']))
			nextId -= 1
		elif doDelete:
			if eventId:
				print(f'Deleting event with ID {eventId}')
			else:
				print(f'Deleting event with title "{title}"')
				row = dbCur.execute('SELECT id FROM events WHERE title = ?', (title,)).fetchone()
				if row is None:
					print(f'ERROR: Could not find event with title {title}')
					break
				eventId = row[0]
			dbCur.execute('DELETE FROM events WHERE id = ?', (eventId,))
			dbCur.execute('DELETE FROM pop WHERE id = ?', (eventId,))
			dbCur.execute('DELETE FROM descs WHERE id = ?', (eventId,))
			dbCur.execute('DELETE FROM event_imgs WHERE id = ?', (eventId,))
			# Note: Intentionally not deleting entries or files for images that become unused.
		else: # doModify
			print(f'Modifying event with ID {eventId}')
			if dbCur.execute('SELECT id FROM events WHERE id = ?', (eventId,)).fetchone() is None:
				print(f'ERROR: Could not find event with ID {eventId}')
				break
			for field in ['title', 'start', 'start_upper', 'end', 'end_upper', 'fmt', 'ctg']:
				if field in event:
					dbCur.execute(f'UPDATE events SET {field} = ? WHERE id = ?', (event[field], eventId,))
			if 'image' in event:
				print('> Adding image')
				image = event['image']
				outFile = os.path.join(imgOutDir, str(nextId) + '.jpg')
				success = convertImage(os.path.join(pickedDir, image['file']), outFile)
				if not success:
					print('ERROR: Conversion failed')
					break
				dbCur.execute('INSERT INTO images VALUES (?, ?, ?, ?, ?)',
					(nextId, image['url'], image['license'], image['artist'], image['credit']))
				row = dbCur.execute('SELECT img_id FROM event_imgs WHERE id = ?', (eventId,)).fetchone()
				if row is None:
					dbCur.execute('INSERT INTO event_imgs VALUES (?, ?)', (eventId, nextId))
				else:
					dbCur.execute('UPDATE event_imgs SET img_id = ? WHERE id = ?', (nextId, eventId))
					# Note: Intentionally not deleting entries or files for images that become unused.
			if 'desc' in event:
				row = dbCur.execute('SELECT desc FROM descs WHERE id = ?', (eventId,)).fetchone()
				if row is None:
					dbCur.execute('INSERT INTO descs VALUES (?, ?)', (eventId, event['desc']))
				else:
					dbCur.execute('UPDATE event_imgs SET desc = ? WHERE id = ?', (event['desc'], eventId))
			if 'pop' in event:
				row = dbCur.execute('SELECT pop FROM pop WHERE id = ?', (eventId,)).fetchone()
				if row is None:
					dbCur.execute('INSERT INTO pop VALUES (?, ?)', (eventId, event['pop']))
				else:
					dbCur.execute('UPDATE pop SET pop = ? WHERE id = ?', (event['pop'], eventId))
			nextId -= 1
	#
	dbCon.commit()
	dbCon.close()

if __name__ == '__main__':
	parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
	args = parser.parse_args()
	#
	genData(PICKED_DIR, PICKED_EVT_FILE, DB_FILE, IMG_OUT_DIR)
