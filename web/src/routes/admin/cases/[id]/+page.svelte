<script lang="ts">
	import { onMount } from 'svelte';
	import { enhance } from '$app/forms';
	import { invalidateAll } from '$app/navigation';
	import Icon from '$lib/components/Icon.svelte';
	import StatusPill from '$lib/components/StatusPill.svelte';
	import Flash from '$lib/components/Flash.svelte';
	import ReportView from '$lib/components/ReportView.svelte';
	import ResultView from '$lib/components/ResultView.svelte';
	import DraftEditor from '$lib/components/DraftEditor.svelte';
	import { CATEGORY, OUTCOME, dateTime, relative, short } from '$lib/format';
	let { data, form } = $props();
	const c = $derived(data.case);

	onMount(() => {
		const timer = setInterval(() => {
			if (['queued', 'analyzing'].includes(data.case.status)) invalidateAll();
		}, 5000);
		return () => clearInterval(timer);
	});
</script>

<svelte:head><title>{CATEGORY[data.report.symptom.category] ?? 'Fall'} · DriverPilot Admin</title></svelte:head>

<a href="/admin" class="inline-flex items-center gap-1.5 text-sm text-muted hover:text-fg mb-4"><Icon name="back" />Alle Fälle</a>

<div class="flex flex-wrap items-start gap-3 mb-4">
	<div class="min-w-0 flex-1">
		<div class="flex flex-wrap items-center gap-2">
			<h1 class="text-2xl font-semibold tracking-tight">{CATEGORY[data.report.symptom.category] ?? 'Fall'}</h1>
			<StatusPill status={c.status} reason={c.status_reason} />
		</div>
		<p class="mt-1 text-sm text-muted">
			<span class="mono">{short(c.id)}</span> · {data.client?.label ?? 'unbekannt'}{#if data.client?.revoked_at} <span class="text-bad">(Zugang widerrufen)</span>{/if}
			· eingegangen {relative(c.received_at, data.now)} · läuft ab {dateTime(c.expires_at)} · Versuche {c.attempts}
		</p>
	</div>
	<div class="flex flex-wrap gap-2">
		{#if data.can.take_over}
			<form method="POST" action="?/takeover" use:enhance><input type="hidden" name="version" value={c.version} /><button class="btn">Manuell übernehmen</button></form>
		{/if}
		{#if data.can.retry}
			<form method="POST" action="?/retry" use:enhance><input type="hidden" name="version" value={c.version} /><button class="btn"><Icon name="refresh" />KI-Neuversuch</button></form>
		{/if}
		<form method="POST" action="?/delete" use:enhance={({ cancel }) => { if (!confirm('Fall samt Bericht, Entwürfen, Ergebnissen und Rückmeldungen löschen?')) cancel(); }}>
			<button class="btn btn-danger"><Icon name="trash" />Löschen</button>
		</form>
	</div>
</div>

<div class="mb-4"><Flash {form} /></div>

{#if c.status === 'analyzing' || c.status === 'queued'}
	<div class="card p-4 mb-4 flex items-center gap-3 border-violet/30">
		<span class="size-2.5 rounded-full bg-violet animate-pulse"></span>
		<p class="text-sm text-muted">{c.status === 'analyzing' ? 'ChatGPT schreibt gerade einen Entwurf. Das dauert meist zwei bis drei Minuten.' : 'Der Fall wartet auf den KI-Worker.'} Die Seite aktualisiert sich selbst.</p>
	</div>
{/if}

<div class="grid 2xl:grid-cols-[1fr_1fr] gap-6 items-start">
	<div class="min-w-0 space-y-3">
		<h2 class="text-sm font-semibold text-muted">Bericht</h2>
		<ReportView report={data.report} />
	</div>

	<div class="min-w-0 space-y-3">
		<div class="flex items-center gap-2">
			<h2 class="text-sm font-semibold text-muted">Entwurf</h2>
			{#if data.draft.origin === 'ai'}
				<span class="pill text-violet bg-violet-dim">KI-Entwurf{data.draft.model ? ` · ${data.draft.model}` : ''}</span>
			{:else if data.draft.saved}
				<span class="pill text-blue bg-blue-dim">von {data.draft.author}</span>
			{:else if data.draft.base_revision}
				<span class="pill text-ok bg-ok-dim">Basis: Revision {data.draft.base_revision}</span>
			{:else}
				<span class="pill text-muted bg-surface-3">Vorlage</span>
			{/if}
			{#if data.draft.created_at}<span class="text-xs text-dim">{relative(data.draft.created_at, data.now)}</span>{/if}
		</div>
		{#if data.draft.origin === 'ai'}
			<p class="rounded-xl border border-violet/30 bg-violet-dim px-4 py-2.5 text-sm text-violet">Ungeprüfter KI-Entwurf. Erst nach deiner Prüfung und Freigabe sieht der Freund etwas davon.</p>
		{/if}
		{#key `${data.draft.id}-${c.version}`}
			<DraftEditor
				initial={data.draft.content}
				report={data.report}
				version={c.version}
				draftId={data.draft.id}
				saved={data.draft.saved}
				aiAssisted={data.draft.origin === 'ai' || (!!data.draft.base_revision && data.results[0]?.body.origin === 'ai_assisted_human_reviewed')}
				problems={data.problems}
				hints={data.hints}
				canRelease={data.can.release}
				nextRevision={c.current_revision + 1}
			/>
		{/key}
	</div>
</div>

{#if data.results.length}
	<h2 class="mt-8 mb-3 text-sm font-semibold text-muted">Freigegebene Revisionen</h2>
	<div class="space-y-3">
		{#each data.results as res, i}
			<details class="card p-5" open={i === 0}>
				<summary class="cursor-pointer flex flex-wrap items-center gap-2">
					<span class="font-semibold">Revision {res.revision}</span>
					<span class="chip">{res.body.origin === 'human' ? 'manuell' : 'KI-gestützt, geprüft'}</span>
					<span class="text-xs text-muted">{dateTime(res.released_at)} · {res.released_by}</span>
				</summary>
				<div class="mt-4"><ResultView result={res.body} /></div>
			</details>
		{/each}
	</div>
{/if}

<div class="mt-8 grid lg:grid-cols-2 gap-3">
	<section class="card p-5">
		<h2 class="label">Rückmeldungen ({data.feedback.length})</h2>
		{#each data.feedback as fb}
			<div class="py-2 border-b border-line/60 last:border-0">
				<p class="text-sm"><span class="font-semibold">{OUTCOME[fb.outcome] ?? fb.outcome}</span> <span class="text-xs text-muted">zu Revision {fb.result_revision} · {dateTime(fb.received_at)}</span></p>
				{#if fb.note}<p class="mt-1 text-sm text-muted whitespace-pre-wrap">{fb.note}</p>{/if}
			</div>
		{:else}
			<p class="text-sm text-dim">Noch keine.</p>
		{/each}
	</section>
	<section class="card p-5">
		<h2 class="label">KI-Läufe</h2>
		{#each data.runs as r}
			<p class="text-sm py-1"><span class="mono text-dim">{short(r.id)}</span> {r.model ?? r.adapter} · {dateTime(r.started_at)} · <span class={r.outcome === 'draft' ? 'text-ok' : r.outcome ? 'text-bad' : 'text-violet'}>{r.outcome ?? 'läuft'}</span></p>
		{:else}
			<p class="text-sm text-dim">Keine (manueller Fall).</p>
		{/each}
	</section>
</div>
