<template>
<div class="relative overflow-hidden z-0" ref="rootRef"
	@pointerdown="onPointerDown" @pointermove="onPointerMove" @pointerup="onPointerUp"
	@pointercancel="onPointerUp" @pointerout="onPointerUp" @pointerleave="onPointerUp"
	@wheel.exact="onWheel" @wheel.shift.exact="onShiftWheel"
	:style="{backgroundColor: !current && closeable ? 'rgba(0,0,0,0.3)' : store.color.bg}">

	<!-- Event density indicators -->
	<template v-if="store.showEventCounts">
		<div v-for="[tickIdx, count] in tickToCount.entries()" :key="ticks[tickIdx].date.toInt()"
			:style="densityIndStyles(tickIdx, count)" class="absolute animate-fadein"></div>
	</template>

	<!-- SVG area -->
	<svg :viewBox="`0 0 ${width} ${height}`" class="relative z-10" ref="svgRef">
		<defs>
			<linearGradient id="eventLineGradient">
				<stop offset="5%" :stop-color="store.color.altDark3"/>
				<stop offset="95%" :stop-color="store.color.altDark"/>
			</linearGradient>
		</defs>

		<!-- Event lines (dashed line indicates imprecise start date) -->
		<template v-if="store.showEventLines">
			<line v-for="id in eventLines.keys()" :key="id"
				x1="0" y1="0" :x2="eventLines.get(id)![2]" y2="0.01"
				stroke="url('#eventLineGradient')" stroke-width="1px"
				:stroke-dasharray="getEventPrecision(idToEvent.get(id)!) <= minorScale ? '' : '16,4'"
				:style="eventLineStyles(id)" class="animate-fadein"/>
				<!-- Note: With a fully vertical or horizontal line, nothing gets displayed -->
				<!-- Note: Can't use :x2="1" with scaling in :style="", as it makes dashed-lines non-uniform -->
		</template>

		<!-- Main line (horizontal line that gets transformed, with extra length to avoid gaps when panning) -->
		<line :stroke="store.color.alt" stroke-width="2px" x1="-1" y1="0" x2="2" y2="0" :style="mainlineStyles"/>

		<!-- Tick markers -->
		<line v-for="tick in ticks" :key="tick.date.toInt()"
			:x1="tick.x1" :y1="tick.y1" :x2="tick.x2" :y2="tick.y2"
			:stroke="store.color.alt" :stroke-width="`${tick.width}px`"
			:style="tickStyles(tick)" class="animate-fadein"
			:class="{'max-tick': tick.bound == 'max', 'min-tick': tick.bound == 'min'}"/>
	</svg>

	<!-- Tick labels -->
	<div v-for="tick, idx in ticks" :key="tick.date.toInt()"
		class="absolute top-0 left-0 text-sm animate-fadein cursor-default select-none" :style="tickLabelStyles[idx]">
		{{tickLabelTexts[idx]}}
	</div>

	<!-- Movement fail indicators -->
	<div class="absolute z-20" :style="failDivStyles(true)" ref="minFailRef"></div>
	<div class="absolute z-20" :style="failDivStyles(false)" ref="maxFailRef"></div>
	<div class="absolute top-0 left-0 w-full h-full z-20" ref="bgFailRef"></div>

	<!-- Events -->
	<div v-for="id in idToPos.keys()" :key="id" class="absolute animate-fadein z-20" :style="eventStyles(id)">
		<!-- Image -->
		<div class="relative rounded-full cursor-pointer hover:brightness-125" :style="eventImgStyles(id)"
			:title="idToEvent.get(id)!.title" @click="emit('info-click', idToEvent.get(id)!.title)">
			<!-- For flashing search results -->
			<transition name="fadeout">
				<div v-if="flashedEventId == id"
					class="absolute w-full h-full top-0 left-0 rounded-[inherit] opacity-70"
					:style="{backgroundColor: getCtgColor(idToEvent.get(id)!.ctg)}"></div>
			</transition>
		</div>
		<!-- Label -->
		<div class="text-center text-stone-100 text-sm whitespace-nowrap text-ellipsis overflow-hidden select-none">
			{{idToEvent.get(id)!.title}}
		</div>
	</div>

	<!-- Timeline position label -->
	<div class="absolute top-1 left-2 z-20 text-lg"
		style="text-shadow: 0px 0px 5px black" :style="{color: current ? store.color.alt : store.color.text}">
		{{timelinePosStr}}
	</div>

	<!-- Buttons -->
	<icon-button v-if="closeable" :size="30" class="absolute top-2 right-2 z-20"
		:style="{color: store.color.text, backgroundColor: store.color.altDark2}"
		@click="emit('close')" title="Close timeline">
		<close-icon/>
	</icon-button>
</div>
</template>

<script setup lang="ts">
import {ref, onMounted, onUnmounted, computed, watch, PropType, Ref} from 'vue';

import IconButton from './IconButton.vue';
import CloseIcon from './icon/CloseIcon.vue';

import {moduloPositive, animateWithClass, getTextWidth} from '../util';
import {
	getDaysInMonth, MIN_CAL_DATE, MONTH_NAMES, HistDate, HistEvent, getImagePath, dateToYearStr, dateToTickStr,
	MIN_DATE, MAX_DATE, MONTH_SCALE, DAY_SCALE, SCALES,
	stepDate, getScaleRatio, getNumSubUnits, getUnitDiff, getEventPrecision, getScaleForJump,
		dateToUnit, dateToScaleDate,
	TimelineState,
} from '../lib';
import {useStore} from '../store';
import {RBTree} from '../rbtree';

const rootRef: Ref<HTMLElement | null> = ref(null);
const svgRef: Ref<HTMLElement | null> = ref(null);
const minFailRef: Ref<HTMLElement | null> = ref(null);
const maxFailRef: Ref<HTMLElement | null> = ref(null);
const bgFailRef: Ref<HTMLElement | null> = ref(null);

const store = useStore();

const props = defineProps({
	width: {type: Number, required: true},
	height: {type: Number, required: true},
	closeable: {type: Boolean, default: true},
	current: {type: Boolean, required: true},
	initialState: {type: Object as PropType<TimelineState>, required: true},

	eventTree: {type: Object as PropType<RBTree<HistEvent>>, required: true},
	unitCountMaps: {type: Object as PropType<Map<number, number>[]>, required: true},

	searchTarget: {type: Object as PropType<[null | HistEvent, boolean]>, required: true},
		// For triggering a jump to a search result
	reset: {type: Boolean, required: true}, // For triggering a bounds reset
});

const emit = defineEmits(['close', 'state-chg', 'event-display', 'info-click']);

// ========== For size tracking ==========

const vert = computed(() => props.height >= props.width);
const availLen = computed(() => vert.value ? props.height : props.width);
const availBreadth = computed(() => vert.value ? props.width : props.height);
const mounted = ref(false);

onMounted(() => mounted.value = true);

// ========== Timeline data ==========

// Note: The visible timeline is divided into 'units', representing time periods on a scale (eg: months, decades).
	// If there is space, units of a smaller scale are displayed (called 'minor units', in contrast to 'major units').

const ID = props.initialState.id as number;

const startDate = ref(props.initialState.startDate); // Earliest date in scale to display
const endDate = ref(props.initialState.endDate); // Latest date in scale to display (may equal startDate)
const startOffset = ref(store.defaultEndTickOffset); // Fraction of a scale unit before startDate to show
	// Note: Without this, the timeline can only move if the distance is over one unit, which makes dragging awkward,
		// can cause unexpected jumps when zooming, and limits display when a unit has many ticks on the next scale
const endOffset = ref(store.defaultEndTickOffset);

const scaleIdx = ref(0); // Index of current scale in SCALES
const scale = computed(() => SCALES[scaleIdx.value])

const hasMinorScale = computed(() => { // If true, display subset of ticks of next lower scale
	let yearlyScaleOnly = startDate.value.isEarlier(MIN_CAL_DATE);
	if (scale.value == DAY_SCALE || yearlyScaleOnly && scale.value == 1){
		return false;
	}
	let numUnits: number;
	if (scale.value >= 1){
		let yearDiff = startDate.value.getYearDiff(endDate.value);
		numUnits = yearDiff / scale.value + startOffset.value + endOffset.value;
	} else { //scale.value == MONTH_SCALE
		let monthDiff = startDate.value.getMonthDiff(endDate.value);
		numUnits = monthDiff + startOffset.value + endOffset.value;
	}
	return (availLen.value / numUnits) >= 2 * store.minTickSep;
});
const minorScaleIdx = computed(() => scaleIdx.value + (hasMinorScale.value ? 1 : 0));
const minorScale = computed(() => SCALES[minorScaleIdx.value]);

