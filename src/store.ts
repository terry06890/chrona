/*
 * Defines a global store for UI settings, palette colors, etc
 */

import {defineStore} from 'pinia';

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
			color,
			scrollRatio: 0.2, // Fraction of timeline length to move by upon scroll
			zoomRatio: 1.5, // Ratio of timeline expansion upon zooming out
			dragInertia: 0.1, // Multiplied by final-drag-speed (pixels-per-sec) to get extra scroll distance
		};
	},
});
