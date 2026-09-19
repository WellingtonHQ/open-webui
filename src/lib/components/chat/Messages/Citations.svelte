<script lang="ts">
	import { getContext } from 'svelte';
	import { embed, showControls, showEmbeds } from '$lib/stores';

	import CitationModal from './Citations/CitationModal.svelte';

	const i18n = getContext('i18n');

	export let id = '';
	export let chatId = '';

	export let sources = [];
	export let content = '';
	export let readOnly = false;

	/**
	 * Canonical form for comparing a URL mentioned in the message text against a stored
	 * source id. Models often rewrite URLs slightly (date dashes vs slashes, dropped query
	 * strings, trailing slashes), so compare on host+path with all punctuation removed.
	 */
	const normalizeUrl = (value: string) =>
		value
			.toLowerCase()
			.replace(/^https?:\/\//, '')
			.replace(/^www\./, '')
			.split(/[?#]/)[0]
			.replace(/\/+$/, '')
			.replace(/[^a-z0-9]/g, '');

	/**
	 * Extract URLs mentioned directly in the message text. Models that write a prose
	 * "Sources" list instead of [n] chips still count as having cited those URLs.
	 */
	const extractCitedUrls = (text: string) => {
		const urls = new Set<string>();

		if (!text) return urls;

		const plain = text
			.replace(/```[\s\S]*?(```|$)/g, '')
			.replace(/`[^`\n]*`/g, '');

		for (const match of plain.matchAll(/https?:\/\/[^\s<>"')\]]+/g)) {
			urls.add(normalizeUrl(match[0].replace(/[.,;:!?)\]}'"]+$/, '')));
		}

		return urls;
	};

	/**
	 * Extract the [n] indices actually cited in the message text (mirrors the marked
	 * citation-extension tokenizer: adjacent [1], [1,2#x] blocks; footnotes ignored).
	 */
	const extractCitedIndices = (text: string) => {
		const indices = new Set<number>();

		if (!text) return indices;

		// Ignore code fences, inline code and markdown link syntax so only rendered [n] chips count.
		const plain = text
			.replace(/```[\s\S]*?(```|$)/g, '')
			.replace(/`[^`\n]*`/g, '')
			.replace(/\[[^\]]*\]\([^)]*\)/g, '');

		for (const group of plain.matchAll(/\[([^\]]+)\]/g)) {
			for (const part of group[1].split(',')) {
				const match = /^\s*(\d+)(?:#.+)?$/.exec(part);
				if (match) indices.add(parseInt(match[1], 10));
			}
		}

		return indices;
	};

	let allCitations = [];
	let citations = [];
	let showPercentage = false;
	let showRelevance = true;

	let citationModal = null;

	let showCitations = false;
	let showCitationModal = false;

	let selectedCitation: any = null;

	export const showSourceModal = (sourceId) => {
		let index;
		let suffix = null;

		if (typeof sourceId === 'string') {
			const output = sourceId.split('#');
			index = parseInt(output[0]) - 1;

			if (output.length > 1) {
				suffix = output[1];
			}
		} else {
			index = sourceId - 1;
		}

		const citationEntry = allCitations[index];

		if (citationEntry) {
			console.log('Showing citation modal for:', citationEntry);

			if (citationEntry?.source?.embed_url) {
				const embedUrl = citationEntry.source.embed_url;
				if (embedUrl) {
					if (readOnly) {
						// Open in new tab if readOnly
						window.open(embedUrl, '_blank');
						return;
					} else {
						showControls.set(true);
						showEmbeds.set(true);
						embed.set({
							url: embedUrl,
							title: citationEntry?.source?.name || 'Embedded Content',
							source: citationEntry,
							chatId: chatId,
							messageId: id,
							sourceId: sourceId
						});
					}
				} else {
					selectedCitation = citationEntry;
					showCitationModal = true;
				}
			} else {
				selectedCitation = citationEntry;
				showCitationModal = true;
			}
		}
	};

	function calculateShowRelevance(sources: any[]) {
		const distances = sources.flatMap((citation) => citation.distances ?? []);
		const inRange = distances.filter((d) => d !== undefined && d >= -1 && d <= 1).length;
		const outOfRange = distances.filter((d) => d !== undefined && (d < -1 || d > 1)).length;

		if (distances.length === 0) {
			return false;
		}

		if (
			(inRange === distances.length - 1 && outOfRange === 1) ||
			(outOfRange === distances.length - 1 && inRange === 1)
		) {
			return false;
		}

		return true;
	}

	function shouldShowPercentage(sources: any[]) {
		const distances = sources.flatMap((citation) => citation.distances ?? []);
		return distances.every((d) => d !== undefined && d >= -1 && d <= 1);
	}

	const isUrlSourceId = (value: unknown) =>
		typeof value === 'string' && (value.startsWith('http://') || value.startsWith('https://'));

	$: {
		allCitations = sources.reduce((acc, source) => {
			if (Object.keys(source).length === 0) {
				return acc;
			}

			source?.document?.forEach((document, index) => {
				const metadata = source?.metadata?.[index];
				const distance = source?.distances?.[index];

				// Within the same citation there could be multiple documents
				const id = metadata?.source ?? source?.source?.id ?? 'N/A';
				let _source = source?.source;

				if (metadata?.name) {
					_source = { ..._source, name: metadata.name };
				}

				if (isUrlSourceId(id)) {
					_source = { ..._source, name: id, url: id };
				}

				const existingSource = acc.find((item) => item.id === id);

				if (existingSource) {
					existingSource.document.push(document);
					existingSource.metadata.push(metadata);
					if (distance !== undefined) existingSource.distances.push(distance);
				} else {
					acc.push({
						id: id,
						source: _source,
						document: [document],
						metadata: metadata ? [metadata] : [],
						distances: distance !== undefined ? [distance] : [],
						pos: acc.length + 1 // 1-based position matching the model's [n] citations
					});
				}
			});

			return acc;
		}, []);

		// Web (http) sources only show up when the model actually cited them in its answer —
		// either as a [n] chip or by naming the URL directly; non-web sources (knowledge files,
		// etc.) keep their existing "show all" behavior.
		const cited = extractCitedIndices(content);
		const citedUrls = extractCitedUrls(content);
		citations = allCitations.filter(
			(item) => !isUrlSourceId(item.id) || cited.has(item.pos) || (citedUrls.size > 0 && citedUrls.has(normalizeUrl(item.id))),
		);
		console.log('citations', citations);

		showRelevance = calculateShowRelevance(allCitations);
		showPercentage = shouldShowPercentage(allCitations);
	}

	const decodeString = (str: string) => {
		try {
			return decodeURIComponent(str);
		} catch (e) {
			return str;
		}
	};
</script>

<CitationModal
	bind:show={showCitationModal}
	citation={selectedCitation}
	{showPercentage}
	{showRelevance}
/>

{#if citations.length > 0}
	{@const urlCitations = citations.filter((c) => c?.source?.name?.startsWith('http'))}
	<div class=" py-1 -mx-0.5 w-full flex gap-1 items-center flex-wrap">
		<button
			class="text-xs font-normal text-gray-600 dark:text-gray-300 px-3.5 h-8 rounded-full hover:bg-gray-100 dark:hover:bg-gray-800 transition flex items-center gap-1 border border-gray-50 dark:border-gray-850/30"
			aria-label={citations.length === 1
				? $i18n.t('Toggle 1 source')
				: $i18n.t('Toggle {{COUNT}} sources', { COUNT: citations.length })}
			aria-expanded={showCitations}
			on:click={() => {
				showCitations = !showCitations;
			}}
		>
			{#if urlCitations.length > 0}
				<div class="flex -space-x-1 items-center">
					{#each urlCitations.slice(0, 3) as citation, idx}
						<img
							src="https://www.google.com/s2/favicons?sz=32&domain={citation.source.name}"
							alt="favicon"
							class="size-4 rounded-full shrink-0 border border-white dark:border-gray-850 bg-white dark:bg-gray-900"
							on:error={(e) => {
								// LICENSE covers this Open WebUI fallback logo.
								// Do not alter, remove, obscure, or replace it except as LICENSE permits:
								// https://docs.openwebui.com/license.
								e.target.src = '/favicon.png';
							}}
						/>
					{/each}
					{#if citations.length > 3}
						<div
							class="size-4 rounded-full shrink-0 border border-white dark:border-gray-850 bg-gray-100 dark:bg-gray-800 flex items-center justify-center text-[0.5rem] font-normal text-gray-500 dark:text-gray-400 whitespace-nowrap tracking-tighter"
							aria-hidden="true"
						>
							+{citations.length - Math.min(urlCitations.length, 3)}
						</div>
					{/if}
				</div>
			{/if}
			<div>
				{#if citations.length === 1}
					{$i18n.t('1 Source')}
				{:else}
					{$i18n.t('{{COUNT}} Sources', {
						COUNT: citations.length
					})}
				{/if}
			</div>
		</button>
	</div>
{/if}

{#if showCitations}
	<div class="py-1.5">
		<div class="text-xs gap-2 flex flex-col">
			{#each citations as citation (citation.id)}
				<button
					id={`source-${id}-${citation.pos}`}
					aria-label={$i18n.t('View source: {{name}}', {
						name: decodeString(citation.source.name)
					})}
					class="no-toggle outline-hidden flex dark:text-gray-300 bg-transparent text-gray-600 rounded-xl gap-1.5 items-center"
					on:click={() => {
						showCitationModal = true;
						selectedCitation = citation;
					}}
				>
					<div class=" font-normal bg-gray-50 dark:bg-gray-850 rounded-md px-1">
						{citation.pos}
					</div>
					<div
						class="flex-1 truncate hover:text-black dark:text-white/60 dark:hover:text-white transition text-left"
					>
						{decodeString(citation.source.name)}
					</div>
				</button>
			{/each}
		</div>
	</div>
{/if}