// Initialise start/end date/offset
if (props.initialState.startOffset != null){
	startOffset.value = props.initialState.startOffset as number;
}
if (props.initialState.endOffset != null){
	endOffset.value = props.initialState.endOffset as number;
}
if (props.initialState.scaleIdx != null){
	scaleIdx.value = props.initialState.scaleIdx as number;
} else {
	onMounted(initScale);
}

// Initialises to smallest usable scale
function initScale(){
	let yearlyScaleOnly = startDate.value.isEarlier(MIN_CAL_DATE);
	let yearDiff = startDate.value.getYearDiff(endDate.value);
	let monthDiff = startDate.value.getMonthDiff(endDate.value);

	// Get largest scale with units no larger than startDate-to-endDate range
	let idx = 0;
	if (yearDiff > 0){
		while (SCALES[idx] > yearDiff){
			if (yearlyScaleOnly && SCALES[idx] == 1){
				break;
			}
			idx += 1;
		}
	} else if (monthDiff > 0){
		idx = SCALES.findIndex(s => s == MONTH_SCALE);
	} else {
		idx = SCALES.findIndex(s => s == DAY_SCALE);
	}

	// Check for usable smaller scale
	while (SCALES[idx] > 1){
		let nextScale = SCALES[idx + 1];
		let numUnits = yearDiff / nextScale + startOffset.value + endOffset.value;
		if (availLen.value / numUnits >= store.minTickSep){
			idx += 1;
		} else {
			break;
		}
	}
	if (!yearlyScaleOnly){
		if (SCALES[idx] == 1){
			let numUnits = monthDiff + startOffset.value + endOffset.value;
			if (availLen.value / numUnits >= store.minTickSep){
				idx += 1;
			}
		}
		if (SCALES[idx] == MONTH_SCALE){
			let numUnits = startDate.value.getDayDiff(endDate.value) + startOffset.value + endOffset.value;
			if (availLen.value / numUnits >= store.minTickSep){
				idx += 1;
			}
		}
	}

	scaleIdx.value = idx;
	onStateChg();
}

// ========== Tick data ==========

const tickLabelMargin = computed(() => vert.value ? 20 : 18); // Distance from label to mainline
const tickLabelSpan = computed( // Leftover breadth in half-mainline-area for tick label
	() => store.mainlineBreadth - store.largeTickLen / 2 - tickLabelMargin.value);

class Tick {
	date: HistDate;
	major: boolean; // False if tick is on the minor scale
	offset: number; // Distance from start of visible timeline, in major units
	bound: null | 'min' | 'max'; // Indicates MIN_DATE or MAX_DATE tick

	x1: number;
	y1: number;
	x2: number;
	y2: number;
	width: number;

	constructor(date: HistDate, major: boolean, offset: number, bound=null as null | 'min' | 'max'){
		this.date = date;
		this.major = major;
		this.offset = offset;
		this.bound = bound;
		if (this.bound == null){
			this.x1 = vert.value ? -store.tickLen / 2 : 0;
			this.y1 = vert.value ? 0 : -store.tickLen / 2;
			this.x2 = vert.value ?  store.tickLen / 2 : 0;
			this.y2 = vert.value ? 0 :  store.tickLen / 2;
			this.width = 1;
		} else {
			this.x1 = vert.value ? -store.endTickSz / 2 : 0;
			this.y1 = vert.value ? 0 : -store.endTickSz / 2;
			this.x2 = vert.value ?  store.endTickSz / 2 : 0;
			this.y2 = vert.value ? 0 :  store.endTickSz / 2;
			this.width = store.endTickSz;
		}
	}
}

// Gets num major units in display range
function getNumDisplayUnits({inclOffsets=true} = {}): number {
	let unitDiff = Math.ceil(getUnitDiff(startDate.value, endDate.value, scale.value));
		// Note: Rounding up due to cases like 1 AD to 10 AD with 10-year scale
	if (inclOffsets){
		unitDiff += startOffset.value + endOffset.value;
	}
	return unitDiff;
}

// For a major unit, returns an array specifying minor ticks to show
function getMinorTicks(date: HistDate, scaleIdx: number, majorUnitSz: number, majorOffset: number): Tick[] {
	if (!hasMinorScale.value){
		return [];
	}
	let minorTicks: Tick[] = [];
	let numMinorUnits = getNumSubUnits(date, scaleIdx);
	let minorUnitSz = majorUnitSz / numMinorUnits;
	let minStep = Math.ceil(store.minTickSep / minorUnitSz);
	let stepFrac = numMinorUnits / Math.floor(numMinorUnits / minStep);

	// Iterate through fractional indexes, using rounded differences to step dates
	let idxFrac = stepFrac;
	let idx = Math.floor(idxFrac);
	let idxChg = idx;
	while (Math.ceil(idxFrac) < numMinorUnits){
		date = stepDate(date, SCALES[scaleIdx + 1], {count: idxChg});
		minorTicks.push(new Tick(date, false, majorOffset + idx / numMinorUnits))
		idxFrac += stepFrac;
		idxChg = Math.floor(idxFrac) - idx;
		idx = Math.floor(idxFrac);
	}
	return minorTicks;
}

// Contains the ticks to render, computed from the start/end dates/offsets, the scale, and display area
const ticks = computed((): Tick[] => {
	let ticks: Tick[] = [];
	if (!mounted.value){
		return ticks;
	}
	let numUnits = getNumDisplayUnits();
	let majorUnitSz = availLen.value / numUnits;

	// Get before-startDate ticks (including start-offset ticks and hidden ticks)
	let panUnits = Math.floor(numUnits * store.scrollRatio); // Potential shift distance upon a pan action
	let date = startDate.value;
	for (let i = 0; i < panUnits + Math.ceil(startOffset.value); i++){
		if (MIN_DATE.equals(date, scale.value)){
			break;
		}
		date = stepDate(date, scale.value, {forward: false});
		// Add minor ticks
		let minorTicks = getMinorTicks(date, scaleIdx.value, majorUnitSz, startOffset.value - (i + 1));
		minorTicks.reverse();
		ticks.push(...minorTicks);
		// Add major date
		ticks.push(new Tick(date, true, startOffset.value - (i + 1)));
	}
	ticks.reverse();

	// Get startDate-to-endDate ticks
	date = startDate.value.clone();
	let numMajorUnits = getNumDisplayUnits({inclOffsets: false});
	for (let i = 0; i <= numMajorUnits; i++){
		// Check for MIN_DATE or MAX_DATE
		let minOrMax = null as null | 'min' | 'max';
		if (i == 0 && date.equals(MIN_DATE, scale.value)){
			minOrMax = 'min';
		} else if (i == numMajorUnits && date.equals(MAX_DATE, scale.value)){
			minOrMax = 'max';
		}
		// Add ticks
		ticks.push(new Tick(date, true, startOffset.value + i, minOrMax));
		if (i == numMajorUnits){
			break;
		}
		let minorTicks = getMinorTicks(date, scaleIdx.value, majorUnitSz, startOffset.value + i);
		ticks.push(...minorTicks);
		date = stepDate(date, scale.value);
	}

	// Get after-endDate ticks (including end-offset ticks and hidden ticks)
	let endDateOffset = ticks[ticks.length - 1].offset;
	for (let i = 0; i < panUnits + Math.ceil(endOffset.value); i++){
		if (MAX_DATE.equals(date, scale.value)){
			break;
		}
		// Add minor ticks
		let minorTicks = getMinorTicks(date, scaleIdx.value, majorUnitSz, endDateOffset + i);
		ticks.push(...minorTicks);
		// Add major date
		date = stepDate(date, scale.value);
		ticks.push(new Tick(date, true, endDateOffset + (i + 1)));
	}

	// Get hidden ticks that might transition in after zooming
	let ticksBefore: Tick[] = [];
	let ticksAfter: Tick[] = [];
	if (scaleIdx.value > 0 &&
			availLen.value / (numUnits * store.zoomRatio) < store.minTickSep){ // If zoom-out would decrease scale
		let zoomUnits = numUnits * (store.zoomRatio - 1); // Potential shift distance upon a zoom-out
		if (zoomUnits > panUnits){
			let zoomedScale = SCALES[scaleIdx.value - 1];
			let unitsPerZoomedUnit = getScaleRatio(scale.value, zoomedScale);
			date = ticks[0].date;
			let offset = ticks[0].offset;
			// Get preceding ticks
			for (let i = 0; i < (zoomUnits - panUnits) / unitsPerZoomedUnit; i++){
				date = stepDate(date, zoomedScale, {forward: false});
				if (date.isEarlier(MIN_DATE, scale.value)){
					break;
				}
				ticksBefore.push(new Tick(date, true, offset - (i + 1) * unitsPerZoomedUnit));
			}
			ticksBefore.reverse();
			// Get following ticks
			date = ticks[ticks.length - 1].date;
			offset = ticks[ticks.length - 1].offset;
			for (let i = 0; i < (zoomUnits - panUnits) / unitsPerZoomedUnit; i++){
				date = stepDate(date, zoomedScale);
				if (MAX_DATE.isEarlier(date, scale.value)){
					break;
				}
				ticksAfter.push(new Tick(date, true, offset + (i + 1) * unitsPerZoomedUnit));
			}
		}
	}

	ticks = [...ticksBefore, ...ticks, ...ticksAfter];
	return ticks;
});

