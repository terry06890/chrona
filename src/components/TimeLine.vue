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
			<line v-else-if="idx >= ticks.vStartIdx && idx <= ticks.vEndIdx"
				:x1="vert ? -TICK_LEN : 0" :y1="vert ? 0 : -TICK_LEN"
				:x2="vert ?  TICK_LEN : 0" :y2="vert ? 0 :  TICK_LEN"
				:stroke="store.color.alt" stroke-width="1px"
				:style="tickStyles(idx)" class="animate-fadein"/>
		</template>
		<!-- Tick labels -->
		<template v-for="date, idx in ticks.dates" :key="date.toInt()">
			<text v-if="idx >= ticks.vStartIdx && idx <= ticks.vEndIdx" :fill="store.color.textDark"
				x="0" y="0" :text-anchor="vert ? 'start' : 'middle'" dominant-baseline="middle"
				:style="tickLabelStyles(idx)" class="text-sm animate-fadein">
				{{date}}
			</text>
		</template>
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
import {WRITING_MODE_HORZ, MIN_DATE, MAX_DATE, MONTH_SCALE, DAY_SCALE, SCALES,
	HistDate, stepDate, inDateScale} from '../lib';
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
const startDate = ref(props.initialStart); // Lowest date on displayed timeline
const endDate = ref(props.initialEnd);
const scaleIdx = ref(0); // Index of current scale in SCALES
const scale = computed(() => SCALES[scaleIdx.value])
// Initialise to smallest usable scale
function initScale(){
	if (startDate.value.year < -4713){ // If a bound is before the Julian period start of 4713 BCE, use a yearly scale
		scaleIdx.value = getYearlyScale(startDate.value, endDate.value, availLen.value);
	} else {
		let dayDiff = startDate.value.getDayDiff(endDate.value);
		// Check for day scale usability
		if (availLen.value / dayDiff >= MIN_TICK_SEP){
			scaleIdx.value = SCALES.findIndex(s => s == DAY_SCALE);
		} else {
			// Check for month scale usability
			let monthDiff = startDate.value.getMonthDiff(endDate.value);
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
	while (SCALES[idx] > yearDiff){
		idx++;
	}
	while (idx < SCALES.length - 1 && availLen * SCALES[idx + 1] / yearDiff > MIN_TICK_SEP){
		idx++;
	}
	return idx;
}
onMounted(initScale);

// Tick data
const TICK_LEN = 8;
const END_TICK_SZ = 4; // Size for MIN_DATE/MAX_DATE ticks
const MIN_TICK_SEP = 5; // Smallest px separation between ticks
const MIN_LAST_TICKS = 3; // When at smallest scale, don't zoom further into less than this many ticks
function getNumTimeUnits(): number {
	if (scale.value == DAY_SCALE){
		return startDate.value.getDayDiff(endDate.value);
	} else if (scale.value == MONTH_SCALE){
		return startDate.value.getMonthDiff(endDate.value);
	} else {
		return Math.floor((endDate.value.year - startDate.value.year) / scale.value);
	}
}
const ticks = computed((): {dates: HistDate[], startIdx: number, endIdx: number,
		vStartIdx: number, vEndIdx: number} => {
		if (!mounted.value){
		return {dates: [], startIdx: 0, endIdx: 0, vStartIdx: 0, vEndIdx: 0};
		}
		// The result holds tick dates, and indexes indicating where the startDate and endDate are
		let numUnits = getNumTimeUnits();
		let tempTicks: HistDate[] = [];
		let startIdx: number;
		let endIdx: number;
		let panUnits = Math.floor(numUnits * store.scrollRatio);
		// Get hidden preceding ticks
		let next: HistDate;
		if (MIN_DATE.isEarlier(startDate.value, scale.value)){
		next = startDate.value;
		for (let i = 0; i < panUnits; i++){
		next = stepDate(next, scale.value, {forward: false});
		tempTicks.push(next);
		if (MIN_DATE.equals(next, scale.value)){
		break;
		}
		}
		tempTicks.reverse();
		}
		startIdx = tempTicks.length;
		// Get ticks between bounds
		next = startDate.value.clone();
		for (let i = 0; i < numUnits + 1; i++){
			tempTicks.push(next);
			next = stepDate(next, scale.value);
		}
		endIdx = tempTicks.length - 1;
		// Get hidden following ticks
		if (next.isEarlier(MAX_DATE, scale.value)){
			for (let i = 0; i < panUnits; i++){
				next = stepDate(next, scale.value);
				tempTicks.push(next)
					if (MAX_DATE.equals(next, scale.value)){
						break;
					}
			}
		}
		// Get hidden ticks that might transition in after zooming
		let tempTicks2: HistDate[] = [];
		let tempTicks3: HistDate[] = [];
		if (scaleIdx.value > 0 &&
				availLen.value / (numUnits * store.zoomRatio) < MIN_TICK_SEP){ // If zoom-out would decrease scale
			let newNumUnits = Math.floor(numUnits * store.zoomRatio) - numUnits - panUnits * 2;
			let zoomedScale = SCALES[scaleIdx.value-1]
				let unitsPerZoomedUnit = zoomedScale / scale.value;
			let next = tempTicks[0];
			if (MIN_DATE.isEarlier(next, scale.value)){
				for (let i = 0; i < newNumUnits / unitsPerZoomedUnit; i++){ // Get preceding ticks
					next = stepDate(next, zoomedScale, {forward: false});
					tempTicks2.push(next);
					if (MIN_DATE.equals(next, scale.value)){
						break;
					}
				}
				tempTicks2.reverse();
			}
			next = tempTicks[tempTicks.length - 1];
			if (next.isEarlier(MAX_DATE, scale.value)){
				for (let i = 0; i < newNumUnits / unitsPerZoomedUnit; i++){ // Get preceding ticks
					next = stepDate(next, zoomedScale);
					tempTicks3.push(next);
					if (MAX_DATE.equals(next, scale.value)){
						break;
					}
				}
			}
		}
		// Join into single array
		let vStartIdx = startIdx;
		while (tempTicks[vStartIdx].isEarlier(MIN_DATE, scale.value)){
			vStartIdx += 1;
		}
		let vEndIdx = endIdx;
		while (MAX_DATE.isEarlier(tempTicks[vEndIdx], scale.value)){
			vEndIdx -= 1;
		}
		startIdx += tempTicks2.length;
		endIdx += tempTicks2.length;
		vStartIdx += tempTicks2.length;
		vEndIdx += tempTicks2.length;
		let dates = [...tempTicks2, ...tempTicks, ...tempTicks3];
		return {dates, startIdx, endIdx, vStartIdx, vEndIdx};
		});

// For panning/zooming
function panTimeline(scrollRatio: number): boolean {
	let numUnits = getNumTimeUnits();
	let chgUnits = Math.trunc(numUnits * scrollRatio);
	if (chgUnits == 0){
		return false;
	}
	let paddedMinDate = stepDate(MIN_DATE, scale.value, {forward: false});
	let paddedMaxDate = stepDate(MAX_DATE, scale.value);
	if (scrollRatio < 0 && startDate.value.equals(paddedMinDate, scale.value)){
		console.log('Reached minimum date limit');
		return true;
	}
	if (scrollRatio > 0 && endDate.value.equals(paddedMaxDate, scale.value)){
		console.log('Reached maximum date limit');
		return true;
	}
	while (chgUnits < 0 && paddedMinDate.isEarlier(startDate.value, scale.value)){
		stepDate(startDate.value, scale.value, {forward: false, inplace: true});
		stepDate(endDate.value, scale.value, {forward: false, inplace: true});
		chgUnits += 1;
	}
	while (chgUnits > 0 && endDate.value.isEarlier(paddedMaxDate, scale.value)){
		stepDate(startDate.value, scale.value, {inplace: true});
		stepDate(endDate.value, scale.value, {inplace: true});
		chgUnits -= 1;
	}
	return true;
}
function zoomTimeline(zoomRatio: number){
	let paddedMinDate = stepDate(MIN_DATE, scale.value, {forward: false});
	let paddedMaxDate = stepDate(MAX_DATE, scale.value);
	if (zoomRatio > 1
			&& startDate.value.equals(paddedMinDate, scale.value)
			&& endDate.value.equals(paddedMaxDate, scale.value)){
		console.log('Reached upper scale limit');
		return;
	}
	let numUnits = getNumTimeUnits();
	let newNumUnits = Math.floor(numUnits * zoomRatio);
	// Get tentative bound changes
	let startChg: number;
	let endChg: number;
	let ptrOffset = props.vert ? pointerY : pointerX;
	if (ptrOffset == null){
		let unitChg = Math.abs(newNumUnits - numUnits);
		startChg = Math.ceil(unitChg / 2);
		endChg = Math.floor(unitChg / 2);
	} else { // Pointer-centered zoom
		// Get element-relative ptrOffset
		let innerOffset = 0;
		if (rootRef.value != null){ // Can become null during dev-server hot-reload for some reason
			let rect = rootRef.value.getBoundingClientRect();
			innerOffset = props.vert ? ptrOffset - rect.top : ptrOffset - rect.left;
		}
		//
		let zoomCenter = numUnits * (innerOffset / availLen.value);
		startChg = Math.round(Math.abs(zoomCenter * (zoomRatio - 1)));
		endChg = Math.abs(newNumUnits - numUnits) - startChg;
	}
	// Get new bounds
	let newStart = startDate.value.clone();
	let newEnd = endDate.value.clone();
	if (zoomRatio <= 1){
		stepDate(newStart, scale.value, {inplace: true, count: startChg});
		stepDate(newEnd, scale.value, {forward: false, inplace: true, count: endChg});
	} else {
		while (startChg > 0 && paddedMinDate.isEarlier(newStart, scale.value)){
			stepDate(newStart, scale.value, {forward: false, inplace: true});
			startChg -= 1;
		}
		endChg += startChg; // Transfer excess into end expansion
		while (endChg > 0 && newEnd.isEarlier(paddedMaxDate, scale.value)){
			stepDate(newEnd, scale.value, {inplace: true});
			endChg -= 1;
		}
		while (endChg > 0 && paddedMinDate.isEarlier(newStart, scale.value)){ // Transfer excess into start expansion
			stepDate(newStart, scale.value, {forward: false, inplace: true});
			endChg -= 1;
		}
		newNumUnits -= endChg;
	}
	// Possibly change the scale
	let tickDiff = availLen.value / newNumUnits;
	if (tickDiff < MIN_TICK_SEP){ // Possibly zoom out
		if (scaleIdx.value == 0){
			console.log('INFO: Reached zoom out limit');
			return;
		} else {
			scaleIdx.value -= 1;
		}
	} else { // Possibly zoom in
		if (scaleIdx.value == SCALES.length - 1){
			if (newNumUnits < MIN_LAST_TICKS){
				console.log('INFO: Reached zoom in limit');
				return;
			}
		} else {
			let nextScale = SCALES[scaleIdx.value + 1];
			let zoomedTickDiff: number;
			if (nextScale == MONTH_SCALE){
				zoomedTickDiff = tickDiff / 12;
			} else if (nextScale == DAY_SCALE){
				zoomedTickDiff = tickDiff / 31;
			} else {
				zoomedTickDiff = tickDiff / (scale.value / nextScale);
			}
			if (zoomedTickDiff > MIN_TICK_SEP){
				scaleIdx.value += 1;
			}
		}
	}
	//
	startDate.value = newStart;
	endDate.value = newEnd;
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
					const moved = panTimeline(-dragDiff / availLen.value);
					if (moved){
						dragDiff = 0;
					}
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
	let offset = (idx - ticks.value.startIdx) / (ticks.value.endIdx - ticks.value.startIdx) * availLen.value;
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
	let offset = (idx - ticks.value.startIdx) / (ticks.value.endIdx - ticks.value.startIdx) * availLen.value;
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
