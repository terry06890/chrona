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
			:vert="vert" :initialState="state" :closeable="timelines.length > 1"
			:eventTree="eventTree" :unitCountMaps="unitCountMaps"
			class="grow basis-full min-h-0 outline outline-1"
			@remove="onTimelineRemove(idx)" @state-chg="onTimelineChg($event, idx)" @event-display="onEventDisplay"/>
		<base-line :vert="vert" :timelines="timelines" class='m-1 sm:m-2'/>
	</div>
</div>
</template>

<script setup lang="ts">
import {ref, computed, onMounted, onUnmounted, Ref, shallowRef, ShallowRef} from 'vue';
// Components
import TimeLine from './components/TimeLine.vue';
import BaseLine from './components/BaseLine.vue';
import IconButton from './components/IconButton.vue';
// Icons
import PlusIcon from './components/icon/PlusIcon.vue';
import SettingsIcon from './components/icon/SettingsIcon.vue';
import HelpIcon from './components/icon/HelpIcon.vue';
// Other
import {timeout, HistDate, HistEvent, queryServer, EventResponseJson, jsonToHistEvent,
	SCALES, stepDate, TimelineState, cmpHistEvent, dateToUnit, DateRangeTree} from './lib';
import {useStore} from './store';
import {RBTree, rbtree_shallow_copy} from './rbtree';

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
let nextTimelineId = 1;
function addTimeline(){
	if (timelines.value.length == 0){
		timelines.value.push(new TimelineState(nextTimelineId, store.initialStartDate, store.initialEndDate));
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
const MIN_TIMELINE_BREADTH = store.mainlineBreadth + store.spacing * 2 + store.eventImgSz + store.eventLabelHeight;
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

// For storing and looking up events
const eventTree: ShallowRef<RBTree<HistEvent>> = shallowRef(new RBTree(cmpHistEvent));
let idToEvent: Map<number, HistEvent> = new Map();
const unitCountMaps: Ref<Map<number, number>[]> = ref(SCALES.map(() => new Map()));
	// For each scale, maps units to event counts
// For keeping event data under a memory limit
const EXCESS_EVENTS_THRESHOLD = 10000;
let displayedEvents: Map<number, number[]> = new Map(); // Maps TimeLine IDs to IDs of displayed events
function reduceEvents(){
	// Get events to keep
	let eventsToKeep: Map<number, HistEvent> = new Map();
	for (let [, ids] of displayedEvents){
		for (let id of ids){
			eventsToKeep.set(id, idToEvent.get(id)!);
		}
	}
	// Create new event tree
	let newTree = new RBTree(cmpHistEvent);
	for (let [, event] of eventsToKeep){
		newTree.insert(event);
	}
	// Create new unit-count maps
	let newMaps: Map<number, number>[] = SCALES.map(() => new Map());
	for (let timeline of timelines.value){
		if (timeline.scaleIdx == null){
			continue;
		}
		// Look for units to keep
		const scaleIdx = timeline.scaleIdx;
		const scale = SCALES[scaleIdx];
		let startUnit = dateToUnit(stepDate(timeline.startDate, scale, {forward: false}), scale);
		let endUnit = dateToUnit(stepDate(timeline.endDate, scale), scale);
		for (let [unit, count] of unitCountMaps.value[scaleIdx]){
			if (unit >= startUnit && unit <= endUnit){
				newMaps[scaleIdx].set(unit, count);
			}
		}
	}
	// Replace old data
	eventTree.value = newTree;
	unitCountMaps.value = newMaps;
	idToEvent = eventsToKeep;
}
// For getting events from server
const EVENT_REQ_LIMIT = 300;
const MAX_EVENTS_PER_UNIT = 4; // Should equal MAX_DISPLAYED_PER_UNIT in backend gen_disp_data.py
let queriedRanges: DateRangeTree[] = SCALES.map(() => new DateRangeTree());
	// For each scale, holds date ranges for which data has already been queried fromm the server
let pendingReq = false; // Used to serialise event-req handling
async function onEventDisplay(
		timelineId: number, eventIds: number[], firstDate: HistDate, lastDate: HistDate, scaleIdx: number){
	while (pendingReq){
		await timeout(100);
	}
	pendingReq = true;
	// Skip if range has been queried, and enough of its events have been obtained
	if (queriedRanges[scaleIdx].contains([firstDate, lastDate])){
		// Get number of events in range, server-side
		let fullCount = 0;
		let date = firstDate.clone();
		let eventCounts: Map<number, number> = new Map(); // For calculating number of events, client-side
		while (date.isEarlier(lastDate)){
			let unit = dateToUnit(date, SCALES[scaleIdx]);
			if (unitCountMaps.value[scaleIdx].has(unit)){
				fullCount += Math.min(MAX_EVENTS_PER_UNIT, unitCountMaps.value[scaleIdx].get(unit)!);
			}
			eventCounts.set(unit, 0);
			stepDate(date, SCALES[scaleIdx], {inplace: true});
		}
		if (fullCount > 0){
			// Get number of events, client-side
			let eventCount = 0;
			let itr = eventTree.value.lowerBound(new HistEvent(0, '', firstDate))
			while (itr.data() != null){
				let event = itr.data()!;
				itr.next();
				if (!event.start.isEarlier(lastDate)){
					break;
				}
				let unit = dateToUnit(event.start, SCALES[scaleIdx]);
				if (eventCounts.has(unit)){
					eventCounts.set(unit, eventCounts.get(unit)! + 1);
				}
			}
			for (let [, count] of eventCounts.entries()){
				eventCount += Math.min(MAX_EVENTS_PER_UNIT, count);
			}
			// If we have enough events
			if (eventCount >= fullCount || eventCount >= EVENT_REQ_LIMIT){
				pendingReq = false;
				return;
			}
		}
	}
	// Get events from server
	let urlParams = new URLSearchParams({
		type: 'events',
		range: `${firstDate}.${lastDate}`,
		scale: String(SCALES[scaleIdx]),
		limit: String(EVENT_REQ_LIMIT),
	});
	let responseObj: EventResponseJson = await queryServer(urlParams);
	if (responseObj == null){
		pendingReq = false;
		return;
	}
	queriedRanges[scaleIdx].add([firstDate, lastDate]);
	// Collect events
	let eventAdded = false;
	for (let eventObj of responseObj.events){
		let event = jsonToHistEvent(eventObj);
		let success = eventTree.value.insert(event);
		if (success){
			eventAdded = true;
			idToEvent.set(event.id, event);
		}
	}
	// Collect unit counts
	const unitCounts = responseObj.unitCounts;
	if (unitCounts == null){
		console.log('WARNING: Exceeded unit-count limit for server query');
	} else {
		for (let [unitStr, count] of Object.entries(unitCounts)){
			let unit = parseInt(unitStr)
			if (isNaN(unit)){
				console.log('WARNING: Invalid non-integer unit value in server response');
				break;
			}
			unitCountMaps.value[scaleIdx].set(unit, count)
		}
	}
	// Notify components if new events were added
	if (eventAdded){
		eventTree.value = rbtree_shallow_copy(eventTree.value); // Note: triggerRef(eventTree) does not work here
	}
	// Check memory limit
	displayedEvents.set(timelineId, eventIds);
	if (eventTree.value.size > EXCESS_EVENTS_THRESHOLD){
		console.log(`INFO: Calling reduceEvents() upon reaching ${eventTree.value.size} events`);
		reduceEvents();
		queriedRanges.forEach((t: DateRangeTree) => t.clear());
	}
	pendingReq = false;
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
	afterResizeHdlr = window.setTimeout(async () => {
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