// Index of first major tick after which events are visible (-1 if none)
const firstIdx = computed((): number => {
	// Look for a first visible major tick, and uses a preceding tick if present
	let idx = -1;
	for (let i = 0; i < ticks.value.length; i++){
		let tick = ticks.value[i];
		if (tick.major){
			if (tick.offset >= 0){
				return (idx < 0) ? i : idx;
			} else {
				idx = i;
			}
		}
	}
	return idx;
});

// Index of last major tick before which events are visible (-1 if none)
const lastIdx = computed((): number => {
	// Look for a last visible major tick, and uses a following tick if present
	let numUnits = getNumDisplayUnits();
	let idx = -1;
	for (let i = ticks.value.length - 1; i >= 0; i--){
		let tick = ticks.value[i];
		if (tick.major){
			if (tick.offset <= numUnits){
				return (idx < 0) ? i : idx;
			} else {
				idx = i;
			}
		}
	}
	return idx;
});

const firstDate = computed(() => firstIdx.value < 0 ? startDate.value : ticks.value[firstIdx.value]!.date);
const lastDate = computed(() => lastIdx.value < 0 ? endDate.value : ticks.value[lastIdx.value]!.date);

// True if the first visible tick is at startDate
const startIsFirstVisible = computed(() => {
	if (ticks.value.length == 0){
		return true;
	} else {
		return ticks.value.find((tick: Tick) => tick.offset >= 0)!.date.equals(startDate.value);
	}
});

const endIsLastVisible = computed(() => {
	if (ticks.value.length == 0){
		return true;
	} else {
		let numUnits = getNumDisplayUnits();
		return ticks.value.findLast((tick: Tick) => tick.offset <= numUnits)!.date.equals(endDate.value);
	}
});

// ========== For event display ==========

const eventWidth = computed(() => store.eventImgSz);
const eventHeight = computed(() => store.eventImgSz + store.eventLabelHeight);
const eventMajorSz = computed(() => vert.value ? eventHeight.value : eventWidth.value);
const eventMinorSz = computed(() => vert.value ? eventWidth.value : eventHeight.value)

const mainlineToSide = computed( // True if unable to fit mainline in middle with events on both sides
	() => availBreadth.value < store.mainlineBreadth + (eventMinorSz.value + store.spacing * 2) * 2);

const mainlineOffset = computed(() => { // Distance from mainline-area line to left/top of display area
	if (!mainlineToSide.value){
		return availBreadth.value / 2 - store.mainlineBreadth /2 + store.largeTickLen / 2;
	} else {
		return availBreadth.value - store.spacing - tickLabelMargin.value
			- (vert.value ? tickLabelSpan.value : store.tickLabelHeight);
	}
});

// Represents candidate events for display, as a map from event IDs to HistEvents
const idToEvent: Ref<Map<number, HistEvent>> = ref(new Map());

function updateIdToEvent(){
	let map: Map<number, HistEvent> = new Map();
	// Find events in date range
	let itr = props.eventTree.lowerBound(new HistEvent(0, '', firstDate.value));
	while (itr.data() != null){
		let event = itr.data()!;
		itr.next();
		if (dateToUnit(event.start, scale.value) > dateToUnit(lastDate.value, scale.value)){
			break;
		}

		// Check for disabled categories and events
		if ((store.ctgs as {[ctg: string]: boolean})[event.ctg] == false){
			continue;
		}
		if (store.reqImgs && event.imgId == null){
			continue;
		}

		// Add to map
		map.set(event.id, event);
	}
	idToEvent.value = map;
}

watch(() => props.eventTree, updateIdToEvent);
watch(ticks, updateIdToEvent);
// Note: updateIdToEvent() is also called when jumping to a search result

// Represents a layout of events in idToEvent, as a map from event IDs to x/y/w/h
const idToPos: Ref<Map<number, [number, number, number, number]>> = ref(new Map());

// Holds IDs of events for which movement transitions should be skipped (for preventing movement across mainline)
const idsToSkipTransition: Ref<Set<number>> = ref(new Set());

type LineCoords = [number, number, number, number]; // x, y, length, angle

// Represents lines from events to mainline, as a map from event IDs to LineCoords
const eventLines: Ref<Map<number, LineCoords>> = ref(new Map());

