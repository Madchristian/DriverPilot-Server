<script lang="ts">
	let { data } = $props();
</script>

<svelte:head><title>Anleitung · DriverPilot</title></svelte:head>

<div class="mx-auto max-w-5xl px-4 py-10 grid lg:grid-cols-[14rem_1fr] gap-10">
	<aside class="hidden lg:block">
		<nav class="sticky top-20 text-sm">
			<p class="label">Inhalt</p>
			<ul class="space-y-1 border-l border-line">
				{#each data.toc as item}
					<li><a href="#{item.id}" class="block -ml-px border-l border-transparent pl-3 py-1 text-muted hover:text-fg hover:border-accent">{item.text.replace(/^\d+\.\s*/, '')}</a></li>
				{/each}
			</ul>
		</nav>
	</aside>
	<article class="doc fade-in min-w-0">
		{@html data.html}
	</article>
</div>
