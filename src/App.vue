<template>
<div class="absolute left-0 top-0 w-screen h-screen overflow-hidden flex flex-col">
	<!-- Title bar -->
	<div class="flex gap-2 p-2" :style="{backgroundColor: store.color.bgDark2}">
		<h1 class="my-auto ml-2 text-4xl" :style="{color: store.color.altDark}">Histplorer</h1>
		<div class="mx-auto"/> <!-- Spacer -->
		<!-- Icons -->
		<icon-button :size="45" :style="buttonStyles" @click="onTimelineAdd" title="Add a timeline">
			<plus-icon/>
		</icon-button>
		<icon-button :size="45" :style="buttonStyles">
			<settings-icon/>
		</icon-button>
		<icon-button :size="45" :style="buttonStyles">
			<help-icon/>
		</icon-button>
	</div>
	<!-- Content area -->
	<div class="grow min-h-0 flex" :class="{'flex-col': !vert}"
			:style="{backgroundColor: store.color.bg}" ref="contentAreaRef">
		<time-line v-for="(state, idx) in timelines" :key="state.id"
			:vert="vert" :initialState="state" :eventMap="eventMap"
			class="grow basis-full min-h-0 outline outline-1"
			@remove="onTimelineRemove(idx)" @state-chg="onTimelineChg($event, idx)" @event-req="onEventReq"/>
		<base-line :vert="vert" :timelines="timelines"/>
	</div>
</div>
</template>

<script setup lang="ts">
import {ref, computed, onMounted, onUnmounted, Ref} from 'vue';
// Components
import TimeLine from './components/TimeLine.vue';
import BaseLine from './components/BaseLine.vue';
import IconButton from './components/IconButton.vue';
// Icons
import PlusIcon from './components/icon/PlusIcon.vue';
import SettingsIcon from './components/icon/SettingsIcon.vue';
import HelpIcon from './components/icon/HelpIcon.vue';
// Other
import {HistDate, TimelineState, HistEvent, getUnitDiff, MONTH_SCALE, DAY_SCALE, stepDate} from './lib';
import {useStore} from './store';

// Refs
const contentAreaRef = ref(null as HTMLElement | null);

// Global store
const store = useStore();

// For content sizing (used to decide between horizontal and vertical mode)
const contentWidth = ref(0);
const contentHeight = ref(0);
const vert = computed(() => contentHeight.value > contentWidth.value);
function updateAreaDims(){
	let contentAreaEl = contentAreaRef.value!;
	contentWidth.value = contentAreaEl.offsetWidth;
	contentHeight.value = contentAreaEl.offsetHeight;
}
onMounted(updateAreaDims)

// Timeline data
const timelines: Ref<TimelineState[]> = ref([]);
const INITIAL_START_DATE = new HistDate(1900, 1, 1);
const INITIAL_END_DATE = new HistDate(2000, 1, 1);
let nextTimelineId = 1;
function addTimeline(){
	if (timelines.value.length == 0){
		timelines.value.push(new TimelineState(nextTimelineId, INITIAL_START_DATE, INITIAL_END_DATE));
	} else {
		let last = timelines.value[timelines.value.length - 1];
		timelines.value.push(new TimelineState(
			nextTimelineId, last.startDate,
			last.endDate, last.startOffset, last.endOffset, last.scaleIdx
		));
	}
	nextTimelineId++;
}
addTimeline();
function onTimelineChg(state: TimelineState, idx: number){
	timelines.value[idx] = state;
}

// For timeline addition/removal
const MIN_TIMELINE_BREADTH = 150;
function onTimelineAdd(){
	if (vert.value && contentWidth.value / (timelines.value.length + 1) < MIN_TIMELINE_BREADTH ||
		!vert.value && contentHeight.value / (timelines.value.length + 1) < MIN_TIMELINE_BREADTH){
		console.log('Reached timeline minimum breadth');
		return;
	}
	addTimeline();
}
function onTimelineRemove(idx: number){
	if (timelines.value.length == 1){
		console.log('Ignored removal of last timeline')
		return;
	}
	timelines.value.splice(idx, 1);
}

// Event data
const eventMap: Ref<Map<number, HistEvent>> = ref(new Map()); // Maps event IDs to HistEvents
let nextEventId = 0; // For generating placeholder events
function onEventReq(startDate: HistDate, endDate: HistDate){
	// Get number of existing events in range
	let numExisting = 0;
	for (let event of eventMap.value.values()){
		if (!event.start.isEarlier(startDate) && !endDate.isEarlier(event.start)){
			numExisting += 1;
		}
	}
	// Possibly add new events
	let tempScale = 1;
	let numUnits = getUnitDiff(startDate, endDate, tempScale);
	if (numUnits < 2){
		tempScale = MONTH_SCALE;
		numUnits = getUnitDiff(startDate, endDate, tempScale);
		if (numUnits < 2){
			tempScale = DAY_SCALE;
			numUnits = getUnitDiff(startDate, endDate, tempScale);
		}
	}
	for (let i = 0; i < 3 - numExisting; i++){
		let start = startDate.clone();
		let steps = Math.floor(Math.random() * (numUnits + 1));
		stepDate(start, tempScale, {count: steps, inplace: true});
		let event = {id: nextEventId, title: `Event ${nextEventId}`, start, startUpper: null, end: null, endUpper: null};
		eventMap.value.set(event.id, event);
		nextEventId += 1;
	}
}

// For resize handling
let lastResizeHdlrTime = 0; // Used to throttle resize handling
let afterResizeHdlr = 0; // Used to trigger handler after ending a run of resize events
async function onResize(){
	// Handle event if not recently done
	let handleResize = async () => {
		updateAreaDims();
	};
	let currentTime = new Date().getTime();
	if (currentTime - lastResizeHdlrTime > 200){
		lastResizeHdlrTime = currentTime;
		await handleResize();
		lastResizeHdlrTime = new Date().getTime();
	}
	// Setup a handler to execute after ending a run of resize events
	clearTimeout(afterResizeHdlr);
	afterResizeHdlr = setTimeout(async () => {
		afterResizeHdlr = 0;
		await handleResize();
		lastResizeHdlrTime = new Date().getTime();
	}, 200); // If too small, touch-device detection when swapping to/from mobile-mode gets unreliable
}
onMounted(() => window.addEventListener('resize', onResize));
onUnmounted(() => window.removeEventListener('resize', onResize));

// Styles
const buttonStyles = computed(() => ({
	color: store.color.text,
	backgroundColor: store.color.altDark2,
}));
</script>