// Computes a layout for events in idToEvent
function getEventLayout(): Map<number, [number, number, number, number]> {
	let map: Map<number, [number, number, number, number]> = new Map();
	if (!mounted.value){
		return map;
	}

	// Determine columns to place event elements in (or rows if !vert.value)
	let cols: [number, number][][] = []; // For each column, for each laid out event, stores an ID and pixel offset
	let colOffsets: number[] = []; // Stores the pixel offset of each column
	let afterMainlineIdx: number | null = null; // Index of first column after the mainline, if there is one
	if (!mainlineToSide.value){
		// Get columns before mainline area
		let colArea = availBreadth.value / 2 - store.mainlineBreadth / 2 - store.spacing * 2;
		let numCols = Math.floor(colArea / eventMinorSz.value);
		let colSep = Math.floor((colArea % eventMinorSz.value) / (numCols + 1));
		let colOffset = store.spacing + colSep;
		for (let i = 0; i < numCols; i++){
			cols.push([]);
			colOffsets.push(colOffset);
			colOffset += eventMinorSz.value + colSep;
		}
		afterMainlineIdx = cols.length;
		// Get columns after mainline area
		colOffset = availBreadth.value / 2 + store.mainlineBreadth / 2 + store.spacing;
		for (let i = 0; i < numCols; i++){
			cols.push([]);
			colOffsets.push(colOffset);
			colOffset += eventMinorSz.value + colSep;
		}
	} else {
		// Get columns before mainline area
		let colArea = availBreadth.value - store.mainlineBreadth - store.spacing * 2;
		let numCols = Math.floor(colArea / eventMinorSz.value);
		let colSep = Math.floor((colArea % eventMinorSz.value) / (numCols + 1));
		let colOffset = store.spacing + colSep;
		for (let i = 0; i < numCols; i++){
			cols.push([]);
			colOffsets.push(colOffset);
			colOffset += eventMinorSz.value + colSep;
		}
	}
	if (cols.length == 0){
		console.log('WARNING: No space for events');
		return map;
	}

	// Place events in columns, trying to minimise distance to points on mainline
		// Note: Placing popular events first so the layout is more stable between event requests
	let MAX_ANGLE = 30 / 180 * Math.PI; // Max event-line angle difference (radians) from perpendicular-to-mainline
	let orderedEvents = [...idToEvent.value.values()];
	orderedEvents.sort((x, y) => y.pop - x.pop);
	if (searchEvent.value != null && idToEvent.value.has(searchEvent.value.id)){
		// Prioritise layout of a searched-for event
		let targetIdx = orderedEvents.findIndex((evt: HistEvent) => evt.id == searchEvent.value!.id);
		let temp = orderedEvents[0];
		orderedEvents[0] = orderedEvents[targetIdx];
		orderedEvents[targetIdx] = temp;
	}
	let numUnits = getNumDisplayUnits();
	const minOffset = store.spacing;
	const maxOffset = availLen.value - eventMajorSz.value - store.spacing;
	for (let event of orderedEvents){
		// Get preferred offset in column
		let pxOffset = dateToUnitOffset(event.start) / numUnits * availLen.value - eventMajorSz.value / 2;
		let targetOffset = Math.max(Math.min(pxOffset, maxOffset), minOffset);

		// Find potential positions
		let positions: [number, number, number][] = [];
			// For each position, holds a column index, a within-column index to insert at, and an offset value
		let colIdx = afterMainlineIdx == null ? cols.length - 1 : afterMainlineIdx - 1;
			// Column index, used to iterate from columns closest to mainline outward
		columnLoop:
		while (colIdx >= 0){ // For each column
			let bestOffset: number | null = null; // Best offset found so far
			let bestIdx: number | null = null; // Index of insertion for bestOffset
			let colMainlineDist = Math.abs(colOffsets[colIdx] - mainlineOffset.value);

			if (Math.atan2(Math.abs(pxOffset - targetOffset), colMainlineDist) > MAX_ANGLE){
				// Invalid angle, skip column
			} else if (cols[colIdx].length == 0){ // Check for empty column
				positions.push([colIdx, 0, targetOffset]);
				break;
			} else {
				// Check placement before first event in column
				let offset = cols[colIdx][0][1] - eventMajorSz.value - store.spacing;
				if (offset >= minOffset){
					if (offset >= targetOffset){
						positions.push([colIdx, 0, targetOffset]);
						break;
					} else {
						if (Math.atan2(Math.abs(pxOffset - offset), colMainlineDist) <= MAX_ANGLE){
							bestOffset = offset;
							bestIdx = 0;
						}
					}
				}
				// Check placement after each event element in column
				for (let elIdx = 0; elIdx < cols[colIdx].length; elIdx++){
					offset = cols[colIdx][elIdx][1] + eventMajorSz.value + store.spacing;
					if (elIdx == cols[colIdx].length - 1){ // If last element in column
						if (offset < maxOffset){
							// Check for better offset
							if (bestOffset == null || Math.abs(pxOffset - offset) < Math.abs(pxOffset - bestOffset)){
								if (offset <= targetOffset){
									positions.push([colIdx, elIdx + 1, targetOffset]);
									break columnLoop;
								} else {
									if (Math.atan2(Math.abs(pxOffset - offset), colMainlineDist) <= MAX_ANGLE){
										bestOffset = offset;
										bestIdx = elIdx + 1;
									}
								}
							}
						}
					} else { // If not last event in column
						// Check for space between this and next element
						let nextOffset = cols[colIdx][elIdx + 1][1];
						if (nextOffset - offset < eventMajorSz.value + store.spacing){
							continue;
						}
						// Check for better offset
						if (bestOffset == null || Math.abs(pxOffset - offset) < Math.abs(pxOffset - bestOffset)){
							if (offset <= targetOffset
									&& targetOffset <= nextOffset - eventMajorSz.value - store.spacing){
								positions.push([colIdx, elIdx + 1, targetOffset]);
								break columnLoop;
							} else {
								if (offset <= targetOffset){
									offset = nextOffset - eventMajorSz.value - store.spacing;
								}
								if (Math.atan2(Math.abs(pxOffset - offset), colMainlineDist) <= MAX_ANGLE){
									bestOffset = offset;
									bestIdx = elIdx + 1;
								}
							}
						} else {
							break;
						}
					}
				}
			}

			// Add potential position
			if (bestOffset != null){
				positions.push([colIdx, bestIdx!, bestOffset]);
			}

			// Update colIdx
			if (afterMainlineIdx == null){
				colIdx -= 1;
			} else {
				if (colIdx < afterMainlineIdx){ // Swap to 'right' of mainline
					colIdx = afterMainlineIdx + (afterMainlineIdx - 1 - colIdx);
				} else { // Swap to 'left' of mainline, and move 'outward'
					colIdx = afterMainlineIdx - 1 - (colIdx - afterMainlineIdx) - 1;
				}
			}
		}

		// Choose position with minimal distance
		if (positions.length > 0){
			let bestPos = positions[0]!;
			for (let i = 1; i < positions.length; i++){
				if (Math.abs(targetOffset - positions[i][2]) < Math.abs(targetOffset - bestPos[2])){
					bestPos = positions[i];
				}
			}
			cols[bestPos[0]].splice(bestPos[1], 0, [event.id, bestPos[2]]);
		}
	}

	// Add events to map
	for (let colIdx = 0; colIdx < cols.length; colIdx++){
		let minorOffset = colOffsets[colIdx];
		for (let [eventId, majorOffset] of cols[colIdx]){
			if (vert.value){
				map.set(eventId, [minorOffset, majorOffset, eventWidth.value, eventHeight.value]);
			} else {
				map.set(eventId, [majorOffset, minorOffset, eventWidth.value, eventHeight.value]);
			}
		}
	}
	return map;
}

// Calls getEventLayout() and updates idToPos and eventLines
	// Also notifies parent, which might get more events from server, adjust eventTree, and trigger relayout
function updateLayout(){
	let map = getEventLayout();

	// Check for events that cross mainline
	for (let [eventId, [x, y, , ]] of map.entries()){
		if (idToPos.value.has(eventId)){
			let [oldX, oldY, , ] = idToPos.value.get(eventId)!;
			if (vert.value && (oldX - mainlineOffset.value) * (x - mainlineOffset.value) < 0
					|| !vert.value && (oldY - mainlineOffset.value) * (y - mainlineOffset.value) < 0){
				idsToSkipTransition.value.add(eventId);
			}
		}
	}
	setTimeout(() => idsToSkipTransition.value.clear(), movementDelay.value);

	// Update idToPos // Note: For some reason, if the map is assigned directly, events won't consistently transition
	let toDelete = [];
	for (let eventId of idToPos.value.keys()){
		if (!map.has(eventId)){
			toDelete.push(eventId);
		}
	}
	for (let eventId of toDelete){
		idToPos.value.delete(eventId);
	}
	for (let [eventId, pos] of map.entries()){
		idToPos.value.set(eventId, pos);
	}
	if (pendingSearch && idToPos.value.has(searchEvent.value!.id)){
		pendingSearch = false;
	}

	// Update event lines
	let newEventLines: Map<number, LineCoords> = new Map();
	let numUnits = getNumDisplayUnits();
	for (let [id, [eventX, eventY, eventW, eventH]] of map){
		let x: number; // For line end on mainline
		let y: number;
		let x2: number; // For line end at event
			// Note: Drawing the line in the reverse direction causes 'detachment' from the mainline during transitions
		let y2: number;
		let event = idToEvent.value.get(id)!;
		let unitOffset = dateToUnitOffset(event.start);
		let posFrac = unitOffset / numUnits;
		if (vert.value){
			x = mainlineOffset.value;
			y = posFrac * availLen.value;
		} else {
			x = posFrac * availLen.value;
			y = mainlineOffset.value;
		}
		x2 = eventX + eventW/2;
		y2 = eventY + eventH/2;
		let l = Math.sqrt((x-x2)**2 + (y-y2)**2);
		let a = Math.atan2(y2-y, x2-x) * 180 / Math.PI;
		if (eventLines.value.has(id)){ // Check if event had previous angle
			let oldA = eventLines.value.get(id)![3];
			// Update old angle with difference, to avoid angle transition jumps (eg: change 170 to 185 instead of -175)
			let rOldA = oldA >= 0 ? // oldA limited to -180 to 180
				(oldA % 180) + (Math.floor(oldA / 180) % 2 == 0 ? 0 : -180) :
				(oldA % 180) + (Math.ceil(oldA / 180) % 2 == 0 ? 0 : 180);
			let angleDiff = (a - rOldA) % 360;
			if (angleDiff > 180){
				a = oldA - (360 - angleDiff);
			} else if (angleDiff < -180){
				a = oldA + (360 + angleDiff);
			} else {
				a = oldA + angleDiff;
			}
		}
		newEventLines.set(id, [x, y, l, a]);
	}
	eventLines.value = newEventLines;

	// Notify parent
	emit('event-display', ID, [...map.keys()], firstDate.value, lastDate.value, minorScaleIdx.value);
}

watch(idToEvent, updateLayout);
watch(() => props.width, updateLayout);
watch(() => props.height, updateLayout);

