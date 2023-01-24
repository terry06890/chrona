import {moduloPositive, intToOrdinal, getNumTrailingZeros} from '/src/util.ts';
import {
	gregorianToJdn, julianToJdn, jdnToGregorian, jdnToJulian, julianToGregorian, gregorianToJulian, getDaysInMonth,
	YearDate, CalDate,
	HistEvent,
	dateToDisplayStr, boundedDateToStr,
	queryServer, jsonToHistDate, jsonToHistEvent,
	DAY_SCALE, MONTH_SCALE, stepDate, inDateScale, getScaleRatio, getUnitDiff,
		getEventPrecision, getScaleForJump, dateToUnit, dateToScaleDate,
	DateRangeTree,
} from '/src/lib.ts';

// ========== General utility functions ==========

test('moduloPositive', () => {
	expect(moduloPositive(4, 2)).toBe(0)
	expect(moduloPositive(5, 3)).toBe(2)
	expect(moduloPositive(-5, 3)).toBe(1)
})

test('intToOrdinal', () => {
	expect(intToOrdinal(1)).toBe('1st')
	expect(intToOrdinal(3)).toBe('3rd')
	expect(intToOrdinal(22)).toBe('22nd')
	expect(intToOrdinal(294)).toBe('294th')
	expect(intToOrdinal(10301)).toBe('10301st')
})

test('getNumTrailingZeros', () => {
	expect(getNumTrailingZeros(1)).toBe(0)
	expect(getNumTrailingZeros(20)).toBe(1)
	expect(getNumTrailingZeros(32000)).toBe(3)
	expect(getNumTrailingZeros(1040)).toBe(1)
	expect(getNumTrailingZeros(380402000)).toBe(3)
	expect(getNumTrailingZeros(1e20)).toBe(20)
})

// ========== For calendar conversion ==========

test('gregorianToJdn', () => {
	expect(gregorianToJdn(2010, 11, 3)).toBe(2455504)
	expect(gregorianToJdn(-4714, 11, 24)).toBe(0)
	expect(gregorianToJdn(-1, 1, 1)).toBe(1721060)
})

test('julianToJdn', () => {
	expect(julianToJdn(2010, 11, 3)).toBe(2455517)
	expect(julianToJdn(-4713, 1, 1)).toBe(0)
	expect(julianToJdn(-1, 1, 1)).toBe(1721058)
})

test('jdnToGregorian', () => {
	expect(jdnToGregorian(2455504)).toEqual([2010, 11, 3])
	expect(jdnToGregorian(0)).toEqual([-4714, 11, 24])
	expect(jdnToGregorian(1721060)).toEqual([-1, 1, 1])
})

test('jdnToJulian', () => {
	expect(jdnToJulian(2455517)).toEqual([2010, 11, 3])
	expect(jdnToJulian(0)).toEqual([-4713, 1, 1])
	expect(jdnToJulian(1721058)).toEqual([-1, 1, 1])
})

test('gregorianToJulian', () => {
	expect(gregorianToJulian(2022, 9, 30)).toEqual([2022, 9, 17])
	expect(gregorianToJulian(1616, 5, 3)).toEqual([1616, 4, 23])
})

test('julianToGregorian', () => {
	expect(julianToGregorian(2022, 9, 17)).toEqual([2022, 9, 30])
	expect(julianToGregorian(1616, 4, 23)).toEqual([1616, 5, 3])
})

test('getDaysInMonth', () => {
	expect(getDaysInMonth(2022, 12)).toBe(31)
	expect(getDaysInMonth(2022, 2)).toBe(28)
	expect(getDaysInMonth(2000, 2)).toBe(29)
})

// ========== For date representation ==========

describe('YearDate', () => {
	test('cmp', () => {
		expect((new YearDate(-5000)).equals(new YearDate(-5000))).toBe(true)
		expect((new YearDate(-6000)).equals(new YearDate(-5999))).toBe(false)
		expect((new YearDate(-6000)).isEarlier(new YearDate(-5000))).toBe(true)
		expect((new YearDate(-5000)).cmp(new YearDate(-6000))).toBe(1)
	})
	test('diff', () => {
		expect((new YearDate(-5000)).getMonthDiff(new YearDate(-5001))).toBe(12)
		expect((new YearDate(-5000)).getYearDiff(new YearDate(-6000))).toBe(1000)
	})
})

