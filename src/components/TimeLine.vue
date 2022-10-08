<template>
<div class="touch-none" :width="width" :height="height"
	@wheel.exact.prevent="onShift" @wheel.shift.exact.prevent="onZoom" ref="rootRef">
	<svg :viewBox="`0 0 ${width} ${height}`">
		<line stroke="yellow" stroke-width="2px" x1="50%" y1="0%" x2="50%" y2="100%"/>
		<template v-for="n in ticks" :key="n">
			<line v-if="n == minDate || n == maxDate"
				:x1="width/2 - 4" y1="0"
				:x2="width/2 + 4" y2="0"
				stroke="yellow" stroke-width="8px" :style="tickStyles(n)" class="animate-fadein"/>
			<line v-else
				:x1="width/2 - 8" y1="0"
				:x2="width/2 + 8" y2="0"
				stroke="yellow" stroke-width="1px" :style="tickStyles(n)" class="animate-fadein"/>
		</template>
		<text fill="#606060" v-for="n in ticks" :key="n"
			:x="width/2 + 12" y="0"
			text-anchor="start" dominant-baseline="middle" :style="tickLabelStyles(n)" class="text-sm animate-fadein">
			{{Math.round(n * 100) / 100}}
		</text>
	</svg>
</div>
</template>

<script setup lang="ts">
import {ref, onMounted, nextTick} from 'vue';

// Refs
const rootRef = ref(null as HTMLElement | null);

// Props
const props = defineProps({
	width: {type: Number, required: true},
	height: {type: Number, required: true},
});

// For date range
const minDate = -1000;
const maxDate = 1000;
const scales = [200, 50, 10, 1, 0.2]; // The timeline get divided into units of scales[0], then scales[1], etc
let scaleIdx = 0; // Index of current scale in 'scales'
const startDate = ref(0);
const endDate = ref(0);
const SHIFT_INC = 0.3; // Proportion of timeline length to shift by
const ZOOM_RATIO = 1.5; // When zooming out, the timeline length gets multiplied by this ratio
const MIN_TICK_SEP = 30; // Smallest px separation between ticks
const MIN_LAST_TICKS = 3; // When at smallest scale, don't zoom further if less than this many ticks would result
const ticks = ref(null); // Holds date value for each tick
let padUnits = 0.5; // Amount of extra scale units to add before/after min/max date

// For initialisation
function initTicks(): number[] {
	// Find smallest usable scale
	for (let i = 0; i < scales.length; i++){
		let len = maxDate - minDate + (padUnits * scales[i]) * 2;
		if (props.height * (scales[i] / len) > MIN_TICK_SEP){
			scaleIdx = i;
		} else {
			break;
		}
	}
	// Set start/end date
	let extraPad = padUnits * scales[scaleIdx];
	startDate.value = minDate - extraPad;
	endDate.value = maxDate + extraPad;
	// Get tick values
	let newTicks = [];
	let next = minDate;
	while (next <= maxDate){
		newTicks.push(next);
		next += scales[scaleIdx];
	}
	ticks.value = newTicks;
	//
	updateTicks();
}
onMounted(() => nextTick(initTicks));

