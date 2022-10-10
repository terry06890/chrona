<template>
<div class="bg-stone-900 text-stone-50 flex" :class="{'flex-col': vert}">
	<div v-for="p in periods" :key="p.label" :style="periodStyles(p)">
		<div :style="labelStyles">{{p.label}}</div>
	</div>
</div>
</template>

<script setup lang="ts">
import {ref, computed, PropType} from 'vue';

// Props
const props = defineProps({
	vert: {type: Boolean, required: true},
	timelineData: {type: Object as PropType<number[][]>, required: true},
});

// Time periods to represent
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
const labelStyles = computed(() => ({
	transform: props.vert ? 'rotate(90deg) translate(50%, 0)' : 'none',
	whiteSpace: 'nowrap',
	width: props.vert ? '40px' : 'auto',
	padding: props.vert ? '0' : '4px',
}));
</script>