describe('CalDate', () => {
	test('cmp', () => {
		expect((new CalDate(2000, 1, 1)).equals(new CalDate(2000, 1, 1))).toBe(true)
		expect((new CalDate(2000, 1, 1)).equals(new CalDate(-1, 1, 1))).toBe(false)
		expect((new CalDate(-1, 1, 1)).isEarlier(new CalDate(1, 1, 1))).toBe(true)
		expect((new CalDate(1, 11, 1)).cmp(new CalDate(2, 1, 11))).toBe(-1)
		expect((new CalDate(100, 12, 1)).cmp(new CalDate(100, 11, 30))).toBe(1)
		expect((new CalDate(10, 3, 10)).cmp(new CalDate(10, 3, 20))).toBe(-1)
	})
	test('diff', () => {
		expect((new CalDate(2000, 1, 1)).getDayDiff(new CalDate(2001, 1, 1))).toBe(366)
		expect((new CalDate(100, 11, 30)).getMonthDiff(new CalDate(101, 4, 1))).toBe(5)
		expect((new CalDate(-1, 10, 3)).getYearDiff(new CalDate(1, 1, 1))).toBe(1)
	})
})

test('toDisplayString', () => {
	expect(dateToDisplayStr(new YearDate(-14_000_000_000))).toBe('14 billion years ago')
	expect(dateToDisplayStr(new YearDate(-14_300_000_000))).toBe('14.3 billion years ago')
	expect(dateToDisplayStr(new YearDate(     -1_230_000))).toBe('1.23 million years ago')
	expect(dateToDisplayStr(new YearDate(     -1_234_567))).toBe('1.235 million years ago')
	expect(dateToDisplayStr(new YearDate(       -123_456))).toBe('123 thousand years ago')
	expect(dateToDisplayStr(new YearDate(         -9_999))).toBe('9,999 BC')
	expect(dateToDisplayStr(new YearDate(           -200))).toBe('200 BC')
	expect(dateToDisplayStr(new YearDate(              1))).toBe('1 AD')
	expect(dateToDisplayStr(new YearDate(           1500))).toBe('1500')
	expect(dateToDisplayStr(new CalDate(2000, 10, 3))).toBe('3rd Oct 2000')
	expect(dateToDisplayStr(new CalDate(-2000, 1, 1))).toBe('1st Jan 2000 BC')
	expect(dateToDisplayStr(new CalDate(1610, 8, 6, false))).toBe('6th Aug 1610 (O.S.)')
	expect(dateToDisplayStr(new CalDate(-100, 2, 2, false))).toBe('2nd Feb 100 BC (O.S.)')
})

test('boundedDateToStr', () => {
	// Start and end N billion/million/thousand years ago
	expect(boundedDateToStr(new YearDate(-1e9),    new YearDate(-1e9))).toBe('1 billion years ago')
	expect(boundedDateToStr(new YearDate(-2e9),    new YearDate(-1.2e9))).toBe('2 to 1.2 billion years ago')
	expect(boundedDateToStr(new YearDate(-2e6),    new YearDate(-30e3))).toBe('2 million to 30 thousand years ago')
	expect(boundedDateToStr(new YearDate(-2e6),    new YearDate(-1e6 - 1))).toBe('About 2 million years ago')
	expect(boundedDateToStr(new YearDate(-10_999), new YearDate(-10_000))).toBe('About 11 thousand years ago')
	// Other year-based start and end
	expect(boundedDateToStr(new YearDate(-2e6), new YearDate(100))).toBe('2 million years ago to 100 AD')
	expect(boundedDateToStr(new YearDate(1),    new YearDate(1000))).toBe('1st millenium')
	expect(boundedDateToStr(new YearDate(1301), new YearDate(1400))).toBe('14th century')
	expect(boundedDateToStr(new YearDate(-199), new YearDate(-100))).toBe('2nd century BC')
	expect(boundedDateToStr(new YearDate(1880), new YearDate(1889))).toBe('1880s')
	expect(boundedDateToStr(new YearDate(-100), new YearDate(-50))).toBe('100 to 50 BC')
	expect(boundedDateToStr(new YearDate(310),  new YearDate(1001))).toBe('310 to 1001 AD')
	expect(boundedDateToStr(new YearDate(-10),  new YearDate(2000))).toBe('10 BC to 2000')
	// Calendar-based start and end
	expect(boundedDateToStr(new CalDate(100, 1, 2), new CalDate(101, 10, 3))).toBe('2nd Jan 100 AD to 3rd Oct 101 AD')
	expect(boundedDateToStr(new CalDate(100, 1, 2), new CalDate(100, 10, 3))).toBe('2nd Jan to 3rd Oct 100 AD')
	expect(boundedDateToStr(new CalDate(100, 1, 2), new CalDate(100, 1, 3))).toBe('2nd to 3rd Jan 100 AD')
	expect(boundedDateToStr(new CalDate(100, 1, 1), new CalDate(100, 1, 31))).toBe('Jan 100 AD')
	expect(boundedDateToStr(new CalDate(100, 1, 1, false), new CalDate(100, 1, 31, false))).toBe('Jan 100 AD (O.S.)')
	// Other
	expect(boundedDateToStr(new CalDate(10, 1, 2), null)).toBe('2nd Jan 10 AD')
	expect(boundedDateToStr(new YearDate(-1e7), new CalDate(1610, 3, 2))).toBe('10 million years ago to 2nd Mar 1610')
})

