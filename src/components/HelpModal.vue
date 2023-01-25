<template>
<div class="fixed left-0 top-0 w-full h-full bg-black/40" @click="onClose" ref="rootRef">
	<div class="absolute left-1/2 -translate-x-1/2 top-1/2 -translate-y-1/2
		w-[90%] max-w-[16cm] max-h-[80%] overflow-auto" :style="styles">
		<close-icon @click.stop="onClose" ref="closeRef"
			class="absolute top-1 right-1 md:top-2 md:right-2 w-8 h-8 hover:cursor-pointer"/>
		<h1 class="text-center text-xl sm:text-2xl font-bold pt-2 pb-1">Help</h1>
		<div class="flex flex-col gap-2 p-2">
			<s-collapsible :class="scClasses">
				<template #summary="slotProps">
					<div :class="scSummaryClasses">
						<down-icon :class="slotProps.open ? downIconExpandedClasses : downIconClasses"/>
						Visual Display
					</div>
				</template>
				<template #content>
					<div :class="contentClasses" class="space-y-3">
						<p>
							Initially, the main area contains one timeline, with ticks representing evenly spaced
							points in time. A square represents a min or max date. '1k BC' means
							1000 BC. 'mya' and 'bya' mean millions and billions of years ago.
						</p>
						<img src="/timeline.png" alt="Timeline with events"
							class="border border-stone-300 rounded mx-auto md:mx-0 md:shrink-0"/>
						<p>
							Events are shown as labelled images. Blue borders indicate
							discovery events. This is so that events like the discovery of Andromeda
							don't look the same as the event of its creation.
						</p>
						<p>
							Events are linked to points on the timeline that match their 'start date'.
							For a person, this is a date of birth. For a book, this is a date of publication.
							{{touchDevice ? 'Tap' : 'Click'}} on an event to bring up more details.
						</p>
						<p>
							The timeline also has varying 'thickness', which indicates how many events
							are present between ticks.
							There are four levels, indicating counts of zero to over a thousand.
						</p>
						<p>
							The + button at the top right adds another timeline, if there's enough space.
						</p>
						<p>
							The sidebar at the {{vert ? 'right' : 'bottom'}} represents the full range of
							possible dates. Each timeline's bounds are displayed as a yellow subregion.
							Timelines will often look very thin, as the whole bar spans billions of years.
						</p>
					</div>
				</template>
			</s-collapsible>

			<s-collapsible :class="scClasses">
				<template #summary="slotProps">
					<div :class="scSummaryClasses">
						<down-icon :class="slotProps.open ? downIconExpandedClasses : downIconClasses"/>
						Other Features
					</div>
				</template>
				<template #content>
					<div :class="contentClasses">
						<h1 :class="contentH1Classes">Keyboard Shortcuts</h1>
						<ul :class="contentULClasses">
							<li>
								<span class="font-bold">{{vert ? 'Up': 'Left'}}</span> and
								<span class="font-bold">{{vert ? 'Down': 'Right'}}</span> pan the timeline
							</li>
							<li>
								<span class="font-bold">{{vert ? 'Left' : 'Up'}}</span> and
								<span class="font-bold">{{vert ? 'Right' : 'Down'}}</span>
								switch between timelines
							</li>
							<li>
								<span class="font-bold">Shift-{{vert ? 'Left' : 'Up'}}</span> and
								<span class="font-bold">Shift-{{vert ? 'Right' : 'Down'}}</span>
								zoom in and out
							</li>
							<li>
								<span class="font-bold">Plus</span> and <span class="font-bold">Delete</span>
								add and remove timelines
							</li>
							<li><span class="font-bold">Ctrl-F</span> opens the search bar</li>
							<li><span class="font-bold">Esc</span> closes an open pane</li>
						</ul>
						<br/>
						<h1 :class="contentH1Classes">Settings</h1>
						<ul :class="contentULClasses">
							<li>
								<h2 :class="contentH2Classes">Categories</h2>
								<p>
									Allows filtering of displayed events by category. Examples include:
								</p>
								<ul :class="contentInnerULClasses">
									<li><span class="font-bold">Event:</span> wars, disasters, celebrations</li>
									<li><span class="font-bold">Place:</span> cities, countries, galaxies</li>
									<li><span class="font-bold">Person:</span> writers, scientists, leaders</li>
									<li><span class="font-bold">Organism:</span> dinosaurs, insects, plants</li>
									<li>
										<span class="font-bold">Work:</span> books, movies, video games
									</li>
									<li><span class="font-bold">Discovery:</span> inventions, ideas, places</li>
								</ul>
								<p class="text-xs md:text-sm text-stone-500 py-1">
									(Unfortunately, timeline thickness isn't yet indicative of filtered events)
								</p>
							</li>
							<li>
								<h2 :class="contentH2Classes">Display</h2>
								<ul :class="contentInnerULClasses">
									<li><span class="font-bold">Only events with images:</span>
										If enabled, only about 20% of events are shown</li>
									<li><span class="font-bold">Minor tick text:</span>
										Toggles labels for small-sized ticks</li>
									<li><span class="font-bold">Event density:</span>
										Toggles timeline thickness</li>
									<li><span class="font-bold">Event lines:</span>
										Toggles lines linking events to timelines</li>
									<li><span class="font-bold">Baseline:</span>
										Toggles the sidebar representing the full date range</li>
								</ul>
							</li>
							<li>
								<h2 :class="contentH2Classes">Input</h2>
								<ul :class="contentInnerULClasses">
									<li><span class="font-bold">Pan ratio:</span>
										Higher values mean faster panning</li>
									<li><span class="font-bold">Zoom ratio:</span>
										Higher values mean faster zooming</li>
								</ul>
							</li>
						</ul>
						<p class="mt-2">
							{{touchDevice ? 'Tapping' : 'Clicking'}} on
							a slider's label resets it to its default value.
						</p>
					</div>
				</template>
			</s-collapsible>

			<s-collapsible :class="scClasses">
				<template #summary="slotProps">
					<div :class="scSummaryClasses">
						<down-icon :class="slotProps.open ? downIconExpandedClasses : downIconClasses"/>
						Licensing and Credits
					</div>
				</template>
				<template #content>
					<div :class="contentClasses">
						<p>The source code is available on GitHub, under the MIT Licence.</p>
						<br/>
						<h1 :class="contentH1Classes">Data Sources</h1>
						<ul :class="contentULClasses">
							<li>
								Event data was obtained from the
								<a href="https://dumps.wikimedia.org/wikidatawiki/entities/" :style="aStyles">
									Wikidata dump</a> for 23/08/22. About 350,000 events were extracted.
							</li>
							<li>
								Event descriptions, images, and popularity were obtained via the
								<a href="https://dumps.wikimedia.org/enwiki/" :style="aStyles">Wikimedia dump</a>
								for 01/05/22.
								Wikipedia page content is available under
								<a href="https://creativecommons.org/licenses/by-sa/3.0/" :style="aStyles"
									>CC BY-SA 3.0</a>.
								For the source of a specific event's image, look in its info pane.
							</li>
						</ul>
						<br/>
						<div>
							<h1 :class="contentH1Classes">Other Credits</h1>
							<ul :class="contentULClasses">
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
					</div>
				</template>
			</s-collapsible>

			<s-collapsible :class="scClasses">
				<template #summary="slotProps">
					<div :class="scSummaryClasses">
						<down-icon :class="slotProps.open ? downIconExpandedClasses : downIconClasses"/>
						FAQs
					</div>
				</template>
				<template #content>
					<div :class="contentClasses">
						<h1 :class="contentH1Classes">How accurate is the information?</h1>
						<div class="space-y-3">
							<p>
								Event data was extracted by looking for objects in the Wikidata knowledge graph that
								have certain properties. These are not always consistent or accurate.
								For example, an event's date might be encoded using a 'start time',
								'temporal range start', or 'earliest date' property, without a clear pattern.
							</p>
							<p>
								Also, some properties have unclear definitions. For example, in looking for
								creative works, a 'genre' property was used. But as it turns out, sometimes
								fictional characters or places will also have that property, which can
								cause unexpected results (like having Hogwarts displayed as a work).
							</p>
							<p>
								As for the short descriptions, they were extracted from marked-up Wikipedia content
								using imprecise heuristics. Many have leftover fragments of code, or incomplete
								sentences.
							</p>
						</div>
						<br/>
						<h1 :class="contentH1Classes">
							In the info boxes, what do terms like "1st century BC" and "O.S." mean?</h1>
						<div class="space-y-3">
							<p>
								Each event can have both a start and end date, both of which may be imprecise.
								For example, the start may range between years 1901 and 2000, which corresponds to the
								20th century. Similarly, the 1st century BC represents years 99 BC to 1 BC.
								There is no year 0 BC, because 1 BC is directly followed by 1 AD.
							</p>
							<p>
								Decades are like centuries, and have ranges like 1701 to 1710, generally ranging from
								a year ending with one up to a year ending with zero. Other scales are
								different. "2nd millenium" means 1000 to 1999. And "About 2 million years ago" means
								2,000,000 BC to 1,000,001 BC.
							</p>
							<p>
								For dates like "1st Jan 1600 (O.S.)", the "O.S." means
								<a href="https://en.wikipedia.org/wiki/Old_Style_and_New_Style_dates" :style="aStyles">
									Old Style</a>, and the date is
								in the Julian Calendar (as opposed to the Gregorian Calendar). These tend to
								appear for events in certain countries between 1550 and 1950.
							</p>
						</div>
						<br/>
						<h1 :class="contentH1Classes">Why am I sometimes unable to zoom into a year?</h1>
						<p>
							Calendar dates are only valid starting from the year {{-MIN_CAL_YEAR}} BC.
							This is because
							<a href="https://en.wikipedia.org/wiki/Julian_day" :style="aStyles">Julian day numbers</a>
							are used to encode calendar dates.
							Before this point, zooming into sub-yearly scales is disabled.
						</p>
						<br/>
						<h1 :class="contentH1Classes">Why are there so many celebrities?</h1>
						<p>
							Events are chosen for display by popularity, which is determined using Wikipedia
							page view counts. Celebrities tend to rank highly with this metric, regardless
							of historical importance. This might be adjusted in future.
						</p>
						<br/>
						<h1 :class="contentH1Classes">Why do some people have their faces clipped out?</h1>
						<p>
							Images from Wikipedia were cropped into squares semi-automatically. This sometimes
							ends badly, with the person's chest or headwear being placed in center focus.
						</p>
					</div>
				</template>
			</s-collapsible>
		</div>
		<p class="text-right text-xs md:text-sm text-stone-500 pr-2 pb-2">
			Last updated 22/01/23
		</p>
	</div>
</div>
</template>

<script setup lang="ts">
import {ref, computed} from 'vue';

import SButton from './SButton.vue';
import SCollapsible from './SCollapsible.vue';
import CloseIcon from './icon/CloseIcon.vue';
import DownIcon from './icon/DownIcon.vue';

import {MIN_DATE, MAX_DATE, MIN_CAL_YEAR, dateToDisplayStr, dateToYearStr} from '../lib';
import {useStore} from '../store';

const rootRef = ref(null as HTMLDivElement | null)
const closeRef = ref(null as typeof CloseIcon | null);

const store = useStore();
const touchDevice = computed(() => store.touchDevice)

const props = defineProps({
	vert: {type: Boolean, required: true},
});

const emit = defineEmits(['close']);

// ========== Event handlers ==========

function onClose(evt: Event){
	if (evt.target == rootRef.value || closeRef.value!.$el.contains(evt.target)){
		emit('close');
	}
}

// ========== For styles ==========

const scClasses = 'border border-stone-400 rounded';
const scSummaryClasses = 'relative text-center p-1 bg-stone-300 hover:brightness-90 hover:bg-amber-200 md:p-2';
const downIconClasses = 'absolute w-6 h-6 my-auto mx-1 transition-transform duration-300';
const downIconExpandedClasses = computed(() => downIconClasses + ' -rotate-90');
const contentClasses = 'py-2 px-2 text-sm md:text-base';
const contentH1Classes = 'text-lg font-bold mb-2';
const contentH2Classes = 'font-bold';
const contentULClasses = 'list-disc pl-4'
const contentInnerULClasses = 'list-[circle] pl-4'

const styles = computed(() => ({
	backgroundColor: store.color.bgAlt,
	borderRadius: store.borderRadius + 'px',
}));

const aStyles = computed(() => ({
	color: store.color.altDark2,
}));
</script>
