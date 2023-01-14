/*
 * Project-wide globals
 */

import {RBTree} from './rbtree';

export const DEBUG = true;
// For detecting screen size
export type Breakpoint = 'sm' | 'md' | 'lg';
export function getBreakpoint(): Breakpoint {
	const w = window.innerWidth;
	if (w < 768){
		return 'sm';
	} else if (w < 1024){
		return 'md';
	} else {
		return 'lg';
	}
}
// For detecting a touch device
export function onTouchDevice(){
	return window.matchMedia('(pointer: coarse)').matches;
}
// For detecting writing-mode
	// Used with ResizeObserver callbacks, to determine which resized dimensions are width and height
export let WRITING_MODE_HORZ = true;
if ('writing-mode' in window.getComputedStyle(document.body)){ // Can be null when testing
	WRITING_MODE_HORZ = window.getComputedStyle(document.body)['writing-mode' as any].startsWith('horizontal');
}

// Similar to %, but for negative LHS, return a positive offset from a lower RHS multiple
export function moduloPositive(x: number, y: number){
	return x - Math.floor(x / y) * y;
}
// Used to async-await for until after a timeout
export async function timeout(ms: number){
	return new Promise(resolve => setTimeout(resolve, ms))
}
// For positive int n, converts 1 to '1st', 2 to '2nd', etc
export function intToOrdinal(n: number){
	if (n == 1 || n > 20 && n % 10 == 1){
		return `${n == 1 ? '' : Math.floor(n / 10)}1st`;
	} else if (n == 2 || n > 20 && n % 10 == 2){
		return `${n == 2 ? '' : Math.floor(n / 10)}2nd`;
	} else if (n == 3 || n > 20 && n % 10 == 3){
		return `${n == 3 ? '' : Math.floor(n / 10)}3rd`;
	} else {
		return String(n) + 'th';
	}
}
// For positive int n, returns number of trailing zeros in decimal representation
export function getNumTrailingZeros(n: number): number {
	let pow10 = 10;
	while (pow10 != Infinity){
		if (n % pow10 != 0){
			return Math.log10(pow10 / 10);
		}
		pow10 *= 10;
	}
	throw new Error('Exceeded floating point precision');
}