// Adds extra ticks outside the visible area (which can transition in upon shift/zoom),
// and adds/removes ticks upon a scale change
function updateTicks(){
	let len = endDate.value - startDate.value;
	let shiftChg = len * SHIFT_INC;
	let scaleChg = len * (ZOOM_RATIO - 1) / 2;
	let scale = scales[scaleIdx];
	// Get ticks in new range, and add hidden ticks that might transition in on a shift action
	let tempTicks = [];
	let next = Math.ceil((Math.max(minDate, startDate.value - shiftChg) - minDate) / scale);
	let last = Math.floor((Math.min(maxDate, endDate.value + shiftChg) - minDate) / scale);
	while (next <= last){
		tempTicks.push(minDate + next * scale);
		next++;
	}
	// Get hidden ticks that might transition in on a zoom action
	let tempTicks2 = [];
	let tempTicks3 = [];
	if (scaleIdx > 0){
		scale = scales[scaleIdx-1];
		let first = Math.ceil((Math.max(minDate, startDate.value - scaleChg) - minDate) / scale);
		while ((minDate + first * scale) < tempTicks[0]){
			tempTicks2.push(minDate + first * scale);
			first++;
		}
		let last = Math.floor((Math.min(maxDate, endDate.value + scaleChg) - minDate) / scale);
		let next = Math.floor((tempTicks[tempTicks.length - 1] - minDate) / scale) + 1;
		while (next <= last){
			tempTicks3.push(minDate + next * scale);
			next++;
		}
	}
	//
	ticks.value = [].concat(tempTicks2, tempTicks, tempTicks3);
}
// Performs a shift action
function shiftTimeline(n: number){
	let len = endDate.value - startDate.value;
	let extraPad = padUnits * scales[scaleIdx]
	let paddedMinDate = minDate - extraPad;
	let paddedMaxDate = maxDate + extraPad;
	let chg = len * n;
	if (startDate.value + chg < paddedMinDate){
		if (startDate.value == paddedMinDate){
			console.log('Reached minDate limit')
			return;
		}
		chg = paddedMinDate - startDate.value;
		startDate.value = paddedMinDate;
		endDate.value += chg;
	} else if (endDate.value + chg > paddedMaxDate){
		if (endDate.value == paddedMaxDate){
			console.log('Reached maxDate limit')
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
	let oldLen = endDate.value - startDate.value;
	let newLen = oldLen * frac;
	let extraPad = padUnits * scales[scaleIdx]
	let paddedMinDate = minDate - extraPad;
	let paddedMaxDate = maxDate + extraPad;
	// Get new bounds
	let newStart: number;
	let newEnd: number;
	if (cursorY == null){
		let lenChg = newLen - oldLen
		newStart = startDate.value - lenChg / 2;
		newEnd = endDate.value + lenChg / 2;
	} else {
		let zoomCenter = startDate.value + (cursorY / props.height) * oldLen;
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
	newLen = newEnd - newStart;
	let tickDiff = props.height * (scales[scaleIdx] / newLen);
	if (tickDiff < MIN_TICK_SEP){
		if (scaleIdx == 0){
			console.log('INFO: Reached zoom out limit');
			return;
		} else {
			scaleIdx--;
		}
	} else {
		if (scaleIdx < scales.length - 1){
			if (tickDiff > MIN_TICK_SEP * scales[scaleIdx] / scales[scaleIdx + 1]){
				scaleIdx++;
			}
		} else {
			if (newLen / tickDiff < MIN_LAST_TICKS){
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

// For cursor tracking
let cursorX = null;
let cursorY = null;
onMounted(() => window.addEventListener('mousemove', (evt: MouseEvent) => {
	if (rootRef.value != null){ // Can become null during dev-server hot-reload for some reason
		let rect = rootRef.value.getBoundingClientRect();
		cursorX = evt.clientX - rect.left;
		cursorY = evt.clientY - rect.top;
	}
}))

// For mouse/etc handling
function onShift(evt: WheelEvent){
	if (evt.deltaY > 0){
		shiftTimeline(SHIFT_INC);
	} else {
		shiftTimeline(-SHIFT_INC);
	}
}
function onZoom(evt: WheelEvent){
	if (evt.deltaY > 0){
		zoomTimeline(ZOOM_RATIO);
	} else {
		zoomTimeline(1/ZOOM_RATIO);
	}
}

// Styles
function tickStyles(tick: number){
	let y = (tick - startDate.value) / (endDate.value - startDate.value) * props.height;
	return {
		transform: `translate(0, ${y}px)`,
		transitionProperty: 'transform',
		transitionDuration: '300ms',
		transitionTimingFunction: 'ease-out',
		display: (y >= 0 && y <= props.height) ? 'block' : 'none',
	}
}
function tickLabelStyles(tick: number){
	let y = (tick - startDate.value) / (endDate.value - startDate.value) * props.height;
	let fontHeight = 10;
	return {
		transform: `translate(0, ${y}px)`,
		transitionProperty: 'transform',
		transitionDuration: '300ms',
		transitionTimingFunction: 'ease-out',
		display: (y >= fontHeight && y <= props.height - fontHeight) ? 'block' : 'none',
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
