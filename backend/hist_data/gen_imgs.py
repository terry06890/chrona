#!/usr/bin/python3

"""
Looks at images described by a database, and generates resized/cropped versions
into an output directory, with names of the form 'eventId1.jpg'.
Adds the image associations and metadata to the history database.

SIGINT can be used to stop, and the program can be re-run to continue
processing. It uses already-existing database entries to decide what
to skip.
"""

import argparse
import os, math, subprocess, signal
import sqlite3, urllib.parse
from PIL import Image

IMG_DIR = os.path.join('enwiki', 'imgs')
IMG_DB = os.path.join('enwiki', 'img_data.db')
OUT_DIR = 'img'
DB_FILE = 'data.db'
#
MAX_MINOR_DIM = 200
MAX_DIM_RATIO = 3/2

def genImgs(imgDir: str, imgDb: str, outDir: str, dbFile: str):
	""" Converts images and updates db, checking for entries to skip """
	if not os.path.exists(outDir):
		os.mkdir(outDir)
	dbCon = sqlite3.connect(dbFile)
	dbCur = dbCon.cursor()
	#
	print('Checking for image tables')
	eventsDone: set[int] = set()
	imgsDone: set[int] = set()
	if dbCur.execute('SELECT name FROM sqlite_master WHERE type="table" AND name="event_imgs"').fetchone() is None:
		# Add image tables
		dbCur.execute('CREATE TABLE event_imgs (id INT PRIMARY KEY, img_id INT)')
		dbCur.execute('CREATE TABLE images (id INT PRIMARY KEY, url TEXT, license TEXT, artist TEXT, credit TEXT)')
	else:
		# Get existing image-associated events
		for (eventId,) in dbCur.execute('SELECT id FROM event_imgs'):
			eventsDone.add(eventId)
		# Get existing event-associated images
		for (imgId,) in dbCur.execute('SELECT id from images'):
			imgsDone.add(imgId)
		print(f'Found {len(eventsDone)} events and {len(imgsDone)} images to skip')
	#
	print('Processing images from eol and enwiki')
	processImgs(imgDir, imgDb, outDir, dbCur, eventsDone, imgsDone)
	#
	dbCon.commit()
	dbCon.close()
def processImgs(imgDir: str, imgDb: str, outDir: str, dbCur: sqlite3.Cursor,
		eventsDone: set[int], imgsDone: set[int]) -> bool:
	""" Converts images and updates db, returning False upon interruption or failure """
	imgDbCon = sqlite3.connect(imgDb)
	imgDbCur = imgDbCon.cursor()
	# Set SIGINT handler
	interrupted = False
	def onSigint(sig, frame):
		nonlocal interrupted
		interrupted = True
	signal.signal(signal.SIGINT, onSigint)
	# Convert images
	flag = False # Set to True upon interruption or failure
	for imgFile in os.listdir(imgDir):
		# Check for SIGINT event
		if interrupted:
			print('Exiting')
			flag = True
			break
		# Get image ID
		imgIdStr, _ = os.path.splitext(imgFile)
		imgId = int(imgIdStr)
		# Get associated events
		eventIds: set[int] = set()
		query = 'SELECT title FROM page_imgs INNER JOIN imgs ON page_imgs.img_name = imgs.name WHERE imgs.id = ?'
		for (title,) in imgDbCur.execute(query, (imgId,)):
			row = dbCur.execute('SELECT id FROM events WHERE title = ?', (title,)).fetchone()
			if row is None:
				print('ERROR: No event ID found for title {title} associated with image {imgFile}')
				continue
			eventIds.add(row[0])
		eventIds = eventIds.difference(eventsDone)
		if not eventIds:
			continue
		# Convert image
		if imgId not in imgsDone:
			success = convertImage(os.path.join(imgDir, imgFile), os.path.join(outDir, str(imgId) + '.jpg'))
			if not success:
				flag = True
				break
		# Add entry to db
		if imgId not in imgsDone:
			row = imgDbCur.execute('SELECT name, license, artist, credit FROM imgs WHERE id = ?', (imgId,)).fetchone()
			if row is None:
				print(f'ERROR: No image record for ID {imgId}')
				flag = True
				break
			name, license, artist, credit = row
			url = 'https://en.wikipedia.org/wiki/File:' + urllib.parse.quote(name)
			dbCur.execute('INSERT INTO images VALUES (?, ?, ?, ?, ?)', (imgId, url, license, artist, credit))
		for eventId in eventIds:
			dbCur.execute('INSERT INTO event_imgs VALUES (?, ?)', (eventId, imgId))
	imgDbCon.close()
	return not flag
def convertImage(imgPath: str, outPath: str):
	print(f'Converting {imgPath} to {outPath}')
	if os.path.exists(outPath):
		print('ERROR: Output image already exists')
		return False
	# Get image dims
	width: int
	height: int
	try:
		with Image.open(imgPath) as image:
			width, height = image.size
	except Exception as e: # Being more specific runs the risk of ending the program without committing to db
		print(f'ERROR: Unable to open {imgPath}: {e}')
		return False
	# Limit output dims
	if width > height:
		if height > MAX_MINOR_DIM:
			width = math.ceil(width * height / MAX_MINOR_DIM)
			height = MAX_MINOR_DIM
		if width / height > MAX_DIM_RATIO:
			width = math.ceil(height * MAX_DIM_RATIO)
	else:
		if width > MAX_MINOR_DIM:
			height = math.ceil(height * width / MAX_MINOR_DIM)
			width = MAX_MINOR_DIM
		if height / width > MAX_DIM_RATIO:
			height = math.ceil(width * MAX_DIM_RATIO)
	# Convert image
	try:
		completedProcess = subprocess.run(
			['npx', 'smartcrop-cli', '--width', str(width), '--height', str(height), imgPath, outPath],
			stdout=subprocess.DEVNULL
		)
	except Exception as e:
		print(f'ERROR: Exception while attempting to run smartcrop: {e}')
		return False
	if completedProcess.returncode != 0:
		print(f'ERROR: smartcrop had exit status {completedProcess.returncode}')
		return False
	return True

if __name__ == '__main__':
	parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
	parser.parse_args()
	#
	genImgs(IMG_DIR, IMG_DB, OUT_DIR, DB_FILE)
