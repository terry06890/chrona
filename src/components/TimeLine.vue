<template>
<div class="touch-none" :width="width" :height="height"
	@wheel.exact.prevent="onShift" @wheel.shift.exact.prevent="onZoom" ref="rootRef">
	<svg :viewBox="`0 0 ${width} ${height}`">
		<line stroke="yellow" stroke-width="2px" x1="50%" y1="0%" x2="50%" y2="100%"/>
		<line v-for="n in ticks" :key="n"
			:x1="width/2-8" y1="0" :x2="width/2+8" y2="0" stroke="yellow" stroke-width="1px"
			:style="tickStyles(n)" class="animate-fadein"/>
		<text fill="#606060" v-for="n in ticks" :key="n"
			:x="width/2 + 12" y="0"
			text-anchor="start" :style="tickLabelStyles(n)" class="text-sm animate-fadein">
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
const startDate = ref(minDate);
const endDate = ref(maxDate);
const SHIFT_INC = 0.3; // Proportion of timeline length to shift by
const ZOOM_RATIO = 1.5; // When zooming out, the timeline length gets multiplied by this ratio
const MIN_TICK_SEP = 30; // Smallest px separation between ticks
const MIN_LAST_TICKS = 3; // When at smallest scale, don't zoom further if less than this many ticks would result
const ticks = ref(null); // Holds date value for each tick

// For initialisation
function initTicks(): number[] {
	let len = maxDate - minDate;
	// Find smallest usable scale
	for (let i = 0; i < scales.length; i++){
		if (props.height * (scales[i] / len) > MIN_TICK_SEP){
			scaleIdx = i;
		} else {
			break;
		}
	}
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
	let chg = len * n;
	if (startDate.value + chg < minDate){
		if (startDate.value == minDate){
			console.log('Reached minDate limit')
			return;
		}
		chg = minDate - startDate.value;
		startDate.value = minDate;
		endDate.value += chg;
	} else if (endDate.value + chg > maxDate){
		if (endDate.value == maxDate){
			console.log('Reached maxDate limit')
			return;
		}
		chg = maxDate - endDate.value;
		endDate.value = maxDate;
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
	// Possibly change the scale
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
	// Get new bounds
	let endChg = (newLen - oldLen) / 2;
	if (startDate.value - endChg < minDate){
		let tempChg = startDate.value - minDate;
		if (endDate.value + endChg + tempChg > maxDate){
			if (startDate.value == minDate && endDate.value == maxDate){
				console.log('Reached upper scale limit');
				return;
			} else {
				startDate.value = minDate;
				endDate.value = maxDate;
			}
		} else {
			startDate.value = minDate;
			endDate.value += endChg + tempChg;
		}
	} else if (endDate.value + endChg > maxDate){
		let tempChg = maxDate - endDate.value;
		if (startDate.value - endChg - tempChg < minDate){
			if (startDate.value == minDate && endDate.value == maxDate){
				console.log('Reached upper scale limit');
				return;
			} else {
				startDate.value = minDate;
				endDate.value = maxDate;
			}
		} else {
			startDate.value -= endChg + tempChg
			endDate.value = maxDate;
		}
	} else {
		startDate.value -= endChg;
		endDate.value += endChg;
	}
	//
	updateTicks();
}

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
	return {
		transform: `translate(0, ${(tick - startDate.value) / (endDate.value - startDate.value) * props.height}px)`,
		transition: 'transform 300ms linear',
	}
}
function tickLabelStyles(tick: number){
	return {
		transform: `translate(0, ${(tick - startDate.value) / (endDate.value - startDate.value) * props.height + 5}px)`,
		transition: 'transform 300ms linear',
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
