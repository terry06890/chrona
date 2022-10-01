"""
Utilities for testing
"""

from typing import Any
import bz2, gzip, sqlite3

def createTestFile(filename: str, content: str) -> None:
	""" Creates a file with the given name and contents """
	with open(filename, 'w') as file:
		file.write(content)

def readTestFile(filename: str) -> str:
	""" Returns the contents of a file with the given name """
	with open(filename) as file:
		return file.read()

def createTestBz2(filename: str, content: str) -> None:
	""" Creates a bzip2 file with the given name and contents """
	with bz2.open(filename, mode='wb') as file:
		file.write(content.encode())

def createTestGzip(filename: str, content: str) -> None:
	""" Creates a gzip file with the given name and contents """
	with gzip.open(filename, mode='wt') as file:
		file.write(content)

TableRows = set[tuple[Any, ...]]
def createTestDbTable(filename: str, createCmd: str | None, insertCmd: str, rows: TableRows) -> None:
	""" Creates an sqlite db with a table specified by creation+insertion commands and records.
		If 'createCmd' is None, just insert into an existing table."""
	dbCon = sqlite3.connect(filename)
	dbCur = dbCon.cursor()
	if createCmd is not None:
		dbCur.execute(createCmd)
	for row in rows:
		dbCur.execute(insertCmd, row)
	dbCon.commit()
	dbCon.close()

def readTestDbTable(filename: str, selectCmd: str) -> TableRows:
	""" Returns the records in a sqlite db with the given name, using the given select command """
	rows: set[tuple[Any, ...]] = set()
	dbCon = sqlite3.connect(filename)
	dbCur = dbCon.cursor()
	for row in dbCur.execute(selectCmd):
		rows.add(row)
	dbCon.close()
	return rows
