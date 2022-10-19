<template>
<div class="touch-none relative"
	@pointerdown.prevent="onPointerDown" @pointermove.prevent="onPointerMove" @pointerup.prevent="onPointerUp"
	@pointercancel.prevent="onPointerUp" @pointerout.prevent="onPointerUp" @pointerleave.prevent="onPointerUp"
	@wheel.exact.prevent="onWheel" @wheel.shift.exact.prevent="onShiftWheel"
	ref="rootRef">
	<svg :viewBox="`0 0 ${width} ${height}`">
		<defs>
			<linearGradient id="eventLineGradient">
				<stop offset="5%" stop-color="#a3691e"/>
				<stop offset="95%" stop-color="gold"/>
			</linearGradient>
		</defs>
		<!-- Tick markers -->
		<template v-for="date, idx in ticks.dates" :key="date.toInt()">
			<line v-if="date.equals(MIN_DATE, scale) || date.equals(MAX_DATE, scale)"
				:x1="vert ? -END_TICK_SZ : 0" :y1="vert ? 0 : -END_TICK_SZ"
				:x2="vert ?  END_TICK_SZ : 0" :y2="vert ? 0 :  END_TICK_SZ"
				:stroke="store.color.alt" :stroke-width="`${END_TICK_SZ * 2}px`"
				:style="tickStyles(idx)" class="animate-fadein"/>
			<line v-else
				:x1="vert ? -TICK_LEN : 0" :y1="vert ? 0 : -TICK_LEN"
				:x2="vert ?  TICK_LEN : 0" :y2="vert ? 0 :  TICK_LEN"
				:stroke="store.color.alt" stroke-width="1px"
				:style="tickStyles(idx)" class="animate-fadein"/>
		</template>
		<!-- Event lines -->
		<line v-for="id in eventLines.keys()" :key="id"
			x1="0" y1="0" x2="1" y2="0.01" stroke="url('#eventLineGradient')" stroke-width="1px"
			:style="eventLineStyles(id)" class="animate-fadein"/>
			<!-- Note: With a fully vertical or horizontal line, nothing gets displayed -->
		<!-- Tick labels -->
		<text v-for="date, idx in ticks.dates" :key="date.toInt()"
			x="0" y="0" :text-anchor="vert ? 'start' : 'middle'" dominant-baseline="middle"
			:fill="store.color.textDark" :style="tickLabelStyles(idx)" class="text-sm animate-fadein">
			{{date}}
		</text>
		<!-- Main line (unit horizontal line that gets transformed, with extra length to avoid gaps when panning) -->
		<line :stroke="store.color.alt" stroke-width="2px" x1="-1" y1="0" x2="2" y2="0" :style="mainlineStyles"/>
	</svg>
	<!-- Events -->
	<div v-for="id in idToPos.keys()" :key="id" class="absolute animate-fadein" :style="eventStyles(id)">
		<!-- Label -->
		<div class="text-center text-stone-100 text-sm whitespace-nowrap text-ellipsis overflow-hidden">
			{{idToEvent.get(id)!.title}}
		</div>
		<!-- Image -->
		<div class="rounded-full border border-yellow-500" :style="eventImgStyles(id)"></div>
	</div>
	<!-- Buttons -->
	<icon-button :size="30" class="absolute top-2 right-2"
		:style="{color: store.color.text, backgroundColor: store.color.altDark2}"
		@click="emit('remove')" title="Remove timeline">
		<minus-icon/>
	</icon-button>
</div>
</template>

<script setup lang="ts">
import {ref, onMounted, computed, watch, watchEffect, PropType, Ref, shallowRef, ShallowRef} from 'vue';
// Components
import IconButton from './IconButton.vue';
// Icons
import MinusIcon from './icon/MinusIcon.vue';
// Other
import {WRITING_MODE_HORZ, MIN_DATE, MAX_DATE, MONTH_SCALE, DAY_SCALE, SCALES, MIN_CAL_DATE,
	HistDate, stepDate, inDateScale, getScaleRatio, getUnitDiff, getDaysInMonth, moduloPositive, TimelineState,
	HistEvent, getImagePath} from '../lib';
