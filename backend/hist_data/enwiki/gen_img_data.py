#!/usr/bin/python3

"""
For some set of page IDs, looks up their content in the wiki dump,
and tries to parse infobox image names, storing them into a database.

The program can be re-run with an updated set of page IDs, and
will skip already-processed page IDs.
"""

import argparse
import os
import re
import bz2
import html
import urllib.parse
import sqlite3

DUMP_FILE = 'enwiki-20220501-pages-articles-multistream.xml.bz2'
INDEX_DB = 'dump_index.db'
IMG_DB = 'img_data.db' # The database to create
DB_FILE = os.path.join('..', 'data.db')

ID_LINE_REGEX = re.compile(r'<id>(.*)</id>')
IMG_LINE_REGEX = re.compile(r'.*\| *image *= *([^|]*)')
BRACKET_IMG_REGEX = re.compile(r'\[\[(File:[^|]*).*]]')
IMG_NAME_REGEX = re.compile(r'.*\.(jpg|jpeg|png|gif|tiff|tif)', flags=re.IGNORECASE)
CSS_IMG_CROP_REGEX = re.compile(r'{{css image crop\|image *= *(.*)', flags=re.IGNORECASE)

# ========== For data generation ==========

def genData(pageIds: set[int], dumpFile: str, indexDb: str, imgDb: str) -> None:
	""" Looks up page IDs in dump and creates database """
	print('Opening databases')
	indexDbCon = sqlite3.connect(indexDb)
	indexDbCur = indexDbCon.cursor()
	imgDbCon = sqlite3.connect(imgDb)
	imgDbCur = imgDbCon.cursor()

	print('Checking tables')
	if imgDbCur.execute('SELECT name FROM sqlite_master WHERE type="table" AND name="page_imgs"').fetchone() is None:
		# Create tables if not present
		imgDbCur.execute('CREATE TABLE page_imgs (page_id INT PRIMARY KEY, title TEXT UNIQUE, img_name TEXT)')
			# 'img_name' values are set to NULL to indicate page IDs where no image was found
		imgDbCur.execute('CREATE INDEX page_imgs_idx ON page_imgs(img_name)')
	else: # Check for already-processed page IDs
		numSkipped = 0
		for (pid,) in imgDbCur.execute('SELECT page_id FROM page_imgs'):
			if pid in pageIds:
				pageIds.remove(pid)
				numSkipped += 1
			else:
				print(f'Found already-processed page ID {pid} which was not in input set')
		print(f'Will skip {numSkipped} already-processed page IDs')

	print('Getting dump-file offsets')
	offsetToPageId: dict[int, list[int]] = {}
	offsetToEnd: dict[int, int] = {} # Maps chunk-start offsets to their chunk-end offsets
	pageIdToTitle: dict[int, str] = {}
	iterNum = 0
	for pageId in pageIds:
		iterNum += 1
		if iterNum % 1e4 == 0:
			print(f'At iteration {iterNum}')

		query = 'SELECT offset, next_offset, title FROM offsets WHERE id = ?'
		row = indexDbCur.execute(query, (pageId,)).fetchone()
		if row is None:
			print(f'WARNING: Page ID {pageId} not found')
			continue
		chunkOffset, endOffset, title = row
		offsetToEnd[chunkOffset] = endOffset
		if chunkOffset not in offsetToPageId:
			offsetToPageId[chunkOffset] = []
		offsetToPageId[chunkOffset].append(pageId)
		pageIdToTitle[pageId] = title
	print(f'Found {len(offsetToEnd)} chunks to check')

	print('Iterating through chunks in dump file')
	with open(dumpFile, mode='rb') as file:
		iterNum = 0
		for pageOffset, endOffset in offsetToEnd.items():
			iterNum += 1
			if iterNum % 100 == 0:
				print(f'At iteration {iterNum}')

			chunkPageIds = offsetToPageId[pageOffset]
			# Jump to chunk
			file.seek(pageOffset)
			compressedData = file.read(None if endOffset == -1 else endOffset - pageOffset)
			data = bz2.BZ2Decompressor().decompress(compressedData).decode()
			# Look in chunk for pages
			lines = data.splitlines()
			lineIdx = 0
			while lineIdx < len(lines):
				# Look for <page>
				if lines[lineIdx].lstrip() != '<page>':
					lineIdx += 1
					continue
				# Check page id
				lineIdx += 3
				idLine = lines[lineIdx].lstrip()
				match = ID_LINE_REGEX.fullmatch(idLine)
				if match is None or int(match.group(1)) not in chunkPageIds:
					lineIdx += 1
					continue
				pageId = int(match.group(1))
				lineIdx += 1
				# Look for <text> in <page>
				foundText = False
				while lineIdx < len(lines):
					if not lines[lineIdx].lstrip().startswith('<text '):
						lineIdx += 1
						continue
					foundText = True
					# Get text content
					content: list[str] = []
					line = lines[lineIdx]
					content.append(line[line.find('>') + 1:])
					lineIdx += 1
					foundTextEnd = False
					while lineIdx < len(lines):
						line = lines[lineIdx]
						if not line.endswith('</text>'):
							content.append(line)
							lineIdx += 1
							continue
						foundTextEnd = True
						content.append(line[:line.rfind('</text>')])
						# Look for image-filename
						imageName = getImageName(content)
						imgDbCur.execute(
							'INSERT into page_imgs VALUES (?, ?, ?)',
							(pageId, None if imageName is None else pageIdToTitle[pageId], imageName))
						break
					if not foundTextEnd:
						print(f'WARNING: Did not find </text> for page id {pageId}')
					break
				if not foundText:
					print(f'WARNING: Did not find <text> for page id {pageId}')

	print('Closing databases')
	indexDbCon.close()
	imgDbCon.commit()
	imgDbCon.close()

