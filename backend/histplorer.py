"""
WSGI script that serves historical data.

Expected HTTP query parameters:
- type:
	If 'events', reply with information on events within a date range, for a given scale
	If 'info', reply with information about a given event
	If 'sugg', reply with search suggestions for an event search string
- range: With type=events, specifies a historical-date range
	If absent, the default is 'all of time'.
	Examples:
		range=1000.1910-10-09 means '1000 AD up to and excluding 09/10/1910'
		range=-13000. means '13000 BC onwards'
- scale: With type=events, specifies a date scale
- incl: With type=events, specifies an event to include, as an event ID
- event: With type=info, specifies the event title to get info for
- input: With type=sugg, specifies a search string to suggest for
- limit: With type=events or type=sugg, specifies the max number of results
- ctg: With type=events or type=sugg, specifies an event category to restrict results to
"""

from typing import Iterable
import sys, re
import urllib.parse, sqlite3
import gzip, jsonpickle
from hist_data.cal import HistDate, dbDateToHistDate, dateToUnit

DB_FILE = 'hist_data/data.db'
MAX_REQ_EVENTS = 500
MAX_REQ_UNIT_COUNTS = MAX_REQ_EVENTS
DEFAULT_REQ_EVENTS = 20
MAX_REQ_SUGGS = 50
DEFAULT_REQ_SUGGS = 5

# Classes for values sent as responses
class Event:
	""" Represents an historical event """
	def __init__(
			self,
			id: int,
			title: str,
			start: HistDate,
			startUpper: HistDate | None,
			end: HistDate | None,
			endUpper: HistDate | None,
			ctg: str,
			imgId: int,
			pop: int):
		self.id = id
		self.title = title
		self.start = start
		self.startUpper = startUpper
		self.end = end
		self.endUpper = endUpper
		self.ctg = ctg
		self.imgId = imgId
		self.pop = pop
	# Used in unit testing
	def __eq__(self, other):
		return isinstance(other, Event) and \
			(self.id, self.title, self.start, self.startUpper, self.end, self.endUpper, \
				self.ctg, self.pop, self.imgId) == \
			(other.id, other.title, other.start, other.startUpper, other.end, other.endUpper, \
				other.ctg, other.pop, other.imgId)
	def __repr__(self):
		return str(self.__dict__)
class EventResponse:
	""" Used when responding to type=events requests """
	def __init__(self, events: list[Event], unitCounts: dict[int, int] | None):
		self.events = events
		self.unitCounts = unitCounts # None indicates exceeding MAX_REQ_UNIT_COUNTS
	# Used in unit testing
	def __eq__(self, other):
		return isinstance(other, EventResponse) and \
			(self.events, self.unitCounts) == (other.events, other.unitCounts)
	def __repr__(self):
		return str(self.__dict__)
class ImgInfo:
	""" Represents an event's associated image """
	def __init__(self, url: str, license: str, artist: str, credit: str):
		self.url = url
		self.license = license
		self.artist = artist
		self.credit = credit
	# Used in unit testing
	def __eq__(self, other):
		return isinstance(other, ImgInfo) and \
			(self.url, self.license, self.artist, self.credit) == \
			(other.url, other.license, other.artist, other.credit)
	def __repr__(self):
		return str(self.__dict__)
class EventInfo:
	""" Used when responding to type=info requests """
	def __init__(self, event: Event, desc: str, wikiId: int, imgInfo: ImgInfo):
		self.event = event
		self.desc = desc
		self.wikiId = wikiId
		self.imgInfo = imgInfo
	# Used in unit testing
	def __eq__(self, other):
		return isinstance(other, EventInfo) and \
			(self.event, self.desc, self.wikiId, self.imgInfo) == (other.event, other.desc, other.wikiId, other.imgInfo)
	def __repr__(self):
		return str(self.__dict__)
class SuggResponse:
	""" Used when responding to type=sugg requests """
	def __init__(self, suggs: list[str], hasMore: bool):
		self.suggs = suggs
		self.hasMore = hasMore
	# Used in unit testing
	def __eq__(self, other):
		return isinstance(other, SuggResponse) and \
			(self.suggs, self.hasMore) == (other.suggs, other.hasMore)
	def __repr__(self):
		return str(self.__dict__)

