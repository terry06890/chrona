"""
Provides functions for converting between Julian calendar, Gregorian calendar,
and Julian day number values. Algorithms were obtained from
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