function dateToUnitOffset(date: HistDate){ // Assumes 'date' is >=firstDate and <=lastDate
	// Find containing major tick
	let tickIdx = firstIdx.value;
	for (let i = tickIdx + 1; i < lastIdx.value; i++){
		if (ticks.value[i].major){
			if (!date.isEarlier(ticks.value[i].date)){
				tickIdx = i;
			} else {
				break;
			}
		}
	}

	// Get offset within unit
	const tick = ticks.value[tickIdx];
	if (!hasMinorScale.value){
		if (scale.value == DAY_SCALE){
			return tick.offset;
		} else {
			const nextScale = SCALES[scaleIdx.value + 1];
			return tick.offset + getUnitDiff(tick.date, date, nextScale) / getNumSubUnits(tick.date, scaleIdx.value);
		}
	} else {
		return tick.offset + getUnitDiff(tick.date, date, minorScale.value) / getNumSubUnits(tick.date, scaleIdx.value);
	}
}

// ========== For event density indicators ==========

// Maps tick index to event count
const tickToCount = computed((): Map<number, number> => {
	let tickToCount: Map<number, number> = new Map();
	if (ticks.value.length == 0){
		return tickToCount;
	}
	const map = props.unitCountMaps[minorScaleIdx.value];
	for (let tickIdx = firstIdx.value; tickIdx < lastIdx.value; tickIdx++){
		let eventCount = 0;
		let date = ticks.value[tickIdx].date.clone();
		let nextDate = ticks.value[tickIdx + 1].date;
		while (date.isEarlier(nextDate)){
			let unit = dateToUnit(date, minorScale.value);
			if (map.has(unit)){
				eventCount += map.get(unit)!;
			}
			stepDate(date, minorScale.value, {inplace: true});
		}
		tickToCount.set(tickIdx, eventCount);
	}
	return tickToCount;
});

// ========== For timeline position label ==========

const timelinePosStr = computed((): string => {
	const moreSym = ' \u27A4';
	const date1 = startIsFirstVisible.value ? startDate.value : firstDate.value;
	const date2 = endIsLastVisible.value ? endDate.value : lastDate.value;
	if (minorScale.value == DAY_SCALE){
		const multiMonth = date1.month != date2.month;
		return `${dateToYearStr(date1)} ${MONTH_NAMES[date1.month - 1]}${multiMonth ? moreSym : ''}`;
	} else if (minorScale.value == MONTH_SCALE){
		const multiYear = date1.year != date2.year;
		return `${dateToYearStr(date1)}${multiYear ? moreSym : ''}`;
	} else {
		if (date1.year > 0){
			return `${dateToYearStr(date1)} - ${dateToYearStr(date2)}`;
		} else {
			return dateToYearStr(date1) + moreSym;
		}
	}
});

// ========== For panning/zooming ==========

// Pans the timeline forward or backward
function panTimeline(scrollRatio: number){
	let numUnits = getNumDisplayUnits();
	let chgUnits = numUnits * scrollRatio;
	let newStart = startDate.value.clone();
	let newEnd = endDate.value.clone();
	let [numStartSteps, numEndSteps, newStartOffset, newEndOffset] =
		getMovedBounds(startOffset.value, endOffset.value, chgUnits, chgUnits);

	if (scrollRatio > 0){
		while (true){ // Incrementally update newStart and newEnd using getMovedBounds() result
			if (newEnd.isEarlier(MAX_DATE, scale.value)){
				if (numEndSteps > 0){
					stepDate(newEnd, scale.value, {inplace: true});
					numEndSteps -= 1;
					if (numStartSteps > 0){
						stepDate(newStart, scale.value, {inplace: true});
						numStartSteps -= 1;
					}
				} else {
					stepDate(newStart, scale.value, {count: numStartSteps, inplace: true});
					break;
				}
			} else {
				// Pan up to an offset of store.defaultEndTickOffset
				if (store.defaultEndTickOffset == endOffset.value){
					console.log('INFO: Reached maximum date limit');
					animateFailDiv('max');
					newStartOffset = startOffset.value;
					newEndOffset = endOffset.value;
				} else {
					if (numEndSteps > 0 || newEndOffset >= store.defaultEndTickOffset){
						chgUnits = store.defaultEndTickOffset - endOffset.value;
						newEndOffset = store.defaultEndTickOffset;
						let extraStartSteps: number;
						[extraStartSteps, , newStartOffset, ] =
							getMovedBounds(startOffset.value, endOffset.value, chgUnits, chgUnits);
						stepDate(newStart, scale.value, {count: extraStartSteps, inplace: true});
					} else {
						stepDate(newStart, scale.value, {count: numStartSteps, inplace: true});
					}
				}
				numStartSteps = 0;
				break;
			}
		}
	} else {
		while (true){
			if (MIN_DATE.isEarlier(newStart, scale.value)){
				if (numStartSteps < 0){
					stepDate(newStart, scale.value, {forward: false, inplace: true});
					numStartSteps += 1;
					if (numEndSteps < 0){
						stepDate(newEnd, scale.value, {forward: false, inplace: true});
						numEndSteps += 1;
					}
				} else {
					stepDate(newEnd, scale.value, {count: numEndSteps, inplace: true});
					break;
				}
			} else {
				// Pan up to an offset of store.defaultEndTickOffset
				if (store.defaultEndTickOffset == startOffset.value){
					console.log('INFO: Reached minimum date limit');
					animateFailDiv('min');
					newStartOffset = startOffset.value;
					newEndOffset = endOffset.value;
				} else {
					if (numStartSteps < 0 || newStartOffset >= store.defaultEndTickOffset){
						chgUnits = -store.defaultEndTickOffset + startOffset.value;
						newStartOffset = store.defaultEndTickOffset;
						let extraEndSteps: number;
						[, extraEndSteps, , newEndOffset] =
							getMovedBounds(startOffset.value, endOffset.value, chgUnits, chgUnits);
						stepDate(newEnd, scale.value, {count: extraEndSteps, inplace: true});
					} else {
						stepDate(newEnd, scale.value, {count: numEndSteps, inplace: true});
					}
				}
				numEndSteps = 0;
				break;
			}
		}
	}

	if (newStart.isEarlier(MIN_CAL_DATE, scale.value) && (scale.value == MONTH_SCALE || scale.value == DAY_SCALE)){
		console.log('INFO: Ignored pan into dates where months/days are invalid');
		return;
	}
	if (!newStart.equals(startDate.value)){
		startDate.value = newStart;
	}
	if (!newEnd.equals(endDate.value)){
		endDate.value = newEnd;
	}
	startOffset.value = newStartOffset;
	endOffset.value = newEndOffset;
}

