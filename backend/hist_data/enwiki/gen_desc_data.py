#!/usr/bin/python3

"""
Reads through the wiki dump, attempts to parse short-descriptions,
and adds them to a database
"""

# Note: In testing, this script took over 10 hours to run, and generated about 5GB

import argparse
import sys
import os
import re
import sqlite3
import bz2
import html

import mwxml
import mwparserfromhell

DUMP_FILE = 'enwiki-20220501-pages-articles-multistream.xml.bz2' # Had about 22e6 pages
DB_FILE = 'desc_data.db'

DESC_LINE_REGEX = re.compile('^ *[A-Z\'"]')
EMBEDDED_HTML_REGEX = re.compile(r'<[^<]+/>|<!--[^<]+-->|<[^</]+>([^<]*|[^<]*<[^<]+>[^<]*)</[^<]+>|<[^<]+$')
	# Recognises a self-closing HTML tag, a tag with 0 children, tag with 1 child with 0 children, or unclosed tag
CONVERT_TEMPLATE_REGEX = re.compile(r'{{convert\|(\d[^|]*)\|(?:(to|-)\|(\d[^|]*)\|)?([a-z][^|}]*)[^}]*}}')
PARENS_GROUP_REGEX = re.compile(r' \([^()]*\)')
LEFTOVER_BRACE_REGEX = re.compile(r'(?:{\||{{).*')

def convertTemplateReplace(match):
	""" Used in regex-substitution with CONVERT_TEMPLATE_REGEX """
	if match.group(2) is None:
		return f'{match.group(1)} {match.group(4)}'
	else:
		return f'{match.group(1)} {match.group(2)} {match.group(3)} {match.group(4)}'

# ========== For data generation ==========

def genData(dumpFile: str, dbFile: str) -> None:
	""" Reads dump, parses descriptions, and writes to db """
	print('Creating database')
	if os.path.exists(dbFile):
		raise Exception(f'ERROR: Existing {dbFile}')
	dbCon = sqlite3.connect(dbFile)
	dbCur = dbCon.cursor()
	dbCur.execute('CREATE TABLE pages (id INT PRIMARY KEY, title TEXT UNIQUE)')
	dbCur.execute('CREATE INDEX pages_title_idx ON pages(title COLLATE NOCASE)')
	dbCur.execute('CREATE TABLE redirects (id INT PRIMARY KEY, target TEXT)')
	dbCur.execute('CREATE INDEX redirects_idx ON redirects(target)')
	dbCur.execute('CREATE TABLE descs (id INT PRIMARY KEY, desc TEXT)')

	print('Iterating through dump file')
	with bz2.open(dumpFile, mode='rt') as file:
		for pageNum, page in enumerate(mwxml.Dump.from_file(file), 1):
			if pageNum % 1e4 == 0:
				print(f'At page {pageNum}')

			if page.namespace == 0:
				try:
					dbCur.execute('INSERT INTO pages VALUES (?, ?)', (page.id, convertTitle(page.title)))
				except sqlite3.IntegrityError as e:
					# Accounts for certain pages that have the same title
					print(f'Failed to add page with title "{page.title}": {e}', file=sys.stderr)
					continue
				if page.redirect is not None:
					dbCur.execute('INSERT INTO redirects VALUES (?, ?)', (page.id, convertTitle(page.redirect)))
				else:
					revision = next(page)
					desc = parseDesc(revision.text)
					if desc is not None:
						dbCur.execute('INSERT INTO descs VALUES (?, ?)', (page.id, desc))

	print('Closing database')
	dbCon.commit()
	dbCon.close()

def parseDesc(text: str) -> str | None:
	"""
	Looks for a description in wikitext content.

	Finds first matching line outside {{...}}, [[...]], and block-html-comment constructs,
	and then accumulates lines until a blank one.

	Some cases not accounted for include:
		disambiguation pages, abstracts with sentences split-across-lines, 
		nested embedded html, 'content significant' embedded-html, markup not removable with mwparsefromhell, 
	"""
	lines: list[str] = []
	openBraceCount = 0
	openBracketCount = 0
	inComment = False
	skip = False
	for line in text.splitlines():
		line = line.strip()
		if not lines:
			if line:
				if openBraceCount > 0 or line[0] == '{':
					openBraceCount += line.count('{')
					openBraceCount -= line.count('}')
					skip = True
				if openBracketCount > 0 or line[0] == '[':
					openBracketCount += line.count('[')
					openBracketCount -= line.count(']')
					skip = True
				if inComment or line.find('<!--') != -1:
					if line.find('-->') != -1:
						if inComment:
							inComment = False
							skip = True
					else:
						inComment = True
						skip = True
				if skip:
					skip = False
					continue
				if line[-1] == ':': # Seems to help avoid disambiguation pages
					return None
				if DESC_LINE_REGEX.match(line) is not None:
					lines.append(line)
		else:
			if not line:
				return removeMarkup(' '.join(lines))
			lines.append(line)
	if lines:
		return removeMarkup(' '.join(lines))
	return None

def removeMarkup(content: str) -> str:
	""" Tries to remove markup from wikitext content """
	content = EMBEDDED_HTML_REGEX.sub('', content)
	content = CONVERT_TEMPLATE_REGEX.sub(convertTemplateReplace, content)
	content = mwparserfromhell.parse(content).strip_code() # Remove wikitext markup
	content = PARENS_GROUP_REGEX.sub('', content)
	content = LEFTOVER_BRACE_REGEX.sub('', content)
	return content

def convertTitle(title: str) -> str:
	""" Replaces underscores in wiki item title """
	return html.unescape(title).replace('_', ' ')

# ========== Main block ==========

if __name__ == '__main__':
	parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
	parser.parse_args()

	genData(DUMP_FILE, DB_FILE)
