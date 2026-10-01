<script lang="ts">
	import Icon from '$lib/components/Icon.svelte';
	import CopyButton from '$lib/components/CopyButton.svelte';
	import { size } from '$lib/format';
	let { data } = $props();
	const setup = $derived(data.files.find((f) => f.kind === 'setup'));
	const others = $derived(data.files.filter((f) => f !== setup));
</script>

<svelte:head><title>Downloads · DriverPilot</title></svelte:head>

<div class="mx-auto max-w-5xl px-4 py-10 fade-in">
	<h1 class="text-3xl font-semibold tracking-tight">Downloads</h1>
	<p class="mt-2 text-muted max-w-2xl">
		Für die Installation die Setup-ZIP laden, entpacken und der <a href="/anleitung#1-installation" class="text-accent hover:underline">Anleitung</a>
		folgen. Die Programme darin sind mit Christians Zertifikat signiert; den Fingerabdruck vorher mit Christian abgleichen.
	</p>

	{#if setup}
		<a href="/downloads/{setup.name}" data-sveltekit-reload download class="mt-8 card card-hover p-6 flex flex-col sm:flex-row sm:items-center gap-5 border-accent/30">
			<img src="/favicon.svg" alt="" class="size-14" />
			<div class="min-w-0 flex-1">
				<p class="text-lg font-semibold">DriverPilot {setup.version ?? ''} installieren</p>
				<p class="text-sm text-muted">{setup.description}</p>
				<p class="mt-1 mono text-dim truncate">{setup.name} · {size(setup.size)}</p>
			</div>
			<span class="btn btn-primary px-4 py-2.5 shrink-0"><Icon name="download" />Setup-ZIP laden</span>
		</a>
	{:else}
		<div class="mt-8 card p-6 text-muted">Zurzeit liegen keine Dateien bereit.</div>
	{/if}

	{#if others.length}
		<h2 class="mt-10 mb-3 text-sm font-semibold text-muted">Weitere Dateien</h2>
		<div class="grid gap-2">
			{#each others as file}
				<div class="card p-4 flex flex-col md:flex-row md:items-center gap-3">
					<div class="min-w-0 flex-1">
						<a href="/downloads/{file.name}" data-sveltekit-reload download class="font-medium hover:text-accent break-all">{file.name}</a>
						<p class="text-xs text-muted mt-0.5">{file.description}</p>
						<p class="mt-1.5 mono text-dim break-all">SHA-256 {file.sha256}</p>
					</div>
					<div class="flex items-center gap-2 shrink-0">
						<span class="text-xs text-muted tabular-nums">{size(file.size)}</span>
						<CopyButton text={file.sha256} label="Prüfsumme" />
						<a href="/downloads/{file.name}" data-sveltekit-reload download class="btn btn-sm"><Icon name="download" class="size-3.5" />Laden</a>
					</div>
				</div>
			{/each}
		</div>
		<p class="mt-4 text-xs text-dim">
			Prüfsumme einer heruntergeladenen Datei in PowerShell: <code class="mono text-muted">Get-FileHash .\Datei -Algorithm SHA256</code>
		</p>
	{/if}
</div>
