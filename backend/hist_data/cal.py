"""
Provides date conversion functions, HistDate, and date scales.
Algorithms for converting between calendars and Julian day number values were obtained from
https://en.wikipedia.org/wiki/Julian_day#Converting_Gregorian_calendar_date_to_Julian_Day_Number.
"""

def gregorianToJdn(year: int, month: int, day: int) -> int:
	"""
	Converts a Gregorian calendar date to a Julian day number,
	denoting the noon-to-noon 'Julian day' that starts within the input day.
	A year of 1 means 1 CE, and -1 means 1 BC (0 is treated like -1).
	A month of 1 means January. Can use a month of 13 and a day of 0.
	Valid for dates from 24th Nov 4714 BC onwards.
	"""
	if year < 0:
		year += 1
	x = int((month - 14) / 12)
	jdn = int(1461 * (year + 4800 + x) / 4)
	jdn += int((367 * (month - 2 - 12 * x)) / 12)
	jdn -= int((3 * int((year + 4900 + x) / 100)) / 4)
	jdn += day - 32075
	return jdn

def julianToJdn(year: int, month: int, day: int) -> int:
	"""
	Like gregorianToJdn(), but converts a Julian calendar date.
	Valid for dates from 1st Jan 4713 BC onwards.
	"""
	if year < 0:
		year += 1
	jdn = 367 * year
	jdn -= int(7 * (year + 5001 + int((month - 9) / 7)) / 4)
	jdn += int(275 * month / 9)
	jdn += day + 1729777
	return jdn

def jdnToGregorian(jdn: int) -> tuple[int, int, int]:
	"""
	Converts a Julian day number to a Gregorian calendar date, denoting the
	day in which the given noon-to-noon 'Julian day' begins.
	Valid for non-negative input.
	"""
	f = jdn + 1401 + (((4 * jdn + 274277) // 146097) * 3) // 4 - 38
	e = 4 * f + 3
	g = (e % 1461) // 4
	h = 5 * g + 2
	D = (h % 153) // 5 + 1
	M = (h // 153 + 2) % 12 + 1
	Y = (e // 1461) - 4716 + (12 + 2 - M) // 12
	if Y <= 0:
		Y -= 1
	return Y, M, D

def jdnToJulian(jdn: int) -> tuple[int, int, int]:
	""" Like jdnToGregorian(), but converts to a Julian calendar date """
	f = jdn + 1401
	e = 4 * f + 3
	g = (e % 1461) // 4
	h = 5 * g + 2
	D = (h % 153) // 5 + 1
	M = (h // 153 + 2) % 12 + 1
	Y = (e // 1461) - 4716 + (12 + 2 - M) // 12
	if Y <= 0:
		Y -= 1
	return Y, M, D

def julianToGregorian(year: int, month: int, day: int) -> tuple[int, int, int]:
	return jdnToGregorian(julianToJdn(year, month, day))

def gregorianToJulian(year: int, month: int, day: int) -> tuple[int, int, int]:
	return jdnToJulian(gregorianToJdn(year, month, day))

MIN_CAL_YEAR = -4713 # Disallow within-year dates before this year
MONTH_SCALE = -1;
DAY_SCALE = -2;
SCALES: list[int] = [int(x) for x in [1e9, 1e8, 1e7, 1e6, 1e5, 1e4, 1e3, 100, 10, 1, MONTH_SCALE, DAY_SCALE]];
class HistDate:
	"""
	Represents a historical date
	- 'year' may be negative (-1 means 1 BCE)
	- 'month' and 'day' are at least 1, if given
	- 'gcal' may be:
		- True: Indicates a Gregorian calendar date
		- False: Means the date should, for display, be converted to a Julian calendar date
		- None: 'month' and 'day' are 1 (used for dates before the Julian period starting year 4713 BCE)
	"""
	def __init__(self, gcal: bool | None, year: int, month=1, day=1):
		self.gcal = gcal
		self.year = year
		self.month = month
		self.day = day
	# Used in unit testing
	def __eq__(self, other):
		return isinstance(other, HistDate) and \
			(self.gcal, self.year, self.month, self.day) == (other.gcal, other.year, other.month, other.day)
	def __repr__(self):
		return str(self.__dict__)
def dbDateToHistDate(n: int, fmt: int, end=False) -> HistDate:
	if fmt == 0: # year
		if n >= MIN_CAL_YEAR:
			return HistDate(True, n, 1, 1)
		else:
			return HistDate(None, n)
	elif fmt == 1 or fmt == 3 and not end: # jdn for julian calendar
		return HistDate(False, *jdnToJulian(n))
	else: # fmt == 2 or fmt == 3 and end
		return HistDate(True, *jdnToGregorian(n))
def dateToUnit(date: HistDate, scale: int) -> int:
	if scale >= 1:
		return date.year // scale
	elif scale == MONTH_SCALE:
		if date.gcal == False:
			return julianToJdn(date.year, date.month, 1)
		else:
			return gregorianToJdn(date.year, date.month, 1)
	else: # scale == DAY_SCALE
		if date.gcal == False:
			return julianToJdn(date.year, date.month, date.day)
		else:
			return gregorianToJdn(date.year, date.month, date.day)