// Zooms the timeline in or out, optionally centered around a given pointer X and Y
function zoomTimeline(zoomRatio: number, pointer: [number, number] | null){
	if (zoomRatio > 1
			&& startDate.value.equals(MIN_DATE, scale.value)
			&& endDate.value.equals(MAX_DATE, scale.value)){
		console.log('INFO: Reached upper scale limit');
		animateFailDiv('both');
		return;
	}
	let numUnits = getNumDisplayUnits();
	let newNumUnits = numUnits * zoomRatio;

	// Get tentative bound changes
	let startChg: number;
	let endChg: number;

	if (pointer == null){
		let unitChg = newNumUnits - numUnits;
		startChg = -unitChg / 2;
		endChg = unitChg / 2;
	} else { // Pointer-centered zoom
		let ptrOffset = vert.value ? pointer[1] : pointer[0];
		// Get element-relative ptrOffset
		let innerOffset = 0;
		if (rootRef.value != null){ // Can become null during dev-server hot-reload for some reason
			let rect = rootRef.value.getBoundingClientRect();
			innerOffset = vert.value ? ptrOffset - rect.top : ptrOffset - rect.left;
		}
		// Get bound changes
		let zoomCenter = numUnits * (innerOffset / availLen.value);
		startChg = -(zoomCenter * (zoomRatio - 1));
		endChg = (numUnits - zoomCenter) * (zoomRatio - 1)
	}

	// Get new bounds
	let newStart = startDate.value.clone();
	let newEnd = endDate.value.clone();
	let [numStartSteps, numEndSteps, newStartOffset, newEndOffset] =
		getMovedBounds(startOffset.value, endOffset.value, startChg, endChg);
	if (zoomRatio <= 1){ // Zooming in
		stepDate(newStart, scale.value, {count: numStartSteps, inplace: true});
		stepDate(newEnd, scale.value, {count: numEndSteps, inplace: true});
	} else { // Zooming out
		newNumUnits = numUnits;
		while (numStartSteps < 0){
			if (newStart.equals(MIN_CAL_DATE, scale.value) && (scale.value == MONTH_SCALE || scale.value == DAY_SCALE)){
				console.log('INFO: Restricting new range to dates where month/day scale is usable');
				newStartOffset = store.defaultEndTickOffset;
				break;
			}
			if (MIN_DATE.equals(newStart, scale.value)){
				newStartOffset = store.defaultEndTickOffset;
				break;
			}
			stepDate(newStart, scale.value, {forward: false, inplace: true});
			numStartSteps += 1;
			newNumUnits += 1;
		}
		while (numEndSteps > 0){
			if (MAX_DATE.equals(newEnd, scale.value)){
				newEndOffset = store.defaultEndTickOffset;
				break;
			}
			stepDate(newEnd, scale.value, {inplace: true});
			numEndSteps -= 1;
			newNumUnits += 1;
		}
		newNumUnits += newStartOffset + newEndOffset;
	}

	// Possibly zoom in/out
	let tickDiff = availLen.value / newNumUnits;
	if (tickDiff < store.minTickSep){ // Zoom out into new scale
		if (scaleIdx.value == 0){
			console.log('INFO: Reached zoom out limit');
			animateFailDiv('both');
			return;
		} else {
			// Scale starting/ending offsets
			let newScale = SCALES[scaleIdx.value - 1];
			let oldUnitsPerNew = getScaleRatio(scale.value, newScale);
			newStartOffset /= oldUnitsPerNew;
			newEndOffset /= oldUnitsPerNew;

			// Shift starting and ending points to align with new scale
			let newStartSubUnits =
				(scale.value == DAY_SCALE) ? getDaysInMonth(newStart.year, newStart.month) :
				(scale.value == MONTH_SCALE) ? 12 :
				getScaleRatio(scale.value, newScale); // Note: Not accounting for no year 0 CE here
			let newStartIdx =
				(scale.value == DAY_SCALE) ? newStart.day - 1 :
				(scale.value == MONTH_SCALE) ? newStart.month - 1 :
				moduloPositive(newStart.year, newScale) / scale.value;
			let startChg = newStartIdx / newStartSubUnits;
			if (newStartOffset >= startChg){
				newStartOffset -= startChg;
			} else {
				startChg = 1 - startChg;
				newStartOffset += startChg;
				stepDate(newStart, newScale, {inplace: true});
			}
			let newEndSubUnits =
				(scale.value == DAY_SCALE) ? getDaysInMonth(newEnd.year, newEnd.month) :
				(scale.value == MONTH_SCALE) ? 12 :
				getScaleRatio(scale.value, newScale);
			let newEndIdx =
				(scale.value == DAY_SCALE) ? newEnd.day - 1 :
				(scale.value == MONTH_SCALE) ? newEnd.month - 1 :
				moduloPositive(newEnd.year, newScale) / scale.value;
			let endChg = newEndIdx / newEndSubUnits;
			if (newEndOffset + endChg < 1){
				newEndOffset += endChg;
			} else {
				endChg = 1 - endChg;
				newEndOffset -= endChg;
				stepDate(newEnd, newScale, {inplace: true});
			}
			if (scale.value == DAY_SCALE){
				newStart.day = 1;
				newEnd.day = 1;
			} else if (scale.value == MONTH_SCALE){
				newStart.month = 1;
				newEnd.month = 1;
			} else {
				newStart.year = Math.floor(newStart.year / newScale) * newScale;
				newEnd.year = Math.floor(newEnd.year / newScale) * newScale;
				// Account for no 0 AD
				if (newStart.year == 0){
					newStart.year = 1;
				}
				if (newEnd.year == 0){
					newEnd.year = 1;
				}
			}

			scaleIdx.value -= 1;
		}
	} else { // If trying to zoom in
		if (scaleIdx.value == SCALES.length - 1){
			if (newNumUnits < store.minLastTicks){
				console.log('INFO: Reached zoom in limit');
				animateFailDiv('bg');
				return;
			}
		} else {
			let newScale = SCALES[scaleIdx.value + 1];
			let newUnitsPerOld = getScaleRatio(newScale, scale.value);
			let zoomedTickDiff = tickDiff / newUnitsPerOld;
			if (zoomedTickDiff > store.minTickSep){ // Zoom in into new scale
				// Update newStart
				newStartOffset *= newUnitsPerOld;
				stepDate(newStart, newScale, {forward: false, count: Math.floor(newStartOffset), inplace: true});
				newStartOffset %= 1;
				if (newStart.isEarlier(MIN_DATE, newScale)){ // Avoid going before MIN_DATE
					newStart = dateToScaleDate(MIN_DATE, newScale);
				}
				if (newStart.equals(MIN_DATE, newScale) // Avoid having large pre-MIN_DATE unit
						&& newStartOffset % 1 > store.defaultEndTickOffset){
					newStartOffset = store.defaultEndTickOffset;
				}

				// Update newEnd
				newEndOffset *= newUnitsPerOld;
				stepDate(newEnd, newScale, {count: Math.floor(newEndOffset), inplace: true});
				newEndOffset %= 1;
				if (MAX_DATE.isEarlier(newEnd, newScale)){
					newEnd = dateToScaleDate(MAX_DATE, newScale);
				}
				if (newEnd.equals(MAX_DATE, newScale) && newEndOffset % 1 > store.defaultEndTickOffset){
					newEndOffset = store.defaultEndTickOffset;
				}

				// Account for zooming into sub-year dates before MIN_CAL_DATE
				if (newStart.isEarlier(MIN_CAL_DATE, newScale) && (newScale == MONTH_SCALE || newScale == DAY_SCALE)){
					console.log('INFO: Ignored zooming into range where month/day scale is invalid');
					animateFailDiv('bg');
					return;
				}
				scaleIdx.value += 1;
			}
		}
	}

	startDate.value = newStart;
	endDate.value = newEnd;
	startOffset.value = newStartOffset;
	endOffset.value = newEndOffset;
}

// Returns a number of start and end steps to take, and new start and end offset values
function getMovedBounds(
		startOffset: number, endOffset: number, startChg: number, endChg: number): [number, number, number, number] {
	let numStartSteps: number;
	let numEndSteps: number;
	let newStartOffset: number;
	let newEndOffset: number;
	if (startChg >= 0){
		numStartSteps = Math.ceil(startChg - startOffset);
		newStartOffset = (startOffset - startChg) - Math.floor(startOffset - startChg);
	} else {
		numStartSteps = Math.ceil(startChg - startOffset);
		newStartOffset = Math.abs((startChg - startOffset) % 1);
	}
	if (endChg >= 0){
		numEndSteps = Math.floor(endChg + endOffset);
		newEndOffset = (endOffset + endChg) % 1;
	} else {
		numEndSteps = Math.floor(endChg + endOffset);
		newEndOffset = (endOffset + endChg) - Math.floor(endOffset + endChg);
	}
	return [numStartSteps, numEndSteps, newStartOffset, newEndOffset];
}

// ========== For mouse/etc handling ==========

let pointerX = 0; // Used for pointer-centered zooming
let pointerY = 0;
const ptrEvtCache: PointerEvent[] = []; // Holds last captured PointerEvent for each pointerId (used for pinch-zoom)
let dragDiff = -1; // Holds accumlated change in pointer's x/y coordinate while dragging
let dragHandler = 0; // Set by a setTimeout() to a handler for pointer dragging
let dragVelocity: number; // Used to add 'drag momentum'
let prevPinchDiff = -1; // Holds distance between two touch points (updated upon a pinch-zoom)
let pinchHandler = 0;
let vUpdateTime: number; // Holds timestamp for last update of 'dragVelocity'
let vPrevPointer: null | number; // Holds pointerX/pointerY used for last update of 'dragVelocity'
let vUpdater = 0; // Set by a setInterval(), used to update 'dragVelocity'

const pointerDown = ref(false);

