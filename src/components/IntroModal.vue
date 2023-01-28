<template>
<div class="fixed left-0 top-0 w-full h-full bg-black/40" @click="onClose" ref="rootRef">
	<div class="absolute left-1/2 -translate-x-1/2 top-1/2 -translate-y-1/2
		max-w-[80%] w-2/3 min-w-[8cm] md:w-[12cm] max-h-[80%]" :style="styles">
		<close-icon @click.stop="onClose" ref="closeRef"
			class="absolute top-1 right-1 md:top-2 md:right-2 w-8 h-8 hover:cursor-pointer"/>

		<h1 class="text-center text-xl font-bold pt-2 pb-2 md:pt-3">
			Welcome
		</h1>

		<div class="px-4 pb-3 md:pb-4">
			<p class="px-2">
				This is an interactive historical timeline spanning 14 billion years.
			</p>
			<ul class="list-disc pl-4 pt-1">
				<li v-if="touchDevice">
					<span class="font-bold">Drag the screen</span> to move
				</li>
				<li v-else>
					<span class="font-bold">Scroll</span> or
					<span class="font-bold">press {{vert ? 'up &amp; down': 'left &amp; right'}}</span>
					to move
				</li>
				<li>
					<span class="font-bold">{{touchDevice ? 'Pinch' : 'Hold shift'}}</span> to zoom in &amp; out
				</li>
			</ul>
		</div>
	</div>
</div>
</template>

<script setup lang="ts">
import {ref, computed} from 'vue';

import CloseIcon from './icon/CloseIcon.vue';
import {useStore} from '../store';

const rootRef = ref(null as HTMLDivElement | null);
const closeRef = ref(null as typeof CloseIcon | null);

const store = useStore();
const touchDevice = computed(() => store.touchDevice)

defineProps({
	vert: {type: Boolean, required: true},
});

const emit = defineEmits(['close']);

function onClose(evt: Event){
	if (evt.target == rootRef.value || closeRef.value!.$el.contains(evt.target)){
		emit('close');
	}
}

const styles = computed(() => ({
	backgroundColor: store.color.bgAltDark,
	borderRadius: store.borderRadius + 'px',
	overflow: 'visible auto',
}));
</script>
