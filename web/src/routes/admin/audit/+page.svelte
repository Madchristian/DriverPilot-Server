<script lang="ts">
	import { dateTime, short } from '$lib/format';
	let { data } = $props();
	let query = $state('');
	const entries = $derived(
		query ? data.entries.filter((e: any) => `${e.actor} ${e.operation} ${e.outcome} ${e.detail ?? ''} ${e.case_id ?? ''}`.toLowerCase().includes(query.toLowerCase())) : data.entries
	);
</script>

<svelte:head><title>Audit · DriverPilot Admin</title></svelte:head>

<div class="flex flex-wrap items-end justify-between gap-3 mb-6">
	<div>
		<h1 class="text-2xl font-semibold tracking-tight mb-1">Audit</h1>
		<p class="text-sm text-muted">Wer hat wann was gemacht. Nur Metadaten, kein Berichtinhalt, 30 Tage.</p>
	</div>
	<input class="input max-w-xs" placeholder="Filtern …" bind:value={query} />
</div>

<div class="card overflow-hidden">
	<div class="overflow-x-auto">
		<table class="table">
			<thead><tr><th>Zeit</th><th>Akteur</th><th>Operation</th><th>Fall</th><th>Ergebnis</th><th>Detail</th></tr></thead>
			<tbody>
				{#each entries as e (e.id)}
					<tr>
						<td class="text-xs text-muted whitespace-nowrap">{dateTime(e.at)}</td>
						<td class="mono text-xs">{e.actor}</td>
						<td class="mono text-xs">{e.operation}</td>
						<td>{#if e.case_id}<a href="/admin/cases/{e.case_id}" class="mono text-xs text-accent hover:underline">{short(e.case_id)}</a>{/if}</td>
						<td class="text-xs {e.outcome === 'ok' || e.outcome === 'accepted' ? 'text-ok' : e.outcome === 'failed' || e.outcome === 'analysis_failed' ? 'text-bad' : 'text-muted'}">{e.outcome}</td>
						<td class="mono text-[11px] text-dim break-all">{e.detail ?? ''}</td>
					</tr>
				{:else}
					<tr><td colspan="6" class="text-muted">Keine Einträge.</td></tr>
				{/each}
			</tbody>
		</table>
	</div>
</div>