import {useStore} from '../store';
import {RBTree} from '../rbtree';

// Refs
const rootRef: Ref<HTMLElement | null> = ref(null);

// Global store
const store = useStore();

// Props + events
const props = defineProps({
	vert: {type: Boolean, required: true},
	initialState: {type: Object as PropType<TimelineState>, required: true},
	eventTree: {type: Object as PropType<RBTree<HistEvent>>, required: true},
});
const emit = defineEmits(['remove', 'state-chg', 'event-req', 'event-display']);

// For size tracking
const width = ref(0);
const height = ref(0);
const availLen = computed(() => props.vert ? height.value : width.value);
const availBreadth = computed(() => props.vert ? width.value : height.value);
const prevVert = ref(props.vert); // For skipping transitions on horz/vert swap
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
			if (props.vert != prevVert.value){
				skipTransition.value = true;
				setTimeout(() => {skipTransition.value = false}, 100); // Note: Using nextTick() doesn't work
				prevVert.value = props.vert;
			}
		}
	}
});
onMounted(() => resizeObserver.observe(rootRef.value as HTMLElement));

//
const MAINLINE_WIDTH = 80; // Breadth of mainline area (including ticks and labels)
const EVENT_IMG_SZ = 100; // Width/height of event images
const EVENT_LABEL_HEIGHT = 15;
const eventWidth = computed(() => EVENT_IMG_SZ);
const eventHeight = computed(() => EVENT_IMG_SZ + EVENT_LABEL_HEIGHT);
const eventMajorSz = computed(() => props.vert ? eventHeight.value : eventWidth.value);
const eventMinorSz = computed(() => props.vert ? eventWidth.value : eventHeight.value)
const SPACING = 10;
const sideMainline = computed( // True if unable to fit mainline in middle with events on both sides
	() => availBreadth.value < MAINLINE_WIDTH + (eventMinorSz.value + SPACING * 2) * 2);
const mainlineOffset = computed(() => { // Distance from side of display area
	if (!sideMainline.value){
		return availBreadth.value / 2 - MAINLINE_WIDTH /2 + LARGE_TICK_LEN;
	} else if (props.vert){
		return SPACING + LARGE_TICK_LEN;
	} else {
		return availBreadth.value - SPACING - tickLabelMargin.value - TICK_LABEL_HEIGHT;
	}
});

// Timeline data
const ID = props.initialState.id as number;
const startDate = ref(props.initialState.startDate); // Earliest date to display
const endDate = ref(props.initialState.endDate);
const INITIAL_EXTRA_OFFSET = 0.5;
const startOffset = ref(INITIAL_EXTRA_OFFSET); // Fraction of a scale unit before startDate to show
	// Note: Without this, the timeline can only move if the distance is over one unit, which makes dragging awkward,
		// can cause unexpected jumps when zooming, and limits display when a unit has many ticks on the next scale
const endOffset = ref(INITIAL_EXTRA_OFFSET);
const scaleIdx = ref(0); // Index of current scale in SCALES
const scale = computed(() => SCALES[scaleIdx.value])
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
	if (startDate.value.isEarlier(MIN_CAL_DATE)){ // If unable to use JDNs, use a yearly scale
		scaleIdx.value = getYearlyScale(startDate.value, endDate.value, availLen.value);
	} else {
		let dayDiff = startDate.value.getDayDiff(endDate.value) + startOffset.value + endOffset.value;
		// Check for day scale usability
		if (availLen.value / dayDiff >= MIN_TICK_SEP){
			scaleIdx.value = SCALES.findIndex(s => s == DAY_SCALE);
		} else {
			// Check for month scale usability
			let monthDiff = startDate.value.getMonthDiff(endDate.value) + startOffset.value + endOffset.value;
			if (availLen.value / monthDiff >= MIN_TICK_SEP){
				scaleIdx.value = SCALES.findIndex(s => s == MONTH_SCALE);
			} else { // Use a yearly scale
				scaleIdx.value = getYearlyScale(startDate.value, endDate.value, availLen.value);
			}
		}
	}
}
function getYearlyScale(startDate: HistDate, endDate: HistDate, availLen: number){
	// Get the smallest yearly scale that divides a date range, without making ticks too close
	let yearDiff = startDate.getYearDiff(endDate);
	let idx = 0;
	while (SCALES[idx] >= yearDiff){ // Get scale with units smaller than yearDiff
		idx += 1;
	}
	while (idx < SCALES.length - 1){ // Check for usable smaller scales
		let nextScale = SCALES[idx + 1]
		let adjustedYearDiff = yearDiff + startOffset.value * nextScale + endOffset.value * nextScale;
		if (availLen / (adjustedYearDiff / nextScale) >= MIN_TICK_SEP){
			idx += 1;
		} else {
			break;
		}
	}
	return idx;
}

