<template>
<div class="fixed left-0 top-0 w-full h-full bg-black/40" @click="onClose" ref="rootRef">
	<div class="absolute left-1/2 -translate-x-1/2 top-1/4 -translate-y-1/2 min-w-3/4 md:min-w-[12cm] flex"
		:style="styles">
		<input type="text" class="block border p-1 px-2 rounded-l-[inherit] grow" ref="inputRef"
			@keyup.enter="onSearch" @keyup.esc="onClose"
			@input="onInput" @keydown.down.prevent="onDownKey" @keydown.up.prevent="onUpKey"/>
		<div class="p-1 hover:cursor-pointer">
			<search-icon @click.stop="onSearch" class="w-8 h-8"/>
		</div>
		<div class="absolute top-[100%] w-full overflow-hidden" :style="suggContainerStyles">
			<div v-for="(sugg, idx) of searchSuggs" :key="sugg"
				:style="{backgroundColor: idx == focusedSuggIdx ? store.color.bgAltDark : store.color.bgAlt}"
				class="border-b p-1 px-2 hover:underline hover:cursor-pointer flex"
				@click="resolveSearch(sugg)">
				<div class="grow overflow-hidden whitespace-nowrap text-ellipsis">
					<span>{{suggDisplayStrings[idx][0]}}</span>
					<span class="font-bold text-yellow-600">{{suggDisplayStrings[idx][1]}}</span>
					<span>{{suggDisplayStrings[idx][2]}}</span>
				</div>
				<info-icon class="hover:cursor-pointer my-auto w-5 h-5"
					@click.stop="onInfoIconClick(sugg)"/>
			</div>
			<div v-if="hasMoreSuggs" class="text-center">&#x2022; &#x2022; &#x2022;</div>
		</div>
	</div>
</div>
</template>

<script setup lang="ts">
import {ref, computed, onMounted, PropType} from 'vue';
import SearchIcon from './icon/SearchIcon.vue';
import InfoIcon from './icon/InfoIcon.vue';
import {HistEvent, queryServer, EventInfoJson, jsonToEventInfo, SuggResponseJson, animateWithClass} from '../lib';
import {useStore} from '../store';
import {RBTree} from '../rbtree';

// Refs
const rootRef = ref(null as HTMLDivElement | null);
const inputRef = ref(null as HTMLInputElement | null);

// Global store
const store = useStore();

// Props + events
const props = defineProps({
	eventTree: {type: Object as PropType<RBTree<HistEvent>>, required: true},
	titleToEvent: {type: Object as PropType<Map<string, HistEvent>>, required: true},
});
const emit = defineEmits(['search', 'close', 'info-click']);

// Search-suggestion data
const searchSuggs = ref([] as string[]);
const hasMoreSuggs = ref(false);
const suggsInput = ref(''); // The input that resulted in the current suggestions (used to highlight matching text)
const suggDisplayStrings = computed((): [string, string, string][] => {
	let result: [string, string, string][] = [];
	let input = suggsInput.value;
	// Split each suggestion's text into parts before/within/after an input match
	for (let title of searchSuggs.value){
		let idx = title.toLowerCase().indexOf(input.toLowerCase());
		if (idx != -1){
			result.push([
				title.substring(0, idx),
				title.substring(idx, idx + input.length),
				title.substring(idx + input.length)
			]);
		} else {
			result.push([input, '', '']);
		}
	}
	return result;
});
const focusedSuggIdx = ref(null as null | number); // Index of a suggestion selected using the arrow keys

