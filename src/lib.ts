/*
 * Project-wide globals
 */

export const DEBUG = true;
export const WRITING_MODE_HORZ =
	window.getComputedStyle(document.body)['writing-mode' as any].startsWith('horizontal');
	// Used with ResizeObserver callbacks, to determine which resized dimensions are width and height

// Similar to %, but for negative LHS, return a positive offset from a lower RHS multiple
export function moduloPositive(x: number, y: number){
	return x - Math.floor(x / y) * y;
}

// For calendar conversion. Mostly copied from backend/hist_data/cal.py
export function gregorianToJdn(year: number, month: number, day: number): number {
	if (year < 0){
		year += 1;
	}
	const x = Math.trunc((month - 14) / 12);
	let jdn = Math.trunc(1461 * (year + 4800 + x) / 4);
	jdn += Math.trunc((367 * (month - 2 - 12 * x)) / 12);
	jdn -= Math.trunc((3 * Math.trunc((year + 4900 + x) / 100)) / 4);
	jdn += day - 32075;
	return jdn;
}
export function julianToJdn(year: number, month: number, day: number): number {
	if (year < 0){
		year += 1;
	}
	let jdn = 367 * year;
	jdn -= Math.trunc(7 * (year + 5001 + Math.trunc((month - 9) / 7)) / 4);
	jdn += Math.trunc(275 * month / 9);
	jdn += day + 1729777;
	return jdn;
}
export function jdnToGregorian(jdn: number): [number, number, number] {
	const f = jdn + 1401 + Math.trunc((Math.trunc((4 * jdn + 274277) / 146097) * 3) / 4) - 38;
	const e = 4 * f + 3;
	const g = Math.trunc((e % 1461) / 4);
	const h = 5 * g + 2;
	const D = Math.trunc((h % 153) / 5) + 1;
	const M = (Math.trunc(h / 153) + 2) % 12 + 1;
	let Y = Math.trunc(e / 1461) - 4716 + Math.trunc((12 + 2 - M) / 12);
	if (Y <= 0){
		Y -= 1;
	}
	return [Y, M, D];
}
export function jdnToJulian(jdn: number): [number, number, number] {
	const f = jdn + 1401;
	const e = 4 * f + 3;
	const g = Math.trunc((e % 1461) / 4);
	const h = 5 * g + 2;
	const D = Math.trunc((h % 153) / 5) + 1;
	const M = (Math.trunc(h / 153) + 2) % 12 + 1;
	let Y = Math.trunc(e / 1461) - 4716 + Math.trunc((12 + 2 - M) / 12);
	if (Y <= 0){
		Y -= 1;
	}
	return [Y, M, D];
}
export function julianToGregorian(year: number, month: number, day: number): [number, number, number] {
	return jdnToGregorian(julianToJdn(year, month, day));
}
export function gregorianToJulian(year: number, month: number, day: number): [number, number, number] {
	return jdnToJulian(gregorianToJdn(year, month, day));
}
export function getDaysInMonth(year: number, month: number){
	return gregorianToJdn(year, month + 1, 1) - gregorianToJdn(year, month, 1);
}

// For date representation
export class HistDate {
	year: number;
	month: number;
	day: number;
	constructor(year: number, month=1, day=1){
		this.year = year;
		this.month = month;
		this.day = day;
	}
	equals(other: HistDate, scale=DAY_SCALE){
		if (scale == DAY_SCALE){
			return this.year == other.year && this.month == other.month && this.day == other.day;
		} else if (scale == MONTH_SCALE){
			return this.year == other.year && this.month == other.month;
		} else {
			return Math.floor(this.year / scale) == Math.floor(other.year / scale);
		}
	}
	isEarlier(other: HistDate, scale=DAY_SCALE){
		const yearlyScale = scale != DAY_SCALE && scale != MONTH_SCALE;
		const thisYear = yearlyScale ? Math.floor(this.year / scale) : this.year;
		const otherYear = yearlyScale ? Math.floor(other.year / scale) : other.year;
		if (yearlyScale || thisYear != otherYear){
			return thisYear < otherYear;
		} else {
			if (scale == MONTH_SCALE || this.month != other.month){
				return this.month < other.month;
			} else {
				return this.day < other.day;
			}
		}
	}
	toInt(){
		return this.day + this.month * 50 + this.year * 1000;
	}
	toString(){
		return `${this.year}-${this.month}-${this.day}`;
	}
	getDayDiff(other: HistDate){
		const jdn2 = gregorianToJdn(this.year, this.month, this.day);
		const jdn1 = gregorianToJdn(other.year, other.month, other.day);
		return Math.abs(jdn1 - jdn2);
	}
	getMonthDiff(other: HistDate){
		// Determine earlier date
		let earlier = this as HistDate;
		let later = other;
		if (other.year < this.year || other.year == this.year && other.month < this.month){
			earlier = other;
			later = this as HistDate;
		}
		//
		const yearDiff = earlier.getYearDiff(later);
		if (yearDiff == 0){
			return later.month - earlier.month;
		} else {
			return (13 - earlier.month) + (yearDiff - 1) * 12 + later.month - 1;
		}
	}
	getYearDiff(other: HistDate){
		let yearDiff = Math.abs(this.year - other.year);
		if (this.year * other.year < 0){ // Account for no 0 CE
			yearDiff -= 1;
		}
		return yearDiff;
	}
	clone(){
		return new HistDate(this.year, this.month, this.day);
	}
}

