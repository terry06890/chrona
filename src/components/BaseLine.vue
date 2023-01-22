<template>
<div class="flex relative" :class="{'flex-col': vert}"
	:style="{color: store.color.text, padding: PADDING + 'px'}" ref="rootRef">
	<!-- Time periods -->
	<div v-for="p in periods" :key="p.label" class="relative" :style="periodStyles(p)">
		<div :style="labelStyles">{{p.label}}</div>
		<!-- Fade-out div for overflowing text -->
		<div :style="fadeDivStyles"></div>
	</div>
	<!-- Timeline 'spans' -->
	<TransitionGroup name="fade" v-if="mounted">
		<div v-for="(state, idx) in timelines" :key="state.id" class="absolute" :style="spanStyles(idx)"></div>
	</TransitionGroup>
</div>
</template>

<script setup lang="ts">
import {ref, computed, onMounted, PropType, Ref} from 'vue';
import {MIN_DATE, MAX_DATE, SCALES, MONTH_SCALE, DAY_SCALE, stepDate, TimelineState} from '../lib';
import {useStore} from '../store';

const rootRef = ref(null as HTMLElement | null);

const store = useStore();

const props = defineProps({
	vert: {type: Boolean, required: true},
	len: {type: Number, required: true},
	timelines: {type: Object as PropType<TimelineState[]>, required: true},
});

const PADDING = 8;
const contentLen = computed(() => props.len - PADDING * 2)
const contentBreadth = computed(() => store.baseLineBreadth - PADDING * 2)

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

const mounted = ref(false);

onMounted(() => mounted.value = true);

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
	width: props.vert ? contentBreadth.value + 'px' : 'auto',
	height: props.vert ? 'auto' : contentBreadth.value + 'px',
	padding: props.vert ? '0' : '4px',
}));

const MIN_SPAN_LEN = 3;

function spanStyles(stateIdx: number){
	const state = props.timelines[stateIdx];
	let styles: Record<string,string>;

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
	let startPx = Math.max(0, contentLen.value * startFrac);
	let lenPx = Math.min(contentLen.value - startPx, contentLen.value * lenFrac);
	if (lenPx < MIN_SPAN_LEN){ // Prevent zero length
		lenPx = MIN_SPAN_LEN;
		startPx -= Math.max(0, startPx + lenPx - contentLen.value);
	}

	// Account for multiple timelines
	const breadth = contentBreadth.value / props.timelines.length;
	let sidePx = breadth * stateIdx;

	startPx += PADDING;
	sidePx += PADDING;
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
		backgroundColor: store.color.alt,
		opacity: 0.6,
		borderWidth: '1px',
		borderColor: store.color.bgDark2,
	};
}

const fadeDivStyles = computed((): Record<string, string> => ({
	position: 'absolute',
	bottom: '0',
	right: '0',
	width: props.vert ? '100%' : '24px',
	height: props.vert ? '24px' : '100%',
	backgroundImage: props.vert
		? 'linear-gradient(to bottom, rgba(0,0,0,0), rgba(0,0,0,1))'
		: 'linear-gradient(to right, rgba(0,0,0,0), rgba(0,0,0,1))',
}));
</script>