# Entry point
def application(environ: dict[str, str], start_response) -> Iterable[bytes]:
	""" Entry point for the WSGI script """
	# Get response object
	val = handleReq(DB_FILE, environ)
	# Construct response
	data = jsonpickle.encode(val, unpicklable=False).encode()
	headers = [('Content-type', 'application/json')]
	if 'HTTP_ACCEPT_ENCODING' in environ and 'gzip' in environ['HTTP_ACCEPT_ENCODING']:
		if len(data) > 100:
			data = gzip.compress(data, compresslevel=5)
			headers.append(('Content-encoding', 'gzip'))
	headers.append(('Content-Length', str(len(data))))
	start_response('200 OK', headers)
	return [data]
def handleReq(dbFile: str, environ: dict[str, str]) -> None | EventResponse | EventInfo | SuggResponse:
	""" Queries the database, and constructs a response object """
	# Open db
	dbCon = sqlite3.connect(dbFile)
	dbCur = dbCon.cursor()
	# Get query params
	queryStr = environ['QUERY_STRING'] if 'QUERY_STRING' in environ else ''
	queryDict = urllib.parse.parse_qs(queryStr)
	params = {k: v[0] for k, v in queryDict.items()}
	# Get data of requested type
	reqType = queryDict['type'][0] if 'type' in queryDict else None
	if reqType == 'events':
		return handleEventsReq(params, dbCur)
	elif reqType == 'info':
		return handleInfoReq(params, dbCur)
	elif reqType == 'sugg':
		return handleSuggReq(params, dbCur)
	return None

# For type=events
def handleEventsReq(params: dict[str, str], dbCur: sqlite3.Cursor) -> EventResponse | None:
	""" Generates a response for a type=events request """
	# Get dates
	dateRange = params['range'] if 'range' in params else '.'
	if '.' not in dateRange:
		print(f'INFO: Invalid date-range value {dateRange}', file=sys.stderr)
		return None
	try:
		start, end = [reqParamToHistDate(s) for s in dateRange.split('.', maxsplit=1)]
	except ValueError:
		print(f'INFO: Invalid date-range value {dateRange}', file=sys.stderr)
		return None
	# Get scale
	if 'scale' not in params:
		print('INFO: No scale provided', file=sys.stderr)
		return None
	try:
		scale = int(params['scale'])
	except ValueError:
		print('INFO: Invalid scale value', file=sys.stderr)
		return None
	# Get event category
	ctg = params['ctg'] if 'ctg' in params else None
	# Get incl value
	try:
		incl = int(params['incl']) if 'incl' in params else None
	except ValueError:
		print('INFO: Invalid incl value', file=sys.stderr)
		return None
	# Get result set limit
	try:
		resultLimit = int(params['limit']) if 'limit' in params else DEFAULT_REQ_EVENTS
	except ValueError:
		print(f'INFO: Invalid results limit {resultLimit}', file=sys.stderr)
		return None
	if resultLimit <= 0 or resultLimit > MAX_REQ_EVENTS:
		print(f'INFO: Invalid results limit {resultLimit}', file=sys.stderr)
		return None
	#
	events = lookupEvents(start, end, scale, ctg, incl, resultLimit, dbCur)
	unitCounts = lookupUnitCounts(start, end, scale, dbCur)
	return EventResponse(events, unitCounts)
def reqParamToHistDate(s: str):
	""" Produces a HistDate from strings like '2010-10-3', '-8000', and '' (throws ValueError if invalid) """
	if not s:
		return None
	m = re.match(r'(-?\d+)(?:-(\d+)-(\d+))?', s)
	if m is None:
		raise ValueError('Invalid HistDate string')
	if m.lastindex == 1:
		return HistDate(None, int(m.group(1)))
	else:
		return HistDate(True, int(m.group(1)), int(m.group(2)), int(m.group(3)))