// Timeline parameters
const currentDate = new Date();
export const MIN_DATE = new HistDate(-13.8e9);
export const MAX_DATE = new HistDate(currentDate.getFullYear(), currentDate.getMonth() + 1, currentDate.getDate());
export const MIN_CAL_DATE = new HistDate(-4700, 1, 1); // Date after which months/day scales are usable
export const MONTH_SCALE = -1;
export const DAY_SCALE = -2;
export const SCALES = [1e9, 1e8, 1e7, 1e6, 1e5, 1e4, 1e3, 100, 10, 1, MONTH_SCALE, DAY_SCALE];
	// The timeline will be divided into units of SCALES[0], then SCALES[1], etc
	// Positive ints represent numbers of years, -1 represents 1 month, -2 represents 1 day
if (DEBUG){
	if (SCALES[SCALES.length - 1] != DAY_SCALE
			|| SCALES[SCALES.length - 2] != MONTH_SCALE
			|| SCALES[SCALES.length - 3] != 1){
		throw new Error('SCALES must end with [1, MONTH_SCALE, DAY_SCALE]');
	}
	for (let i = 1; i < SCALES.length - 2; i++){
		if (SCALES[i] <= 0){
			throw new Error('SCALES must only have positive ints before MONTH_SCALE');
		}
		if (SCALES[i-1] <= SCALES[i]){
			throw new Error('SCALES must hold decreasing values');
		}
		if (SCALES[i-1] % SCALES[i] > 0){
			throw new Error('Each positive int in SCALES must divide the previous int');
		}
	}
}
export function stepDate(date: HistDate, scale: number, {forward=true, count=1, inplace=false} = {}): HistDate {
	const newDate = inplace ? date : date.clone();
	if (count < 0){
		count = -count;
		forward = !forward;
	}
	while (count > 0){
		if (scale == DAY_SCALE){
			if (forward && newDate.day < 28){
				const chg = Math.min(28 - newDate.day, count);
				newDate.day += chg;
				count -= chg;
			} else if (!forward && newDate.day > 1){
				const chg = Math.min(newDate.day - 1, count);
				newDate.day -= chg;
				count -= chg;
			} else {
				let jdn = gregorianToJdn(newDate.year, newDate.month, newDate.day)
				jdn += forward ? 1 : -1;
				[newDate.year, newDate.month, newDate.day] = jdnToGregorian(jdn);
				count -= 1;
			}
		} else if (scale == MONTH_SCALE){
			if (forward){
				if (newDate.month < 12){
					const chg = Math.min(12 - newDate.month, count);
					newDate.month += chg;
					count -= chg;
				} else {
					newDate.year += 1;
					if (newDate.year == 0){
						newDate.year = 1;
					}
					newDate.month = 1;
					count -= 1;
				}
			} else {
				if (newDate.month > 1){
					const chg = Math.min(newDate.month - 1, count);
					newDate.month -= chg;
					count -= chg;
				} else {
					newDate.year -= 1;
					if (newDate.year == 0){
						newDate.year = -1;
					}
					newDate.month = 12;
					count -= 1;
				}
			}
		} else {
			let newYear;
			if (forward){
				newYear = newDate.year + count*scale;
				if (newYear == 0){ // Account for there being no 0 CE
					newYear = 1;
				} else if (newDate.year == 1 && scale > 1){
					newYear -= 1;
				}
			} else {
				newYear = newDate.year - count*scale;
				if (newYear == 0 && scale > 1){
					newYear = 1;
				} else if (newDate.year == 1){
					newYear -= 1;
				}
			}
			newDate.year = newYear;
			count = 0;
		}
	}
	return newDate;
}
export function inDateScale(date: HistDate, scale: number): boolean {
	if (scale == DAY_SCALE){
		return true;
	} else if (scale == MONTH_SCALE){
		return date.day == 1;
	} else {
		return (date.year == 1 || date.year % scale == 0) && date.month == 1 && date.day == 1;
	}
}
export function getScaleRatio(scale: number, scale2: number){
	// Returns upper number of units in 'scale' per unit in 'scale2'
	if (scale == DAY_SCALE){
		scale = 1 / 12 / 31;
	} else if (scale == MONTH_SCALE){
		scale = 1 / 12;
	}
	if (scale2 == DAY_SCALE){
		scale2 = 1 / 12 / 31;
	} else if (scale2 == MONTH_SCALE){
		scale2 = 1 / 12;
	}
	return scale2 / scale;
}
export function getUnitDiff(date: HistDate, date2: HistDate, scale: number): number {
	if (scale == DAY_SCALE){
		return date.getDayDiff(date2);
	} else if (scale == MONTH_SCALE){
		return date.getMonthDiff(date2);
	} else {
		return date.getYearDiff(date2) / scale;
	}
}

// For sending timeline-bound data to BaseLine
export class TimelineState {
	id: number;
	startDate: HistDate;
	endDate: HistDate;
	startOffset: number | null;
	endOffset: number | null;
	scaleIdx: number | null;
	constructor(id: number, startDate: HistDate, endDate: HistDate,
			startOffset: number | null = null, endOffset: number | null = null, scaleIdx: number | null = null){
		this.id = id;
		this.startDate = startDate;
		this.endDate = endDate;
		this.startOffset = startOffset;
		this.endOffset = endOffset;
		this.scaleIdx = scaleIdx;
	}
}

export type HistEvent = {
	id: number,
	title: string,
	start: HistDate,
	startUpper: HistDate | null,
	end: HistDate | null,
	endUpper: HistDate | null,
};
