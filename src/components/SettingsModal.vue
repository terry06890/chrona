<template>
<div class="fixed left-0 top-0 w-full h-full bg-black/40" @click="onClose" ref="rootRef">
	<div class="absolute left-1/2 -translate-x-1/2 top-1/2 -translate-y-1/2
		min-w-[8cm] sm:min-w-[9cm] max-w-[80%] max-h-[80%] overflow-auto" :style="styles">
		<close-icon @click.stop="onClose" ref="closeRef"
			class="absolute top-1 right-1 md:top-2 md:right-2 w-8 h-8 hover:cursor-pointer" />
		<h1 class="text-xl md:text-2xl font-bold text-center py-2" :class="borderBClasses">Settings</h1>

		<!-- Categories -->
		<div class="pb-2 sm:pb-3" :class="borderBClasses">
			<h2 class="font-bold md:text-xl text-center pt-1 md:pt-2 md:pb-1">Categories</h2>
			<ul class="px-2 grid grid-cols-3 sm:px-4">
				<!-- Row 1 -->
				<li> <label> <input type="checkbox" v-model="store.ctgs.event" :disabled="lastCtg == 'event'"
					@change="onSettingChg('ctgs.event')"/> Event </label> </li>
				<li> <label> <input type="checkbox" v-model="store.ctgs.person" :disabled="lastCtg == 'person'"
					@change="onSettingChg('ctgs.person')"/> Person </label> </li>
				<li> <label> <input type="checkbox" v-model="store.ctgs.work" :disabled="lastCtg == 'work'"
					@change="onSettingChg('ctgs.work')"/> Work </label> </li>
				<!-- Row 2 -->
				<li> <label> <input type="checkbox" v-model="store.ctgs.place" :disabled="lastCtg == 'place'"
					@change="onSettingChg('ctgs.place')"/> Place </label> </li>
				<li> <label> <input type="checkbox" v-model="store.ctgs.organism" :disabled="lastCtg == 'organism'"
					@change="onSettingChg('ctgs.organism')"/> Organism </label> </li>
				<li> <label> <input type="checkbox" v-model="store.ctgs.discovery" :disabled="lastCtg == 'discovery'"
					@change="onSettingChg('ctgs.discovery')"/> Discovery </label> </li>
			</ul>
		</div>

		<!-- Display settings -->
		<div class="pb-2 sm:pb-3" :class="borderBClasses">
			<h2 class="font-bold md:text-xl text-center pt-1 md:pt-2 md:pb-1">Display</h2>
			<div class="grid grid-cols-2 px-2 sm:px-4">
				<div class="col-span-2">
					<label> <input type="checkbox" v-model="store.reqImgs"
						@change="onSettingChg('reqImgs')"/> Only events with images </label>
				</div>
				<div>
					<label> <input type="checkbox" v-model="store.showMinorTicks"
						@change="onSettingChg('showMinorTicks')"/> Minor tick text </label>
				</div>
				<div>
					<label> <input type="checkbox" v-model="store.showEventLines"
						@change="onSettingChg('showEventLines')"/> Event lines </label>
				</div>
				<div>
					<label> <input type="checkbox" v-model="store.showEventCounts"
						@change="onSettingChg('showEventCounts')"/> Event density </label>
				</div>
				<div>
					<label> <input type="checkbox" v-model="store.showBaseLine"
						@change="onSettingChg('showBaseLine')"/> Baseline </label>
				</div>
			</div>
		</div>

		<!-- Input settings -->
		<div v-if="store.touchDevice == false" class="pb-2" :class="borderBClasses">
			<h2 class="font-bold md:text-xl text-center pt-1 md:pt-2 md:pb-1">Input</h2>
			<div class="px-2 sm:px-4 pb-1">
				<label> <input type="checkbox" v-model="store.disableShortcuts"
					@change="onSettingChg('disableShortcuts')"/> Disable keyboard shortcuts </label>
			</div>
			<div class="grid grid-cols-[100px_minmax(0,1fr)_30px] gap-1 w-fit mx-auto px-2 sm:px-4">
				<!-- Row 1 -->
				<label for="scrollRatio" @click="onResetOne('scrollRatio')" :class="rLabelClasses">
					Pan ratio
				</label>
				<input type="range" min="0.1" max="0.8" step="0.1" v-model.number="store.scrollRatio"
					@change="onSettingChg('scrollRatio')" name="scrollRatio"/>
				<div class="my-auto text-right">{{store.scrollRatio}}</div>
				<!-- Row 2 -->
				<label for="zoomRatio" @click="onResetOne('zoomRatio')" :class="rLabelClasses">
					Zoom ratio
				</label>
				<input type="range" min="1.2" max="5" step="0.2" v-model.number="store.zoomRatio"
					@change="onSettingChg('zoomRatio')" name="zoomRatio"/>
				<div class="my-auto text-right">{{store.zoomRatio}}</div>
			</div>
		</div>

		<!-- Reset button -->
		<s-button class="mx-auto my-2" :style="{color: store.color.text, backgroundColor: store.color.bg}"
			@click="onReset">
			Reset
		</s-button>

		<!-- Save indicator -->
		<transition name="fade">
			<div v-if="saved" class="absolute right-1 bottom-1" ref="saveIndRef"> Saved </div>
		</transition>
	</div>
</div>
</template>

<script setup lang="ts">
import {ref, computed} from 'vue';
import SButton from './SButton.vue';
import CloseIcon from './icon/CloseIcon.vue';
import {useStore} from '../store';

const rootRef = ref(null as HTMLDivElement | null);
const closeRef = ref(null as typeof CloseIcon | null);
const saveIndRef = ref(null as HTMLDivElement | null);

const store = useStore();

const emit = defineEmits(['close', 'change']);

// ========== Settings change handling ==========

const saved = ref(false); // Set to true after a setting is saved

const lastCtg = computed(() => { // When all but one category is disabled, names the remaining category
	let enabledCtgs = Object.entries(store.ctgs).filter(([, enabled]) => enabled).map(([ctg, ]) => ctg);
	if (enabledCtgs.length == 1){
		return enabledCtgs[0];
	} else {
		return null;
	}
});

let changedCtg: string | null = null; // Used to defer signalling of a category change until modal closes

function onSettingChg(option: string){ 
	store.save(option);

	if (option.startsWith('ctgs.')){
		changedCtg = option;
	} else {
		emit('change', option);
	}

	// Make 'Saved' indicator appear/animate
	if (!saved.value){
		saved.value = true;
	} else {
		let el = saveIndRef.value!;
		el.classList.remove('animate-flash-yellow');
		el.offsetWidth; // Triggers reflow
		el.classList.add('animate-flash-yellow');
	}
}

function onResetOne(option: string){
	store.resetOne(option);
	onSettingChg(option);
}

function onReset(){
	store.reset();
	store.clear();
	saved.value = false;
}

// ========== Close handling ==========

function onClose(evt: Event){
	if (evt.target == rootRef.value || closeRef.value!.$el.contains(evt.target)){
		emit('close');
		if (changedCtg != null){
			emit('change', changedCtg);
		}
	}
}

// ========== For styling ==========

const borderBClasses = 'border-b border-stone-400';
const rLabelClasses = "w-fit hover:cursor-pointer hover:text-yellow-600"; // For reset-upon-click labels

const styles = computed(() => ({
	backgroundColor: store.color.bgAlt,
	borderRadius: store.borderRadius + 'px',
}));
</script>
