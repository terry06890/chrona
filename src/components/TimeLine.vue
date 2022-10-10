<template>
<div class="touch-none relative"
	@wheel.exact.prevent="onWheel" @wheel.shift.exact.prevent="onShiftWheel"
	@pointerdown.prevent="onPointerDown" @pointermove.prevent="onPointerMove" @pointerup.prevent="onPointerUp"
	@pointercancel.prevent="onPointerUp" @pointerout.prevent="onPointerUp" @pointerleave.prevent="onPointerUp"
	ref="rootRef">
	<svg :viewBox="`0 0 ${width} ${height}`">
		<line stroke="yellow" stroke-width="2px" x1="0" y1="0" x2="1" y2="0" :style="mainlineStyles"/>
		<template v-for="n in ticks" :key="n">
			<line v-if="n == MIN_DATE || n == MAX_DATE"
				:x1="vert ? -END_TICK_SZ : 0" :y1="vert ? 0 : -END_TICK_SZ"
				:x2="vert ?  END_TICK_SZ : 0" :y2="vert ? 0 :  END_TICK_SZ"
				stroke="yellow" :stroke-width="`${END_TICK_SZ * 2}px`" :style="tickStyles(n)" class="animate-fadein"/>
			<line v-else
				:x1="vert ? -TICK_LEN : 0" :y1="vert ? 0 : -TICK_LEN"
				:x2="vert ?  TICK_LEN : 0" :y2="vert ? 0 :  TICK_LEN"
				stroke="yellow" stroke-width="1px" :style="tickStyles(n)" class="animate-fadein"/>
		</template>
		<text fill="#606060" v-for="n in ticks" :key="n"
			x="0" y="0" :text-anchor="vert ? 'start' : 'middle'" dominant-baseline="middle"
			:style="tickLabelStyles(n)" class="text-sm animate-fadein">
			{{n}}
		</text>
	</svg>
	<!-- Icons -->
	<icon-button :size="30" class="absolute bottom-2 right-2 text-stone-50 bg-yellow-600"
		@click="onClose" title="Remove timeline">
		<minus-icon/>
	</icon-button>
</div>
</template>

<script setup lang="ts">
import {ref, onMounted, computed, nextTick} from 'vue';
// Components
import IconButton from './IconButton.vue';
// Icons
import MinusIcon from './icon/MinusIcon.vue';

// Refs
const rootRef = ref(null as HTMLElement | null);

// Props + events
const props = defineProps({
	vert: {type: Boolean, default: false},
});
const emit = defineEmits(['close']);

// For skipping transitions on horz/vert swap
const skipTransition = ref(false);
const prevVert = ref(props.vert);

// For size tracking
const width = ref(0);
const height = ref(0);
const WRITING_MODE_HORZ = window.getComputedStyle(document.body)['writing-mode'].startsWith('horizontal');
const resizeObserver = new ResizeObserver((entries) => {
	for (const entry of entries){
		if (entry.contentBoxSize){
			const boxSize = Array.isArray(entry.contentBoxSize) ? entry.contentBoxSize[0] : entry.contentBoxSize;
			width.value = WRITING_MODE_HORZ ? boxSize.inlineSize : boxSize.blockSize;
			height.value = WRITING_MODE_HORZ ? boxSize.blockSize : boxSize.inlineSize;
			if (props.vert != prevVert.value){
				skipTransition.value = true;
				setTimeout(() => {skipTransition.value = false}, 100); // Note: Using nextTick() doesn't work
				prevVert.value = props.vert;
			}
		}
	}
});
onMounted(() => resizeObserver.observe(rootRef.value));

// Vars
const MIN_DATE = -1000; // Lowest date that gets marked
const MAX_DATE = 1000;
const startDate = ref(0); // Lowest date on displayed timeline
const endDate = ref(0);
const SCALES = [200, 50, 10, 1, 0.2]; // The timeline get divided into units of SCALES[0], then SCALES[1], etc
let scaleIdx = 0; // Index of current scale in SCALES
const ticks = ref(null); // Holds date value for each tick
const SCROLL_SHIFT_CHG = 0.2; // Proportion of timeline length to shift by upon scroll
const ZOOM_RATIO = 1.5; // When zooming out, the timeline length gets multiplied by this ratio
const MIN_TICK_SEP = 30; // Smallest px separation between ticks
const MIN_LAST_TICKS = 3; // When at smallest scale, don't zoom further into less than this many ticks
const padUnits = computed(() => props.vert ? 0.5 : 1); // Amount of extra scale units to add before/after min/max date
const TICK_LEN = 8;
const END_TICK_SZ = 4; // Size for MIN_DATE/MAX_DATE ticks
const availLen = computed(() => props.vert ? height.value : width.value);