def lookupEvents(start: HistDate | None, end: HistDate | None, scale: int, ctg: str | None,
		incl: int | None, resultLimit: int, dbCur: sqlite3.Cursor) -> list[Event]:
	""" Looks for events within a date range, in given scale,
		restricted by event category, an optional particular inclusion, and a result limit """
	#query = \
	#	'SELECT events.id, title, start, start_upper, end, end_upper, fmt, ctg, images.id, pop.pop FROM events' \
	#	' INNER JOIN event_disp ON events.id = event_disp.id' \
	#	' INNER JOIN pop ON events.id = pop.id' \
	#	' INNER JOIN event_imgs ON events.id = event_imgs.id' \
	#	' INNER JOIN images ON event_imgs.img_id = images.id'
	query = \
		'SELECT events.id, title, start, start_upper, end, end_upper, fmt, ctg, pop.pop FROM events' \
		' INNER JOIN event_disp ON events.id = event_disp.id' \
		' INNER JOIN pop ON events.id = pop.id'
	constraints = ['event_disp.scale = ?']
	params: list[str | int] = [scale]
	# Constrain by start/end
	startUnit = dateToUnit(start, scale) if start is not None else None
	endUnit = dateToUnit(end, scale) if end is not None else None
	if startUnit is not None and startUnit == endUnit:
		constraints.append('event_disp.unit = ?')
		params.append(startUnit)
	else:
		if startUnit is not None:
			constraints.append('event_disp.unit >= ?')
			params.append(startUnit)
		if endUnit is not None:
			constraints.append('event_disp.unit < ?')
			params.append(endUnit)
	# Constrain by event category
	if ctg is not None:
		constraints.append('ctg = ?')
		params.append(ctg)
	# Add constraints to query
	query2 = query
	if constraints:
		query2 += ' WHERE ' + ' AND '.join(constraints)
	query2 += ' ORDER BY pop.pop DESC'
	query2 += f' LIMIT {resultLimit}'
	# Run query
	results: list[Event] = []
	for row in dbCur.execute(query2, params):
		results.append(eventEntryToResults(row))
		if incl is not None and incl == row[0]:
			incl = None
	# Get any additional inclusion
	if incl is not None:
		constraints.append('events.id = ?')
		params.append(incl)
		row = dbCur.execute(query + ' WHERE ' + ' AND '.join(constraints), params).fetchone()
		if row is not None:
			if len(results) == resultLimit:
				results.pop()
			results.append(eventEntryToResults(row))
	#
	return results
def eventEntryToResults(
		#row: tuple[int, str, int, int | None, int | None, int | None, int, str, int, int]) -> Event:
		row: tuple[int, str, int, int | None, int | None, int | None, int, str, int]) -> Event:
	#eventId, title, start, startUpper, end, endUpper, fmt, ctg, imageId, pop = row
	eventId, title, start, startUpper, end, endUpper, fmt, ctg, pop = row
	""" Helper for converting an 'events' db entry into an Event object """
	# Convert dates
	dateVals: list[int | None] = [start, startUpper, end, endUpper]
	newDates: list[HistDate | None] = [None for n in dateVals]
	for i, n in enumerate(dateVals):
		if n is not None:
			newDates[i] = dbDateToHistDate(n, fmt, i < 2)
	#
	#return Event(eventId, title, newDates[0], newDates[1], newDates[2], newDates[3], ctg, imageId, pop)
	return Event(eventId, title, newDates[0], newDates[1], newDates[2], newDates[3], ctg, 0, pop)
def lookupUnitCounts(
		start: HistDate | None, end: HistDate | None, scale: int, dbCur: sqlite3.Cursor) -> dict[int, int] | None:
	# Build query
	query = 'SELECT unit, count FROM dist WHERE scale = ?'
	params = [scale]
	if start:
		query += ' AND unit >= ?'
		params.append(dateToUnit(start, scale))
	if end:
		query += ' AND unit < ?'
		params.append(dateToUnit(end, scale))
	query += ' ORDER BY unit ASC LIMIT ' + str(MAX_REQ_UNIT_COUNTS + 1)
	# Get results
	unitCounts: dict[int, int] = {}
	for unit, count in dbCur.execute(query, params):
		unitCounts[unit] = count
	return unitCounts if len(unitCounts) <= MAX_REQ_UNIT_COUNTS else None

