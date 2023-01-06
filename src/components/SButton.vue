<template>
<button :disabled="disabled" class="block rounded px-4 py-2"
	:class="{'hover:brightness-125': !disabled, 'brightness-50': disabled}">
	<slot>?</slot>
</button>
</template>

<script setup lang="ts">
defineProps({
	disabled: {type: Boolean, default: false},
});
</script>
