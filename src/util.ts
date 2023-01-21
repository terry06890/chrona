/*
 * General utility functions
 */

// ========== For device detection ==========

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

// Returns true for a touch device
export function onTouchDevice(){
	return window.matchMedia('(pointer: coarse)').matches;
}

// For detecting writing mode
	// Used with ResizeObserver callbacks, to determine which resized dimensions are width and height
export let WRITING_MODE_HORZ = true;

if ('writing-mode' in window.getComputedStyle(document.body)){ // Can be null when testing
	const bodyStyles = window.getComputedStyle(document.body);
	if ('writing-mode' in bodyStyles){
		WRITING_MODE_HORZ = (bodyStyles['writing-mode'] as string).startsWith('horizontal');
	}
}

// ========== For handler throttling ==========

// For creating throttled version of handler function
export function makeThrottled(hdlr: (...args: any[]) => void, delay: number){
	let timeout = 0;
	return (...args: any[]) => {
		clearTimeout(timeout);
		timeout = window.setTimeout(async () => hdlr(...args), delay);
	};
}

// Like makeThrottled(), but accepts an async function
export function makeThrottledAsync(hdlr: (...args: any[]) => Promise<void>, delay: number){
	let timeout = 0;
	return async (...args: any[]) => {
		clearTimeout(timeout);
		timeout = window.setTimeout(async () => await hdlr(...args), delay);
	};
}

// Like makeThrottled(), but, for runs of fast handler calls, calls it at spaced intervals, and at the start/end
export function makeThrottledSpaced(hdlr: (...args: any[]) => void, delay: number){
	let lastHdlrTime = 0; // Used for throttling
	let endHdlr = 0; // Used to call handler after ending a run of calls
	return (...args: any[]) => {
		clearTimeout(endHdlr);
		const currentTime = new Date().getTime();
		if (currentTime - lastHdlrTime > delay){
			lastHdlrTime = currentTime;
			hdlr(...args);
			lastHdlrTime = new Date().getTime();
		} else {
			endHdlr = window.setTimeout(async () => {
				endHdlr = 0;
				hdlr(...args);
				lastHdlrTime = new Date().getTime();
			}, delay);
		}
	};
}

// ========== Other ==========

// Similar to %, but for negative LHS, return a positive offset from a lower RHS multiple
export function moduloPositive(x: number, y: number){
	return x - Math.floor(x / y) * y;
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

// Removes a class from an element, triggers reflow, then adds the class
export function animateWithClass(el: HTMLElement, className: string){
	el.classList.remove(className);
	el.offsetWidth; // Triggers reflow
	el.classList.add(className);
}

// Used to async-await for until after a timeout
export async function timeout(ms: number){
	return new Promise(resolve => setTimeout(resolve, ms))
}

// For estimating text width (via https://stackoverflow.com/questions/118241/calculate-text-width-with-javascript)
const _getTextWidthCanvas = document.createElement('canvas');
export function getTextWidth(text: string, font: string): number {
	const context = _getTextWidthCanvas.getContext('2d')!;
	context.font = font;
	const metrics = context.measureText(text);
	return metrics.width;
}