// For server requests
const lastReqTime = ref(0);
const pendingReqParams = ref(null as null | URLSearchParams); // Holds data for latest request to make
const pendingReqInput = ref(''); // Holds the user input associated with pendingReqData
const pendingDelayedSuggReq = ref(0); // Set via setTimeout() for making a request despite a previous one still waiting
async function onInput(){
	let input = inputRef.value!;
	// Check for empty input
	if (input.value.length == 0){
		searchSuggs.value = [];
		hasMoreSuggs.value = false;
		focusedSuggIdx.value = null;
		return;
	}
	// Create URL params
	let urlParams = new URLSearchParams({
		type: 'sugg',
		input: input.value,
		limit: String(store.searchSuggLimit),
	});
	if (Object.values(store.ctgs).some((b: boolean) => !b)){ // If any event categories are disabled
		let visibleCtgs = Object.entries(store.ctgs).filter(([, enabled]) => enabled).map(([ctg, ]) => ctg);
		urlParams.append('ctgs', visibleCtgs.join('.'));
	}
	if (store.reqImgs){
		urlParams.append('imgonly', 'true');
	}
	// Code for querying server
	pendingReqParams.value = urlParams;
	pendingReqInput.value = input.value;
	let doReq = async () => {
		let reqInput = pendingReqInput.value;
		let responseObj: SuggResponseJson | null = await queryServer(pendingReqParams.value!);
		if (responseObj == null){
			return;
		}
		searchSuggs.value = responseObj.suggs;
		hasMoreSuggs.value = responseObj.hasMore;
		suggsInput.value = reqInput;
		// Auto-select first result if present
		if (searchSuggs.value.length > 0){
			focusedSuggIdx.value = 0;
		} else {
			focusedSuggIdx.value = null;
		}
	};
	// Query server, delaying/skipping if a request was recently sent
	let currentTime = new Date().getTime();
	if (lastReqTime.value == 0){
		lastReqTime.value = currentTime;
		await doReq();
		if (lastReqTime.value == currentTime){
			lastReqTime.value = 0;
		}
	} else if (pendingDelayedSuggReq.value == 0){
		lastReqTime.value = currentTime;
		pendingDelayedSuggReq.value = window.setTimeout(async () => {
			pendingDelayedSuggReq.value = 0;
			await doReq();
			if (lastReqTime.value == currentTime){
				lastReqTime.value = 0;
			}
		}, 300);
	}
}

// For search events
function onSearch(){
	if (focusedSuggIdx.value == null){
		let input = inputRef.value!.value;
		resolveSearch(input)
	} else {
		resolveSearch(searchSuggs.value[focusedSuggIdx.value]);
	}
}
async function resolveSearch(eventTitle: string){
	if (eventTitle == ''){
		return;
	}
	let visibleCtgs = null as null | string[];
	if (Object.values(store.ctgs).some((b: boolean) => !b)){
		visibleCtgs = Object.entries(store.ctgs).filter(([, enabled]) => enabled).map(([ctg, ]) => ctg);
	}
	// Check if the event data is already here
	if (props.titleToEvent.has(eventTitle)){
		let event = props.titleToEvent.get(eventTitle)!;
		// Check for disabled event categories
		if (visibleCtgs != null && !visibleCtgs.includes(event.ctg)){
			console.log('INFO: Ignoring search for known event due to category filter');
			return;
		}
		if (store.reqImgs && event.imgId == null){
			console.log('INFO: Ignoring search for known event due to image-only display');
			return;
		}
		emit('search', event);
		return;
	}
	// Query server for event
	let urlParams = new URLSearchParams({type: 'info', event: eventTitle});
	if (visibleCtgs != null){
		urlParams.append('ctgs', visibleCtgs.join('.'));
	}
	if (store.reqImgs){
		urlParams.append('imgonly', 'true');
	}
	let responseObj: EventInfoJson | null = await queryServer(urlParams);
	if (responseObj != null){
		let eventInfo = jsonToEventInfo(responseObj);
		if (store.reqImgs && eventInfo.event.imgId == null){
			console.log('INFO: Ignoring search result due to image-only display');
			return;
		}
		emit('search', eventInfo.event);
	} else { // Trigger failure animation
		animateWithClass(inputRef.value!, 'animate-red-then-fade');
	}
}

// More event handling
function onClose(evt: Event){
	if (evt.target == rootRef.value){
		emit('close');
	}
}
function onDownKey(){
	if (focusedSuggIdx.value != null){
		focusedSuggIdx.value = (focusedSuggIdx.value + 1) % searchSuggs.value.length;
	}
}
function onUpKey(){
	if (focusedSuggIdx.value != null){
		focusedSuggIdx.value = (focusedSuggIdx.value - 1 + searchSuggs.value.length) % searchSuggs.value.length;
			// The addition after '-1' is to avoid becoming negative
	}
}
function onInfoIconClick(eventTitle: string){
	emit('info-click', eventTitle);
}

// Focus input on mount
onMounted(() => inputRef.value!.focus())

// Styles
const styles = computed((): Record<string,string> => {
	let br = store.borderRadius;
	return {
		backgroundColor: store.color.bgAlt,
		borderRadius: (searchSuggs.value.length == 0) ? `${br}px` : `${br}px ${br}px 0 0`,
	};
});
const suggContainerStyles = computed((): Record<string,string> => {
	let br = store.borderRadius;
	return {
		backgroundColor: store.color.bgAlt,
		borderRadius: `0 0 ${br}px ${br}px`,
	};
});
</script>
