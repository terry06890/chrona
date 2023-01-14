<template>
<div class="touch-none relative overflow-hidden z-0" ref="rootRef"
	@pointerdown="onPointerDown" @pointermove="onPointerMove" @pointerup="onPointerUp"
	@pointercancel="onPointerUp" @pointerout="onPointerUp" @pointerleave="onPointerUp"
	@wheel.exact="onWheel" @wheel.shift.exact="onShiftWheel">
	<template v-if="store.showEventCounts">
		<div v-for="[tickIdx, count] in tickToCount.entries()" :key="ticks[tickIdx].date.toInt()"
			:style="countDivStyles(tickIdx, count)" class="absolute animate-fadein"></div>
	</template>
	<svg :viewBox="`0 0 ${width} ${height}`" class="relative z-10" ref="svgRef">
		<defs>
			<linearGradient id="eventLineGradient">
				<stop offset="5%" stop-color="#a3691e"/>
				<stop offset="95%" stop-color="gold"/>
			</linearGradient>
		</defs>
		<!-- Event lines (dashed line indicates imprecise start date) -->
		<line v-for="id in eventLines.keys()" :key="id"
			x1="0" y1="0" :x2="eventLines.get(id)![2]" y2="0.01"
			stroke="url('#eventLineGradient')" stroke-width="1px"
			:stroke-dasharray="getEventPrecision(idToEvent.get(id)!) <= minorScale ? '' : '16,4'"
			:style="eventLineStyles(id)" class="animate-fadein"/>
			<!-- Note: With a fully vertical or horizontal line, nothing gets displayed -->
			<!-- Note: Can't use :x2="1" with scaling in :style="", as it makes dashed-lines non-uniform -->
		<!-- Main line (unit horizontal line that gets transformed, with extra length to avoid gaps when panning) -->
		<line :stroke="store.color.alt" stroke-width="2px" x1="-1" y1="0" x2="2" y2="0" :style="mainlineStyles"/>
		<!-- Tick markers -->
		<template v-for="tick in ticks" :key="tick.date.toInt()">
			<line v-if="tick.major && (tick.date.equals(MIN_DATE, scale) || tick.date.equals(MAX_DATE, scale))"
				:x1="vert ? -store.endTickSz / 2 : 0" :y1="vert ? 0 : -store.endTickSz / 2"
				:x2="vert ?  store.endTickSz / 2 : 0" :y2="vert ? 0 :  store.endTickSz / 2"
				:stroke="store.color.alt" :stroke-width="`${store.endTickSz}px`"
				:style="tickStyles(tick)" class="animate-fadein"/>
			<line v-else
				:x1="vert ? -store.tickLen / 2 : 0" :y1="vert ? 0 : -store.tickLen / 2"
				:x2="vert ?  store.tickLen / 2 : 0" :y2="vert ? 0 :  store.tickLen / 2"
				:stroke="store.color.alt" stroke-width="1px"
				:style="tickStyles(tick)" class="animate-fadein"/>
		</template>
		<!-- Tick labels -->
		<template v-for="tick in ticks" :key="tick.date.toInt()">
			<text v-if="tick.major || store.showMinorTicks"
				x="0" y="0" :text-anchor="vert ? 'start' : 'middle'" dominant-baseline="middle"
				:fill="store.color.textDark" :style="tickLabelStyles(tick)"
				class="text-sm animate-fadein cursor-default select-none">
				{{tick.date.toTickString()}}
			</text>
		</template>
	</svg>
	<!-- Events -->
	<div v-for="id in idToPos.keys()" :key="id" class="absolute animate-fadein z-20" :style="eventStyles(id)">
		<!-- Image -->
		<div class="rounded-full cursor-pointer hover:brightness-125" :style="eventImgStyles(id)"
			:title="idToEvent.get(id)!.title" @click="emit('info-click', idToEvent.get(id)!.title)"></div>
		<!-- Label -->
		<div class="text-center text-stone-100 text-sm whitespace-nowrap text-ellipsis overflow-hidden select-none">
			{{idToEvent.get(id)!.title}}
		</div>
	</div>
	<!-- Timeline position label -->
	<div class="absolute top-2 left-2 z-20 text-lg" :class="[current ? 'text-yellow-300' : 'text-stone-50']">
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
// Components
import IconButton from './IconButton.vue';
// Icons
import CloseIcon from './icon/CloseIcon.vue';
// Other
import {WRITING_MODE_HORZ, MIN_DATE, MAX_DATE, MONTH_SCALE, DAY_SCALE, SCALES, MONTH_NAMES, MIN_CAL_DATE,
	getDaysInMonth, HistDate, stepDate, getScaleRatio, getNumSubUnits, getUnitDiff,
	getEventPrecision, dateToUnit, dateToScaleDate,
	moduloPositive, TimelineState, HistEvent, getImagePath} from '../lib';
