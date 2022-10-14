<template>
<div class="touch-none relative"
	@pointerdown.prevent="onPointerDown" @pointermove.prevent="onPointerMove" @pointerup.prevent="onPointerUp"
	@pointercancel.prevent="onPointerUp" @pointerout.prevent="onPointerUp" @pointerleave.prevent="onPointerUp"
	@wheel.exact.prevent="onWheel" @wheel.shift.exact.prevent="onShiftWheel"
	ref="rootRef">
	<svg :viewBox="`0 0 ${width} ${height}`">
		<!-- Main line (unit horizontal line that gets transformed, with extra length to avoid gaps when panning) -->
		<line :stroke="store.color.alt" stroke-width="2px" x1="-1" y1="0" x2="2" y2="0" :style="mainlineStyles"/>
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
		<!-- Tick labels -->
		<text v-for="date, idx in ticks.dates" :key="date.toInt()"
			x="0" y="0" :text-anchor="vert ? 'start' : 'middle'" dominant-baseline="middle"
			:fill="store.color.textDark" :style="tickLabelStyles(idx)" class="text-sm animate-fadein">
			{{date}}
		</text>
	</svg>
	<!-- Buttons -->
	<icon-button :size="30" class="absolute top-2 right-2"
		:style="{color: store.color.text, backgroundColor: store.color.altDark2}"
		@click="emit('remove')" title="Remove timeline">
		<minus-icon/>
	</icon-button>
</div>
</template>

<script setup lang="ts">
import {ref, onMounted, computed, watch, PropType} from 'vue';
// Components
import IconButton from './IconButton.vue';
// Icons
import MinusIcon from './icon/MinusIcon.vue';
// Other
import {WRITING_MODE_HORZ, MIN_DATE, MAX_DATE, MONTH_SCALE, DAY_SCALE, SCALES, MIN_CAL_DATE,
	HistDate, stepDate, inDateScale, getScaleRatio} from '../lib';
import {useStore} from '../store';

// Refs
const rootRef = ref(null as HTMLElement | null);

// Global store
const store = useStore();

// Props + events
const props = defineProps({
	vert: {type: Boolean, required: true},
	initialStart: {type: Object as PropType<HistDate>, required: true},
	initialEnd: {type: Object as PropType<HistDate>, required: true},
});
const emit = defineEmits(['remove', 'range-chg']);

// For size tracking
const width = ref(0);
const height = ref(0);
const availLen = computed(() => props.vert ? height.value : width.value);
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

// Timeline data
const startDate = ref(props.initialStart); // Earliest date to display
const endDate = ref(props.initialEnd);
const INITIAL_EXTRA_OFFSET = 0.5;
const startOffset = ref(INITIAL_EXTRA_OFFSET); // Fraction of a scale unit before startDate to show
	// Note: Without this, the timeline can only move if the distance is over one unit, which makes dragging awkward,
		// can cause unexpected jumps when zooming, and limits display when a unit has many ticks on the next scale
