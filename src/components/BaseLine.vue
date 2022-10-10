<template>
<div class="bg-stone-900 text-stone-50 flex relative" :class="{'flex-col': vert}" ref="rootRef">
	<div v-for="p in periods" :key="p.label" :style="periodStyles(p)">
		<div :style="labelStyles">{{p.label}}</div>
	</div>
	<TransitionGroup name="fade">
		<div v-for="d in timelineData" :key="d.id"
			class="absolute bg-yellow-200/30" :style="spanStyles(d)">
			{{d.id}}
		</div>
	</TransitionGroup>
</div>
</template>

<script setup lang="ts">
import {ref, computed, onMounted} from 'vue';
import {MIN_DATE, MAX_DATE} from '../lib';

// Refs
const rootRef = ref(null as HTMLElement | null);

// Props
const props = defineProps({
	vert: {type: Boolean, required: true},
	timelineData: {type: Object, required: true},
});

// Static time periods to represent
const periods = ref([
	{label: 'One', len: 1},
	{label: 'Two', len: 2},
	{label: 'Three', len: 1},
]);

// For size tracking
const width = ref(0);
const height = ref(0);
const WRITING_MODE_HORZ = window.getComputedStyle(document.body)['writing-mode'].startsWith('horizontal');
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
function periodStyles(period){
	return {
		outline: '1px solid gray',
		flexGrow: period.len,
	};
}
const labelStyles: Record<string,string> = computed(() => ({
	transform: props.vert ? 'rotate(90deg) translate(50%, 0)' : 'none',
	whiteSpace: 'nowrap',
	width: props.vert ? '40px' : 'auto',
	padding: props.vert ? '0' : '4px',
}));
function spanStyles(d){
	let styles: Record<string,string>;
	let availLen = props.vert ? height.value : width.value;
	let startFrac = (d.start - MIN_DATE) / (MAX_DATE - MIN_DATE);
	let lenFrac = (d.end - d.start) / (MAX_DATE - MIN_DATE);
	let startPx = Math.max(0, availLen * startFrac); // Prevent negatives due to end-padding
	let lenPx = Math.min(availLen - startPx, availLen * lenFrac);
	lenPx = Math.max(1, lenPx);
	if (props.vert){
		styles = {
			top: startPx + 'px',
			left: 0,
			height: lenPx + 'px',
			width: '100%',
		}
	} else {
		styles = {
			top: 0,
			left: startPx + 'px',
			height: '100%',
			width: lenPx + 'px',
		}
	}
	return {
		...styles,
		transition: 'all 300ms ease-out',
	};
}
</script>