// ========== For server requests ==========

test('queryServer', async () => {
	const oldFetch = fetch
	fetch = vi.fn(() => ({json: () => ({test: 'value'})}))
	const json = await queryServer('', 'http://example.com/')
	expect(json).toEqual({test: 'value'})
	fetch = oldFetch
})

test('jsonToHistDate', () => {
	expect(jsonToHistDate({gcal: true, year: 1000, month: 1, day: 10})).toEqual(new CalDate(1000, 1, 10))
	expect(jsonToHistDate({gcal: null, year: -5000, month: 1, day: 1})).toEqual(new YearDate(-5000))
})

test('jsonToHistEvent', () => {
	const jsonEvent = {
		id: 3,
		title: 'abc',
		start: {gcal: true, year: 2000, month: 10, day: 5},
		startUper: null,
		end: {gcal: true, year: 2010, month: 1, day: 1},
		endUpper: null,
		ctg: 'event',
		imgId: 100,
		pop: 301,
	}
	expect(jsonToHistEvent(jsonEvent)).toEqual({
		id: 3,
		title: 'abc',
		start: new CalDate(2000, 10, 5),
		startUpper: null,
		end: new CalDate(2010, 1, 1),
		endUpper: null,
		ctg: 'event',
		imgId: 100,
		pop: 301,
	});
})

// ========== For dates in a timeline ==========

test('stepDate', () => {
	expect(stepDate(new CalDate(2000, 1, 1), DAY_SCALE)).toEqual(new CalDate(2000, 1, 2))
	expect(stepDate(new CalDate(2000, 1, 2), DAY_SCALE, {forward: false, count: 10})).toEqual(new CalDate(1999, 12, 23))
	expect(stepDate(new CalDate(2000, 10, 11), MONTH_SCALE, {count: 5})).toEqual(new CalDate(2001, 3, 11))
	expect(stepDate(new CalDate(2000, 1, 3), 1, {count: 10})).toEqual(new CalDate(2010, 1, 3))
	expect(stepDate(new YearDate(-5000), 1e3, {forward: false, count: 6})).toEqual(new YearDate(-11000))
})

test('inDateScale', () => {
	expect(inDateScale(new CalDate(100, 2, 3), DAY_SCALE)).toBe(true)
	expect(inDateScale(new CalDate(100, 2, 3), MONTH_SCALE)).toBe(false)
	expect(inDateScale(new CalDate(100, 2, 1), MONTH_SCALE)).toBe(true)
	expect(inDateScale(new CalDate(100, 2, 1), 1)).toBe(false)
	expect(inDateScale(new CalDate(100, 1, 1), 1)).toBe(true)
	expect(inDateScale(new YearDate(-5000), 1e3)).toBe(true)
	expect(inDateScale(new YearDate(-5100), 1e3)).toBe(false)
})

test('getScaleRatio', () => {
	expect(getScaleRatio(DAY_SCALE, MONTH_SCALE)).toBe(31)
	expect(getScaleRatio(MONTH_SCALE, 1)).toBe(12)
	expect(getScaleRatio(MONTH_SCALE, 10)).toBe(120)
	expect(getScaleRatio(200, 10)).toBeCloseTo(1/20, 5)
})

test('getUnitDiff', () => {
	expect(getUnitDiff(new CalDate(2000, 1, 1), (new CalDate(2000, 2, 2)), DAY_SCALE)).toBe(32)
	expect(getUnitDiff(new CalDate(2000, 10, 10), (new CalDate(2001, 11, 2)), MONTH_SCALE)).toBe(13)
	expect(getUnitDiff(new CalDate(-1, 1, 10), (new CalDate(10, 11, 2)), 1)).toBe(10)
	expect(getUnitDiff(new YearDate(-5000), (new YearDate(-6500)), 10)).toBe(150)
})

test('getEventPrecision', () => {
	expect(getEventPrecision(new HistEvent(1, 'one', new YearDate(-5000), new YearDate(-4991)))).toBe(10)
	expect(getEventPrecision(new HistEvent(1, 'one', new YearDate(-5000), new YearDate(-4990)))).toBe(100)
	expect(getEventPrecision(new HistEvent(1, 'one', new CalDate(2000, 1, 1), new CalDate(2150, 1, 1)))).toBe(1000)
	expect(getEventPrecision(new HistEvent(1, 'one', new CalDate(1, 2, 3), new CalDate(1, 2, 25)))).toBe(MONTH_SCALE)
	expect(getEventPrecision(new HistEvent(1, 'one', new CalDate(1, 2, 3), new CalDate(1, 2, 3)))).toBe(DAY_SCALE)
})

