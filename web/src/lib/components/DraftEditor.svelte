<script lang="ts">
	import { untrack } from 'svelte';
	import { enhance, applyAction } from '$app/forms';
	import { invalidateAll } from '$app/navigation';
	import Icon from './Icon.svelte';
	import ResultView from './ResultView.svelte';

	type Props = {
		initial: any;
		report: any;
		version: number;
		draftId: string | null;
		saved: boolean;
		aiAssisted: boolean;
		problems: string[];
		hints: string[];
		canRelease: boolean;
		nextRevision: number;
	};
	let { initial, report, version, draftId, saved, aiAssisted, problems, hints, canRelease, nextRevision }: Props = $props();

	const KEYS = ['summary', 'facts', 'hypotheses', 'next_steps', 'open_questions', 'warnings', 'sources'];
	function normalize(value: any) {
		const v = structuredClone(value ?? {});
		v.summary ??= '';
		for (const key of KEYS.slice(1)) if (!Array.isArray(v[key])) v[key] = [];
		return v;
	}

	// Startwert bewusst einmalig: die Fallseite baut den Editor per {#key} neu auf, wenn sich der Entwurf aendert.
	const start = normalize(untrack(() => initial));
	let draft = $state(start);
	const startText = JSON.stringify(start);
	let ai = $state(untrack(() => aiAssisted));
	let mode = $state<'form' | 'json' | 'preview'>('form');
	let jsonText = $state('');
	let jsonError = $state('');
	let checkProblems = $state<string[] | null>(null);
	let checkHints = $state<string[]>([]);
	let busy = $state(false);
	let message = $state<{ ok: boolean; text: string } | null>(null);

	const dirty = $derived(JSON.stringify(draft) !== startText || ai !== aiAssisted);
	const shownProblems = $derived(checkProblems ?? problems);
	const shownHints = $derived(checkProblems ? checkHints : hints);
	const releasable = $derived(saved && !dirty && canRelease && shownProblems.length === 0 && !!draftId);

	const findingOptions = $derived(report.findings.map((f: any) => ({ id: f.id, label: `${f.id} · ${f.source} ${f.event_id} (${f.count}×)` })));
	const deviceOptions = $derived(report.devices.map((d: any) => ({ id: d.id, label: `${d.id} · ${d.class}${d.model ? ` ${d.model.vendor_id}:${d.model.product_id}` : ''}` })));
	const POINTERS = [
		'/symptom/category', '/symptom/description', '/symptom/reproduction_steps', '/symptom/occurred_at',
		'/hardware/windows_version', '/hardware/windows_build', '/hardware/cpu', '/hardware/ram_gb', '/hardware/system_model',
		'/hardware/board_model', '/hardware/bios_version', '/hardware/bios_date',
		'/collection/hardware', '/collection/devices', '/collection/system_events', '/collection/wlan_events',
		'/wow/game_build', '/wow/problem_scope', '/wow/addon_test'
	];

	function nextId(prefix: string, list: any[]) {
		let n = list.length + 1;
		while (list.some((item) => item.id === `${prefix}-${n}`)) n++;
		return `${prefix}-${n}`;
	}
	function addFact() {
		const ref = findingOptions[0] ? { kind: 'finding', id: findingOptions[0].id } : { kind: 'report_field', pointer: '/symptom/description' };
		draft.facts.push({ id: nextId('fact', draft.facts), text: '', references: [ref] });
	}
	function addStep() {
		draft.next_steps.push({ title: '', rationale: '', instructions: '', risk_class: 'read_only', required_privileges: 'none', expected_outcome: '', rollback: null, abort_condition: null });
	}
	function setRefKind(ref: any, kind: string) {
		for (const key of Object.keys(ref)) delete ref[key];
		ref.kind = kind;
		if (kind === 'finding') ref.id = findingOptions[0]?.id ?? '';
		else if (kind === 'device') ref.id = deviceOptions[0]?.id ?? '';
		else ref.pointer = '/symptom/description';
	}
	function toggleFactRef(h: any, id: string) {
		h.fact_refs = h.fact_refs.includes(id) ? h.fact_refs.filter((x: string) => x !== id) : [...h.fact_refs, id];
	}
	function nullable(value: string) {
		return value.trim() === '' ? null : value;
	}

	function switchMode(next: 'form' | 'json' | 'preview') {
		if (mode === 'json' && next !== 'json') {
			try {
				draft = normalize(JSON.parse(jsonText));
				jsonError = '';
			} catch (e) {
				jsonError = `JSON ungültig: ${(e as Error).message}`;
				return;
			}
		}
		if (next === 'json') jsonText = JSON.stringify(draft, null, 2);
		mode = next;
	}

	function payload() {
		if (mode === 'json') {
			try {
				draft = normalize(JSON.parse(jsonText));
				jsonError = '';
			} catch (e) {
				jsonError = `JSON ungültig: ${(e as Error).message}`;
			}
		}
		return JSON.stringify(draft);
	}

	const preview = $derived({ ...draft });
	const count = (value: string | null | undefined, max: number) => `${(value ?? '').length}/${max}`;