# For type=info
def handleInfoReq(params: dict[str, str], dbCur: sqlite3.Cursor):
	""" Generates a response for a type=info request """
	if 'event' not in params:
		print('INFO: No \'event\' parameter for type=info request', file=sys.stderr)
		return None
	return lookupEventInfo(params['event'], dbCur)
def lookupEventInfo(eventTitle: str, dbCur: sqlite3.Cursor) -> EventInfo | None:
	""" Look up an event with given title, and return a descriptive EventInfo """
	return EventInfo(
		Event(1, eventTitle, HistDate(True, 2000, 10, 1), None, None, None, 'event', 10, 100),
		f'DESC for {eventTitle}', 1, ImgInfo(f'http://example.org/{eventTitle}', 'license', 'artist', 'credit'))
	#query = \
	#	'SELECT events.id, title, start, start_upper, end, end_upper, fmt, ctg, images.id, pop.pop, ' \
	#		' descs.desc, descs.wiki_id, ' \
	#		' images.url, images.license, images.artist, images.credit FROM events' \
	#	' INNER JOIN pop ON events.id = pop.id' \
	#	' INNER JOIN descs ON events.id = descs.id' \
	#	' INNER JOIN event_imgs ON events.id = event_imgs.id' \
	#	' INNER JOIN images ON event_imgs.img_id = images.id' \
	#	' WHERE events.title = ? COLLATE NOCASE'
	#row = dbCur.execute(query, (eventTitle,)).fetchone()
	#if row is not None:
	#	event = eventEntryToResults(row[:10])
	#	desc, wikiId, url, license, artist, credit = row[10:]
	#	return EventInfo(event, desc, wikiId, ImgInfo(url, license, artist, credit))
	#else:
	#	return None

# For type=sugg
def handleSuggReq(params: dict[str, str], dbCur: sqlite3.Cursor):
	""" Generates a response for a type=sugg request """
	# Get search string
	if  'input' not in params:
		print('INFO: No \'input\' parameter for type=sugg request', file=sys.stderr)
		return None
	searchStr = params['input']
	if not searchStr:
		print('INFO: Empty \'input\' parameter for type=sugg request', file=sys.stderr)
		return None
	# Get result limit
	try:
		resultLimit = int(params['limit']) if 'limit' in params else DEFAULT_REQ_SUGGS
	except ValueError:
		print(f'INFO: Invalid suggestion limit {resultLimit}', file=sys.stderr)
		return None
	if resultLimit <= 0 or resultLimit > MAX_REQ_SUGGS:
		print(f'INFO: Invalid suggestion limit {resultLimit}', file=sys.stderr)
		return None
	#
	ctg = params['ctg'] if 'ctg' in params else None
	return lookupSuggs(searchStr, resultLimit, ctg, dbCur)
def lookupSuggs(searchStr: str, resultLimit: int, ctg: str | None, dbCur: sqlite3.Cursor) -> SuggResponse:
	""" For a search string, returns a SuggResponse describing search suggestions """
	tempLimit = resultLimit + 1 # For determining if 'more suggestions exist'
	query = 'SELECT title FROM events LEFT JOIN pop ON events.id = pop.id WHERE title LIKE ?'
	if ctg is not None:
		query += ' AND ctg = ?'
	query += f' ORDER BY pop.pop DESC LIMIT + {tempLimit}'
	suggs: list[str] = []
	# Prefix search
	params = [searchStr + '%'] + ([ctg] if ctg is not None else [])
	for (title,) in dbCur.execute(query, params):
		suggs.append(title)
	# If insufficient results, try substring search
	if len(suggs) < tempLimit:
		existing = set(suggs)
		params = ['%' + searchStr + '%'] + ([ctg] if ctg is not None else [])
		for (title,) in dbCur.execute(query, params):
			if title not in existing:
				suggs.append(title)
				if len(suggs) == tempLimit:
					break
	#
	return SuggResponse(suggs[:resultLimit], len(suggs) > resultLimit)
