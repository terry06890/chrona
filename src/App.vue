<template>
<div class="absolute left-0 top-0 w-screen h-screen overflow-hidden flex flex-col">
	<!-- Title bar -->
	<div class="flex gap-2 p-2" :style="{backgroundColor: store.color.bgDark2}">
		<h1 class="my-auto sm:ml-2 text-3xl sm:text-4xl hover:cursor-pointer" :style="{color: store.color.altDark}"
			@click="onReset" title="Reset Timeline">Histplorer</h1>
		<div class="mx-auto"/> <!-- Spacer -->
		<!-- Icons -->
		<icon-button :size="45" :style="buttonStyles" @click="helpOpen = true" title="Show help info">
			<help-icon/>
		</icon-button>
		<icon-button :size="45" :style="buttonStyles" @click="settingsOpen = true" title="Show settings">
			<settings-icon/>
		</icon-button>
		<icon-button :size="45" :disabled="maxTimelines" :style="buttonStyles"
			@click="onTimelineAdd" title="Add a timeline">
			<plus-icon/>
		</icon-button>
		<icon-button :size="45" :style="buttonStyles" @click="searchOpen = true" title="Search">
			<search-icon/>
		</icon-button>
	</div>
	<!-- Content area -->
	<div class="grow min-h-0 flex" :class="{'flex-col': !vert}"
			:style="{backgroundColor: store.color.bg}" ref="contentAreaRef">
		<time-line v-for="(state, idx) in timelines" :key="state.id"
			:vert="vert" :initialState="state" :closeable="timelines.length > 1"
			:eventTree="eventTree" :unitCountMaps="unitCountMaps" :current="idx == currentTimelineIdx && !modalOpen"
			:searchTarget="searchTargets[idx]" :reset="resetFlags[idx]"
			class="grow basis-full min-h-0 outline outline-1"
			@close="onTimelineClose(idx)" @state-chg="onTimelineChg($event, idx)" @event-display="onEventDisplay"
			@info-click="onInfoClick" @pointerenter="currentTimelineIdx = idx"/>
		<base-line v-if="store.showBaseLine" :vert="vert" :timelines="timelines" class='m-1 sm:m-2'/>
	</div>
	<!-- Modals -->
	<transition name="fade">
		<search-modal v-if="searchOpen" :eventTree="eventTree" :titleToEvent="titleToEvent"
			@close="searchOpen = false" @search="onSearch" @info-click="onInfoClick"
			@net-wait="primeLoadInd(SERVER_WAIT_MSG)" @net-get="endLoadInd"/>
	</transition>
	<transition name="fade">
		<info-modal v-if="infoModalData != null" :eventInfo="infoModalData" @close="infoModalData = null"/>
	</transition>
	<transition name="fade">
		<settings-modal v-if="settingsOpen" @close="settingsOpen = false" @change="onSettingChg"/>
	</transition>
	<transition name="fade">
		<help-modal v-if="helpOpen" @close="helpOpen = false"/>
	</transition>
	<transition name="fade">
		<loading-modal v-if="loadingMsg != null" :msg="loadingMsg"/>
	</transition>
</div>
</template>

<script setup lang="ts">
import {ref, computed, onMounted, onUnmounted, Ref, shallowRef, ShallowRef} from 'vue';
// Components
import TimeLine from './components/TimeLine.vue';
import BaseLine from './components/BaseLine.vue';
import InfoModal from './components/InfoModal.vue';
import SearchModal from './components/SearchModal.vue';
import SettingsModal from './components/SettingsModal.vue';
import HelpModal from './components/HelpModal.vue';
import LoadingModal from './components/LoadingModal.vue';
import IconButton from './components/IconButton.vue';
// Icons
import HelpIcon from './components/icon/HelpIcon.vue';
import SettingsIcon from './components/icon/SettingsIcon.vue';
import PlusIcon from './components/icon/PlusIcon.vue';
import SearchIcon from './components/icon/SearchIcon.vue';
// Other
import {HistDate, HistEvent, queryServer,
	EventResponseJson, jsonToHistEvent, EventInfo, EventInfoJson, jsonToEventInfo,
	SCALES, stepDate, TimelineState, cmpHistEvent, dateToUnit, DateRangeTree,
	makeThrottled, makeThrottledSpaced} from './lib';
import {useStore} from './store';
import {RBTree, rbtree_shallow_copy} from './rbtree';

// Refs
const contentAreaRef = ref(null as HTMLElement | null);

// Global store
const store = useStore();

// For content sizing (used to decide between horizontal and vertical mode)
const contentWidth = ref(1);
const contentHeight = ref(1);
const vert = computed(() => contentHeight.value > contentWidth.value);
function updateAreaDims(){
	let contentAreaEl = contentAreaRef.value!;
	contentWidth.value = contentAreaEl.offsetWidth;
	contentHeight.value = contentAreaEl.offsetHeight;
}
onMounted(updateAreaDims);

