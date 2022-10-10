/*
 * Project-wide globals
 */

export const MIN_DATE = -1000;
export const MAX_DATE = 1000;
export const SCALES = [200, 50, 10, 1, 0.2]; // Timeline gets divided into units of SCALES[0], then SCALES[1], etc

export const WRITING_MODE_HORZ =
	window.getComputedStyle(document.body)['writing-mode' as any].startsWith('horizontal');
	// Used with ResizeObserver callbacks, to determine which resized dimensions are width and height

export type TimelineRange = {
	id: number,
	start: number,
	end: number,
};
