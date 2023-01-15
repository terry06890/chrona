<template>
<div :style="styles" class="p-2 rounded-full"
	:class="{'hover:brightness-125': !disabled, 'brightness-50': disabled, 'hover:cursor-pointer': !disabled}">
	<slot class="w-full h-full">?</slot>
</div>
</template>

<script setup lang="ts">
import {computed} from 'vue';

const props = defineProps({
	size: {type: Number, default: 36},
	disabled: {type: Boolean, default: false},
});

const styles = computed(() => ({
	minWidth: props.size + 'px',
	maxWidth: props.size + 'px',
	minHeight: props.size + 'px',
	maxHeight: props.size + 'px',
	padding: (props.size / 5) + 'px',
}));
</script>
