<template>
<div class="fixed left-0 top-0 w-full h-full bg-black/40" @click="onClose" ref="rootRef">
	<div class="absolute left-1/2 -translate-x-1/2 top-1/2 -translate-y-1/2
		w-[90%] max-w-[16cm] max-h-[80%] overflow-auto" :style="styles">
		<close-icon @click.stop="onClose" ref="closeRef"
			class="absolute top-1 right-1 md:top-2 md:right-2 w-8 h-8 hover:cursor-pointer"/>
		<h1 class="text-center text-xl font-bold pt-2 pb-1">Help</h1>
		<p class="px-4">
			Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore.
		</p>
		<div class="flex flex-col gap-2 p-2">
			<!-- Licensing and Credits -->
			<s-collapsible :class="scClasses">
				<template #summary="slotProps">
					<div :class="scSummaryClasses">
						<down-icon :class="slotProps.open ? downIconExpandedClasses : downIconClasses"/>
						Licensing and Credits
					</div>
				</template>
				<template #content>
					<div :class="contentClasses">
						<p>Source code is available on GitHub, under the MIT Licence.</p>
						<h1 class="text-lg font-bold">Data Sources</h1>
						<ul class="list-disc pl-4">
							<li>
								The short descriptions, the remaining images, and other data,
								were obtained from the
								<a href="https://dumps.wikimedia.org/wikidatawiki/entities/" :style="aStyles">
									Wikidata dump</a>.
								Wikipedia page content is available under
								<a href="https://creativecommons.org/licenses/by-sa/3.0/" :style="aStyles"
									>CC BY-SA 3.0</a>.
							</li>
						</ul>
						<br/>
						<h1 class="text-lg font-bold">Other Credits</h1>
						<ul class="list-disc pl-4">
							<li>
								The UI was mostly coded in
								<a href="https://www.typescriptlang.org/" :style="aStyles">Typescript</a>,
								and built wth <a href="https://vuejs.org/" :style="aStyles">Vue</a>,
								<a href="https://vitejs.dev/" :style="aStyles">Vite</a> &amp;
								<a href="https://pinia.vuejs.org/" :style="aStyles">Pinia</a>
							</li>
							<li>
								Tree data was processed using
								<a href="https://www.python.org/" :style="aStyles">Python</a>,
								and stored using
								<a href="https://www.sqlite.org/index.html" :style="aStyles">Sqlite</a>
							</li>
							<li>
								Styling was enhanced using
								<a href="https://tailwindcss.com/" :style="aStyles">Tailwind</a>
							</li>
							<li>
								The font is <a href="https://design.ubuntu.com/font/" :style="aStyles">Ubuntu Font</a>,
								licensed under
								<a href="https://ubuntu.com/legal/font-licence"
									:style="aStyles">Ubuntu font licence</a>
							</li>
							<li>Icons were used from
								<a href="https://feathericons.com/" :style="aStyles">Feathericons</a>
								and <a href="https://ionic.io/ionicons" :style="aStyles">Ionicons</a>,
								both under MIT License
							</li>
							<li>
								Images were cropped using
								<a href="https://github.com/jwagner/smartcrop.js" :style="aStyles">Smartcrop</a>
							</li>
						</ul>
					</div>
				</template>
			</s-collapsible>

			<!-- FAQs -->
			<s-collapsible :class="scClasses">
				<template #summary="slotProps">
					<div :class="scSummaryClasses">
						<down-icon :class="slotProps.open ? downIconExpandedClasses : downIconClasses"/>
						FAQs
					</div>
				</template>
				<template #content>
					<div :class="contentClasses">
						<h1 class="text-lg font-bold">Test Question</h1>
						<p>Test Answer.</p>
						<br/>
						<h1 class="text-lg font-bold">Test Question</h1>
						<p>Test Answer.</p>
					</div>
				</template>
			</s-collapsible>
		</div>
	</div>
</div>
</template>

<script setup lang="ts">
import {ref, computed} from 'vue';
import SButton from './SButton.vue';
import SCollapsible from './SCollapsible.vue';
import CloseIcon from './icon/CloseIcon.vue';
import DownIcon from './icon/DownIcon.vue';
import {useStore} from '../store';

const rootRef = ref(null as HTMLDivElement | null)
const closeRef = ref(null as typeof CloseIcon | null);

const store = useStore();

const emit = defineEmits(['close']);

// ========== Event handlers ==========

function onClose(evt: Event){
	if (evt.target == rootRef.value || closeRef.value!.$el.contains(evt.target)){
		emit('close');
	}
}

// ========== For styles ==========

const scClasses = 'border border-stone-400 rounded';
const scSummaryClasses = 'relative text-center p-1 bg-stone-300 hover:brightness-90 hover:bg-yellow-200 md:p-2';
const downIconClasses = 'absolute w-6 h-6 my-auto mx-1 transition-transform duration-300';
const downIconExpandedClasses = computed(() => downIconClasses + ' -rotate-90');
const contentClasses = 'py-2 px-2 text-sm md:text-base';

const styles = computed(() => ({
	backgroundColor: store.color.bgAlt,
	borderRadius: store.borderRadius + 'px',
}));

const aStyles = computed(() => ({
	color: store.color.altDark,
}));
</script>