// For initialisation
function initTicks(): number[] {
	// Find smallest usable scale
	for (let i = 0; i < SCALES.length; i++){
		let dateLen = MAX_DATE - MIN_DATE + (padUnits.value * SCALES[i]) * 2;
		if (availLen.value * (SCALES[i] / dateLen) > MIN_TICK_SEP){
			scaleIdx = i;
		} else {
			break;
		}
	}
	// Set start/end date
	let extraPad = padUnits.value * SCALES[scaleIdx];
	startDate.value = MIN_DATE - extraPad;
	endDate.value = MAX_DATE + extraPad;
	// Get tick values
	let newTicks = [];
	let next = MIN_DATE;
	while (next <= MAX_DATE){
		newTicks.push(next);
		next += SCALES[scaleIdx];
	}
	ticks.value = newTicks;
	updateTicks();
}
onMounted(() => nextTick(initTicks));

// Adds extra ticks outside the visible area (which might transition in upon shift/zoom),
// and adds/removes ticks upon a scale change
function updateTicks(){
	let dateLen = endDate.value - startDate.value;
	let shiftChg = dateLen * SCROLL_SHIFT_CHG;
	let scaleChg = dateLen * (ZOOM_RATIO - 1) / 2;
	let scale = SCALES[scaleIdx];
	// Get ticks in new range, and add hidden ticks that might transition in on a shift action
	let tempTicks = [];
	let next = Math.ceil((Math.max(MIN_DATE, startDate.value - shiftChg) - MIN_DATE) / scale);
	let last = Math.floor((Math.min(MAX_DATE, endDate.value + shiftChg) - MIN_DATE) / scale);
	while (next <= last){
		tempTicks.push(MIN_DATE + next * scale);
		next++;
	}
	// Get hidden ticks that might transition in on a zoom action
	let tempTicks2 = [];
	let tempTicks3 = [];
	if (scaleIdx > 0){
		scale = SCALES[scaleIdx-1];
		let first = Math.ceil((Math.max(MIN_DATE, startDate.value - scaleChg) - MIN_DATE) / scale);
		while ((MIN_DATE + first * scale) < tempTicks[0]){
			tempTicks2.push(MIN_DATE + first * scale);
			first++;
		}
		let last = Math.floor((Math.min(MAX_DATE, endDate.value + scaleChg) - MIN_DATE) / scale);
		let next = Math.floor((tempTicks[tempTicks.length - 1] - MIN_DATE) / scale) + 1;
		while (next <= last){
			tempTicks3.push(MIN_DATE + next * scale);
			next++;
		}
	}
	//
	ticks.value = [].concat(tempTicks2, tempTicks, tempTicks3);
}
// Performs a shift action
function shiftTimeline(n: number){
	let dateLen = endDate.value - startDate.value;
	let extraPad = padUnits.value * SCALES[scaleIdx]
	let paddedMinDate = MIN_DATE - extraPad;
	let paddedMaxDate = MAX_DATE + extraPad;
	let chg = dateLen * n;
	if (startDate.value + chg < paddedMinDate){
		if (startDate.value == paddedMinDate){
			console.log('Reached MIN_DATE limit')
			return;
		}
		chg = paddedMinDate - startDate.value;
		startDate.value = paddedMinDate;
		endDate.value += chg;
	} else if (endDate.value + chg > paddedMaxDate){
		if (endDate.value == paddedMaxDate){
			console.log('Reached MAX_DATE limit')
			return;
		}
		chg = paddedMaxDate - endDate.value;
		endDate.value = paddedMaxDate;
		startDate.value += chg;
	} else {
		startDate.value += chg;
		endDate.value += chg;
	}
	updateTicks();
}
// Performs a zoom action
function zoomTimeline(frac: number){
	let oldDateLen = endDate.value - startDate.value;
	let newDateLen = oldDateLen * frac;
	let extraPad = padUnits.value * SCALES[scaleIdx]
	let paddedMinDate = MIN_DATE - extraPad;
	let paddedMaxDate = MAX_DATE + extraPad;
	// Get new bounds
	let newStart: number;
	let newEnd: number;
	let ptrOffset = props.vert ? pointerY : pointerX;
	if (ptrOffset == null){
		let lenChg = newDateLen - oldDateLen
		newStart = startDate.value - lenChg / 2;
		newEnd = endDate.value + lenChg / 2;
	} else {
		let innerOffset = 0; // Element-relative ptrOffset
		if (rootRef.value != null){ // Can become null during dev-server hot-reload for some reason
			let rect = rootRef.value.getBoundingClientRect();
			innerOffset = ptrOffset - rect.top;
		}
		let zoomCenter = startDate.value + (innerOffset / availLen.value) * oldDateLen;
		newStart = zoomCenter - (zoomCenter - startDate.value) * frac;
		newEnd = zoomCenter + (endDate.value - zoomCenter) * frac;
	}
	if (newStart < paddedMinDate){
		newEnd += paddedMinDate - newStart;
		newStart = paddedMinDate;
		if (newEnd > paddedMaxDate){
			if (startDate.value == paddedMinDate && endDate.value == paddedMaxDate){
				console.log('Reached upper scale limit');
				return;
			} else {
				newEnd = paddedMaxDate;
			}
		}
	} else if (newEnd > paddedMaxDate){
		newStart -= newEnd - paddedMaxDate;
		newEnd = paddedMaxDate;
		if (newStart < paddedMinDate){
			if (startDate.value == paddedMinDate && endDate.value == paddedMaxDate){
				console.log('Reached upper scale limit');
				return;
			} else {
				newStart = paddedMinDate;
			}
		}
	}
	// Possibly change the scale
	newDateLen = newEnd - newStart;
	let tickDiff = availLen.value * (SCALES[scaleIdx] / newDateLen);
	if (tickDiff < MIN_TICK_SEP){
		if (scaleIdx == 0){
			console.log('INFO: Reached zoom out limit');
			return;
		} else {
			scaleIdx--;
		}
	} else {
		if (scaleIdx < SCALES.length - 1){
			if (tickDiff > MIN_TICK_SEP * SCALES[scaleIdx] / SCALES[scaleIdx + 1]){
				scaleIdx++;
			}
		} else {
			if (newDateLen / tickDiff < MIN_LAST_TICKS){
				console.log('INFO: Reached zoom in limit');
				return;
			}
		}
	}
	//
	startDate.value = newStart;
	endDate.value = newEnd;
	updateTicks();
}