// Timeline data
const timelines: Ref<TimelineState[]> = ref([]);
const currentTimelineIdx = ref(0);
let nextTimelineId = 1;
function addTimeline(){
	if (timelines.value.length == 0){
		timelines.value.push(new TimelineState(nextTimelineId, store.initialStartDate, store.initialEndDate));
	} else {
		let state = timelines.value[currentTimelineIdx.value];
		timelines.value.splice(currentTimelineIdx.value, 0, new TimelineState(
			nextTimelineId, state.startDate, state.endDate, state.startOffset, state.endOffset, state.scaleIdx));
	}
	searchTargets.value.splice(currentTimelineIdx.value, 0, [null, false]);
	resetFlags.value.splice(currentTimelineIdx.value, 0, false);
	currentTimelineIdx.value += 1;
	nextTimelineId += 1;
}
onMounted(addTimeline);
function onTimelineChg(state: TimelineState, idx: number){
	timelines.value[idx] = state;
	currentTimelineIdx.value = idx;
}

// For timeline addition/removal
const MIN_TIMELINE_BREADTH = store.mainlineBreadth + store.spacing * 2 + store.eventImgSz + store.eventLabelHeight;
const maxTimelines = computed(() => {
	return vert.value && contentWidth.value / (timelines.value.length + 1) < MIN_TIMELINE_BREADTH
		|| !vert.value && contentHeight.value / (timelines.value.length + 1) < MIN_TIMELINE_BREADTH
});
function onTimelineAdd(){
	if (maxTimelines.value){
		console.log('Ignored addition of timeline upon reaching max');
		return;
	}
	addTimeline();
}
function onTimelineClose(idx: number){
	if (timelines.value.length == 1){
		console.log('Ignored removal of last timeline')
		return;
	}
	timelines.value.splice(idx, 1);
	searchTargets.value.splice(idx, 1);
	resetFlags.value.splice(idx, 1);
	if (currentTimelineIdx.value >= idx){
		currentTimelineIdx.value = Math.max(0, idx - 1);
	}
}

// For storing and looking up events
const eventTree: ShallowRef<RBTree<HistEvent>> = shallowRef(new RBTree(cmpHistEvent));
let idToEvent: Map<number, HistEvent> = new Map();
let titleToEvent: Map<string, HistEvent> = new Map();
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
	titleToEvent.clear();
	for (let event of eventsToKeep.values()){
		titleToEvent.set(event.title, event);
	}
}
// For getting events from server
const eventReqLimit = computed(() => {
	const eventSz = store.eventImgSz * (store.eventImgSz + store.eventLabelHeight);
	return Math.max(20, Math.ceil(contentWidth.value * contentHeight.value / eventSz));
});
const MAX_EVENTS_PER_UNIT = 4; // Should equal MAX_DISPLAYED_PER_UNIT in backend gen_disp_data.py
let queriedRanges: DateRangeTree[] = SCALES.map(() => new DateRangeTree());
	// For each scale, holds date ranges for which data has already been queried fromm the server
let lastQueriedRange: [HistDate, HistDate] | null = null;
async function handleOnEventDisplay(
		timelineId: number, eventIds: number[], firstDate: HistDate, lastDate: HistDate, scaleIdx: number){
	let timelineIdx = timelines.value.findIndex((s : TimelineState) => s.id == timelineId);
	let targetEvent = searchTargets.value[timelineIdx][0];
	// Skip if range has been queried, and enough of its events have been obtained
	if (queriedRanges[scaleIdx].contains([firstDate, lastDate])
			&& (targetEvent == null || idToEvent.has(targetEvent.id))){
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
			if (eventCount >= fullCount || eventCount >= eventReqLimit.value){
				return;
			}
		}
	}
	// Get events from server
	if (lastQueriedRange != null && lastQueriedRange[0].equals(firstDate) && lastQueriedRange[1].equals(lastDate)
			&& (targetEvent == null || idToEvent.has(targetEvent.id))){
		console.log(`INFO: Skipping redundant server request from ${firstDate} to ${lastDate}`);
		return;
	}
	lastQueriedRange = [firstDate, lastDate];
	let urlParams = new URLSearchParams({
		// Note: Intentionally not filtering by event categories (would need category-sensitive
		// unit count data to determine when enough events have been obtained)
		type: 'events',
		range: `${firstDate}.${lastDate}`,
		scale: String(SCALES[scaleIdx]),
		limit: String(eventReqLimit.value),
	});
	if (targetEvent != null){
		urlParams.append('incl', String(targetEvent.id));
	}
	if (store.reqImgs){
		urlParams.append('imgonly', 'true');
	}
	let responseObj: EventResponseJson | null = await loadFromServer(urlParams, 2000);
	if (responseObj == null){
		console.log('WARNING: Server gave null response to event query');
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
			titleToEvent.set(event.title, event);
		}
	}
	if (targetEvent != null){
		if (!idToEvent.has(targetEvent.id)){
			console.log(`WARNING: Server response did not include event matching 'incl=${targetEvent.id}'`);
		}
		searchTargets.value[timelineIdx][0] = null;
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
}
const onEventDisplay = makeThrottled(handleOnEventDisplay, 200);

