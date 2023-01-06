<template>
<div class="fixed left-0 top-0 w-full h-full bg-black/40" @click="onClose" ref="rootRef">
	<div class="absolute left-1/2 -translate-x-1/2 top-1/2 -translate-y-1/2
		max-w-[80%] w-2/3 min-w-[8cm] md:w-[14cm] lg:w-[16cm] max-h-[80%]" :style="styles">
		<close-icon @click.stop="onClose" ref="closeRef"
			class="absolute top-1 right-1 md:top-2 md:right-2 w-8 h-8 hover:cursor-pointer"/>
		<h1 class="text-center text-xl font-bold pt-2 pb-1 md:text-2xl md:pt-3 md:pb-1">
			{{event.title}}
		</h1>
		<p class="text-center text-sm md:text-base">{{datesDisplayStr}}</p>
		<div class="border-t border-stone-400 p-2 md:p-3">
			<div class="mt-1 mr-2 md:mb-2 md:mr-4 md:float-left">
				<!-- Image -->
				<a :href="eventInfo.imgInfo.url" target="_blank" class="block w-fit mx-auto" :style="imgStyles"></a>
				<!-- Image Source -->
				<s-collapsible class="text-sm text-center w-fit max-w-full md:max-w-[200px] mx-auto">
					<template v-slot:summary="slotProps">
						<div class="py-1 hover:underline">
							<down-icon class="inline-block w-4 h-4 mr-1 transition-transform duration-300"
								:class="{'-rotate-90': slotProps.open}"/>
							Image Source
						</div>
					</template>
					<template v-slot:content>
						<ul class="rounded overflow-x-auto p-1"
							:style="{backgroundColor: store.color.bg, color: store.color.text}">
							<li>
								<span :style="{color: store.color.altDark}">Source: </span>
								<a :href="eventInfo.imgInfo.url" target="_blank">Link</a>
								<external-link-icon class="inline-block w-3 h-3 ml-1"/>
							</li>
							<li class="whitespace-nowrap">
								<span :style="{color: store.color.altDark}">Artist: </span>
								{{eventInfo.imgInfo.artist}}
							</li>
							<li v-if="eventInfo.imgInfo.credit != ''" class="whitespace-nowrap">
								<span :style="{color: store.color.altDark}">Credits: </span>
								{{eventInfo.imgInfo.credit}}
							</li>
							<li>
								<span :style="{color: store.color.altDark}">License: </span>
								<a :href="licenseToUrl(eventInfo.imgInfo.license)" target="_blank">
									{{eventInfo.imgInfo.license}}
								</a>
								<external-link-icon class="inline-block w-3 h-3 ml-1"/>
							</li>
							<li>
								<span :style="{color: store.color.altDark}">Obtained via: </span>
								<a href="https://www.wikipedia.org/">Wikipedia</a>
								<external-link-icon class="inline-block w-3 h-3 ml-1"/>
							</li>
							<li>
								<span :style="{color: store.color.altDark}">Changes: </span>
								Cropped and resized
							</li>
						</ul>
					</template>
				</s-collapsible>
			</div>
			<div>{{eventInfo.desc}}</div>
			<div class="text-sm text-right">
				<a :href="'https://en.wikipedia.org/?curid=' + eventInfo.wikiId" target="_blank">From Wikipedia</a>
				(via <a :href="'https://www.wikidata.org/wiki/Q' + event.id" target="_blank">Wikidata</a>)
				<external-link-icon class="inline-block w-3 h-3 ml-1"/>
			</div>
		</div>
	</div>
</div>
</template>

<script setup lang="ts">
import {ref, computed, PropType} from 'vue';
import SCollapsible from './SCollapsible.vue';
import CloseIcon from './icon/CloseIcon.vue';
import DownIcon from './icon/DownIcon.vue';
import ExternalLinkIcon from './icon/ExternalLinkIcon.vue';
import {EventInfo} from '../lib';
import {useStore} from '../store';

// Refs
const rootRef = ref(null as HTMLDivElement | null);
const closeRef = ref(null as typeof CloseIcon | null);

// Global store
const store = useStore();

// Props + events
const props = defineProps({
	eventInfo: {type: Object as PropType<EventInfo>, required: true},
});
const emit = defineEmits(['close']);

// For data display
const event = computed(() => props.eventInfo.event)
const datesDisplayStr = computed(() => {
	return event.value.start.toString() + (event.value.end == null ? '' : ' to ' + event.value.end.toString())
});
function licenseToUrl(license: string){
	license = license.toLowerCase().replaceAll('-', ' ');
	if (license == 'cc0'){
		return 'https://creativecommons.org/publicdomain/zero/1.0/';
	} else if (license == 'cc publicdomain'){
		return 'https://creativecommons.org/licenses/publicdomain/';
	} else {
		const regex = /cc by( nc)?( sa)?( ([0-9.]+)( [a-z]+)?)?/;
		let results = regex.exec(license);
		if (results != null){
			let url = 'https://creativecommons.org/licenses/by';
			if (results[1] != null){
				url += '-nc';
			}
			if (results[2] != null){
				url += '-sa';
			}
			if (results[4] != null){
				url += '/' + results[4];
			} else {
				url += '/4.0';
			}
			if (results[5] != null){
				url += '/' + results[5].substring(1);
			}
			return url;
		}
		return "[INVALID LICENSE]";
	}
}

// Close handling
function onClose(evt: Event){
	if (evt.target == rootRef.value || closeRef.value!.$el.contains(evt.target)){
		emit('close');
	}
}

// Styles
const styles = computed(() => ({
	backgroundColor: store.color.bgAlt,
	borderRadius: store.borderRadius + 'px',
	overflow: 'visible auto',
}));
const imgStyles = computed(() => {
	return {
		width: '200px',
		height: '200px',
		//backgroundImage:
		backgroundColor: store.color.bgDark,
		//backgroundSize: 'cover',
		borderRadius: store.borderRadius + 'px',
	};
});
</script>