function onPointerDown(evt: PointerEvent){
	pointerDown.value = true;
	ptrEvtCache.push(evt);

	// Update pointer position
	pointerX = evt.clientX;
	pointerY = evt.clientY;

	// Update data for dragging
	dragDiff = 0;
	dragVelocity = 0;
	vUpdateTime = Date.now();
	vPrevPointer = null;
	vUpdater = window.setInterval(() => {
		if (ptrEvtCache.length != 1){
			return;
		}
		if (vPrevPointer != null){
			let time = Date.now();
			let ptrDiff = (vert.value ? pointerY! : pointerX!) - vPrevPointer;
			dragVelocity = ptrDiff / (time - vUpdateTime) * 1000;
			vUpdateTime = time;
		}
		vPrevPointer = (vert.value ? pointerY : pointerX);
	}, 50);
}

function onPointerMove(evt: PointerEvent){
	// Update event cache
	if (ptrEvtCache.length > 0){
		const index = ptrEvtCache.findIndex((e) => e.pointerId == evt.pointerId);
		ptrEvtCache[index] = evt;
	}

	if (ptrEvtCache.length == 1){
		// Handle pointer dragging
		dragDiff += vert.value ? evt.clientY - pointerY! : evt.clientX - pointerX!;
		if (dragHandler == 0){
			dragHandler = window.setTimeout(() => {
				if (Math.abs(dragDiff) > 2){
					panTimeline(-dragDiff / availLen.value);
					dragDiff = 0;
				}
				dragHandler = 0;
			}, 50);
		}
	} else if (ptrEvtCache.length == 2){
		// Handle pinch-zoom
		const pinchDiff = Math.abs(vert.value ?
			ptrEvtCache[0].clientY - ptrEvtCache[1].clientY :
			ptrEvtCache[0].clientX - ptrEvtCache[1].clientX);
		if (prevPinchDiff == -1){
			prevPinchDiff = pinchDiff;
		} else {
			if (pinchHandler == 0){
				pinchHandler = window.setTimeout(() => {
					let pinchChg = pinchDiff - prevPinchDiff;
					if (Math.abs(pinchChg) > 10 && ptrEvtCache.length == 2){
						zoomTimeline(prevPinchDiff / pinchDiff, [
							(ptrEvtCache[0].clientX + ptrEvtCache[1].clientX) / 2,
							(ptrEvtCache[0].clientY + ptrEvtCache[1].clientY) / 2,
						]);
						prevPinchDiff = pinchDiff;
					}
					pinchHandler = 0;
				}, 50);
			}
		}
	}

	// Update stored cursor position
	pointerX = evt.clientX;
	pointerY = evt.clientY;
}

function onPointerUp(evt: PointerEvent){
	// Ignore for dragging between child elements
	if (evt.relatedTarget != null && rootRef.value!.contains(evt.relatedTarget as HTMLElement)){
		return;
	}

	// Remove from event cache
	if (ptrEvtCache.length > 0){
		const index = ptrEvtCache.findIndex((e) => e.pointerId == evt.pointerId);
		ptrEvtCache.splice(index, 1);
	}

	// Possibly trigger 'drag momentum'
	if (vUpdater != 0){ // Might be zero on pointerleave/etc
		clearInterval(vUpdater);
		vUpdater = 0;
		if (prevPinchDiff == -1 && Math.abs(dragVelocity) > 10){
			let scrollChg = dragVelocity * store.dragInertia;
			panTimeline(-scrollChg / availLen.value);
		}
	}

	if (ptrEvtCache.length < 2){
		pointerDown.value = false;
		prevPinchDiff = -1;
	}
	dragDiff = -1;
}

function onWheel(evt: WheelEvent){
	let shiftDir = (evt.deltaY > 0 ? 1 : -1) * (!vert.value ? -1 : 1);
	panTimeline(shiftDir * store.scrollRatio);
}

function onShiftWheel(evt: WheelEvent){
	let zoomRatio = evt.deltaY > 0 ? store.zoomRatio : 1/store.zoomRatio;
	zoomTimeline(zoomRatio, [pointerX, pointerY]);
}

// ========== For bound-change signalling ==========

function onStateChg(){
	emit('state-chg', new TimelineState(
		ID, startDate.value, endDate.value, startOffset.value, endOffset.value, scaleIdx.value
	));
}

watch(startDate, onStateChg);
watch(endDate, onStateChg);

// ========== For jumping to search result ==========

const searchEvent = ref(null as null | HistEvent); // Holds most recent search result
let pendingSearch = false; // Used to prevent removal of search highlighting until after a search jump has completed
const flashedEventId = ref(-1); // Holds ID of event to flash after a jump
	// -1 indicates no flash, 0 indicates pending search, >0 indicates an event ID

watch(() => props.searchTarget, () => {
	const event = props.searchTarget[0];
	if (event == null){
		return;
	}
	if (MAX_DATE.isEarlier(event.start)){
		console.log('INFO: Ignoring search target past maximum date');
		animateFailDiv('max');
		return;
	}

	if (!idToPos.value.has(event.id)){ // If not already visible
		// Determine new time range
		let tempScale = getScaleForJump(event);
		let targetDate = dateToScaleDate(event.start, tempScale);
		const startEndDiff = getUnitDiff(startDate.value, endDate.value, scale.value);
		let targetStart = stepDate(targetDate, tempScale, {forward: false, count: Math.floor(startEndDiff / 2)});
		if (targetStart.isEarlier(MIN_DATE)){
			targetStart = MIN_DATE;
		}
		let targetEnd = stepDate(targetStart, tempScale, {count: startEndDiff});
		if (MAX_DATE.isEarlier(targetEnd)){
			if (targetStart != MIN_DATE){
				targetStart = stepDate(targetStart, tempScale,
					{forward: false, count: getUnitDiff(targetEnd, MAX_DATE, tempScale)});
				if (targetStart.isEarlier(MIN_DATE)){
					targetStart = MIN_DATE;
				}
			}
			targetEnd = MAX_DATE;
		}

		// Jump to range
		if (startDate.value.equals(targetStart) && endDate.value.equals(targetEnd) && scale.value == tempScale){
			updateIdToEvent();
		} else { // Trigger bound change and relayout
			startDate.value = targetStart;
			endDate.value = targetEnd;
			scaleIdx.value = SCALES.findIndex((s: number) => s == tempScale);
		}
		pendingSearch = true;
		flashedEventId.value = 0;
	} else { // Flash result
		flashedEventId.value = event.id;
		setTimeout(() => {flashedEventId.value = -1;}, 300);
	}

	searchEvent.value = event;
});

// Remove highlighting of search results that have become out of range
watch(idToEvent, () => {
	if (searchEvent.value != null && !idToEvent.value.has(searchEvent.value.id) && !pendingSearch){
		searchEvent.value = null;
	}
});

// For flashing search result after a jump
watch(idToEvent, () => {
	if (flashedEventId.value == 0 && searchEvent.value != null && idToEvent.value.has(searchEvent.value.id)){
		flashedEventId.value = searchEvent.value.id;
		setTimeout(() => {flashedEventId.value = -1;}, 300);
	}
});

// ========== For bound resets ==========

watch(() => props.reset, () => {
	startDate.value = store.initialStartDate;
	endDate.value = store.initialEndDate;
	startOffset.value = store.defaultEndTickOffset;
	endOffset.value = store.defaultEndTickOffset;
	initScale();
});

// ========== For keyboard shortcuts ==========

function onKeyDown(evt: KeyboardEvent){
	if (!props.current || store.disableShortcuts){
		return;
	}
	if (evt.key == 'ArrowUp'){
		if (evt.shiftKey){
			zoomTimeline(1/store.zoomRatio, null);
		} else if (vert.value){
			panTimeline(-store.scrollRatio);
		}
	} else if (evt.key == 'ArrowDown'){
		if (evt.shiftKey){
			zoomTimeline(store.zoomRatio, null);
		} else if (vert.value){
			panTimeline(store.scrollRatio);
		}
	} else if (evt.key == 'ArrowLeft'){
		if (!vert.value){
			panTimeline(-store.scrollRatio);
		}
	} else if (evt.key == 'ArrowRight'){
		if (!vert.value){
			panTimeline(store.scrollRatio);
		}
	}
}

onMounted(() => {
	window.addEventListener('keydown', onKeyDown);
});

onUnmounted(() => {
	window.removeEventListener('keydown', onKeyDown);
});

// ========== For skipping transitions on startup (and on horz/vert swap) ==========

const skipTransition = ref(true);
function tempSkipTransition(){
	skipTransition.value = true;
	setTimeout(() => {skipTransition.value = false}, 100);
}