def getImageName(content: list[str]) -> str | None:
	""" Given an array of text-content lines, tries to return an infoxbox image name, or None """
	# Note: Doesn't try and find images in outside-infobox [[File:...]] and <imagemap> sections
	for line in content:
		match = IMG_LINE_REGEX.match(line)
		if match is not None:
			imageName = match.group(1).strip()
			if imageName == '':
				return None
			imageName = html.unescape(imageName)
			# Account for {{...
			if imageName.startswith('{'):
				match = CSS_IMG_CROP_REGEX.match(imageName)
				if match is None:
					return None
				imageName = match.group(1)
			# Account for [[File:...|...]]
			if imageName.startswith('['):
				match = BRACKET_IMG_REGEX.match(imageName)
				if match is None:
					return None
				imageName = match.group(1)
			# Account for <!--
			if imageName.find('<!--') != -1:
				return None
			# Remove an initial 'File:'
			if imageName.startswith('File:'):
				imageName = imageName[5:]
			# Remove an initial 'Image:'
			if imageName.startswith('Image:'):
				imageName = imageName[6:]
			# Check for extension
			match = IMG_NAME_REGEX.match(imageName)
			if match is not None:
				imageName = match.group(0)
				imageName = urllib.parse.unquote(imageName)
				imageName = html.unescape(imageName) # Intentionally unescaping again (handles some odd cases)
				imageName = imageName.replace('_', ' ')
				return imageName
			# Exclude lines like: | image = &lt;imagemap&gt;
			return None
	return None

# ========== For getting input page IDs ==========

def getInputPageIdsFromDb(dbFile: str, indexDb: str) -> set[int]:
	print('Getting event data')
	titles: set[str] = set()
	dbCon = sqlite3.connect(dbFile)
	for (title,) in dbCon.execute('SELECT title from events'):
		titles.add(title)
	dbCon.close()

	print('Getting page IDs')
	pageIds: set[int] = set()
	dbCon = sqlite3.connect(indexDb)
	dbCur = dbCon.cursor()
	for title in titles:
		row = dbCur.execute('SELECT id FROM offsets WHERE title = ?', (title,)).fetchone()
		if row:
			pageIds.add(row[0])
	dbCon.close()

	print(f'Result: {len(pageIds)} out of {len(titles)}')
	return pageIds

# ========== Main block ==========

if __name__ == '__main__':
	parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
	parser.parse_args()

	pageIds = getInputPageIdsFromDb(DB_FILE, INDEX_DB)
	genData(pageIds, DUMP_FILE, INDEX_DB, IMG_DB)