import {useStore} from '../store';
import {RBTree} from '../rbtree';

// Refs
const rootRef: Ref<HTMLElement | null> = ref(null);
const svgRef: Ref<HTMLElement | null> = ref(null);

// Global store
const store = useStore();

// Props + events
const props = defineProps({
	vert: {type: Boolean, required: true},
	closeable: {type: Boolean, default: true},
	initialState: {type: Object as PropType<TimelineState>, required: true},
	eventTree: {type: Object as PropType<RBTree<HistEvent>>, required: true},
	unitCountMaps: {type: Object as PropType<Map<number, number>[]>, required: true},
	current: {type: Boolean, required: true},
	searchTarget: {type: Object as PropType<[null | HistEvent, boolean]>, required: true},
});
const emit = defineEmits(['close', 'state-chg', 'event-display', 'info-click']);

// For size tracking
const width = ref(0);
const height = ref(0);
const availLen = computed(() => props.vert ? height.value : width.value);
const availBreadth = computed(() => props.vert ? width.value : height.value);
const mounted = ref(false);
onMounted(() => {
	let rootEl = rootRef.value!;
	width.value = rootEl.offsetWidth;
	height.value = rootEl.offsetHeight;
	mounted.value = true;
})
const resizeObserver = new ResizeObserver((entries) => {
	for (const entry of entries){
		if (entry.contentBoxSize){
			// Get resized dimensions
			const boxSize = Array.isArray(entry.contentBoxSize) ? entry.contentBoxSize[0] : entry.contentBoxSize;
			width.value = WRITING_MODE_HORZ ? boxSize.inlineSize : boxSize.blockSize;
			height.value = WRITING_MODE_HORZ ? boxSize.blockSize : boxSize.inlineSize;
			// Check for horz/vert swap
			skipTransition.value = true;
			setTimeout(() => {skipTransition.value = false}, 100); // Note: Using nextTick() doesn't work
		}
	}
});
onMounted(() => resizeObserver.observe(rootRef.value as HTMLElement));

//
const eventWidth = computed(() => store.eventImgSz);
const eventHeight = computed(() => store.eventImgSz + store.eventLabelHeight);
const eventMajorSz = computed(() => props.vert ? eventHeight.value : eventWidth.value);
const eventMinorSz = computed(() => props.vert ? eventWidth.value : eventHeight.value)
const sideMainline = computed( // True if unable to fit mainline in middle with events on both sides
	() => availBreadth.value < store.mainlineBreadth + (eventMinorSz.value + store.spacing * 2) * 2);
const mainlineOffset = computed(() => { // Distance from mainline-area line to left/top of display area
	if (!sideMainline.value){
		return availBreadth.value / 2 - store.mainlineBreadth /2 + store.largeTickLen / 2;
	} else {
		return availBreadth.value - store.spacing - tickLabelMargin.value
			- (props.vert ? tickLabelWidth.value : store.tickLabelHeight);
	}
});

