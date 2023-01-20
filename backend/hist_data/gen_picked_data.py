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
from cal import SCALES, dbDateToHistDate, dateToUnit

PICKED_DIR = 'picked'
PICKED_EVT_FILE = 'events.json'
DB_FILE = 'data.db'
IMG_OUT_DIR = 'img'

def genData(pickedDir: str, pickedEvtFile: str, dbFile: str, imgOutDir: str, scales: list[int]) -> None:
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
			# Update image, description, and popularity tables
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
			# Update event distribution tables
			for scale in scales:
				unit = dateToUnit(dbDateToHistDate(event['start'], event['fmt']), scale)
				if dbCur.execute('SELECT count FROM dist WHERE scale = ? AND unit = ?', (scale, unit)).fetchone():
					dbCur.execute('UPDATE dist SET count = count + 1 WHERE scale = ? AND unit = ?', (scale, unit))
				else:
					dbCur.execute('INSERT INTO dist VALUES (?, ?, ?)', (scale, unit, 1))
				dbCur.execute('INSERT INTO event_disp VALUES (?, ?, ?)', (nextId, scale, unit))
			#
			nextId -= 1
		elif doDelete:
			if eventId:
				print(f'Deleting event with ID {eventId}')
				row = dbCur.execute('SELECT id, start, fmt FROM events WHERE id = ?', (eventId,)).fetchone()
			else:
				print(f'Deleting event with title "{title}"')
				row = dbCur.execute('SELECT id, start, fmt FROM events WHERE title = ?', (title,)).fetchone()
				if row is None:
					print(f'ERROR: Could not find event with title {title}')
					break
			eventId, eventStart, eventFmt = row
			# Note: Intentionally not deleting entries or files for images that become unused.
			dbCur.execute('DELETE FROM events WHERE id = ?', (eventId,))
			dbCur.execute('DELETE FROM pop WHERE id = ?', (eventId,))
			dbCur.execute('DELETE FROM descs WHERE id = ?', (eventId,))
			dbCur.execute('DELETE FROM event_imgs WHERE id = ?', (eventId,))
			for scale in scales:
				unit = dateToUnit(dbDateToHistDate(eventStart, eventFmt), scale)
				(oldCount,) = dbCur.execute(
					'SELECT count FROM dist WHERE scale = ? AND unit = ?', (scale, unit)).fetchone()
				if oldCount == 1:
					dbCur.execute('DELETE FROM dist WHERE scale = ? AND unit = ?', (scale, unit))
				else:
					dbCur.execute('UPDATE dist SET count = count - 1 WHERE scale = ? AND unit = ?', (scale, unit))
			dbCur.execute('DELETE FROM event_disp WHERE id = ?', (eventId,))
		else: # doModify
			print(f'Modifying event with ID {eventId}')
			row = dbCur.execute('SELECT start, fmt FROM events WHERE id = ?', (eventId,)).fetchone()
			if row is None:
				print(f'ERROR: Could not find event with ID {eventId}')
				break
			oldStart, oldFmt = row
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
				if dbCur.execute('SELECT img_id FROM event_imgs WHERE id = ?', (eventId,)).fetchone():
					dbCur.execute('UPDATE event_imgs SET img_id = ? WHERE id = ?', (nextId, eventId))
					# Note: Intentionally not deleting entries or files for images that become unused.
				else:
					dbCur.execute('INSERT INTO event_imgs VALUES (?, ?)', (eventId, nextId))
			if 'desc' in event:
				if dbCur.execute('SELECT desc FROM descs WHERE id = ?', (eventId,)).fetchone():
					dbCur.execute('UPDATE event_imgs SET desc = ? WHERE id = ?', (event['desc'], eventId))
				else:
					dbCur.execute('INSERT INTO descs VALUES (?, ?)', (eventId, event['desc']))
			if 'pop' in event:
				if dbCur.execute('SELECT pop FROM pop WHERE id = ?', (eventId,)).fetchone():
					dbCur.execute('UPDATE pop SET pop = ? WHERE id = ?', (event['pop'], eventId))
				else:
					dbCur.execute('INSERT INTO pop VALUES (?, ?)', (eventId, event['pop']))
			if 'start' in event:
				# Remove old distribution data
				for scale in scales:
					unit = dateToUnit(dbDateToHistDate(oldStart, oldFmt), scale)
					(oldCount,) = dbCur.execute(
						'SELECT count FROM dist WHERE scale = ? AND unit = ?', (scale, unit)).fetchone()
					if oldCount == 1:
						dbCur.execute('DELETE FROM dist WHERE scale = ? AND unit = ?', (scale, unit))
					else:
						dbCur.execute('UPDATE dist SET count = count - 1 WHERE scale = ? AND unit = ?', (scale, unit))
				dbCur.execute('DELETE FROM event_disp WHERE id = ?', (eventId,))
				# Add new distribution data
				newFmt = event['fmt'] if 'fmt' in event else oldFmt
				for scale in scales:
					unit = dateToUnit(dbDateToHistDate(event['start'], newFmt), scale)
					if dbCur.execute('SELECT count FROM dist WHERE scale = ? AND unit = ?', (scale, unit)).fetchone():
						dbCur.execute('UPDATE dist SET count = count + 1 WHERE scale = ? AND unit = ?', (scale, unit))
					else:
						dbCur.execute('INSERT INTO dist VALUES (?, ?, ?)', (scale, unit, 1))
					dbCur.execute('INSERT INTO event_disp VALUES (?, ?, ?)', (eventId, scale, unit))
			# Note: Intentionally not updating 'event_disp' table to account for 'indirect event displayability'
			nextId -= 1
	#
	dbCon.commit()
	dbCon.close()

if __name__ == '__main__':
	parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
	args = parser.parse_args()
	#
	genData(PICKED_DIR, PICKED_EVT_FILE, DB_FILE, IMG_OUT_DIR, SCALES)
