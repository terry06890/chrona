/*
 * Defines a global store for UI settings, palette colors, etc
 */

import {defineStore} from 'pinia';
import {HistDate, CalDate} from './lib';
import {getBreakpoint, Breakpoint, onTouchDevice} from './lib';

// ========== For store state ==========

export type StoreState = {
	// Device info
	touchDevice: boolean,
	breakpoint: Breakpoint,

	// Tick display
	tickLen: number, //px
	largeTickLen: number,
	endTickSz: number // Size for start/end ticks
	tickLabelHeight: number,
	minTickSep: number, // Smallest gap between ticks
	minLastTicks: number // When at smallest scale, don't zoom further into less than this many ticks
	defaultEndTickOffset: number, // Default fraction of a unit to offset start/end ticks
	showMinorTicks: boolean,

	// Mainline and event display
	mainlineBreadth: number, // Breadth of mainline area (incl ticks and labels)
	eventImgSz: number, // Width/height of event images
	eventLabelHeight: number,
	spacing: number, // Spacing between display edge, events, and mainline area
	showEventLines: boolean,

	// User input
	scrollRatio: number, // Fraction of timeline length to move by upon scroll
	zoomRatio: number, // Ratio of timeline expansion upon zooming out (eg: 1.5)
	dragInertia: number, // Multiplied by final-drag-speed (pixels-per-sec) to get extra scroll distance
	disableShortcuts: boolean,

	// Other feature-specific
	reqImgs: boolean, // Only show events with images
	showEventCounts: boolean,
	showBaseLine: boolean,
	searchSuggLimit: number,
	ctgs: { // Specifies event categories, and which ones should be visible
		event: boolean,
		place: boolean,
		organism: boolean,
		person: boolean,
		work: boolean,
		discovery: boolean,
	},

	// Other
	initialStartDate: HistDate,
	initialEndDate: HistDate, // Must be later than initialStartDate
	color: {
		text: string, // CSS color
		textDark: string,
		textDark2: string,
		bg: string,
		bgLight: string,
		bgDark: string,
		bgLight2: string,
		bgDark2: string,
		alt: string,
		altDark: string,
		altDark2: string,
		altBg: string,
		bgAlt: string,
		bgAltDark: string,
		accent: string,
	},
	borderRadius: number, // px
	transitionDuration: number, // ms
};

function getDefaultState(): StoreState {
	const breakpoint = getBreakpoint();
	const color = {
		text: '#fafaf9',      // stone-50
		textDark: '#a8a29e',  // stone-400
		textDark2: '#68625d', // darker version of stone-500
		bg: '#292524',        // stone-800
		bgLight: '#44403c',   // stone-700
		bgDark: '#1c1917',    // stone-900
		bgLight2: '#57534e',  // stone-600
		bgDark2: '#0e0c0b',   // darker version of stone-900
		alt: '#fde047',       // yellow-300
		altDark: '#eab308',   // yellow-500
		altDark2: '#ca8a04',  // yellow-600
		altBg: '#6a5e2e',
		bgAlt: '#f5f5f4',     // stone-100
		bgAltDark: '#d6d3d1', // stone-300
		accent: '#2563eb',    // blue-600
	};
	return {
		// Device info
		touchDevice: onTouchDevice(),
		breakpoint: breakpoint,

		// Tick display
		tickLen: 16,
		largeTickLen: 32,
		endTickSz: 8,
		tickLabelHeight: 10,
		minTickSep: 30,
		minLastTicks: 3,
		defaultEndTickOffset: 0.5,
		showMinorTicks: true,

		// Mainline and event display
		mainlineBreadth: 70,
		eventImgSz: 100,
		eventLabelHeight: 20,
		spacing: 10,
		showEventLines: true,

		// User input
		scrollRatio: 0.2,
		zoomRatio: 1.5,
		dragInertia: 0.1,
		disableShortcuts: false,

		// Other feature-specific
		reqImgs: true,
		showEventCounts: true,
		showBaseLine: true,
		searchSuggLimit: 10,
		ctgs: {
			event: true,
			place: true,
			organism: true,
			person: true,
			work: true,
			discovery: true,
		},

		// Other
		initialStartDate: new CalDate(1900, 1, 1),
		initialEndDate: new CalDate(2030, 1, 1),
		color,
		borderRadius: 5,
		transitionDuration: 300,
	};
}

// Gets 'composite keys' which have the form 'key1' or 'key1.key2' (usable to specify properties of store objects)
function getCompositeKeys(state: StoreState){
	const compKeys = [];
	for (const key of Object.getOwnPropertyNames(state) as (keyof StoreState)[]){
		if (typeof state[key] != 'object'){
			compKeys.push(key);
		} else {
			for (const subkey of Object.getOwnPropertyNames(state[key])){
				compKeys.push(`${key}.${subkey}`);
			}
		}
	}
	return compKeys;
}

const STORE_COMP_KEYS = getCompositeKeys(getDefaultState());

// ========== For getting/setting/loading store state ==========

function getStoreVal(state: StoreState, compKey: string): any {
	if (compKey in state){
		return state[compKey as keyof StoreState];
	}
	const [s1, s2] = compKey.split('.', 2);
	if (s1 in state){
		const key1 = s1 as keyof StoreState;
		if (typeof state[key1] == 'object' && s2 in (state[key1] as any)){
			return (state[key1] as any)[s2];
		}
	}
	return null;
}

function setStoreVal(state: StoreState, compKey: string, val: any): void {
	if (compKey in state){
		(state[compKey as keyof StoreState] as any) = val;
		return;
	}
	const [s1, s2] = compKey.split('.', 2);
	if (s1 in state){
		const key1 = s1 as keyof StoreState;
		if (typeof state[key1] == 'object' && s2 in (state[key1] as any)){
			(state[key1] as any)[s2] = val;
			return;
		}
	}
}

function loadFromLocalStorage(state: StoreState){
	for (const key of STORE_COMP_KEYS){
		const item = localStorage.getItem(key)
		if (item != null){
			setStoreVal(state, key, JSON.parse(item));
		}
	}
}

// ========== Main export ==========

export const useStore = defineStore('store', {
	state: () => {
		const state = getDefaultState();
		loadFromLocalStorage(state);
		return state;
	},

	actions: {
		reset(): void {
			Object.assign(this, getDefaultState());
		},

		resetOne(key: string){
			const val = getStoreVal(this, key);
			if (val != null){
				const val2 = getStoreVal(getDefaultState(), key);
				if (val != val2){
					setStoreVal(this, key, val2);
				}
			}
		},

		save(key: string){
			if (STORE_COMP_KEYS.includes(key)){
				localStorage.setItem(key, JSON.stringify(getStoreVal(this, key)));
			}
		},

		load(): void {
			loadFromLocalStorage(this);
		},

		clear(): void {
			for (const key of STORE_COMP_KEYS){
				localStorage.removeItem(key);
			}
		},
	},
});
