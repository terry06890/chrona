<template>
<div class="absolute left-0 top-0 w-screen h-screen overflow-hidden flex flex-col" style="bg-stone-800" >
	<!-- Title bar -->
	<div class="flex shadow gap-2 p-2 bg-stone-900 text-yellow-500">
		<h1 class="my-auto ml-2 text-4xl">Histplorer</h1>
		<div class="mx-auto"/> <!-- Spacer -->
		<!-- Icons -->
		<icon-button :size="45" class="text-stone-50 bg-yellow-600" @click="onTimelineAdd" title="Add a timeline">
			<plus-icon/>
		</icon-button>
		<icon-button :size="45" class="text-stone-50 bg-yellow-600">
			<settings-icon/>
		</icon-button>
		<icon-button :size="45" class="text-stone-50 bg-yellow-600">
			<help-icon/>
		</icon-button>
	</div>
	<!-- Content area -->
	<div class="grow min-h-0 bg-stone-800 relative" ref="contentAreaRef">
		<time-line v-for="(data, idx) in timelineData" :key="data"
			:style="{
				position: 'absolute',
				top: (vert ? 0 : idx * contentHeight / timelineData.length) + 'px',
				left: (vert ? idx * contentWidth / timelineData.length : 0) + 'px',
				outline: 'black solid 1px',
			}"
			:width="vert ? contentWidth / timelineData.length : contentWidth"
			:height="vert ? contentHeight : contentHeight / timelineData.length"
			:vert="vert"
			@close="onTimelineClose(idx)"/>
	</div>
</div>
</template>

<script setup lang="ts">
import {ref, computed, onMounted, onUnmounted} from 'vue';
// Components
import TimeLine from './components/TimeLine.vue';
import IconButton from './components/IconButton.vue';
// Icons
import PlusIcon from './components/icon/PlusIcon.vue';
import SettingsIcon from './components/icon/SettingsIcon.vue';
import HelpIcon from './components/icon/HelpIcon.vue';

// Refs
const contentAreaRef = ref(null as HTMLElement | null);

// For content sizing
const contentWidth = ref(0);
const contentHeight = ref(0);
function updateAreaDims(){
	let contentAreaEl = contentAreaRef.value!;
	contentWidth.value = contentAreaEl.offsetWidth;
	contentHeight.value = contentAreaEl.offsetHeight;
}
onMounted(updateAreaDims)

// For multiple timelines
const vert = computed(() => contentHeight.value > contentWidth.value);
const timelineData = ref([{}]);
function onTimelineAdd(){
	if (vert.value && contentWidth.value / (timelineData.value.length + 1) < 150 ||
		!vert.value && contentHeight.value / (timelineData.value.length + 1) < 150){
		console.log('Reached timeline min size');
		return;
	}
	timelineData.value.push({});
}
function onTimelineClose(idx: number){
	if (timelineData.value.length == 1){
		console.log('Ignored close for last timeline')
		return;
	}
	timelineData.value.splice(idx, 1);
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
</script>
