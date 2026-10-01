<script lang="ts">
	import { RISK, PRIVILEGES } from '$lib/format';
	let { result }: { result: any } = $props();
	const refLabel = (ref: any) => (ref.kind === 'report_field' ? ref.pointer : ref.id);
</script>

<div class="space-y-4 text-sm">
	{#if result.summary}<p class="text-base leading-relaxed whitespace-pre-wrap">{result.summary}</p>{/if}

	{#if result.facts?.length}
		<div>
			<p class="label">Fakten</p>
			<ul class="space-y-1.5">
				{#each result.facts as fact}
					<li class="flex gap-2">
						<span class="text-ok mt-0.5">●</span>
						<span class="min-w-0">
							{fact.text}
							{#each fact.references ?? [] as ref}<span class="chip ml-1 mono">{refLabel(ref)}</span>{/each}
						</span>
					</li>
				{/each}
			</ul>
		</div>
	{/if}

	{#if result.hypotheses?.length}
		<div>
			<p class="label">Vermutungen (unbewiesen)</p>
			<ul class="space-y-1.5">
				{#each result.hypotheses as h}
					<li class="flex gap-2"><span class="text-warn mt-0.5">?</span><span>{h.text}</span></li>
				{/each}
			</ul>
		</div>
	{/if}

	{#if result.next_steps?.length}
		<div>
			<p class="label">Nächste Schritte</p>
			<ol class="space-y-2">
				{#each result.next_steps as step, i}
					<li class="rounded-xl border border-line bg-bg/40 p-4">
						<div class="flex flex-wrap items-center gap-2">
							<span class="font-mono text-xs text-dim">{i + 1}.</span>
							<span class="font-semibold">{step.title}</span>
							<span class="pill {RISK[step.risk_class]?.tone ?? ''}">{RISK[step.risk_class]?.label ?? step.risk_class}</span>
							<span class="chip">{PRIVILEGES[step.required_privileges] ?? step.required_privileges}</span>
						</div>
						<p class="mt-2 whitespace-pre-wrap">{step.instructions}</p>
						<div class="mt-2 grid gap-1 text-xs text-muted">
							<span><b class="text-dim font-medium">Warum:</b> {step.rationale}</span>
							<span><b class="text-dim font-medium">Erwartung:</b> {step.expected_outcome}</span>
							{#if step.rollback}<span><b class="text-dim font-medium">Rückweg:</b> {step.rollback}</span>{/if}
							{#if step.abort_condition}<span><b class="text-dim font-medium">Abbrechen, wenn:</b> {step.abort_condition}</span>{/if}
						</div>
					</li>
				{/each}
			</ol>
		</div>
	{/if}

	{#if result.open_questions?.length}
		<div>
			<p class="label">Rückfragen</p>
			<ul class="list-disc pl-5 space-y-1">{#each result.open_questions as q}<li>{q}</li>{/each}</ul>
		</div>
	{/if}
	{#if result.warnings?.length}
		<div>
			<p class="label">Hinweise</p>
			<ul class="space-y-1">{#each result.warnings as w}<li class="rounded-lg bg-warn-dim text-warn px-3 py-2">{w}</li>{/each}</ul>
		</div>
	{/if}
	{#if result.sources?.length}
		<div>
			<p class="label">Quellen</p>
			<ul class="space-y-1">{#each result.sources as s}<li>{s.title} <span class="mono text-dim break-all">{s.url}</span></li>{/each}</ul>
		</div>
	{/if}
</div>