// Tick data
const TICK_LEN = 8; // Length of half of tick
const LARGE_TICK_LEN = 16;
const END_TICK_SZ = 4; // Size for MIN_DATE/MAX_DATE ticks
const MIN_TICK_SEP = 30; // Smallest px separation between ticks
const MIN_LAST_TICKS = 3; // When at smallest scale, don't zoom further into less than this many ticks
const TICK_LABEL_HEIGHT = 10;
const tickLabelMargin = computed(() => props.vert ? 20 : 30); // Distance from label to mainline
const tickLabelWidth = computed(() => MAINLINE_WIDTH - LARGE_TICK_LEN - tickLabelMargin.value);
type Ticks = {
	dates: HistDate[], // One for each tick to render
	startIdx: number,
		// Index of first visible tick (hidden ticks are used for smoother transitions)
		// Ignored if 'dates' is empty
	endIdx: number, // Index of last visible tick
};
function getNumVisibleUnits(): number {
	let unitDiff = getUnitDiff(startDate.value, endDate.value, scale.value);
	return unitDiff + startOffset.value + endOffset.value;
}
const ticks = computed((): Ticks => {
	if (!mounted.value){
		return {dates: [], startIdx: 0, endIdx: 0};
	}
	let numUnits = getNumVisibleUnits();
	let dates: HistDate[] = [];
	let startIdx: number;
	let endIdx: number;
	// Get hidden preceding ticks
	let panUnits = Math.floor(numUnits * store.scrollRatio); // Potential distance shifted upon a pan action
	if (MIN_DATE.isEarlier(startDate.value, scale.value)){
		let date = startDate.value;
		for (let i = 0; i < panUnits; i++){
			date = stepDate(date, scale.value, {forward: false});
			dates.push(date);
			if (MIN_DATE.equals(date, scale.value)){
				break;
			}
		}
		dates.reverse();
	}
	startIdx = dates.length;
	// Get visible ticks
	let date = startDate.value.clone()
	dates.push(date);
	for (let i = 0; i < Math.round(numUnits - startOffset.value - endOffset.value); i++){
		date = stepDate(date, scale.value);
		dates.push(date);
	}
	endIdx = dates.length - 1;
	// Get hidden following ticks
	if (date.isEarlier(MAX_DATE, scale.value)){
		for (let i = 0; i < panUnits; i++){
			date = stepDate(date, scale.value);
			dates.push(date);
			if (MAX_DATE.equals(date, scale.value)){
				break;
			}
		}
	}
	// Get hidden ticks that might transition in after zooming
	let datesBefore: HistDate[] = [];
	let datesAfter: HistDate[] = [];
	if (scaleIdx.value > 0 &&
			availLen.value / (numUnits * store.zoomRatio) < MIN_TICK_SEP){ // If zoom-out would decrease scale
		let zoomUnits = numUnits * (store.zoomRatio - 1); // Potential distance shifted upon a zoom-out
		if (zoomUnits > panUnits){
			let zoomedScale = SCALES[scaleIdx.value-1];
			let unitsPerZoomedUnit = getScaleRatio(scale.value, zoomedScale);
			date = dates[0];
			// Get preceding ticks
			for (let i = 0; i < (zoomUnits - panUnits) / unitsPerZoomedUnit; i++){
				date = stepDate(date, zoomedScale, {forward: false});
				if (date.isEarlier(MIN_DATE, scale.value)){
					break;
				}
				datesBefore.push(date);
			}
			datesBefore.reverse();
			// Get following ticks
			date = dates[dates.length - 1];
			for (let i = 0; i < (zoomUnits - panUnits) / unitsPerZoomedUnit; i++){
				date = stepDate(date, zoomedScale);
				if (MAX_DATE.isEarlier(date, scale.value)){
					break;
				}
				datesAfter.push(date);
			}
		}
	}
	//
	dates = [...datesBefore, ...dates, ...datesAfter];
	startIdx += datesBefore.length;
	endIdx += datesBefore.length;
	return {dates, startIdx, endIdx};
});

