<template>
<div class="flex relative" :class="{'flex-col': vert}"
	:style="{color: store.color.text}" ref="rootRef">
	<!-- Time periods -->
	<div v-for="p in periods" :key="p.label" class="relative" :style="periodStyles(p)">
		<div :style="labelStyles">{{p.label}}</div>
		<div v-if="props.vert" class="absolute bottom-0 w-full h-6"
			style="background-image: linear-gradient(to bottom, rgba(0,0,0,0), rgba(0,0,0,1))"></div>
	</div>
	<!-- Timeline spans -->
	<TransitionGroup name="fade" v-if="mounted">
		<div v-for="(state, idx) in timelines" :key="state.id" class="absolute" :style="spanStyles(idx)"></div>
	</TransitionGroup>
</div>
</template>

<script setup lang="ts">
import {ref, computed, onMounted, PropType, Ref} from 'vue';
import {MIN_DATE, MAX_DATE, SCALES, MONTH_SCALE, DAY_SCALE, WRITING_MODE_HORZ, TimelineState, stepDate} from '../lib';
import {useStore} from '../store';

const rootRef = ref(null as HTMLElement | null);

const store = useStore();

const props = defineProps({
	vert: {type: Boolean, required: true},
	timelines: {type: Object as PropType<TimelineState[]>, required: true},
});

// ========== Static time periods ==========

type Period = {label: string, len: number};

const periods: Ref<Period[]> = ref([
	{label: 'Pre Hadean', len: 8},
	{label: 'Hadean', len: 1},
	{label: 'Archaean', len: 1.5},
	{label: 'Proterozoic', len: 2},
	{label: 'Phanerozoic', len: 0.5},
]);

// ========== For skipping transitions on startup ==========

const skipTransition = ref(true);
onMounted(() => setTimeout(() => {skipTransition.value = false}, 100));

// ========== For size and mount-status tracking ==========

const width = ref(0);
const height = ref(0);
const mounted = ref(false);

onMounted(() => {
	let rootEl = rootRef.value!;
	width.value = rootEl.offsetWidth;
	height.value = rootEl.offsetHeight;
	mounted.value = true;
})

const resizeObserver = new ResizeObserver((entries) => {
	for (const entry of entries){
		if (entry.contentBoxSize){
			const boxSize = Array.isArray(entry.contentBoxSize) ? entry.contentBoxSize[0] : entry.contentBoxSize;
			width.value = WRITING_MODE_HORZ ? boxSize.inlineSize : boxSize.blockSize;
			height.value = WRITING_MODE_HORZ ? boxSize.blockSize : boxSize.inlineSize;
		}
	}
});
onMounted(() => resizeObserver.observe(rootRef.value as HTMLElement));

// ========== For styles ==========

function periodStyles(period: Period){
	return {
		backgroundColor: store.color.bgDark2,
		outline: '1px solid gray',
		flexGrow: period.len,
		overflow: 'hidden',
	};
}

const labelStyles = computed((): Record<string, string> => ({
	transform: props.vert ? 'rotate(90deg) translate(50%, 0)' : 'none',
	whiteSpace: 'nowrap',
	width: props.vert ? '40px' : 'auto',
	padding: props.vert ? '0' : '4px',
}));

function spanStyles(stateIdx: number){
	const state = props.timelines[stateIdx];
	let styles: Record<string,string>;
	const availLen = props.vert ? height.value : width.value;
	const availBreadth = props.vert ? width.value : height.value;

	// Determine start/end date
	if (state.startOffset == null || state.endOffset == null || state.scaleIdx == null){
		return {display: 'none'};
	}
	let start = state.startDate.clone();
	let end = state.endDate.clone();
	let scale = SCALES[state.scaleIdx];
	if (scale != MONTH_SCALE && scale != DAY_SCALE){ // Account for offsets
		stepDate(start, 1, {forward: false, count: Math.floor(state.startOffset * scale), inplace: true});
		stepDate(end, 1, {count: Math.floor(state.endOffset * scale), inplace: true});
	}

	// Determine positions in full timeline (only uses year information)
	let startFrac = (start.year - MIN_DATE.year) / (MAX_DATE.year - MIN_DATE.year);
	let lenFrac = (end.year - start.year) / (MAX_DATE.year - MIN_DATE.year);
	let startPx = Math.max(0, availLen * startFrac); // Prevent negatives due to end-padding
	let lenPx = Math.min(availLen - startPx, availLen * lenFrac);
	if (lenPx < 3){ // Prevent zero length
		lenPx = 3;
		startPx -= Math.max(0, startPx + lenPx - availLen);
	}

	// Account for multiple timelines
	const breadth = availBreadth / props.timelines.length;
	const sidePx = breadth * stateIdx;

	if (props.vert){
		styles = {
			top: startPx + 'px',
			left: sidePx + 'px',
			height: lenPx + 'px',
			width: breadth + 'px',
		}
	} else {
		styles = {
			top: sidePx + 'px',
			left: startPx + 'px',
			height: breadth + 'px',
			width: lenPx + 'px',
		}
	}
	return {
		...styles,
		transition: skipTransition.value ? 'none' : 'all 300ms ease-out',
		color: 'black',
		backgroundColor: store.color.alt,
		opacity: 0.6,
		borderWidth: '1px',
		borderColor: store.color.bg,
	};
}
</script>
