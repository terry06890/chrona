<template>
<div class="flex relative" :class="{'flex-col': vert}"
	:style="{color: store.color.text, backgroundColor: store.color.bgDark}" ref="rootRef">
	<div v-for="p in periods" :key="p.label" :style="periodStyles(p)">
		<div :style="labelStyles">{{p.label}}</div>
	</div>
	<TransitionGroup name="fade">
		<div v-for="range in timelineRanges" :key="range.id" class="absolute" :style="spanStyles(range)">
			{{range.id}}
		</div>
	</TransitionGroup>
</div>
</template>

<script setup lang="ts">
import {ref, computed, onMounted, PropType, Ref} from 'vue';
import {MIN_DATE, MAX_DATE, WRITING_MODE_HORZ, TimelineRange} from '../lib';
import {useStore} from '../store';

// Refs
const rootRef = ref(null as HTMLElement | null);

// Global store
const store = useStore();

// Props
const props = defineProps({
	vert: {type: Boolean, required: true},
	timelineRanges: {type: Object as PropType<TimelineRange[]>, required: true},
});

// Static time periods
type Period = {label: string, len: number};
const periods: Ref<Period[]> = ref([
	{label: 'One', len: 1},
	{label: 'Two', len: 2},
	{label: 'Three', len: 1},
]);

// For size tracking (used to prevent time spans shrinking below 1 pixel)
const width = ref(0);
const height = ref(0);
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

// Styles
function periodStyles(period: Period){
	return {
		outline: '1px solid gray',
		flexGrow: period.len,
	};
}
const labelStyles = computed((): Record<string, string> => ({
	transform: props.vert ? 'rotate(90deg) translate(50%, 0)' : 'none',
	whiteSpace: 'nowrap',
	width: props.vert ? '40px' : 'auto',
	padding: props.vert ? '0' : '4px',
}));
function spanStyles(range: TimelineRange){
	let styles: Record<string,string>;
	let availLen = props.vert ? height.value : width.value;
	let startFrac = (range.start - MIN_DATE) / (MAX_DATE - MIN_DATE);
	let lenFrac = (range.end - range.start) / (MAX_DATE - MIN_DATE);
	let startPx = Math.max(0, availLen * startFrac); // Prevent negatives due to end-padding
	let lenPx = Math.min(availLen - startPx, availLen * lenFrac);
	lenPx = Math.max(1, lenPx);
	if (props.vert){
		styles = {
			top: startPx + 'px',
			left: '0',
			height: lenPx + 'px',
			width: '100%',
		}
	} else {
		styles = {
			top: '0',
			left: startPx + 'px',
			height: '100%',
			width: lenPx + 'px',
		}
	}
	return {
		...styles,
		transition: 'all 300ms ease-out',
		color: 'black',
		backgroundColor: store.color.alt,
		opacity: 0.3,
	};
}
</script>
