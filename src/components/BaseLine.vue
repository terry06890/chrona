<template>
<div class="bg-stone-900 text-stone-50 flex relative" :class="{'flex-col': vert}">
	<div v-for="p in periods" :key="p.label" :style="periodStyles(p)">
		<div :style="labelStyles">{{p.label}}</div>
	</div>
	<TransitionGroup name="fade">
		<div v-for="d in timelineData" :key="d.id"
			class="absolute bg-yellow-200/50" :style="spanStyles(d)">
			{{d.id}}
		</div>
	</TransitionGroup>
</div>
</template>

<script setup lang="ts">
import {ref, computed} from 'vue';
import {MIN_DATE, MAX_DATE} from '../lib';

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
	let beforeFrac = Math.max(0, (d.start - MIN_DATE) / (MAX_DATE - MIN_DATE)); // Clip at zero due to end-padding
	let lenFrac = Math.min(1 - beforeFrac, (d.end - d.start) / (MAX_DATE - MIN_DATE));
	if (props.vert){
		styles = {
			top: beforeFrac * 100 + '%',
			left: 0,
			height: lenFrac * 100 + '%',
			width: '100%',
		}
	} else {
		styles = {
			top: 0,
			left: beforeFrac * 100 + '%',
			height: '100%',
			width: lenFrac * 100 + '%',
		}
	}
	return {
		...styles,
		transition: 'all 300ms ease-out',
	};
}
</script>
