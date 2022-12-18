import {moduloPositive,
	gregorianToJdn, julianToJdn, jdnToGregorian, jdnToJulian, gregorianToJulian, julianToGregorian, getDaysInMonth,
	HistDate, YearDate, CalDate,
	queryServer, jsonToHistDate, jsonToHistEvent,
	DAY_SCALE, MONTH_SCALE, stepDate, inDateScale, getScaleRatio, getUnitDiff,
	DateRangeTree,
} from '/src/lib.ts'

test('moduloPositive', () => {
	expect(moduloPositive(4, 2)).toBe(0)
	expect(moduloPositive(5, 3)).toBe(2)
	expect(moduloPositive(-5, 3)).toBe(1)
})

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

describe('YearDate', () => {
	test('constructor', () => {
		expect(() => new YearDate(2000)).toThrowError()
		expect(() => new YearDate(-5000)).not.toThrowError()
	})
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

test('queryServer', async () => {
	let oldFetch = fetch
	fetch = vi.fn(() => ({json: () => ({test: 'value'})}))
	let json = await queryServer('', 'http://example.com/')
	expect(json).toEqual({test: 'value'})
	fetch = oldFetch
})
test('jsonToHistDate', () => {
	expect(jsonToHistDate({gcal: true, year: 1000, month: 1, day: 10})).toEqual(new CalDate(1000, 1, 10))
	expect(jsonToHistDate({gcal: null, year: -5000, month: 1, day: 1})).toEqual(new YearDate(-5000))
})
test('jsonToHistEvent', () => {
	let jsonEvent = {
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

test('DateRangeTree', () => {
	let ranges = new DateRangeTree()
	ranges.add([new CalDate(100, 1, 1), new CalDate(200, 1, 1)])
	ranges.add([new CalDate(300, 1, 1), new CalDate(400, 1, 1)])
	expect(ranges.tree.size).toBe(2)
	expect(ranges.has([new CalDate(300, 1, 1), new CalDate(400, 1, 1)])).toBe(true)
	ranges.add([new CalDate(-100, 1, 1), new CalDate(150, 1, 1)])
	ranges.add([new CalDate(400, 1, 1), new CalDate(500, 1, 1)])
	expect(ranges.tree.size).toBe(2)
	expect(ranges.has([new CalDate(-100, 1, 1), new CalDate(200, 1, 1)])).toBe(true)
	expect(ranges.has([new CalDate(300, 1, 1), new CalDate(500, 1, 1)])).toBe(true)
	ranges.add([new CalDate(-1000, 1, 1), new CalDate(310, 10, 2)])
	expect(ranges.tree.size).toBe(1)
	expect(ranges.has([new CalDate(-1000, 1, 1), new CalDate(500, 1, 1)])).toBe(true)
	expect(ranges.has([new CalDate(-1, 1, 1), new CalDate(1, 1, 1)])).toBe(true)
})