// For info modal
const infoModalData = ref(null as EventInfo | null);
async function onInfoClick(eventTitle: string){
	// Query server for event info
	let urlParams = new URLSearchParams({type: 'info', event: eventTitle});
	let responseObj: EventInfoJson | null = await loadFromServer(urlParams);
	if (responseObj != null){
		infoModalData.value = jsonToEventInfo(responseObj);
	} else {
		console.log('WARNING: Server gave null response to info query');
	}
}

// For search modal
const searchOpen = ref(false);
const searchTargets = ref([] as [HistEvent | null, boolean][]); // For communicating search results to timelines
	// A boolean flag is used to trigger jumping even when the same event occurs twice
function onSearch(event: HistEvent){
	searchOpen.value = false;
	// Trigger jump in current timeline
	let oldVal = searchTargets.value[currentTimelineIdx.value];
	searchTargets.value.splice(currentTimelineIdx.value, 1, [event, !oldVal[1]]);
}

// For settings modal
const settingsOpen = ref(false);
function onSettingChg(option: string){
	if (option == 'reqImgs'){
		// Reset event data
		eventTree.value = new RBTree(cmpHistEvent); // Will trigger event re-query
		unitCountMaps.value = SCALES.map(() => new Map());
		idToEvent.clear();
		titleToEvent.clear();
		lastQueriedRange = null;
	}
}

// For help modal
const helpOpen = ref(false);

// For loading modal
const SERVER_WAIT_MSG = 'Loading data';
const loadingMsg = ref(null as null | string);
const pendingLoadingRevealHdlr = ref(0); // Used to delay showing the loading modal
function primeLoadInd(msg: string, delay?: number){ // Sets up a loading message to display after a timeout
	clearTimeout(pendingLoadingRevealHdlr.value);
	pendingLoadingRevealHdlr.value = window.setTimeout(() => {
		loadingMsg.value = msg;
	}, delay == null ? 500 : delay);
}
function endLoadInd(){ // Cancels or closes a loading message
	clearTimeout(pendingLoadingRevealHdlr.value);
	pendingLoadingRevealHdlr.value = 0;
	if (loadingMsg.value != null){
		loadingMsg.value = null;
	}
}
async function loadFromServer(urlParams: URLSearchParams, delay?: number){ // Like queryServer() but uses loading modal
	primeLoadInd(SERVER_WAIT_MSG, delay);
	let responseObj = await queryServer(urlParams);
	endLoadInd();
	return responseObj;
}

// For timeline reset
const resetFlags: Ref<boolean[]> = ref([]);
function onReset(){
	let oldFlag = resetFlags.value[currentTimelineIdx.value];
	resetFlags.value.splice(currentTimelineIdx.value, 1, !oldFlag);
}

//
const modalOpen = computed(() =>
	(infoModalData.value != null || searchOpen.value || settingsOpen.value || helpOpen.value));

// For resize handling
const onResize = makeThrottledSpaced(updateAreaDims, 200);
	// Note: If delay is too small, touch-device detection when swapping to/from mobile-mode gets unreliable
onMounted(() => window.addEventListener('resize', onResize));
onUnmounted(() => window.removeEventListener('resize', onResize));

// For keyboard shortcuts
function onKeyDown(evt: KeyboardEvent){
	if (store.disableShortcuts){
		return;
	}
	if (evt.key == 'Escape'){
		if (infoModalData.value != null){
			infoModalData.value = null;
		} else if (searchOpen.value){
			searchOpen.value = false;
		} else if (settingsOpen.value){
			settingsOpen.value = false;
		} else if (helpOpen.value){
			helpOpen.value = false;
		}
	} else if (evt.key == 'f' && evt.ctrlKey){
		evt.preventDefault();
		// Open/focus search bar
		if (!searchOpen.value){
			searchOpen.value = true;
		}
	} else if (evt.key.startsWith('Arrow') && !modalOpen.value && !evt.shiftKey){
		if (evt.key == 'ArrowUp'){
			if (!vert.value){
				if (currentTimelineIdx.value > 0){
					currentTimelineIdx.value -= 1;
				}
			}
		} else if (evt.key == 'ArrowDown'){
			if (!vert.value){
				if (currentTimelineIdx.value < timelines.value.length - 1){
					currentTimelineIdx.value += 1;
				}
			}
		} else if (evt.key == 'ArrowLeft'){
			if (vert.value){
				if (currentTimelineIdx.value > 0){
					currentTimelineIdx.value -= 1;
				}
			}
		} else if (evt.key == 'ArrowRight'){
			if (vert.value){
				if (currentTimelineIdx.value < timelines.value.length - 1){
					currentTimelineIdx.value += 1;
				}
			}
		}
	} else if (evt.key == '+' && !modalOpen.value){
		onTimelineAdd();
	} else if (evt.key == 'Delete' && !modalOpen.value){
		onTimelineClose(currentTimelineIdx.value);
	}
}
onMounted(() => {
	window.addEventListener('keydown', onKeyDown);
		// Note: Need 'keydown' instead of 'keyup' to override default CTRL-F
});
onUnmounted(() => {
	window.removeEventListener('keydown', onKeyDown);
});

// Styles
const buttonStyles = computed(() => ({
	color: store.color.text,
	backgroundColor: store.color.altDark2,
}));
</script>
