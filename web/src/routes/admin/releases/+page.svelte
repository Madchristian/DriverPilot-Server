<script lang="ts">
	import { onMount } from 'svelte';
	import { enhance } from '$app/forms';
	import { invalidateAll } from '$app/navigation';
	import Icon from '$lib/components/Icon.svelte';
	import Flash from '$lib/components/Flash.svelte';
	import { dateTime, size } from '$lib/format';
	let { data, form } = $props();
	const last = $derived(data.last);
	const tone: Record<string, string> = { running: 'text-violet bg-violet-dim', done: 'text-ok bg-ok-dim', failed: 'text-bad bg-bad-dim', idle: 'text-muted bg-surface-3' };

	onMount(() => {
		const timer = setInterval(() => {
			if (data.last?.state === 'running') invalidateAll();
		}, 3000);
		return () => clearInterval(timer);
	});
</script>

<svelte:head><title>Releases · DriverPilot Admin</title></svelte:head>

<h1 class="text-2xl font-semibold tracking-tight mb-1">Releases und Downloads</h1>
<p class="text-sm text-muted mb-6">Neue Releases im Repo <span class="mono">{data.client_repo}</span> landen über den GitHub-Webhook automatisch auf der Downloadseite.</p>
<div class="mb-4"><Flash {form} /></div>

<div class="grid xl:grid-cols-[26rem_1fr] gap-6 items-start">
	<section class="card p-5 space-y-4">
		<div class="space-y-2 text-sm">
			<p class="flex justify-between"><span class="text-dim">GitHub-Token</span>{#if data.configured}<span class="text-ok">konfiguriert</span>{:else}<span class="text-bad">fehlt (DP_GITHUB_TOKEN)</span>{/if}</p>
			<p class="flex justify-between"><span class="text-dim">Webhook</span><span class={data.webhook_configured ? 'text-ok' : 'text-dim'}>{data.webhook_configured ? 'aktiv' : 'aus'}</span></p>
			<p class="flex justify-between"><span class="text-dim">Sync-Endpunkt</span><span class={data.endpoint_configured ? 'text-ok' : 'text-dim'}>{data.endpoint_configured ? 'aktiv' : 'aus'}</span></p>
			<p class="flex justify-between"><span class="text-dim">Versionen behalten</span><span>{data.keep}</span></p>
		</div>
		<div class="rounded-xl border border-line bg-bg/50 p-4">
			<div class="flex items-center gap-2">
				<span class="pill {tone[last.state] ?? tone.idle}">{last.state}</span>
				{#if last.tag}<span class="mono text-sm">{last.tag}</span>{/if}
			</div>
			{#if last.started_at}<p class="mt-2 text-xs text-muted">{dateTime(last.started_at)}{last.source ? ` · ${last.source}` : ''}</p>{/if}
			{#if last.message}<p class="mt-1 text-sm {last.state === 'failed' ? 'text-bad' : 'text-muted'}">{last.message}</p>{/if}
		</div>
		<form method="POST" action="?/fetch" use:enhance class="flex gap-2">
			<input name="tag" class="input mono" maxlength="64" placeholder="Tag, leer = neuestes" />
			<button class="btn btn-primary shrink-0" disabled={!data.configured || last.state === 'running'}><Icon name="refresh" />Holen</button>
		</form>
	</section>

	<section class="card overflow-hidden">
		<div class="flex items-center justify-between px-4 py-3 border-b border-line">
			<h2 class="font-semibold text-sm">Dateien auf der Downloadseite</h2>
			<a href="/downloads" class="text-xs text-accent hover:underline" target="_blank" rel="noopener">öffentliche Seite</a>
		</div>
		<div class="overflow-x-auto">
			<table class="table">
				<thead><tr><th>Datei</th><th>Größe</th><th>SHA-256</th></tr></thead>
				<tbody>
					{#each data.files as f}
						<tr>
							<td class="font-medium break-all">{f.name}<span class="block text-xs text-dim font-normal">{f.description}</span></td>
							<td class="text-xs text-muted whitespace-nowrap">{size(f.size)}</td>
							<td class="mono text-[11px] text-dim break-all">{f.sha256}</td>
						</tr>
					{:else}
						<tr><td colspan="3" class="text-muted">Keine Dateien.</td></tr>
					{/each}
				</tbody>
			</table>
		</div>
	</section>
</div>