// Timeline data
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
//
function initScale(){ // Initialises to smallest usable scale
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
	//
	scaleIdx.value = idx;
	onStateChg();
}

// Tick data
const tickLabelMargin = computed(() => props.vert ? 20 : 30); // Distance from label to mainline
const tickLabelWidth = computed(() => store.mainlineBreadth - store.largeTickLen / 2 - tickLabelMargin.value);
class Tick {
	date: HistDate;
	major: boolean; // False if tick is on the minor scale
	offset: number; // Distance from start of visible timeline, in major units
	constructor(date: HistDate, major: boolean, offset: number){
		this.date = date;
		this.major = major;
		this.offset = offset;
	}
}
function getNumDisplayUnits({inclOffsets=true} = {}): number { // Get num major units in display range
	let unitDiff = Math.ceil(getUnitDiff(startDate.value, endDate.value, scale.value));
		// Note: Rounding up due to cases like 1 AD to 10 AD with 10-year scale
	if (inclOffsets){
		unitDiff += startOffset.value + endOffset.value;
	}
	return unitDiff;
}
function getMinorTicks(date: HistDate, scaleIdx: number, majorUnitSz: number, majorOffset: number): Tick[] {
	// For a major unit, returns an array specifying minor ticks to show
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
		ticks.push(new Tick(date, true, startOffset.value + i));
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
	//
	ticks = [...ticksBefore, ...ticks, ...ticksAfter];
	return ticks;
});
const firstIdx = computed((): number => { // Index of first major tick after which events are visible (-1 if none)
	// Looks for a first visible major tick, and uses a preceding tick if present
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
const firstDate = computed(() => firstIdx.value < 0 ? startDate.value : ticks.value[firstIdx.value]!.date);
const lastIdx = computed((): number => { // Index of last major tick before which events are visible (-1 if none)
	// Looks for a last visible major tick, and uses a following tick if present
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
const lastDate = computed(() => lastIdx.value < 0 ? endDate.value : ticks.value[lastIdx.value]!.date);
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

// For displayed events
function dateToOffset(date: HistDate){ // Assumes 'date' is >=firstDate and <=lastDate
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
const idToEvent = computed(() => { // Maps visible event IDs to HistEvents
	let map: Map<number, HistEvent> = new Map();
	// Find events to display
	let itr = props.eventTree.lowerBound(new HistEvent(0, '', firstDate.value));
	while (itr.data() != null){
		let event = itr.data()!;
		itr.next();
		if (dateToUnit(event.start, scale.value) > dateToUnit(lastDate.value, scale.value)){
			break;
		}
		if ((store.ctgs as {[ctg: string]: boolean})[event.ctg] == false){
			continue;
		}
		map.set(event.id, event);
	}
	return map;
});
watch(idToEvent, () => { // Remove highlighting of search results that have become out of range
	if (searchEvent.value != null && !idToEvent.value.has(searchEvent.value.id)){
		searchEvent.value = null;
	}
});
const idToPos: Ref<Map<number, [number, number, number, number]>> = ref(new Map()); // Maps event IDs to x/y/w/h
const idsToSkipTransition: Ref<Set<number>> = ref(new Set()); // Used to prevent events moving across mainline
type LineCoords = [number, number, number, number]; // x, y, length, angle
const eventLines: Ref<Map<number, LineCoords>> = ref(new Map()); // Maps event ID to event line data
function getEventLayout(): Map<number, [number, number, number, number]> {
	let map: Map<number, [number, number, number, number]> = new Map();
	if (!mounted.value){
		return map;
	}
	// Determine columns to place event elements in (or rows if !props.vert)
	let cols: [number, number][][] = []; // For each column, for each laid out event, stores an ID and pixel offset
	let colOffsets: number[] = []; // Stores the pixel offset of each column
	let afterMainlineIdx: number | null = null; // Index of first column after the mainline, if there is one
	if (!sideMainline.value){
		// Get columns before mainline area
		let columnOffset = availBreadth.value / 2 - store.mainlineBreadth / 2 - store.spacing - eventMinorSz.value;
		while (columnOffset >= store.spacing){
			cols.push([]);
			colOffsets.push(columnOffset);
			columnOffset -= eventMinorSz.value + store.spacing;
		}
		colOffsets.reverse();
		afterMainlineIdx = cols.length;
		// Get columns after mainline area
		columnOffset = availBreadth.value / 2 + store.mainlineBreadth / 2 + store.spacing;
		while (columnOffset + eventMinorSz.value + store.spacing < availBreadth.value){
			cols.push([]);
			colOffsets.push(columnOffset);
			columnOffset += eventMinorSz.value + store.spacing;
		}
	} else {
		// Get columns before mainline area
		let columnOffset = mainlineOffset.value - store.spacing - eventMinorSz.value - store.spacing;
		while (columnOffset >= store.spacing){
			cols.push([]);
			colOffsets.push(columnOffset);
			columnOffset -= eventMinorSz.value + store.spacing;
		}
		colOffsets.reverse();
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
		let pxOffset = dateToOffset(event.start) / numUnits * availLen.value - eventMajorSz.value / 2;
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
			if (props.vert){
				map.set(eventId, [minorOffset, majorOffset, eventWidth.value, eventHeight.value]);
			} else {
				map.set(eventId, [majorOffset, minorOffset, eventWidth.value, eventHeight.value]);
			}
		}
	}
	return map;
}
watch(idToEvent, () => { // Updates idToPos and eventLines
	let map = getEventLayout();
	// Check for events that cross mainline
	idsToSkipTransition.value.clear();
	for (let [eventId, [x, y, , ]] of map.entries()){
		if (idToPos.value.has(eventId)){
			let [oldX, oldY, , ] = idToPos.value.get(eventId)!;
			if (props.vert && (oldX - mainlineOffset.value) * (x - mainlineOffset.value) < 0
					|| !props.vert && (oldY - mainlineOffset.value) * (y - mainlineOffset.value) < 0){
				idsToSkipTransition.value.add(eventId);
			}
		}
	}
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
		let unitOffset = dateToOffset(event.start);
		let posFrac = unitOffset / numUnits;
		if (props.vert){
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
});

// For event-count indicators
const tickToCount = computed((): Map<number, number> => {
	let tickToCount: Map<number, number> = new Map(); // Maps tick index to event count
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

// For timeline position label
const timelinePosStr = computed((): string => {
	const date1 = startIsFirstVisible.value ? startDate.value : firstDate.value;
	const date2 = endIsLastVisible.value ? endDate.value : lastDate.value;
	if (minorScale.value == DAY_SCALE){
		const multiMonth = date1.month != date2.month;
		return `${date1.toYearString()} ${MONTH_NAMES[date1.month - 1]}${multiMonth ? ' >' : ''}`;
	} else if (minorScale.value == MONTH_SCALE){
		const multiYear = date1.year != date2.year;
		return `${date1.toYearString()}${multiYear ? ' >' : ''}`;
	} else {
		if (date1.year > 0){
			return `${date1.toYearString()} - ${date2.toYearString()}`;
		} else {
			return `${date1.toYearString()} >`;
		}
	}
});

// For panning/zooming
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
					console.log('Reached maximum date limit');
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
					console.log('Reached minimum date limit');
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
		console.log('Unable to pan into dates where months/days are invalid');
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
function zoomTimeline(zoomRatio: number, ignorePointer=false){
	if (zoomRatio > 1
			&& startDate.value.equals(MIN_DATE, scale.value)
			&& endDate.value.equals(MAX_DATE, scale.value)){
		console.log('Reached upper scale limit');
		return;
	}
	let numUnits = getNumDisplayUnits();
	let newNumUnits = numUnits * zoomRatio;
	// Get tentative bound changes
	let startChg: number;
	let endChg: number;
	let ptrOffset = props.vert ? pointerY : pointerX;
	if (ptrOffset == null || ignorePointer){
		let unitChg = newNumUnits - numUnits;
		startChg = -unitChg / 2;
		endChg = unitChg / 2;
	} else { // Pointer-centered zoom
		// Get element-relative ptrOffset
		let innerOffset = 0;
		if (rootRef.value != null){ // Can become null during dev-server hot-reload for some reason
			let rect = rootRef.value.getBoundingClientRect();
			innerOffset = props.vert ? ptrOffset - rect.top : ptrOffset - rect.left;
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
				console.log('Restricting new range to dates where month/day scale is usable');
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
			console.log('Reached zoom out limit');
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
			//
			scaleIdx.value -= 1;
		}
	} else { // If trying to zoom in
		if (scaleIdx.value == SCALES.length - 1){
			if (newNumUnits < store.minLastTicks){
				console.log('Reached zoom in limit');
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
					console.log('Unable to zoom into range where month/day scale is invalid');
					return;
				}
				scaleIdx.value += 1;
			}
		}
	}
	//
	startDate.value = newStart;
	endDate.value = newEnd;
	startOffset.value = newStartOffset;
	endOffset.value = newEndOffset;
}
function getMovedBounds(
		startOffset: number, endOffset: number, startChg: number, endChg: number): [number, number, number, number] {
	// Returns a number of start and end steps to take, and new start and end offset values
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

// For mouse/etc handling
let pointerX: number | null = null; // Used for pointer-centered zooming
let pointerY: number | null = null;
const ptrEvtCache: PointerEvent[] = []; // Holds last captured PointerEvent for each pointerId (used for pinch-zoom)
let lastPinchDiff = -1; // Holds last x/y distance between two pointers that are down
let dragDiff = 0; // Holds accumlated change in pointer's x/y coordinate while dragging
let dragHandler = 0; // Set by a setTimeout() to a handler for pointer dragging
let dragVelocity: number; // Used to add 'drag momentum'
let vUpdateTime: number; // Holds timestamp for last update of 'dragVelocity'
let vPrevPointer: null | number; // Holds pointerX/pointerY used for last update of 'dragVelocity'
let vUpdater = 0; // Set by a setInterval(), used to update 'dragVelocity'
function onPointerDown(evt: PointerEvent){
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
		if (vPrevPointer != null){
			let time = Date.now();
			let ptrDiff = (props.vert ? pointerY! : pointerX!) - vPrevPointer;
			dragVelocity = ptrDiff / (time - vUpdateTime) * 1000;
			vUpdateTime = time;
		}
		vPrevPointer = (props.vert ? pointerY : pointerX);
	}, 50);
}
function onPointerMove(evt: PointerEvent){
	// Update event cache
	if (ptrEvtCache.length > 0){
		const index = ptrEvtCache.findIndex((e) => e.pointerId == evt.pointerId);
		ptrEvtCache[index] = evt;
	}
	//
	if (ptrEvtCache.length == 1){
		// Handle pointer dragging
		dragDiff += props.vert ? evt.clientY - pointerY! : evt.clientX - pointerX!;
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
		const pinchDiff = Math.abs(props.vert ?
			ptrEvtCache[0].clientY - ptrEvtCache[1].clientY :
			ptrEvtCache[0].clientX - ptrEvtCache[1].clientX);
		if (lastPinchDiff > 0){
			if (pinchDiff > lastPinchDiff){
				console.log('Pinching out, zooming in');
				//TODO: implement pinch-zooming
			} else if (pinchDiff < lastPinchDiff){
				console.log('Pinching in, zooming out');
				//TODO: implement pinch-zooming
			}
		}
		lastPinchDiff = pinchDiff;
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
		if (lastPinchDiff == -1 && Math.abs(dragVelocity) > 10){
			let scrollChg = dragVelocity * store.dragInertia;
			panTimeline(-scrollChg / availLen.value);
		}
	}
	//
	if (ptrEvtCache.length < 2){
		lastPinchDiff = -1;
	}
	dragDiff = 0;
}
function onWheel(evt: WheelEvent){
	let shiftDir = (evt.deltaY > 0 ? 1 : -1) * (!props.vert ? -1 : 1);
	panTimeline(shiftDir * store.scrollRatio);
}
function onShiftWheel(evt: WheelEvent){
	let zoomRatio = evt.deltaY > 0 ? store.zoomRatio : 1/store.zoomRatio;
	zoomTimeline(zoomRatio);
}

// For bound-change signalling
function onStateChg(){
	emit('state-chg', new TimelineState(
		ID, startDate.value, endDate.value, startOffset.value, endOffset.value, scaleIdx.value
	));
}
watch(startDate, onStateChg);

// For jumping to search result
const searchEvent = ref(null as null | HistEvent); // Holds most recent search result
watch(() => props.searchTarget, () => {
	const event = props.searchTarget[0];
	if (event == null){
		return;
	}
	if (!idToPos.value.has(event.id)){ // If not already visible
		// Determine new time range
		let tempScale = scale.value;
		let targetDate = event.start;
		if (targetDate.isEarlier(MIN_CAL_DATE) && tempScale < 1){ // Account for jumping out of calendar limits
			tempScale = getEventPrecision(event);
		}
		targetDate = dateToScaleDate(targetDate, tempScale);
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
		startDate.value = targetStart;
		endDate.value = targetEnd;
		scaleIdx.value = SCALES.findIndex((s: number) => s == tempScale);
	}
	searchEvent.value = event;
});

// For keyboard shortcuts
function onKeyDown(evt: KeyboardEvent){
	if (!props.current || store.disableShortcuts){
		return;
	}
	if (evt.key == 'ArrowUp'){
		if (evt.shiftKey){
			zoomTimeline(1/store.zoomRatio, true);
		} else if (props.vert){
			panTimeline(-store.scrollRatio);
		}
	} else if (evt.key == 'ArrowDown'){
		if (evt.shiftKey){
			zoomTimeline(store.zoomRatio, true);
		} else if (props.vert){
			panTimeline(store.scrollRatio);
		}
	} else if (evt.key == 'ArrowLeft'){
		if (!props.vert){
			panTimeline(-store.scrollRatio);
		}
	} else if (evt.key == 'ArrowRight'){
		if (!props.vert){
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

// For skipping transitions on startup (and on horz/vert swap)
const skipTransition = ref(true);
onMounted(() => setTimeout(() => {skipTransition.value = false}, 100));

// Styles
const mainlineStyles = computed(() => {
	return {
		transform: props.vert ?
			`translate(${mainlineOffset.value}px, 0) rotate(90deg) scale(${availLen.value},1)` :
			`translate(0, ${mainlineOffset.value}px) rotate(0deg) scale(${availLen.value},1)`,
		transitionProperty: skipTransition.value ? 'none' : 'transform',
		transitionDuration: store.transitionDuration + 'ms',
		transitionTimingFunction: 'ease-out',
	};
});
function tickStyles(tick: Tick){
	let numMajorUnits = getNumDisplayUnits();
	let pxOffset = tick.offset / numMajorUnits * availLen.value;
	let scaleFactor = tick.major ? store.largeTickLen / store.tickLen : 1;
	return {
		transform: props.vert ?
			`translate(${mainlineOffset.value}px,  ${pxOffset}px) scale(${scaleFactor})` :
			`translate(${pxOffset}px, ${mainlineOffset.value}px) scale(${scaleFactor})`,
		transitionProperty: skipTransition.value ? 'none' : 'transform, opacity',
		transitionDuration: store.transitionDuration + 'ms',
		transitionTimingFunction: 'linear',
		opacity: (pxOffset >= 0 && pxOffset <= availLen.value) ? 1 : 0,
	}
}
function tickLabelStyles(tick: Tick){
	let numMajorUnits = getNumDisplayUnits();
	let pxOffset = tick.offset / numMajorUnits * availLen.value;
	let pxOffset2 = tick.major ? 20 : 0;
	let labelSz = props.vert ? store.tickLabelHeight : tickLabelWidth.value;
	return {
		transform: props.vert ?
			`translate(${mainlineOffset.value + tickLabelMargin.value + pxOffset2}px, ${pxOffset}px)` :
			`translate(${pxOffset}px, ${mainlineOffset.value + tickLabelMargin.value + pxOffset2}px)`,
		transitionProperty: skipTransition.value ? 'none' : 'transform, opacity',
		transitionDuration: store.transitionDuration + 'ms',
		transitionTimingFunction: 'linear',
		display: (pxOffset >= labelSz && pxOffset <= availLen.value - labelSz) ? 'block' : 'none',
	}
}
function eventStyles(eventId: number){
	const [x, y, w, h] = idToPos.value.get(eventId)!;
	return {
		left: x + 'px',
		top: y + 'px',
		width: w + 'px',
		height: h + 'px',
		transitionProperty: (skipTransition.value || idsToSkipTransition.value.has(eventId)) ? 'none' : 'all',
		transitionDuration: store.transitionDuration + 'ms',
		transitionTimingFunction: 'ease-out',
	};
}
function eventImgStyles(eventId: number){
	const event = idToEvent.value.get(eventId)!;
	let isSearchResult = searchEvent.value != null && searchEvent.value.id == eventId;
	let color = event.ctg == 'discovery' ? store.color.accent : store.color.altDark;
	return {
		width: store.eventImgSz + 'px',
		height: store.eventImgSz + 'px',
		backgroundImage: `url(${getImagePath(event.imgId)})`,
		backgroundColor: store.color.bgDark,
		backgroundSize: 'cover',
		borderColor: color,
		borderWidth: '1px',
		boxShadow: isSearchResult ? '0 0 4px 2px ' + color : 'none',
	};
}
function eventLineStyles(eventId: number){
	const [x, y, , a] = eventLines.value.get(eventId)!;
	return {
		transform: `translate(${x}px, ${y}px) rotate(${a}deg)`,
		transitionProperty: (skipTransition.value || idsToSkipTransition.value.has(eventId)) ? 'none' : 'transform',
		transitionDuration: store.transitionDuration + 'ms',
		transitionTimingFunction: 'ease-out',
	};
}
function countDivStyles(tickIdx: number, count: number): Record<string,string> {
	let tick = ticks.value[tickIdx];
	let numMajorUnits = getNumDisplayUnits();
	let pxOffset = tick.offset / numMajorUnits * availLen.value;
	let nextPxOffset = ticks.value[tickIdx + 1].offset / numMajorUnits * availLen.value;
	let len = nextPxOffset - pxOffset;
	let countLevel = Math.min(Math.ceil(Math.log10(count+1)), 4);
	let breadth = countLevel * 4 + 4;
	return {
		backgroundColor: store.color.altBg,
		top: props.vert ? pxOffset + 'px' : (mainlineOffset.value - breadth / 2) + 'px',
		left: props.vert ? (mainlineOffset.value - breadth / 2) + 'px' : pxOffset + 'px',
		width: props.vert ? breadth + 'px' : len + 'px',
		height: props.vert ? len + 'px' : breadth + 'px',
		transitionProperty: skipTransition.value ? 'none' : 'top, left, width, height',
		transitionDuration: store.transitionDuration + 'ms',
		transitionTimingFunction: 'linear',
	}
}
</script>
