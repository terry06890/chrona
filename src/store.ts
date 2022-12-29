/*
 * Defines a global store for UI settings, palette colors, etc
 */

import {defineStore} from 'pinia';
import {CalDate} from './lib';

export const useStore = defineStore('store', {
	state: () => {
		const color = { // Note: For scrollbar colors on chrome, edit ./index.css
			text: '#fafaf9',     // stone-50
			textDark: '#a8a29e', // stone-400
			bg: '#292524',       // stone-800
			bgLight: '#44403c',  // stone-700
			bgDark: '#1c1917',   // stone-900
			bgLight2: '#57534e', // stone-600
			bgDark2: '#0e0c0b',  // darker version of stone-900
			alt: '#fde047',      // yellow-300
			altDark: '#eab308',  // yellow-500
			altDark2: '#ca8a04', // yellow-600
		};
		return {
			tickLen: 16,
			largeTickLen: 32,
			endTickSz: 8, // Size for start/end ticks
			tickLabelHeight: 10,
			minTickSep: 30, // Smallest px separation between ticks
			minLastTicks: 3, // When at smallest scale, don't zoom further into less than this many ticks
			defaultEndTickOffset: 0.5, // Default fraction of a unit to offset start/end ticks
			//
			mainlineBreadth: 80, // Breadth of mainline area (including ticks and labels)
			eventImgSz: 100, // Width/height of event images
			eventLabelHeight: 20,
			spacing: 10, // Spacing between display edge, events, and mainline area
			//
			scrollRatio: 0.2, // Fraction of timeline length to move by upon scroll
			zoomRatio: 1.5, // Ratio of timeline expansion upon zooming out
			dragInertia: 0.1, // Multiplied by final-drag-speed (pixels-per-sec) to get extra scroll distance
			//
			initialStartDate: new CalDate(1900, 1, 1),
			initialEndDate: new CalDate(2000, 1, 1),
			color,
			showEventCounts: true,
			transitionDuration: 300,
		};
	},
});