// For mouse/etc handling
let pointerX = null; // Stores pointer position (used for pointer-centered zooming)
let pointerY = null;
const ptrEvtCache = []; // Holds last captured PointerEvent for each pointerId (used for pinch-zoom)
let lastPinchDiff = -1; // Holds last x/y distance between two pointers that are down
let dragDiff = 0; // Holds accumlated change in pointer's x/y coordinate while dragging
let dragHandler = 0; // Set by a setTimeout() to a handler for pointer dragging
let dragVelocity: number; // Used to add 'drag momentum'
let vUpdateTime: number; // Holds timestamp for last update of 'dragVelocityY'
let vPrevPointer: null | number; // Holds pointerX/pointerY used for last update of 'dragVelocity'
let vUpdater = 0; // Set by a setInterval(), used to update 'dragVelocity'
function onPointerDown(evt: PointerEvent){
	ptrEvtCache.push(evt);
	// Update stored cursor position
	pointerX = evt.clientX;
	pointerY = evt.clientY;
	// Update vars for dragging
	dragDiff = 0;
	dragVelocity = 0;
	vUpdateTime = Date.now();
	vPrevPointer = null;
	vUpdater = setInterval(() => {
		if (vPrevPointer != null){
			let time = Date.now();
			let ptrDiff = (props.vert ? pointerY : pointerX) - vPrevPointer;
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
		dragDiff += props.vert ? evt.clientY - pointerY : evt.clientX - pointerX;
		if (dragHandler == 0){
			dragHandler = setTimeout(() => {
				if (Math.abs(dragDiff) > 2){
					shiftTimeline(-dragDiff / availLen.value);
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
			let scrollChg = dragVelocity * 0.1;
			shiftTimeline(-scrollChg / availLen.value);
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
	shiftTimeline(shiftDir * SCROLL_SHIFT_CHG);
}
function onShiftWheel(evt: WheelEvent){
	if (evt.deltaY > 0){
		zoomTimeline(ZOOM_RATIO);
	} else {
		zoomTimeline(1/ZOOM_RATIO);
	}
}

// For button handling
function onClose(){
	emit('close');
}

// Styles
const mainlineStyles = computed(() => ({
	transform: props.vert ?
		`translate(${width.value/2}px, 0) rotate(90deg) scale(${height.value},1)` :
		`translate(0, ${height.value/2}px) scale(${width.value},1)`,
	transitionProperty: skipTransition.value ? 'none' : 'transform',
	transitionDuration: '300ms',
	transitionTimingFunction: 'ease-out',
}));
function tickStyles(tick: number){
	let offset = (tick - startDate.value) / (endDate.value - startDate.value) * availLen.value;
	let scale = 1;
	if (scaleIdx > 0 && tick % SCALES[scaleIdx-1] == 0){ // If the tick exists on the scale directly above this one
		scale = 2;
	}
	return {
		transform: props.vert ?
			`translate(${width.value/2}px,  ${offset}px) scale(${scale})` :
			`translate(${offset}px, ${height.value/2}px) scale(${scale})`,
		transitionProperty: skipTransition.value ? 'none' : 'transform, opacity',
		transitionDuration: '300ms',
		transitionTimingFunction: 'ease-out',
		opacity: (offset >= 0 && offset <= availLen.value) ? 1 : 0,
	}
}
function tickLabelStyles(tick: number){
	let offset = (tick - startDate.value) / (endDate.value - startDate.value) * availLen.value;
	let labelSz = props.vert ? 10 : 30;
	return {
		transform: props.vert ?
			`translate(${width.value / 2 + 20}px, ${offset}px)` :
			`translate(${offset}px, ${height.value / 2 + 30}px)`,
		transitionProperty: skipTransition.value ? 'none' : 'transform, opacity',
		transitionDuration: '300ms',
		transitionTimingFunction: 'ease-out',
		opacity: (offset >= labelSz && offset <= availLen.value - labelSz) ? 1 : 0,
	}
}
</script>

<style>
.animate-fadein {
	animation-name: fadein;
	animation-duration: 300ms;
	animation-timing-function: ease-in;
}
@keyframes fadein {
	from {
		opacity: 0;
	}
	to {
		opacity: 1;
	}
}
</style>