// For displayed events
const idToEvent = computed(() => { // Maps visible event IDs to HistEvents
	let map: Map<number, HistEvent> = new Map();
	// Find events to display
	let itr = props.eventTree.lowerBound(new HistEvent(0, '', startDate.value));
	while (itr.data() != null){
		let event = itr.data()!;
		itr.next();
		if (endDate.value.isEarlier(event.start)){
			break;
		}
		map.set(event.id, event);
	}
	return map;
});
const idToPos = computed(() => {
	if (!mounted.value){
		return new Map();
	}
	let map: Map<number, [number, number, number, number]> = new Map(); // Maps visible event IDs to x/y/w/h
	// Do basic grid-like layout
	let posX = SPACING, posY = SPACING;
	let full = false;
	for (let event of idToEvent.value.values()){
		// Layout as if props.vert
		if (posY + eventMajorSz.value + SPACING > availLen.value){ // If at end of column
			posY = SPACING;
			posX += eventMinorSz.value + SPACING;
			// If finished last row
			if (posX + eventMinorSz.value + SPACING > availBreadth.value){
				full = true;
				break;
			}
		}
		// Avoid collision with timeline
		if (!sideMainline.value){
			if (posX <= availBreadth.value / 2 + MAINLINE_WIDTH / 2 + SPACING &&
					posX + eventMinorSz.value >= availBreadth.value / 2 - MAINLINE_WIDTH / 2 - SPACING){
				posX = availBreadth.value / 2 + MAINLINE_WIDTH / 2 + SPACING;
			}
		} else {
			if (props.vert){
				if (posX <= SPACING + MAINLINE_WIDTH + SPACING){
					posX = SPACING + MAINLINE_WIDTH + SPACING;
				}
			} else {
				if (posX + eventMinorSz.value + SPACING > mainlineOffset.value){
					break;
				}
			}
		}
		// Add coords
		if (props.vert){
			map.set(event.id, [posX, posY, eventWidth.value, eventHeight.value]);
		} else {
			map.set(event.id, [posY, posX, eventWidth.value, eventHeight.value]);
		}
		// Update to next position
		posY += eventMajorSz.value + SPACING;
	}
	// If more events could be displayed, notify parent
	if (!full){
		emit('event-req', startDate.value, endDate.value);
	} else { // Send displayed event IDs to parent
		emit('event-display', [...idToEvent.value.keys()], ID);
	}
	//
	return map;
});
type LineCoords = [number, number, number, number];
const eventLines: ShallowRef<Map<number, LineCoords>> = shallowRef(new Map());
	// Maps event ID to event line data (x, y, length, and angle)