const endOffset = ref(INITIAL_EXTRA_OFFSET);
const scaleIdx = ref(0); // Index of current scale in SCALES
const scale = computed(() => SCALES[scaleIdx.value])
// Initialise to smallest usable scale
function initScale(){
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
	let yearDiff = endDate.year - startDate.year;
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
onMounted(initScale);

// Tick data
const TICK_LEN = 8;
const END_TICK_SZ = 4; // Size for MIN_DATE/MAX_DATE ticks
const MIN_TICK_SEP = 30; // Smallest px separation between ticks
const MIN_LAST_TICKS = 3; // When at smallest scale, don't zoom further into less than this many ticks
type Ticks = {
	dates: HistDate[], // One for each tick to render
	startIdx: number,
		// Index of first visible tick (hidden ticks are used for smoother transitions)
		// Ignored if 'dates' is empty
	endIdx: number, // Index of last visible tick
};
function getNumVisibleUnits(): number {
	let numUnits: number;
	if (scale.value == DAY_SCALE){
		numUnits = startDate.value.getDayDiff(endDate.value);
	} else if (scale.value == MONTH_SCALE){
		numUnits = startDate.value.getMonthDiff(endDate.value);
	} else {
		numUnits = (endDate.value.year - startDate.value.year) / scale.value;
	}
	return numUnits + startOffset.value + endOffset.value;
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

// For panning/zooming
function panTimeline(scrollRatio: number){
	let numUnits = getNumVisibleUnits();
	let chgUnits = numUnits * scrollRatio;
	let newStart = startDate.value.clone();
	let newEnd = endDate.value.clone();
	let [numStartSteps, numEndSteps, newStartOffset, newEndOffset] = getMovedBounds(chgUnits, chgUnits);
	if (scrollRatio > 0){
		while (true){
			if (newEnd.equals(MAX_DATE, scale.value)){
				let extraChg = INITIAL_EXTRA_OFFSET - endOffset.value;
				if (extraChg == 0){
					console.log('Reached maximum date limit');
					newStartOffset = startOffset.value;
					newEndOffset = endOffset.value;
				} else {
					let extraStartSteps: number;
					[extraStartSteps, , newStartOffset, ] = getMovedBounds(extraChg, extraChg);
					newEndOffset = INITIAL_EXTRA_OFFSET;
					stepDate(newStart, scale.value, {count: extraStartSteps, inplace: true});
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
				let extraChg = INITIAL_EXTRA_OFFSET - startOffset.value;
				if (extraChg == 0){
					console.log('Reached minimum date limit');
					newStartOffset = startOffset.value;
					newEndOffset = endOffset.value;
				} else {
					let extraEndSteps: number;
					[, extraEndSteps, , newEndOffset] = getMovedBounds(extraChg, extraChg);
					newStartOffset = INITIAL_EXTRA_OFFSET;
					stepDate(newEnd, scale.value, {count: extraEndSteps, inplace: true});
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
	startDate.value = newStart;
	endDate.value = newEnd;
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
	let [numStartSteps, numEndSteps, newStartOffset, newEndOffset] = getMovedBounds(startChg, endChg);
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
			let newScale = SCALES[scaleIdx.value - 1];
			let oldUnitsPerNew = getScaleRatio(scale.value, newScale);
			newStartOffset /= oldUnitsPerNew;
			newEndOffset /= oldUnitsPerNew;
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
function getMovedBounds(startChg: number, endChg: number): [number, number, number, number] {
	// Returns a number of start and end steps to take, and new start and end offset values
	let numStartSteps: number;
	let numEndSteps: number;
	let newStartOffset: number;
	let newEndOffset: number;
	if (startChg >= 0){
		numStartSteps = Math.ceil(startChg - startOffset.value);
		newStartOffset = (startOffset.value - startChg) - Math.floor(startOffset.value - startChg);
	} else {
		numStartSteps = Math.ceil(startChg - startOffset.value);
		newStartOffset = Math.abs((startChg - startOffset.value) % 1);
	}
	if (endChg >= 0){
		numEndSteps = Math.floor(endChg + endOffset.value);
		newEndOffset = (endOffset.value + endChg) % 1;
	} else {
		numEndSteps = Math.floor(endChg + endOffset.value);
		newEndOffset = (endOffset.value + endChg) - Math.floor(endOffset.value + endChg);
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
	emit('range-chg', [startDate.value, endDate.value]);
});

// For skipping transitions on startup (and on horz/vert swap)
const skipTransition = ref(true);
onMounted(() => setTimeout(() => {skipTransition.value = false}, 100));

// Styles
const transitionDuration = '300ms';
const transitionTimingFunction = 'ease-out';
const mainlineStyles = computed(() => ({
	transform: props.vert ?
		`translate(${width.value/2}px, 0) rotate(90deg) scale(${height.value},1)` :
		`translate(0, ${height.value/2}px) scale(${width.value},1)`,
	transitionProperty: skipTransition.value ? 'none' : 'transform',
	transitionDuration,
	transitionTimingFunction,
}));
function tickStyles(idx: number){
	let offset =
		(idx - ticks.value.startIdx + startOffset.value) /
		(ticks.value.endIdx - ticks.value.startIdx + startOffset.value + endOffset.value) * availLen.value;
	let scaleFactor = 1;
	if (scaleIdx.value > 0 &&
			inDateScale(ticks.value.dates[idx], SCALES[scaleIdx.value-1])){ // If tick exists on larger scale
		scaleFactor = 2;
	}
	return {
		transform: props.vert ?
			`translate(${width.value/2}px,  ${offset}px) scale(${scaleFactor})` :
			`translate(${offset}px, ${height.value/2}px) scale(${scaleFactor})`,
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
	let labelSz = props.vert ? 10 : 30;
	return {
		transform: props.vert ?
			`translate(${width.value / 2 + 20}px, ${offset}px)` :
			`translate(${offset}px, ${height.value / 2 + 30}px)`,
		transitionProperty: skipTransition.value ? 'none' : 'transform, opacity',
		transitionDuration,
		transitionTimingFunction,
		opacity: (offset >= labelSz && offset <= availLen.value - labelSz) ? 1 : 0,
	}
}
</script>