onMounted(tempSkipTransition);
watch(() => props.width, tempSkipTransition);
watch(() => props.height, tempSkipTransition);

// ========== For styles ==========

const movementDelay = computed(() => pointerDown.value ? store.animationDelay : store.transitionDuration);

const mainlineStyles = computed(() => {
	return {
		transform: vert.value ?
			`translate(${mainlineOffset.value}px, 0) rotate(90deg) scale(${availLen.value},1)` :
			`translate(0, ${mainlineOffset.value}px) rotate(0deg) scale(${availLen.value},1)`,
	};
});

function tickStyles(tick: Tick){
	let numMajorUnits = getNumDisplayUnits();
	let pxOffset = tick.offset / numMajorUnits * availLen.value;
	let scaleFactor = tick.major ? store.largeTickLen / store.tickLen : 1;
	return {
		transform: vert.value ?
			`translate(${mainlineOffset.value}px,  ${pxOffset}px) scale(${scaleFactor})` :
			`translate(${pxOffset}px, ${mainlineOffset.value}px) scale(${scaleFactor})`,
		transitionProperty: skipTransition.value ? 'none' : 'transform, opacity',
		transitionDuration: movementDelay.value + 'ms',
		transitionTimingFunction: 'linear',
		opacity: (pxOffset >= 0 && pxOffset <= availLen.value) ? 1 : 0,
	}
}

const REF_LABEL = '9999 BC'; // Used as a reference for preventing tick label overlap
const refTickLabelWidth = getTextWidth(REF_LABEL, '14px Ubuntu') + 10;

const tickLabelTexts = computed(() => ticks.value.map((tick: Tick) => dateToTickStr(tick.date)));

const tickLabelStyles = computed((): Record<string,string>[] => {
	let numMajorUnits = getNumDisplayUnits();
	let labelSz = vert.value ? store.tickLabelHeight : tickLabelSpan.value;

	// Get offsets, and check for label overlap
	let pxOffsets: number[] = [];
	let hasLongLabel = false; // True if a label has text longer than REF_LABEL (labels will be rotated)
	for (let i = 0; i < ticks.value.length; i++){
		if (tickLabelTexts.value[i].length > REF_LABEL.length){
			hasLongLabel = true;
		}
		pxOffsets.push(ticks.value[i].offset / numMajorUnits * availLen.value);
	}
	let visibilities: boolean[] = pxOffsets.map(() => true); // Elements set to false for overlapping ticks
	if (!hasLongLabel && !vert.value){
		// Iterate through ticks, checking for subsequent overlapping ticks, prioritising major ticks over minor ones
		for (let i = 0; i < ticks.value.length; i++){
			if (pxOffsets[i] < labelSz || pxOffsets[i] > availLen.value - labelSz){ // Hidden ticks
				visibilities[i] = false;
				continue;
			}
			if (visibilities[i] == false){ // Hidden by previous iteration
				continue;
			}
			let tick = ticks.value[i];
			for (let j = i + 1; j < ticks.value.length; j++){ // Look at following ticks
				if (pxOffsets[j] - pxOffsets[i] < refTickLabelWidth){ // Found overlap
					if (!tick.major && ticks.value[j].major){
						visibilities[i] = false;
						break;
					}
					visibilities[j] = false;
				} else {
					break;
				}
			}
		}
	}

	// Determine styles
	let styles: Record<string,string>[] = [];
	for (let i = 0; i < ticks.value.length; i++){
		let tick = ticks.value[i];
		let pxOffset = pxOffsets[i];
		styles.push({
			color: tick.major ? store.color.textDark : store.color.textDark2,
			transform: vert.value ?
				`translate(${mainlineOffset.value + tickLabelMargin.value}px, ${pxOffset}px) translate(0, -50%)` :
				`translate(${pxOffset}px, ${mainlineOffset.value + tickLabelMargin.value}px) `
					+ (hasLongLabel ? 'rotate(30deg)' : 'translate(-50%, 0)'),
			transitionProperty: skipTransition.value ? 'none' : 'transform, opacity',
			transitionDuration: movementDelay.value + 'ms',
			transitionTimingFunction: 'linear',
			display: (tick.major || store.showMinorTicks) && visibilities[i] ? 'block' : 'none',
		});
	}
	return styles;
});

function eventStyles(eventId: number){
	const [x, y, w, h] = idToPos.value.get(eventId)!;
	return {
		left: x + 'px',
		top: y + 'px',
		width: w + 'px',
		height: h + 'px',
		transitionProperty: (skipTransition.value || idsToSkipTransition.value.has(eventId)) ? 'none' : 'all',
		transitionDuration: movementDelay.value + 'ms',
		transitionTimingFunction: 'linear',
	};
}

function getCtgColor(ctg: string){
	if (ctg == 'discovery'){
		return store.color.accent;
	} else {
		return store.color.altDark;
	}
}

function eventImgStyles(eventId: number){
	const event = idToEvent.value.get(eventId)!;
	let isSearchResult = searchEvent.value != null && searchEvent.value.id == eventId;
	let color = getCtgColor(event.ctg);
	return {
		width: store.eventImgSz + 'px',
		height: store.eventImgSz + 'px',
		backgroundImage: event.imgId == null ? 'none' : `url(${getImagePath(event.imgId)})`,
		backgroundColor: store.color.bgDark,
		backgroundSize: 'cover',
		borderColor: color,
		borderWidth: '1px',
		boxShadow: isSearchResult ? '0 0 6px 4px ' + color : 'none',
	};
}

function eventLineStyles(eventId: number){
	const [x, y, , a] = eventLines.value.get(eventId)!;
	return {
		transform: `translate(${x}px, ${y}px) rotate(${a}deg)`,
		transitionProperty: (skipTransition.value || idsToSkipTransition.value.has(eventId)) ? 'none' : 'transform',
		transitionDuration: movementDelay.value + 'ms',
		transitionTimingFunction: 'linear',
	};
}

function densityIndStyles(tickIdx: number, count: number): Record<string,string> {
	let tick = ticks.value[tickIdx];
	let numMajorUnits = getNumDisplayUnits();
	let pxOffset = tick.offset / numMajorUnits * availLen.value;
	let nextPxOffset = ticks.value[tickIdx + 1].offset / numMajorUnits * availLen.value;
	let len = nextPxOffset - pxOffset;
	let countLevel = Math.min(Math.ceil(Math.log10(count+1)), 4);
	let breadth = countLevel * 4 + 4;
	return {
		backgroundColor: store.color.altBg,
		top: vert.value ? pxOffset + 'px' : (mainlineOffset.value - breadth / 2) + 'px',
		left: vert.value ? (mainlineOffset.value - breadth / 2) + 'px' : pxOffset + 'px',
		width: vert.value ? breadth + 'px' : len + 'px',
		height: vert.value ? len + 'px' : breadth + 'px',
		transitionProperty: skipTransition.value ? 'none' : 'top, left, width, height',
		transitionDuration: movementDelay.value + 'ms',
		transitionTimingFunction: 'linear',
	}
}

function animateFailDiv(which: 'min' | 'max' | 'both' | 'bg'){
	if (which == 'min'){
		animateWithClass(minFailRef.value!, 'animate-show-then-fade');
	} else if (which == 'max'){
		animateWithClass(maxFailRef.value!, 'animate-show-then-fade');
	} else if (which == 'both'){
		animateWithClass(minFailRef.value!, 'animate-show-then-fade');
		animateWithClass(maxFailRef.value!, 'animate-show-then-fade');
	} else {
		animateWithClass(bgFailRef.value!, 'animate-red-then-fade');
	}
}

function failDivStyles(minDiv: boolean){
	const gradientDir = vert.value ? (minDiv ? 'top' : 'bottom') : (minDiv ? 'left' : 'right');
	return {
		top: vert.value ? (minDiv ? 0 : 'auto') : 0,
		bottom: vert.value ? (minDiv ? 'auto' : 0) : 'auto',
		left: vert.value ? 0 : (minDiv ? 0 : 'auto'),
		right: vert.value ? 'auto' : (minDiv ? 'auto' : 0),
		width: vert.value ? '100%' : '2cm',
		height: vert.value ? '2cm' : '100%',
		backgroundImage: `linear-gradient(to ${gradientDir}, rgba(255,0,0,0), rgba(255,0,0,0.3))`,
		opacity: 0,
	};
}
</script>