watchEffect(() => { // Used instead of computed() in order to access old values
	let newEventLines: Map<number, LineCoords> = new Map();
	let numUnits = getNumVisibleUnits();
	for (let [id, [eventX, eventY, eventW, eventH]] of idToPos.value){
		let x: number; // For line end on mainline
		let y: number;
		let x2: number; // For line end at event
			// Note: Drawing the line in the reverse direction causes 'detachment' from the mainline during transitions
		let y2: number;
		let event = idToEvent.value.get(id)!;
		let unitOffset = getUnitDiff(event.start, startDate.value, scale.value) + startOffset.value;
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
});

// For panning/zooming
function panTimeline(scrollRatio: number){
	let numUnits = getNumVisibleUnits();
	let chgUnits = numUnits * scrollRatio;
	let newStart = startDate.value.clone();
	let newEnd = endDate.value.clone();
	let [numStartSteps, numEndSteps, newStartOffset, newEndOffset] =
		getMovedBounds(startOffset.value, endOffset.value, chgUnits, chgUnits);
	if (scrollRatio > 0){
		while (true){
			if (newEnd.equals(MAX_DATE, scale.value)){
				// Pan up to an offset of INITIAL_EXTRA_OFFSET
				if (INITIAL_EXTRA_OFFSET == endOffset.value){
					console.log('Reached maximum date limit');
					newStartOffset = startOffset.value;
					newEndOffset = endOffset.value;
				} else {
					if (numEndSteps > 0 || newEndOffset >= INITIAL_EXTRA_OFFSET){
						chgUnits = INITIAL_EXTRA_OFFSET - endOffset.value;
						newEndOffset = INITIAL_EXTRA_OFFSET;
						let extraStartSteps: number;
						[extraStartSteps, , newStartOffset, ] =
							getMovedBounds(startOffset.value, endOffset.value, chgUnits, chgUnits);
						stepDate(newStart, scale.value, {count: extraStartSteps, inplace: true});
					} else {
						if (numStartSteps > 0){
							stepDate(newStart, scale.value, {count: numStartSteps, inplace: true});
						}
					}
				}
				numStartSteps = 0;
				break;
			}
			if (numEndSteps > 0){
				stepDate(newEnd, scale.value, {inplace: true});
				numEndSteps -= 1;
				if (numStartSteps > 0){
					stepDate(newStart, scale.value, {inplace: true});
					numStartSteps -= 1;
				}
			} else {
				if (numStartSteps > 0){
					stepDate(newStart, scale.value, {count: numStartSteps, inplace: true});
				}
				break;
			}
		}
	} else {
		while (true){
			if (MIN_DATE.equals(newStart, scale.value)){
				// Pan up to an offset of INITIAL_EXTRA_OFFSET
				if (INITIAL_EXTRA_OFFSET == startOffset.value){
					console.log('Reached minimum date limit');
					newStartOffset = startOffset.value;
					newEndOffset = endOffset.value;
				} else {
					if (numStartSteps < 0 || newStartOffset >= INITIAL_EXTRA_OFFSET){
						chgUnits = -INITIAL_EXTRA_OFFSET + startOffset.value;
						newStartOffset = INITIAL_EXTRA_OFFSET;
						let extraEndSteps: number;
						[, extraEndSteps, , newEndOffset] =
							getMovedBounds(startOffset.value, endOffset.value, chgUnits, chgUnits);
						stepDate(newEnd, scale.value, {count: extraEndSteps, inplace: true});
					} else {
						if (numEndSteps < 0){
							stepDate(newEnd, scale.value, {count: numEndSteps, inplace: true});
						}
					}
				}
				numEndSteps = 0;
				break;
			}
			if (numStartSteps < 0){
				stepDate(newStart, scale.value, {forward: false, inplace: true});
				numStartSteps += 1;
				if (numEndSteps < 0){
					stepDate(newEnd, scale.value, {forward: false, inplace: true});
					numEndSteps += 1;
				}
			} else {
				if (numEndSteps < 0){
					stepDate(newEnd, scale.value, {count: numEndSteps, inplace: true});
				}
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
function zoomTimeline(zoomRatio: number){
	if (zoomRatio > 1
			&& startDate.value.equals(MIN_DATE, scale.value)
			&& endDate.value.equals(MAX_DATE, scale.value)){
		console.log('Reached upper scale limit');
		return;
	}
	let numUnits = getNumVisibleUnits();
	let newNumUnits = numUnits * zoomRatio;
	// Get tentative bound changes
	let startChg: number;
	let endChg: number;
	let ptrOffset = props.vert ? pointerY : pointerX;
	if (ptrOffset == null){
		let unitChg = newNumUnits - numUnits;
		startChg = unitChg / 2;
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
				newStartOffset = INITIAL_EXTRA_OFFSET;
				break;
			}
			if (MIN_DATE.equals(newStart, scale.value)){
				newStartOffset = INITIAL_EXTRA_OFFSET;
				break;
			}
			stepDate(newStart, scale.value, {forward: false, inplace: true});
			numStartSteps += 1;
			newNumUnits += 1;
		}
		while (numEndSteps > 0){
			if (MAX_DATE.equals(newEnd, scale.value)){
				newEndOffset = INITIAL_EXTRA_OFFSET;
				break;
			}
			stepDate(newEnd, scale.value, {inplace: true});
			numEndSteps -= 1;
			newNumUnits += 1;
		}
		newNumUnits += newStartOffset + newEndOffset;
	}
	// Possibly change the scale
	let tickDiff = availLen.value / newNumUnits;
	if (tickDiff < MIN_TICK_SEP){ // Possibly zoom out
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
				// Note: There is some distortion due to not accounting for no year 0 CE here
					// But the result seems tolerable, and resolving it adds a fair bit of code complexity
			let newStartSubUnits =
				(scale.value == DAY_SCALE) ? getDaysInMonth(newStart.year, newStart.month) :
				(scale.value == MONTH_SCALE) ? 12 :
				getScaleRatio(scale.value, newScale);
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
				// Account for no 0 CE
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
	} else { // Possibly zoom in
		if (scaleIdx.value == SCALES.length - 1){
			if (newNumUnits < MIN_LAST_TICKS){
				console.log('Reached zoom in limit');
				return;
			}
		} else {
			let newScale = SCALES[scaleIdx.value + 1];
			let newUnitsPerOld = getScaleRatio(newScale, scale.value);
			let zoomedTickDiff = tickDiff / newUnitsPerOld;
			if (zoomedTickDiff > MIN_TICK_SEP){
				// Update offsets
				newStartOffset *= newUnitsPerOld;
				stepDate(newStart, newScale, {forward: false, count: Math.floor(newStartOffset), inplace: true});
				newStartOffset %= 1;
				newEndOffset *= newUnitsPerOld;
				stepDate(newEnd, newScale, {count: Math.floor(newEndOffset), inplace: true});
				newEndOffset %= 1;
				//
				if (newStart.isEarlier(MIN_CAL_DATE, newScale) && (newScale == MONTH_SCALE || newScale == DAY_SCALE)){
					console.log('Unable to zoom into range where month/day scale is invalid');
					return;
				}
				if (newStart.isEarlier(MIN_DATE, newScale) || MAX_DATE.isEarlier(newEnd, newScale)){
					console.log('Disallowing zooming in beyond min/max dates');
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
	vUpdater = setInterval(() => {
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
	const index = ptrEvtCache.findIndex((e) => e.pointerId == evt.pointerId);
	ptrEvtCache[index] = evt;
	//
	if (ptrEvtCache.length == 1){
		// Handle pointer dragging
		dragDiff += props.vert ? evt.clientY - pointerY! : evt.clientX - pointerX!;
		if (dragHandler == 0){
			dragHandler = setTimeout(() => {
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
	// Ignore if dragging between div elements
	if (evt.relatedTarget != null && rootRef.value!.contains(evt.relatedTarget as HTMLElement)){
		return;
	}
	// Remove from event cache
	const index = ptrEvtCache.findIndex((e) => e.pointerId == evt.pointerId);
	ptrEvtCache.splice(index, 1);
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
	let shiftDir = evt.deltaY > 0 ? 1 : -1;
	if (!props.vert){
		shiftDir *= -1;
	}
	panTimeline(shiftDir * store.scrollRatio);
}
function onShiftWheel(evt: WheelEvent){
	let zoomRatio = evt.deltaY > 0 ? store.zoomRatio : 1/store.zoomRatio;
	zoomTimeline(zoomRatio);
}

// For bound-change signalling
watch(startDate, () => {
	emit('state-chg', new TimelineState(
		ID, startDate.value, endDate.value, startOffset.value, endOffset.value, scaleIdx.value
	));
});

// For skipping transitions on startup (and on horz/vert swap)
const skipTransition = ref(true);
onMounted(() => setTimeout(() => {skipTransition.value = false}, 100));

// Styles
const transitionDuration = '300ms';
const transitionTimingFunction = 'ease-out';
const mainlineStyles = computed(() => {
	return {
		transform: props.vert ?
			`translate(${mainlineOffset.value}px, 0) rotate(90deg) scale(${availLen.value},1)` :
			`translate(0, ${mainlineOffset.value}px) rotate(0deg) scale(${availLen.value},1)`,
		transitionProperty: skipTransition.value ? 'none' : 'transform',
		transitionDuration,
		transitionTimingFunction,
	};
});
function tickStyles(idx: number){
	let offset =
		(idx - ticks.value.startIdx + startOffset.value) /
		(ticks.value.endIdx - ticks.value.startIdx + startOffset.value + endOffset.value) * availLen.value;
	let scaleFactor = 1;
	if (scaleIdx.value > 0 &&
			inDateScale(ticks.value.dates[idx], SCALES[scaleIdx.value-1])){ // If tick exists on larger scale
		scaleFactor = LARGE_TICK_LEN / TICK_LEN;
	}
	return {
		transform: props.vert ?
			`translate(${mainlineOffset.value}px,  ${offset}px) scale(${scaleFactor})` :
			`translate(${offset}px, ${mainlineOffset.value}px) scale(${scaleFactor})`,
		transitionProperty: skipTransition.value ? 'none' : 'transform, opacity',
		transitionDuration,
		transitionTimingFunction,
		opacity: (offset >= 0 && offset <= availLen.value) ? 1 : 0,
	}
}
function tickLabelStyles(idx: number){
	let offset =
		(idx - ticks.value.startIdx + startOffset.value) /
		(ticks.value.endIdx - ticks.value.startIdx + startOffset.value + endOffset.value) * availLen.value;
	let labelSz = props.vert ? TICK_LABEL_HEIGHT : tickLabelWidth.value;
	return {
		transform: props.vert ?
			`translate(${mainlineOffset.value + tickLabelMargin.value}px, ${offset}px)` :
			`translate(${offset}px, ${mainlineOffset.value + tickLabelMargin.value}px)`,
		transitionProperty: skipTransition.value ? 'none' : 'transform, opacity',
		transitionDuration,
		transitionTimingFunction,
		opacity: (offset >= labelSz && offset <= availLen.value - labelSz) ? 1 : 0,
	}
}
function eventStyles(eventId: number){
	const [x, y, w, h] = idToPos.value.get(eventId)!;
	return {
		left: x + 'px',
		top: y + 'px',
		width: w + 'px',
		height: h + 'px',
		transitionProperty: skipTransition.value ? 'none' : 'all',
		transitionDuration,
		transitionTimingFunction,
	};
}
function eventImgStyles(eventId: number){
	const event = idToEvent.value.get(eventId)!;
	return {
		width: EVENT_IMG_SZ + 'px',
		height: EVENT_IMG_SZ + 'px',
		backgroundImage: `url(${getImagePath(event.imgId)})`,
		backgroundSize: 'cover',
	};
}
function eventLineStyles(eventId: number){
	const [x, y, l, a] = eventLines.value.get(eventId)!;
	return {
		transform: `translate(${x}px, ${y}px) rotate(${a}deg) scaleX(${l})`,
		transitionProperty: skipTransition.value ? 'none' : 'transform',
		transitionDuration,
		transitionTimingFunction,
	};
}
</script>
