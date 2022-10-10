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
		<time-line v-for="(range, idx) in timelineRanges" :key="range.id"
			:vert="vert" :initialStart="range.start" :initialEnd="range.end"
			class="grow basis-full min-h-0 outline outline-1"
			@remove="onTimelineRemove(idx)" @range-chg="onRangeChg($event, idx)"/>
		<base-line :vert="vert" :timelineRanges="timelineRanges"/>
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
import {TimelineRange} from './lib';
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
const timelineRanges: Ref<TimelineRange[]> = ref([]);
let nextTimelineId = 1;
function addNewTimelineRange(){
	timelineRanges.value.push({id: nextTimelineId, start: -500, end: 500});
	nextTimelineId++;
}
addNewTimelineRange();
function onRangeChg(newBounds: [number, number], idx: number){
	let range = timelineRanges.value[idx];
	range.start = newBounds[0];
	range.end = newBounds[1];
}

// For timeline addition/removal
const MIN_TIMELINE_BREADTH = 150;
function onTimelineAdd(){
	if (vert.value && contentWidth.value / (timelineRanges.value.length + 1) < MIN_TIMELINE_BREADTH ||
		!vert.value && contentHeight.value / (timelineRanges.value.length + 1) < MIN_TIMELINE_BREADTH){
		console.log('Reached timeline minimum breadth');
		return;
	}
	addNewTimelineRange();
}
function onTimelineRemove(idx: number){
	if (timelineRanges.value.length == 1){
		console.log('Ignored removal of last timeline')
		return;
	}
	timelineRanges.value.splice(idx, 1);
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