</script>

<div class="card overflow-hidden">
	<div class="flex flex-wrap items-center gap-2 border-b border-line px-4 py-3">
		<div class="inline-flex rounded-lg border border-line bg-bg p-0.5 text-sm">
			{#each [['form', 'Formular'], ['json', 'JSON'], ['preview', 'Vorschau']] as [key, label]}
				<button type="button" class="rounded-md px-3 py-1 {mode === key ? 'bg-surface-3 text-fg' : 'text-muted hover:text-fg'}" onclick={() => switchMode(key as any)}>{label}</button>
			{/each}
		</div>
		{#if dirty}<span class="pill text-warn bg-warn-dim">ungespeichert</span>{:else if saved}<span class="pill text-ok bg-ok-dim">gespeichert</span>{/if}
		<label class="ml-auto flex items-center gap-2 text-sm text-muted">
			<input type="checkbox" bind:checked={ai} class="accent-[var(--color-accent)]" /> beruht auf KI-Entwurf
		</label>
	</div>

	<div class="p-4 sm:p-5">
		{#if jsonError}<p class="mb-3 rounded-lg bg-bad-dim text-bad px-3 py-2 text-sm">{jsonError}</p>{/if}

		{#if mode === 'json'}
			<textarea class="input mono min-h-[28rem]" spellcheck="false" bind:value={jsonText}></textarea>
		{:else if mode === 'preview'}
			<p class="mb-3 text-xs text-dim">So sieht der Freund das Ergebnis in DriverPilot (als reiner Text).</p>
			<ResultView result={preview} />
		{:else}
			<div class="space-y-6">
				<div>
					<div class="flex justify-between"><label class="label" for="summary">Zusammenfassung</label><span class="text-[11px] text-dim">{count(draft.summary, 2000)}</span></div>
					<textarea id="summary" class="input min-h-24" maxlength="2000" bind:value={draft.summary} placeholder="Was ist los, in zwei, drei Sätzen?"></textarea>
				</div>

				<section>
					<div class="flex items-center justify-between mb-2">
						<p class="label mb-0">Fakten mit Belegen</p>
						<button type="button" class="btn btn-sm" onclick={addFact}><Icon name="plus" class="size-3.5" />Fakt</button>
					</div>
					<div class="space-y-2">
						{#each draft.facts as fact, i (i)}
							<div class="rounded-xl border border-line bg-bg/40 p-3">
								<div class="flex gap-2">
									<input class="input mono w-28 shrink-0" bind:value={fact.id} aria-label="Fakt-ID" />
									<textarea class="input min-h-10" rows="2" maxlength="1000" bind:value={fact.text} placeholder="Belegte Aussage"></textarea>
									<button type="button" class="btn btn-sm self-start" title="Fakt entfernen" onclick={() => draft.facts.splice(i, 1)}><Icon name="trash" class="size-3.5" /></button>
								</div>
								<div class="mt-2 flex flex-wrap items-center gap-2">
									{#each fact.references as ref, j (j)}
										<div class="flex items-center gap-1 rounded-lg border border-line bg-surface px-1.5 py-1">
											<select class="bg-transparent text-xs text-muted" value={ref.kind} onchange={(e) => setRefKind(ref, e.currentTarget.value)}>
												<option value="finding">Befund</option>
												<option value="device">Gerät</option>
												<option value="report_field">Feld</option>
											</select>
											{#if ref.kind === 'finding'}
												<select class="bg-transparent text-xs mono max-w-56" bind:value={ref.id}>{#each findingOptions as o}<option value={o.id}>{o.label}</option>{/each}</select>
											{:else if ref.kind === 'device'}
												<select class="bg-transparent text-xs mono max-w-56" bind:value={ref.id}>{#each deviceOptions as o}<option value={o.id}>{o.label}</option>{/each}</select>
											{:else}
												<input class="bg-transparent text-xs mono w-48" list="pointers" bind:value={ref.pointer} />
											{/if}
											<button type="button" class="text-dim hover:text-bad px-1" title="Beleg entfernen" onclick={() => fact.references.splice(j, 1)}>×</button>
										</div>
									{/each}
									<button type="button" class="text-xs text-accent hover:underline" onclick={() => fact.references.push({ kind: 'report_field', pointer: '/symptom/description' })}>+ Beleg</button>
								</div>
							</div>
						{:else}
							<p class="text-sm text-dim">Noch keine Fakten.</p>
						{/each}
					</div>
					<datalist id="pointers">{#each POINTERS as p}<option value={p}></option>{/each}</datalist>
				</section>

				<section>
					<div class="flex items-center justify-between mb-2">
						<p class="label mb-0">Vermutungen (unbewiesen)</p>
						<button type="button" class="btn btn-sm" onclick={() => draft.hypotheses.push({ text: '', proven: false, fact_refs: [] })}><Icon name="plus" class="size-3.5" />Vermutung</button>
					</div>
					<div class="space-y-2">
						{#each draft.hypotheses as h, i (i)}
							<div class="rounded-xl border border-line bg-bg/40 p-3">
								<div class="flex gap-2">
									<textarea class="input min-h-10" rows="2" maxlength="1000" bind:value={h.text} placeholder="Vermutung, ausdrücklich unbewiesen"></textarea>
									<button type="button" class="btn btn-sm self-start" title="Entfernen" onclick={() => draft.hypotheses.splice(i, 1)}><Icon name="trash" class="size-3.5" /></button>
								</div>
								<div class="mt-2 flex flex-wrap gap-1.5 text-xs">
									<span class="text-dim">stützt sich auf:</span>
									{#each draft.facts as fact}
										<button type="button" class="chip mono {h.fact_refs.includes(fact.id) ? '!text-accent !border-accent/40' : ''}" onclick={() => toggleFactRef(h, fact.id)}>{fact.id}</button>
									{/each}
								</div>
							</div>
						{/each}
					</div>
				</section>

				<section>
					<div class="flex items-center justify-between mb-2">
						<p class="label mb-0">Nächste Schritte</p>
						<button type="button" class="btn btn-sm" onclick={addStep}><Icon name="plus" class="size-3.5" />Schritt</button>
					</div>
					<div class="space-y-2">
						{#each draft.next_steps as step, i (i)}
							<div class="rounded-xl border border-line bg-bg/40 p-3 grid gap-2">
								<div class="flex gap-2">
									<span class="mono text-dim pt-2">{i + 1}.</span>
									<input class="input" maxlength="200" bind:value={step.title} placeholder="Titel" />
									<button type="button" class="btn btn-sm" title="Entfernen" onclick={() => draft.next_steps.splice(i, 1)}><Icon name="trash" class="size-3.5" /></button>
								</div>
								<textarea class="input min-h-20" maxlength="4000" bind:value={step.instructions} placeholder="Anleitung: manuelle Schritte in Prosa, keine Befehle"></textarea>
								<div class="grid sm:grid-cols-2 gap-2">
									<input class="input" maxlength="1000" bind:value={step.rationale} placeholder="Warum?" />
									<input class="input" maxlength="1000" bind:value={step.expected_outcome} placeholder="Woran erkennt man den Erfolg?" />
									<input class="input" maxlength="1000" value={step.rollback ?? ''} oninput={(e) => (step.rollback = nullable(e.currentTarget.value))} placeholder="Rückweg (optional)" />
									<input class="input" maxlength="1000" value={step.abort_condition ?? ''} oninput={(e) => (step.abort_condition = nullable(e.currentTarget.value))} placeholder="Abbrechen, wenn … (optional)" />
									<select class="input" bind:value={step.risk_class}>
										<option value="read_only">Risiko: nur lesen</option>
										<option value="reversible_change">Risiko: rückgängig machbar</option>
										<option value="expert_only">Risiko: nur für Experten</option>
									</select>
									<select class="input" bind:value={step.required_privileges}>
										<option value="none">Rechte: keine</option>
										<option value="standard_user">Rechte: normaler Benutzer</option>
										<option value="administrator">Rechte: Administrator</option>
									</select>
								</div>
							</div>
						{/each}
					</div>
				</section>

				{#each [['open_questions', 'Rückfragen an den Freund', 'Rückfrage'], ['warnings', 'Hinweise', 'Hinweis']] as [key, title, item]}
					<section>
						<div class="flex items-center justify-between mb-2">
							<p class="label mb-0">{title}</p>
							<button type="button" class="btn btn-sm" onclick={() => draft[key].push('')}><Icon name="plus" class="size-3.5" />{item}</button>
						</div>
						<div class="space-y-2">
							{#each draft[key] as _, i (i)}
								<div class="flex gap-2">
									<input class="input" maxlength="1000" bind:value={draft[key][i]} />
									<button type="button" class="btn btn-sm" title="Entfernen" onclick={() => draft[key].splice(i, 1)}><Icon name="trash" class="size-3.5" /></button>
								</div>
							{/each}
						</div>
					</section>
				{/each}

				<section>
					<div class="flex items-center justify-between mb-2">
						<p class="label mb-0">Quellen (nur offizielle https-Seiten)</p>
						<button type="button" class="btn btn-sm" onclick={() => draft.sources.push({ title: '', url: 'https://' })}><Icon name="plus" class="size-3.5" />Quelle</button>
					</div>
					<div class="space-y-2">
						{#each draft.sources as source, i (i)}
							<div class="grid sm:grid-cols-[1fr_1.4fr_auto] gap-2">
								<input class="input" maxlength="200" bind:value={source.title} placeholder="Titel" />
								<input class="input mono" maxlength="500" bind:value={source.url} placeholder="https://…" />
								<button type="button" class="btn btn-sm" title="Entfernen" onclick={() => draft.sources.splice(i, 1)}><Icon name="trash" class="size-3.5" /></button>
							</div>
						{/each}
					</div>
				</section>
			</div>
		{/if}
	</div>

	{#if shownProblems.length || shownHints.length}
		<div class="border-t border-line px-4 py-3 space-y-1 text-sm">
			{#each shownProblems as p}<p class="text-bad flex gap-2"><Icon name="alert" class="size-4 shrink-0 mt-0.5" />{p}</p>{/each}
			{#each shownHints as p}<p class="text-warn/80 text-xs">{p}</p>{/each}
		</div>
	{:else if checkProblems}
		<div class="border-t border-line px-4 py-3 text-sm text-ok flex gap-2"><Icon name="check" />Entwurf entspricht dem Ergebnisschema.</div>
	{/if}
	{#if message}
		<div class="border-t border-line px-4 py-3 text-sm {message.ok ? 'text-ok' : 'text-bad'}">{message.text}</div>
	{/if}

	<div class="flex flex-wrap items-center gap-2 border-t border-line bg-surface-2/50 px-4 py-3">
		<form
			method="POST"
			action="?/validate"
			use:enhance={({ formData }) => {
				formData.set('content', payload());
				busy = true;
				return async ({ result }) => {
					busy = false;
					if (result.type === 'success') {
						checkProblems = (result.data?.problems as string[]) ?? [];
						checkHints = (result.data?.hints as string[]) ?? [];
						message = null;
					} else if (result.type === 'failure') {
						message = { ok: false, text: String(result.data?.error ?? 'Prüfung fehlgeschlagen') };
					}
				};
			}}
		>
			<button class="btn" disabled={busy}><Icon name="check" />Prüfen</button>
		</form>
		<form
			method="POST"
			action="?/draft"
			use:enhance={({ formData }) => {
				formData.set('content', payload());
				formData.set('ai_assisted', ai ? '1' : '0');
				busy = true;
				return async ({ result }) => {
					busy = false;
					if (result.type === 'success') {
						message = { ok: true, text: 'Entwurf gespeichert.' };
						checkProblems = null;
						await invalidateAll();
					} else if (result.type === 'failure') {
						message = { ok: false, text: String(result.data?.error ?? 'Speichern fehlgeschlagen') };
					} else await applyAction(result);
				};
			}}
		>
			<button class="btn btn-blue" disabled={busy || !!jsonError}><Icon name="check" />Entwurf speichern</button>
		</form>
		<form
			method="POST"
			action="?/release"
			class="ml-auto"
			use:enhance={({ cancel }) => {
				if (!confirm(`Revision ${nextRevision} freigeben? Sie ist danach unveränderlich und für den Freund sichtbar.`)) return cancel();
				busy = true;
				return async ({ update }) => {
					busy = false;
					await update();
				};
			}}
		>
			<input type="hidden" name="draft_id" value={draftId ?? ''} />
			<input type="hidden" name="version" value={version} />
			<button class="btn btn-primary" disabled={busy || !releasable} title={releasable ? '' : dirty ? 'Erst speichern' : !canRelease ? 'Fall erst übernehmen' : 'Entwurf hat noch Fehler'}>
				<Icon name="share" />Revision {nextRevision} freigeben
			</button>
		</form>
	</div>
</div>
