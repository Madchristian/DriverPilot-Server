<script lang="ts">
	import { onMount } from 'svelte';
	import { invalidateAll } from '$app/navigation';
	import Kpi from '$lib/components/Kpi.svelte';
	import StatusPill from '$lib/components/StatusPill.svelte';
	import { CATEGORY, relative, dateTime, short } from '$lib/format';
	let { data } = $props();
	let filter = $state<'open' | 'all'>('open');
	const cases = $derived(filter === 'open' ? data.cases.filter((c: any) => c.status !== 'released') : data.cases);
	const s = $derived(data.stats);

	onMount(() => {
		const timer = setInterval(() => invalidateAll(), 15000);
		return () => clearInterval(timer);
	});
</script>

<svelte:head><title>Fälle · DriverPilot Admin</title></svelte:head>

<div class="flex flex-wrap items-end justify-between gap-3 mb-5">
	<div>
		<h1 class="text-2xl font-semibold tracking-tight">Fälle</h1>
		<p class="text-sm text-muted">Aktualisiert sich alle 15 Sekunden · KI {data.ai_offered ? `aktiv (${data.settings.codex_model ?? data.settings.ai_provider})` : 'aus'}</p>
	</div>
	<a href="/admin/invitations" class="btn btn-primary">Freund einladen</a>
</div>

<div class="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-3 mb-6">
	<Kpi label="Wartet auf dich" value={s.by_status.awaiting_review ?? 0} tone={(s.by_status.awaiting_review ?? 0) ? 'text-warn' : 'text-fg'} />
	<Kpi label="KI läuft / wartet" value={`${s.by_status.analyzing ?? 0} / ${s.by_status.queued ?? 0}`} tone="text-violet" />
	<Kpi label="Fehlgeschlagen" value={s.by_status.analysis_failed ?? 0} tone={(s.by_status.analysis_failed ?? 0) ? 'text-bad' : 'text-fg'} />
	<Kpi label="Neue Fälle heute" value={`${s.today} / ${data.settings.max_new_cases_global_per_day}`} />
	<Kpi label="Aktive Zugänge" value={s.clients_active} />
	<Kpi label="KI-Aufrufe heute" value={`${s.ai_budget_used} / ${s.ai_budget_total}`} sub={s.ai_provider} />
</div>

<div class="card overflow-hidden">
	<div class="flex items-center gap-2 border-b border-line px-4 py-2.5">
		<div class="inline-flex rounded-lg border border-line bg-bg p-0.5 text-sm">
			<button class="rounded-md px-3 py-1 {filter === 'open' ? 'bg-surface-3 text-fg' : 'text-muted'}" onclick={() => (filter = 'open')}>Offen ({s.open})</button>
			<button class="rounded-md px-3 py-1 {filter === 'all' ? 'bg-surface-3 text-fg' : 'text-muted'}" onclick={() => (filter = 'all')}>Alle ({data.cases.length})</button>
		</div>
	</div>
	{#if cases.length}
		<ul class="divide-y divide-line">
			{#each cases as c (c.id)}
				<li>
					<a href="/admin/cases/{c.id}" class="flex flex-col md:flex-row md:items-center gap-2 md:gap-4 px-4 py-3 hover:bg-surface-2 transition-colors">
						<div class="md:w-52 shrink-0"><StatusPill status={c.status} reason={c.status_reason} /></div>
						<div class="min-w-0 flex-1">
							<p class="font-medium truncate">{CATEGORY[c.symptom_category] ?? c.symptom_category} <span class="text-dim font-normal">· {c.client_label}</span></p>
							<p class="text-xs text-muted">
								<span class="mono">{short(c.id)}</span> · eingegangen {relative(c.received_at, data.now)} · läuft ab {dateTime(c.expires_at)}
							</p>
						</div>
						<div class="flex flex-wrap gap-1.5 text-xs">
							{#if c.external_ai_allowed}<span class="chip">KI erlaubt</span>{/if}
							{#if c.current_revision}<span class="chip">Rev. {c.current_revision}</span>{/if}
							{#if c.feedback_count}<span class="chip text-accent">{c.feedback_count} Rückmeldung{c.feedback_count > 1 ? 'en' : ''}</span>{/if}
						</div>
					</a>
				</li>
			{/each}
		</ul>
	{:else}
		<p class="px-4 py-10 text-center text-muted">{filter === 'open' ? 'Keine offenen Fälle. Alles erledigt.' : 'Noch keine Fälle.'}</p>
	{/if}
</div>
