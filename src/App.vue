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
			:vert="vert" :initialState="state" :eventTree="eventTree"
			class="grow basis-full min-h-0 outline outline-1"
			@remove="onTimelineRemove(idx)" @state-chg="onTimelineChg($event, idx)"
			@event-req="onEventReq" @event-display="onEventDisplay($event, idx)"/>
		<base-line :vert="vert" :timelines="timelines"/>
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
import {timeout, HistDate, YearDate, HistEvent, queryServer, HistEventJson, jsonToHistEvent,
	TimelineState, cmpHistEvent, DateRangeTree} from './lib';
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
let exhaustedRanges = new DateRangeTree(); // Holds ranges for which the server has no more events
// For getting events from server
const EVENT_REQ_LIMIT = 30;
const REQ_EXCLS_LIMIT = 100;
let pendingReq = false; // Used to serialise event-req handling
async function onEventReq(startDate: HistDate, endDate: HistDate){
	while (pendingReq){
		await timeout(100);
	}
	pendingReq = true;
	// Skip if exhausted range
	if (exhaustedRanges.has([startDate, endDate])){
		pendingReq = false;
		return;
	}
	// Get existing events in range
	let existingEventIds: number[] = [];
	let itr = eventTree.value.lowerBound(new HistEvent(0, '', startDate));
	while (itr.data() != null){
		let event = itr.data()!;
		itr.next();
		if (endDate.isEarlier(event.start)){
			break;
		}
		existingEventIds.push(event.id);
	}
	if (existingEventIds.length > REQ_EXCLS_LIMIT){
		console.log('WARNING: Exceeded request exclusions limit');
		pendingReq = false;
		return;
	}
	// Get events from server
	let urlParams = new URLSearchParams({
		type: 'events',
		range: `${startDate}.${endDate}`,
		limit: String(EVENT_REQ_LIMIT),
		excl: existingEventIds.join('.'),
	});
	let responseObj: HistEventJson[] = await queryServer(urlParams);
	if (responseObj == null){
		pendingReq = false;
		return;
	}
	// Add to map
	let added = false;
	for (let eventObj of responseObj){
		let event = jsonToHistEvent(eventObj);
		let success = eventTree.value.insert(event);
		if (success){
			added = true;
			idToEvent.set(event.id, event);
		}
	}
	// Notify components if new events were added
	if (added){
		eventTree.value = rbtree_shallow_copy(eventTree.value); // Note: triggerRef(eventTree) does not work here
	} else {
		exhaustedRanges.add([startDate, endDate]); // Mark as exhausted range
	}
	// Check memory limit
	if (eventTree.value.size > EXCESS_EVENTS_THRESHOLD){
		reduceEvents();
	}
	pendingReq = false;
}
// For keeping event data under a memory limit
const EXCESS_EVENTS_THRESHOLD = 10000;
let displayedEvents: Map<number, number[]> = new Map(); // Maps TimeLine IDs to IDs of displayed events
function onEventDisplay(eventIds: number[], timelineId: number){
	displayedEvents.set(timelineId, eventIds);
}
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
	// Replace old data
	eventTree.value = newTree;
	idToEvent = eventsToKeep;
	exhaustedRanges.clear();
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
