#!/usr/bin/python3

"""
Reads image names from a database, and uses enwiki's online API to obtain
licensing information for them, adding the info to the database.

SIGINT causes the program to finish an ongoing download and exit.
The program can be re-run to continue downloading, and looks
at already-processed names to decide what to skip.
"""

import re
import sqlite3, urllib.parse, html
import requests
import time, signal

IMG_DB = 'img_data.db'
#
API_URL = 'https://en.wikipedia.org/w/api.php'
USER_AGENT = 'terryt.dev (terry06890@gmail.com)'
BATCH_SZ = 50 # Max 50
TAG_REGEX = re.compile(r'<[^<]+>')
WHITESPACE_REGEX = re.compile(r'\s+')

def downloadInfo(imgDb: str) -> None:
	print('Opening database')
	dbCon = sqlite3.connect(imgDb)
	dbCur = dbCon.cursor()
	print('Checking for table')
	if dbCur.execute('SELECT name FROM sqlite_master WHERE type="table" AND name="imgs"').fetchone() is None:
		dbCur.execute('CREATE TABLE imgs (id INT PRIMARY KEY, name TEXT UNIQUE, ' \
			'license TEXT, artist TEXT, credit TEXT, restrictions TEXT, url TEXT)')
	#
	print('Reading image names')
	imgNames: set[str] = set()
	for (imgName,) in dbCur.execute('SELECT DISTINCT img_name FROM page_imgs WHERE img_name NOT NULL'):
		imgNames.add(imgName)
	print(f'Found {len(imgNames)}')
	#
	print('Checking for already-processed images')
	nextImgId = 1
	oldSz = len(imgNames)
	for (imgId, imgName,) in dbCur.execute('SELECT id, name FROM imgs'):
		imgNames.discard(imgName)
		if imgId >= nextImgId:
			nextImgId = imgId + 1
	print(f'Found {oldSz - len(imgNames)}')
	#
	# Set SIGINT handler
	interrupted = False
	oldHandler = None
	def onSigint(sig, frame):
		nonlocal interrupted
		interrupted = True
		signal.signal(signal.SIGINT, oldHandler)
	oldHandler = signal.signal(signal.SIGINT, onSigint)
	#
	print('Iterating through image names')
	imgNameList = list(imgNames)
	iterNum = 0
	for i in range(0, len(imgNameList), BATCH_SZ):
		iterNum += 1
		if iterNum % 1 == 0:
			print(f'At iteration {iterNum} (after {(iterNum - 1) * BATCH_SZ} images)')
		if interrupted:
			print(f'Exiting loop at iteration {iterNum}')
			break
		# Get batch
		imgBatch = imgNameList[i:i+BATCH_SZ]
		imgBatch = ['File:' + x for x in imgBatch]
		# Make request
		headers = {
			'user-agent': USER_AGENT,
			'accept-encoding': 'gzip',
		}
		params = {
			'action': 'query',
			'format': 'json',
			'prop': 'imageinfo',
			'iiprop': 'extmetadata|url',
			'maxlag': '5',
			'titles': '|'.join(imgBatch),
			'iiextmetadatafilter': 'Artist|Credit|LicenseShortName|Restrictions',
		}
		responseObj = None
		try:
			response = requests.get(API_URL, params=params, headers=headers)
			responseObj = response.json()
		except Exception as e:
			print(f'ERROR: Exception while downloading info: {e}')
			print('\tImage batch: ' + '|'.join(imgBatch))
			continue
		# Parse response-object
		if 'query' not in responseObj or 'pages' not in responseObj['query']:
			print('WARNING: Response object doesn\'t have page data')
			print('\tImage batch: ' + '|'.join(imgBatch))
			if 'error' in responseObj:
				errorCode = responseObj['error']['code']
				print(f'\tError code: {errorCode}')
				if errorCode == 'maxlag':
					time.sleep(5)
			continue
		pages = responseObj['query']['pages']
		normalisedToInput: dict[str, str] = {}
		if 'normalized' in responseObj['query']:
			for entry in responseObj['query']['normalized']:
				normalisedToInput[entry['to']] = entry['from']
		for page in pages.values():
			# Some fields // More info at https://www.mediawiki.org/wiki/Extension:CommonsMetadata#Returned_data
				# LicenseShortName: short human-readable license name, apparently more reliable than 'License',
				# Artist: author name (might contain complex html, multiple authors, etc)
				# Credit: 'source'
					# For image-map-like images, can be quite large/complex html, creditng each sub-image
					# May be <a href='text1'>text2</a>, where the text2 might be non-indicative
				# Restrictions: specifies non-copyright legal restrictions
			title: str = page['title']
			if title in normalisedToInput:
				title = normalisedToInput[title]
			title = title[5:] # Remove 'File:'
			if title not in imgNames:
				print(f'WARNING: Got title "{title}" not in image-name list')
				continue
			if 'imageinfo' not in page:
				print(f'WARNING: No imageinfo section for page "{title}"')
				continue
			metadata = page['imageinfo'][0]['extmetadata']
			url: str = page['imageinfo'][0]['url']
			license: str | None = metadata['LicenseShortName']['value'] if 'LicenseShortName' in metadata else None
			artist: str | None = metadata['Artist']['value'] if 'Artist' in metadata else None
			credit: str | None = metadata['Credit']['value'] if 'Credit' in metadata else None
			restrictions: str | None = metadata['Restrictions']['value'] if 'Restrictions' in metadata else None
			# Remove markup
			if artist is not None:
				artist = TAG_REGEX.sub(' ', artist).strip()
				artist = WHITESPACE_REGEX.sub(' ', artist)
				artist = html.unescape(artist)
				artist = urllib.parse.unquote(artist)
			if credit is not None:
				credit = TAG_REGEX.sub(' ', credit).strip()
				credit = WHITESPACE_REGEX.sub(' ', credit)
				credit = html.unescape(credit)
				credit = urllib.parse.unquote(credit)
			# Add to db
			dbCur.execute('INSERT INTO imgs VALUES (?, ?, ?, ?, ?, ?, ?)',
				(nextImgId, title, license, artist, credit, restrictions, url))
			nextImgId += 1
	#
	print('Closing database')
	dbCon.commit()
	dbCon.close()

if __name__ == '__main__':
	import argparse
	parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
	parser.parse_args()
	#
	downloadInfo(IMG_DB)