test('getScaleForJump', () => {
	expect(getScaleForJump(new HistEvent(1, '1', new CalDate(1970, 2, 3), null))).toBe(DAY_SCALE)
	expect(getScaleForJump(new HistEvent(1, '1', new CalDate(1970, 2, 1), null))).toBe(MONTH_SCALE)
	expect(getScaleForJump(new HistEvent(1, '1', new CalDate(100, 1, 1), new CalDate(100, 1, 31)))).toBe(MONTH_SCALE)
	expect(getScaleForJump(new HistEvent(1, '1', new CalDate(12, 1, 1), null))).toBe(1)
	expect(getScaleForJump(new HistEvent(1, '1', new YearDate(-20), null))).toBe(10)
	expect(getScaleForJump(new HistEvent(1, '1', new YearDate(-100), null))).toBe(100)
	expect(getScaleForJump(new HistEvent(1, '1', new YearDate(-99), new CalDate(-1, 1, 1)))).toBe(100)
	expect(getScaleForJump(new HistEvent(1, '1', new YearDate(1501), new CalDate(1600, 1, 1)))).toBe(100)
	expect(getScaleForJump(new HistEvent(1, '1', new YearDate(1500), new CalDate(1599, 1, 1)))).toBe(100)
	expect(getScaleForJump(new HistEvent(1, '1', new YearDate(1001), null))).toBe(1)
	expect(getScaleForJump(new HistEvent(1, '1', new YearDate(1001), new YearDate(2000)))).toBe(1000)
	expect(getScaleForJump(new HistEvent(1, '1', new CalDate(1e5, 1, 1), null))).toBe(1e5)
	expect(getScaleForJump(new HistEvent(1, '1', new CalDate(1e5+1, 1, 1), null))).toBe(1)
})

test('dateToUnit', () => {
	expect(dateToUnit(new CalDate(2013), 1e3)).toBe(2)
	expect(dateToUnit(new CalDate(2013), 100)).toBe(20)
	expect(dateToUnit(new CalDate(2013), 1)).toBe(2013)
	expect(dateToUnit(new YearDate(-5123), 10)).toBe(-513)
	expect(dateToUnit(new CalDate(1911, 12, 3), MONTH_SCALE)).toBe(gregorianToJdn(1911, 12, 1))
	expect(dateToUnit(new CalDate(1911, 12, 3, false), DAY_SCALE)).toBe(julianToJdn(1911, 12, 3))
})

test('dateToScaleDate', () => {
	expect(dateToScaleDate(new CalDate(2013, 10, 3), DAY_SCALE)).toEqual(new CalDate(2013, 10, 3))
	expect(dateToScaleDate(new CalDate(2013, 10, 3, false), MONTH_SCALE)).toEqual(new CalDate(2013, 10, 1))
	expect(dateToScaleDate(new CalDate(2013, 10, 3), 1)).toEqual(new CalDate(2013, 1, 1))
	expect(dateToScaleDate(new CalDate(2013, 10, 3), 1e3)).toEqual(new CalDate(2000, 1, 1))
	expect(dateToScaleDate(new CalDate(2013, 10, 3), 1e4)).toEqual(new CalDate(1, 1, 1))
	expect(dateToScaleDate(new YearDate(-1222333), 1e6)).toEqual(new YearDate(-2000000))
})

// ========== For DateRangeTree ==========

test('DateRangeTree', () => {
	const ranges = new DateRangeTree()
	ranges.add([new CalDate(100, 1, 1), new CalDate(200, 1, 1)])
	ranges.add([new CalDate(300, 1, 1), new CalDate(400, 1, 1)])
	expect(ranges.tree.size).toBe(2)
	expect(ranges.contains([new CalDate(300, 1, 1), new CalDate(400, 1, 1)])).toBe(true)
	ranges.add([new CalDate(-100, 1, 1), new CalDate(150, 1, 1)])
	ranges.add([new CalDate(400, 1, 1), new CalDate(500, 1, 1)])
	expect(ranges.tree.size).toBe(2)
	expect(ranges.contains([new CalDate(-100, 1, 1), new CalDate(200, 1, 1)])).toBe(true)
	expect(ranges.contains([new CalDate(300, 1, 1), new CalDate(500, 1, 1)])).toBe(true)
	ranges.add([new CalDate(-1000, 1, 1), new CalDate(310, 10, 2)])
	expect(ranges.tree.size).toBe(1)
	expect(ranges.contains([new CalDate(-1000, 1, 1), new CalDate(500, 1, 1)])).toBe(true)
	expect(ranges.contains([new CalDate(-1, 1, 1), new CalDate(1, 1, 1)])).toBe(true)
})
