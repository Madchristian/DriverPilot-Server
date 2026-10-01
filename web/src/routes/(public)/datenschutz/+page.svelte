<script lang="ts">
	let { data } = $props();
	function split(paragraph: string): { head: string | null; body: string } {
		const match = paragraph.match(/^([^:\n]{3,40}):\s([\s\S]*)$/);
		return match ? { head: match[1], body: match[2] } : { head: null, body: paragraph };
	}
</script>

<svelte:head><title>Datenschutz · DriverPilot</title></svelte:head>

<div class="mx-auto max-w-3xl px-4 py-10 fade-in">
	<h1 class="text-3xl font-semibold tracking-tight">Datenschutzhinweis</h1>
	<p class="mt-2 text-sm text-muted">Version <span class="mono text-fg">{data.version}</span>. Genau diesen Text zeigt DriverPilot vor dem Senden an.</p>
	<p class="mt-6 text-muted">{data.title}</p>
	<div class="mt-6 space-y-3">
		{#each data.paragraphs as paragraph}
			{@const part = split(paragraph)}
			<section class="card p-5">
				{#if part.head}<h2 class="font-semibold mb-1.5">{part.head}</h2>{/if}
				<p class="text-sm text-muted leading-relaxed whitespace-pre-line">{part.body}</p>
			</section>
		{/each}
	</div>
</div>
