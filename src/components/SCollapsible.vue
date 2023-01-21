<template>
<div :style="styles">
	<div class="hover:cursor-pointer" @click="onClick">
		<slot name="summary" :open="open">(Summary)</slot>
	</div>
	<transition @enter="onEnter" @after-enter="onAfterEnter" @leave="onLeave" @before-leave="onBeforeLeave">
		<div v-show="open" :style="contentStyles" class="max-h-0" ref="content">
			<slot name="content">(Content)</slot>
		</div>
	</transition>
</div>
</template>

<script setup lang="ts">
import {ref, computed, watch} from 'vue';

const props = defineProps({
	modelValue: {type: Boolean, default: false}, // For using v-model on the component
});

const emit = defineEmits(['update:modelValue', 'open']);

// ========== For open status ==========

const open = ref(false);
watch(() => props.modelValue, (newVal) => {open.value = newVal})

function onClick(){
	open.value = !open.value;
	emit('update:modelValue', open.value);
	if (open.value){
		emit('open');
	}
}

// ========== For styles ==========

const styles = computed(() => ({
	overflow: open.value ? 'visible' : 'hidden',
}));

const contentStyles = computed(() => ({
	overflow: 'hidden',
	opacity: open.value ? '1' : '0',
	transitionProperty: 'max-height, opacity',
	transitionDuration: '300ms',
	transitionTimingFunction: 'ease-in-out',
}));

function onEnter(el: HTMLDivElement){
	el.style.maxHeight = el.scrollHeight + 'px';
}

function onAfterEnter(el: HTMLDivElement){
	el.style.maxHeight = 'none';
		// Allows the content to grow after the transition ends, as the scrollHeight sometimes is too short
}

function onBeforeLeave(el: HTMLDivElement){
	el.style.maxHeight = el.scrollHeight + 'px';
	el.offsetWidth; // Triggers reflow
}

function onLeave(el: HTMLDivElement){
	el.style.maxHeight = '0';
}
</script>
