<template>
<div class="absolute left-0 top-0 w-screen h-screen overflow-hidden flex flex-col" style="bg-stone-800" >
	<!-- Title bar -->
	<div class="flex shadow gap-2 p-2 bg-stone-900 text-yellow-500">
		<h1 class="my-auto ml-2 text-4xl">Histplorer</h1>
		<div class="mx-auto"/> <!-- Spacer -->
		<!-- Icons -->
		<icon-button :size="45" class="text-stone-50 bg-yellow-600">
			<help-icon/>
		</icon-button>
		<icon-button :size="45" class="text-stone-50 bg-yellow-600">
			<settings-icon/>
		</icon-button>
	</div>
	<!-- Content area -->
	<div class="grow min-h-0 relative bg-stone-800">
		<div class="text-stone-50 p-4">Content</div>
	</div>
</div>
</template>

<script setup lang="ts">
import {ref, computed, watch, onMounted, onUnmounted, nextTick} from 'vue';
// Components
import IconButton from './components/IconButton.vue';
// Icons
import SettingsIcon from './components/icon/SettingsIcon.vue';
import HelpIcon from './components/icon/HelpIcon.vue';

</script>