// For calendar conversion (mostly copied from backend/hist_data/cal.py)
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
export const MIN_CAL_YEAR = -4713; // Earliest year where months/day scales are usable
export const MONTH_NAMES = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
export class HistDate {
	gcal: boolean | null;
	year: number;
	month: number;
	day: number;
	constructor(gcal: boolean | null, year: number, month: number, day: number){
		this.gcal = gcal;
		this.year = year;
		this.month = gcal == null ? 1 : month;
		this.day = gcal == null ? 1 : day;
	}
	equals(other: HistDate, scale=DAY_SCALE){ // Does not check gcal
		if (scale == DAY_SCALE){
			return this.year == other.year && this.month == other.month && this.day == other.day;
		} else if (scale == MONTH_SCALE){
			return this.year == other.year && this.month == other.month;
		} else {
			return Math.floor(this.year / scale) == Math.floor(other.year / scale);
		}
	}
	clone(){
		return new HistDate(this.gcal, this.year, this.month, this.day);
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
	cmp(other: HistDate, scale=DAY_SCALE){
		if (this.isEarlier(other, scale)){
			return -1;
		} else if (!this.equals(other, scale)){
			return 1;
		} else {
			return 0;
		}
	}
	getDayDiff(other: HistDate){ // Assumes neither date has gcal=null
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
		if (this.year * other.year < 0){ // Account for no 0 AD
			yearDiff -= 1;
		}
		return yearDiff;
	}
	toString(){
		if (this.gcal != null){
			return `${this.year}-${this.month}-${this.day}`;
		} else {
			return `${this.year}`;
		}
	}
	toYearString(){
		if (this.year >= 1000){
			return String(this.year);
		} else if (this.year > 0){
			return String(this.year) + ' AD';
		} else if (this.year > -1e3){
			return String(-this.year) + ' BC';
		} else if (this.year > -1e6){
			if (this.year % 1e3 == 0){
				return String(Math.floor(-this.year / 1e3)) + 'k BC';
			} else if (this.year % 100 == 0){
				return String(Math.floor(-this.year / 100) / 10) + 'k BC';
			} else {
				return String(-this.year) + ' BC';
			}
		} else if (this.year > -1e9){
			if (this.year % 1e6 == 0){
				return String(Math.floor(-this.year / 1e6)) + ' mya';
			} else if (this.year % 1e3 == 0){
				return String(Math.floor(-this.year / 1e3) / 1e3) + ' mya';
			} else {
				return String(this.year.toLocaleString());
			}
		} else {
			if (this.year % 1e9 == 0){
				return String(Math.floor(-this.year / 1e9)) + ' bya';
			} else if (this.year % 1e6 == 0){
				return String(Math.floor(-this.year / 1e6) / 1e3) + ' bya';
			} else {
				return String(this.year.toLocaleString());
			}
		}
	}
	toTickString(){
		if (this.month == 1 && this.day == 1){
			return this.toYearString();
		} else if (this.day == 1){
			return MONTH_NAMES[this.month - 1];
		} else {
			return intToOrdinal(this.day);
		}
	}
	toDisplayString(){
		if (this.year <= -1e4){ // N.NNN billion/million/thousand years ago
			if (this.year <= -1e9){
				return `${Math.round(-this.year / 1e6) / 1e3} billion years ago`;
			} else if (this.year <= -1e6){
				return `${Math.round(-this.year / 1e3) / 1e3} million years ago`;
			} else {
				return `${Math.round(-this.year / 1e3)} thousand years ago`;
			}
		} else if (this.gcal == null){
			if (this.year < 0){ // eg: 1,000 BC
				return `${(-this.year).toLocaleString()} BC`;
			} else if (this.year < 1500){ // eg: 10 AD
				return `${this.year} AD`;
			} else {
				return `${this.year}`; // eg: 2010
			}
		} else { // eg: 2nd Mar 1710 BC (OS)
			let bcSuffix = this.year < 0 ? ' BC' : (this.year < 1500 ? ' AD' : '');
			let calStr = this.gcal ? '' : ' (OS)';
			return `${intToOrdinal(this.day)} ${MONTH_NAMES[this.month-1]} ${Math.abs(this.year)}${bcSuffix}${calStr}`;
		}
	}
	toInt(){ // Used for v-for keys
		return this.day + this.month * 50 + this.year * 1000;
	}
}
export class YearDate extends HistDate {
	declare gcal: null;
	declare year: number;
	declare month: 1;
	declare day: 1;
	constructor(year: number){
		// Note: Intentionally not enforcing year < MIN_CAL_YEAR here.  This does mean a YearDate can be
		// interpreted as the same day as a CalDate, but it also avoids having HistEvents that span across
		// MIN_CAL_YEAR that have a mix of YearDates and CalDates.
		super(null, year, 1, 1);
	}
}
export class CalDate extends HistDate {
	declare gcal: boolean;
	declare year: number;
	declare month: number;
	declare day: number;
	constructor(year: number, month: number, day: number, gcal=true){
		if (year < MIN_CAL_YEAR){
			throw new Error(`Year must not be before ${MIN_CAL_YEAR}`);
		}
		super(gcal, year, month, day);
	}
}
export const MIN_CAL_DATE = new CalDate(MIN_CAL_YEAR, 1, 1);
export function boundedDateToStr(start: HistDate, end: HistDate | null) : string {
	// Converts a date with uncertain end bound to string for display
	if (end == null){
		return start.toDisplayString();
	}
	const startStr = start.toDisplayString();
	const endStr = end.toDisplayString();
	if (startStr == endStr){
		return startStr;
	}
	if (start.gcal == null && end.gcal == null){
		if (startStr.endsWith(' years ago') && endStr.endsWith(' years ago')){
			const dateRegex = /^(.*) (.*) years ago$/;
			const startMatch = dateRegex.exec(startStr)!;
			const endMatch = dateRegex.exec(endStr)!;
			if (startMatch[2] == endMatch[2]){ // Same billion/million/thousand scale
				let startZeros = getNumTrailingZeros(start.year);
				if (startZeros >= 4 && end.year == start.year + 10 ** startZeros - 1
					|| (start.year - 1) % 1e3 == 0 && end.year == start.year + 999){
					return `About ${startStr}`; // Includes cases like -20_000 to -10_001 and -21999 to -21000
				}
				return `${startMatch[1]} to ${endMatch[1]} ${startMatch[2]} years ago`;
			} else {
				return `${startMatch[1]} ${startMatch[2]} to ${endMatch[1]} ${endMatch[2]} years ago`;
			}
		} else if (moduloPositive(start.year, 1000) == 1 && end.year == start.year + 999){ // eg: 2nd millenium
			let ordinal = intToOrdinal(Math.abs(start.year - 1) / 1000 + (start.year > 0 ? 1 : 0));
			return ordinal + ' millenium' + (start.year < 0 ? ' BC' : '');
		} else if (moduloPositive(start.year, 100) == 1 && end.year == start.year + 99){ // eg: 4th century BC
			let ordinal = intToOrdinal(Math.abs(start.year - 1) / 100 + (start.year > 0 ? 1 : 0));
			return ordinal + ' century' + (start.year < 0 ? ' BC' : '');
		} else if (start.year % 10 == 0 && end.year == start.year + 9){ // eg: 1880s
			return String(start.year) + 's';
		} else {
			const suffixes = [' BC', ' AD'];
			for (let suffix of suffixes){ // eg: 1st Jan to 2nd Feb 100 AD
				if (startStr.endsWith(suffix) && endStr.endsWith(suffix)){
					return startStr.slice(0, startStr.length - suffix.length) + ' to ' + endStr;
				}
			}
		}
	} else if (start.gcal != null && end.gcal != null){
		const dateRegex = /^(\S*) (\S*) (.*)$/; // Matches day, month, and suffix
		const startMatch = dateRegex.exec(startStr);
		const endMatch = dateRegex.exec(endStr);
		if (startMatch != null && endMatch != null && startMatch[3] == endMatch[3]){ // Same suffix
			if (startMatch[2] == endMatch[2]){ // Same month
				const calToJdn = start.gcal ? gregorianToJdn : julianToJdn;
				if (start.day == 1 && calToJdn(end.year, end.month, end.day) == calToJdn(end.year, end.month+1, 0)){
					return `${startMatch[2]} ${startMatch[3]}`; // eg: Jan 2002
				}
				return `${startMatch[1]} to ${endMatch[1]} ${startMatch[2]} ${startMatch[3]}`;
			}
			return `${startMatch[1]} ${startMatch[2]} to ${endMatch[1]} ${endMatch[2]} ${startMatch[3]}`;
		}
	}
	return `${startStr} to ${endStr}`;
}

// For event representation
export class HistEvent {
	id: number;
	title: string;
	start: HistDate;
	startUpper: HistDate | null;
	end: HistDate | null;
	endUpper: HistDate | null;
	ctg: string;
	imgId: number;
	pop: number;
	constructor(
			id: number, title: string, start: HistDate, startUpper: HistDate | null = null,
			end: HistDate | null = null, endUpper: HistDate | null = null, ctg='', imgId=0, pop=0){
		this.id = id;
		this.title = title;
		this.start = start;
		this.startUpper = startUpper;
		this.end = end;
		this.endUpper = endUpper;
		this.ctg = ctg;
		this.imgId = imgId;
		this.pop = pop;
	}
}
export class ImgInfo {
	url: string;
	license: string;
	artist: string;
	credit: string;
	constructor(url: string, license: string, artist: string, credit: string){
		this.url = url;
		this.license = license;
		this.artist = artist;
		this.credit = credit;
	}
}
export class EventInfo {
	event: HistEvent;
	desc: string | null;
	wikiId: number;
	imgInfo: ImgInfo;
	constructor(event: HistEvent, desc: string, wikiId: number, imgInfo: ImgInfo){
		this.event = event;
		this.desc = desc;
		this.wikiId = wikiId;
		this.imgInfo = imgInfo;
	}
}
export function cmpHistEvent(event: HistEvent, event2: HistEvent){
	const cmp = event.start.cmp(event2.start);
	return cmp != 0 ? cmp : event.id - event2.id;
}

// For server requests
const SERVER_DATA_URL = (new URL(window.location.href)).origin + '/data/'
const SERVER_IMG_PATH = '/hist_data/img/'
export async function queryServer(params: URLSearchParams, serverDataUrl=SERVER_DATA_URL){
	// Construct URL
	const url = new URL(serverDataUrl);
	url.search = params.toString();
	// Query server
	let responseObj;
	try {
		const response = await fetch(url.toString());
		responseObj = await response.json();
	} catch (error){
		console.log(`Error with querying ${url.toString()}: ${error}`);
		return null;
	}
	return responseObj;
}
export function getImagePath(imgId: number): string {
	return SERVER_IMG_PATH + String(imgId) + '.jpg';
}
// For server responses
export type HistDateJson = {
	gcal: boolean | null,
	year: number,
	month: number,
	day: number,
}
export type HistEventJson = {
	id: number,
	title: string,
	start: HistDateJson,
	startUpper: HistDateJson | null,
	end: HistDateJson | null,
	endUpper: HistDateJson | null,
	ctg: string,
	imgId: number,
	pop: number,
}
export type EventResponseJson = {
	events: HistEventJson[],
	unitCounts: {[x: number]: number} | null,
}
export type EventInfoJson = {
	event: HistEventJson,
	desc: string,
	wikiId: number,
	imgInfo: ImgInfoJson,
}
export type ImgInfoJson = {
	url: string,
	license: string,
	artist: string,
	credit: string,
}
export type SuggResponseJson = {
	suggs: string[],
	hasMore: boolean,
}
export function jsonToHistDate(json: HistDateJson): HistDate {
	return new HistDate(json.gcal, json.year, json.month, json.day);
}
export function jsonToHistEvent(json: HistEventJson): HistEvent {
	return new HistEvent(
		json.id,
		json.title,
		jsonToHistDate(json.start),
		json.startUpper == null ? null : jsonToHistDate(json.startUpper),
		json.end == null ? null : jsonToHistDate(json.end),
		json.endUpper == null ? null : jsonToHistDate(json.endUpper),
		json.ctg,
		json.imgId,
		json.pop,
	);
}
export function jsonToEventInfo(json: EventInfoJson): EventInfo {
	return new EventInfo(jsonToHistEvent(json.event), json.desc, json.wikiId, jsonToImgInfo(json.imgInfo));
}
export function jsonToImgInfo(json: ImgInfoJson): ImgInfo {
	return new ImgInfo(json.url, json.license, json.artist, json.credit);
}

// For dates in a timeline
const currentDate = new Date();
export const MIN_DATE = new YearDate(-13.8e9);
export const MAX_DATE = new CalDate(currentDate.getFullYear(), currentDate.getMonth() + 1, currentDate.getDate());
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
export function stepDate( // Steps a date N units along a scale
	date: HistDate, scale: number, {forward=true, count=1, inplace=false} = {}): HistDate {
	// If stepping by month or years, leaves day value unchanged
	// Does not account for stepping a CalDate into before MIN_CAL_YEAR
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
				if (newYear == 0){ // Account for there being no 0 AD
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
export function getScaleRatio(scale: number, scale2: number, lowerVal=false){
	// Returns number of units in 'scale' per unit in 'scale2' (provides upper/lower value for days-per-month/year)
	const daysPerMonth = lowerVal ? 28 : 31;
	if (scale == DAY_SCALE){
		scale = 1 / 12 / daysPerMonth;
	} else if (scale == MONTH_SCALE){
		scale = 1 / 12;
	}
	if (scale2 == DAY_SCALE){
		scale2 = 1 / 12 / daysPerMonth;
	} else if (scale2 == MONTH_SCALE){
		scale2 = 1 / 12;
	}
	return scale2 / scale;
}
export function getNumSubUnits(date: HistDate, scaleIdx: number){
	// Returns number of sub-units for a unit starting at 'date' on scale for 'scaleIdx'
	const scale = SCALES[scaleIdx]
	if (scale == DAY_SCALE){
		throw new Error('Cannot get sub-units for DAY_SCALE unit');
	} else if (scale == MONTH_SCALE){
		return getDaysInMonth(date.year, date.month); // Note: Intentionally not checking with MIN_CAL_YEAR
	} else if (scale == 1){
		return 12;
	} else {
		return scale / SCALES[scaleIdx + 1] - (date.year == 1 ? 1 : 0); // Account for lack of 0 AD
	}
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
export function getEventPrecision(event: HistEvent): number {
	// Returns smallest scale at which 'event's start-startUpper range is within one unit, or infinity
	// Note: Intentionally not adding an exception for century and millenia ranges like
		// 101 to 200 (as opposed to 100 to 199) being interpreted as 'within' one 100/1000-year scale unit
	const {start, startUpper} = event;
	if (startUpper == null || start.getDayDiff(startUpper) == 0){
		return DAY_SCALE;
	}
	if (start.getMonthDiff(startUpper) == 0){
		return MONTH_SCALE;
	}
	const yearScaleIdx = SCALES.length - 1 - 2;
	for (let scaleIdx = yearScaleIdx; scaleIdx >= 0; scaleIdx--){
		const scale = SCALES[scaleIdx];
		if (Math.floor(start.year / scale) == Math.floor(startUpper.year / scale)){
			return scale;
		}
	}
	return Number.POSITIVE_INFINITY;
}
export function dateToUnit(date: HistDate, scale: number): number {
	// For a YearDate and sub-yearly scale, uses the first day of the YearDate's year
	if (scale >= 1){
		return Math.floor(date.year / scale);
	} else if (scale == MONTH_SCALE){
		if (!date.gcal){
			return julianToJdn(date.year, date.month, 1);
		} else {
			return gregorianToJdn(date.year, date.month, 1);
		}
	} else { // scale == DAY_SCALE
		if (!date.gcal){
			return julianToJdn(date.year, date.month, date.day);
		} else {
			return gregorianToJdn(date.year, date.month, date.day);
		}
	}
}
export function dateToScaleDate(date: HistDate, scale: number): HistDate {
	// Returns a date representing the unit on 'scale' that 'date' is within
	if (scale == DAY_SCALE){
		return new CalDate(date.year, date.month, date.day);
	} else if (scale == MONTH_SCALE){
		return new CalDate(date.year, date.month, 1);
	} else {
		const year = Math.floor(date.year / scale) * scale;
		if (year < MIN_CAL_YEAR){
			return new YearDate(year);
		} else {
			return new CalDate(year == 0 ? 1 : year, 1, 1);
		}
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

// For managing sets of non-overlapping date ranges
export type DateRange = [HistDate, HistDate];
export class DateRangeTree {
	tree: RBTree<DateRange>;
	constructor(){
		this.tree = new RBTree((r1: DateRange, r2: DateRange) => r1[0].cmp(r2[0]));
	}
	add(range: DateRange){
		const rangesToRemove: HistDate[] = []; // Holds starts of ranges to remove
		const dummyDate = new YearDate(1);
		// Find ranges to remove
		const itr = this.tree.lowerBound([range[0], dummyDate]);
		let prevRange = itr.prev();
		if (prevRange != null){ // Check for start-overlapping range
			if (prevRange[1].isEarlier(range[0])){
				prevRange = null;
			} else {
				rangesToRemove.push(prevRange[0]);
			}
		}
		let r = itr.next();
		while (r != null && !range[1].isEarlier(r[1])){ // Check for included ranges
			rangesToRemove.push(r[0]);
			r = itr.next();
		}
		let nextRange = itr.data();
		if (nextRange != null){ // Check for end-overlapping range
			if (range[1].isEarlier(nextRange[0])){
				nextRange = null;
			} else {
				rangesToRemove.push(nextRange[0])
			}
		}
		// Remove included/overlapping ranges
		for (const start of rangesToRemove){
			this.tree.remove([start, dummyDate]);
		}
		// Add possibly-merged range
		const startDate = prevRange != null ? prevRange[0] : range[0];
		const endDate = nextRange != null ? nextRange[1] : range[1];
		this.tree.insert([startDate, endDate]);
	}
	contains(range: DateRange): boolean {
		const itr = this.tree.lowerBound([range[0], new YearDate(1)]);
		let r = itr.data();
		if (r == null){
			r = itr.prev();
			if (r == null){
				return false;
			} else {
				return !r[1].isEarlier(range[1]);
			}
		} else {
			if (range[0].isEarlier(r[0])){
				return false;
			} else {
				return !r[1].isEarlier(range[1]);
			}
		}
	}
	clear(){
		this.tree.clear();
	}
}
