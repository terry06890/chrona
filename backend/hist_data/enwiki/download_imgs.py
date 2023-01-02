#!/usr/bin/python3

"""
Downloads images from URLs in an image database, into an output directory,
with names of the form 'imgId1.ext1'.

SIGINT causes the program to finish an ongoing download and exit.
The program can be re-run to continue downloading, and looks
in the output directory do decide what to skip.
"""

import argparse
import re, os, time, signal
import sqlite3
import urllib.parse, requests

IMG_DB = 'img_data.db' # About 130k image names
OUT_DIR = 'imgs'
#
LICENSE_REGEX = re.compile(r'cc0|cc([ -]by)?([ -]sa)?([ -][1234]\.[05])?( \w\w\w?)?', flags=re.IGNORECASE)
USER_AGENT = 'terryt.dev (terry06890@gmail.com)'
TIMEOUT = 1
	# https://en.wikipedia.org/wiki/Wikipedia:Database_download says to 'throttle to 1 cache miss per sec'
	# It's unclear how to properly check for cache misses, so we just aim for 1 per sec
EXP_BACKOFF = False # If True, double the timeout each time a download error occurs (otherwise just exit)

def downloadImgs(imgDb: str, outDir: str, timeout: int) -> None:
	if not os.path.exists(outDir):
		os.mkdir(outDir)
	print('Checking for already-downloaded images')
	fileList = os.listdir(outDir)
	imgIdsDone: set[int] = set()
	for filename in fileList:
		imgIdsDone.add(int(os.path.splitext(filename)[0]))
	print(f'Found {len(imgIdsDone)}')
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
	print('Opening database')
	dbCon = sqlite3.connect(imgDb)
	dbCur = dbCon.cursor()
	print('Starting downloads')
	iterNum = 0
	query = 'SELECT id, license, artist, credit, restrictions, url FROM imgs'
	for imgId, license, artist, credit, restrictions, url in dbCur.execute(query):
		if imgId in imgIdsDone:
			continue
		if interrupted:
			print('Exiting loop')
			break
		# Check for problematic attributes
		if license is None or LICENSE_REGEX.fullmatch(license) is None:
			continue
		if artist is None or artist == '' or len(artist) > 100 or re.match(r'(\d\. )?File:', artist) is not None:
			continue
		if credit is None or len(credit) > 300 or re.match(r'File:', credit) is not None:
			continue
		if restrictions is not None and restrictions != '':
			continue
		# Download image
		iterNum += 1
		print(f'Iteration {iterNum}: Downloading for image ID {imgId}')
		urlParts = urllib.parse.urlparse(url)
		extension = os.path.splitext(urlParts.path)[1]
		if len(extension) <= 1:
			print(f'WARNING: No filename extension found in URL {url}')
			continue
		outFile = os.path.join(outDir, f'{imgId}{extension}')
		headers = {
			'user-agent': USER_AGENT,
			'accept-encoding': 'gzip',
		}
		try:
			response = requests.get(url, headers=headers)
			with open(outFile, 'wb') as file:
				file.write(response.content)
			time.sleep(timeout)
		except Exception as e:
			print(f'Error while downloading to {outFile}: {e}')
			if not EXP_BACKOFF:
				return
			else:
				timeout *= 2
				print(f'New timeout: {timeout}')
				continue
	print('Closing database')
	dbCon.close()

if __name__ == '__main__':
	parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
	parser.parse_args()
	#
	downloadImgs(IMG_DB, OUT_DIR, TIMEOUT)
