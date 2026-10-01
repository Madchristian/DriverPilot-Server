<script lang="ts">
	import { CATEGORY, SEVERITY, dateTime } from '$lib/format';
	let { report }: { report: any } = $props();
	const hw = $derived(report.hardware ?? {});
	const hardwareRows = $derived([
		['Windows', [hw.windows_version, hw.windows_build && `Build ${hw.windows_build}`, hw.architecture].filter(Boolean).join(' · ')],
		['CPU', hw.cpu],
		['RAM', hw.ram_gb ? `${hw.ram_gb} GB` : null],
		['System', [hw.system_manufacturer, hw.system_model].filter(Boolean).join(' ') || null],
		['Mainboard', [hw.board_manufacturer, hw.board_model, hw.board_revision && `Rev. ${hw.board_revision}`].filter(Boolean).join(' ') || null],
		['BIOS', [hw.bios_version, hw.bios_date].filter(Boolean).join(' vom ') || null],
		['Bauform', hw.is_portable === null || hw.is_portable === undefined ? null : hw.is_portable ? 'Notebook' : 'Desktop']
	]);
	const collectionTone: Record<string, string> = {
		complete: 'text-ok bg-ok-dim',
		truncated: 'text-warn bg-warn-dim',
		failed: 'text-bad bg-bad-dim',
		unavailable: 'text-muted bg-surface-3'
	};
	const collectionLabel: Record<string, string> = { hardware: 'Hardware', devices: 'Geräte', system_events: 'Systemereignisse', wlan_events: 'WLAN' };
	const scopeLabel: Record<string, string> = { wow_only: 'nur in WoW', also_elsewhere: 'auch anderswo', unknown: 'unbekannt' };
</script>

<div class="grid lg:grid-cols-[1.3fr_1fr] gap-3">
	<section class="card p-5">
		<div class="flex flex-wrap items-center gap-2">
			<span class="pill text-blue bg-blue-dim">{CATEGORY[report.symptom.category] ?? report.symptom.category}</span>
			<span class="text-xs text-muted">aufgetreten {dateTime(report.symptom.occurred_at)}</span>
		</div>
		<p class="mt-3 whitespace-pre-wrap break-words leading-relaxed">{report.symptom.description}</p>
		{#if report.symptom.reproduction_steps}
			<p class="label mt-4">Nachstellen</p>
			<p class="whitespace-pre-wrap break-words text-sm text-muted">{report.symptom.reproduction_steps}</p>
		{/if}
		{#if report.wow}
			<div class="mt-4 flex flex-wrap gap-2 text-xs">
				<span class="chip">WoW {report.wow.game_build ?? '?'}</span>
				<span class="chip">Problem {scopeLabel[report.wow.problem_scope] ?? report.wow.problem_scope}</span>
				<span class="chip">Addon-Test: {report.wow.addon_test}</span>
			</div>
		{/if}
		<div class="mt-4 pt-4 border-t border-line grid sm:grid-cols-2 gap-2 text-xs text-muted">
			<span>Scan {dateTime(report.scanned_at)}</span>
			<span>Fenster {dateTime(report.observation_start)} – {dateTime(report.observation_end)}</span>
			<span>App {report.app_version}</span>
			<span>Zustimmung {dateTime(report.consent.accepted_at)} · KI {report.consent.external_ai_allowed ? 'erlaubt' : 'nein'}</span>
		</div>
		<div class="mt-3 flex flex-wrap gap-1.5">
			{#each Object.entries(report.collection) as [key, value]}
				<span class="pill {collectionTone[value as string]}" title="Erfassung {collectionLabel[key] ?? key}">{collectionLabel[key] ?? key}: {value}</span>
			{/each}
		</div>
	</section>

	<section class="card p-5">
		<h3 class="label">Hardware</h3>
		<dl class="grid grid-cols-[6rem_1fr] gap-x-3 gap-y-1.5 text-sm">
			{#each hardwareRows as [key, value]}
				<dt class="text-dim">{key}</dt>
				<dd class="break-words">{#if value}{value}{:else}<span class="text-dim">–</span>{/if}</dd>
			{/each}
		</dl>
	</section>
</div>

<section class="card mt-3 overflow-hidden">
	<h3 class="label px-5 pt-4">Befunde ({report.findings.length})</h3>
	<div class="overflow-x-auto">
		<table class="table">
			<thead><tr><th>ID</th><th>Quelle</th><th>Ereignis</th><th class="text-right">Anzahl</th><th>Zeitraum</th><th>Stufe</th><th>Gerät</th></tr></thead>
			<tbody>
				{#each report.findings as f}
					<tr>
						<td class="mono text-dim">{f.id}</td>
						<td class="whitespace-nowrap">{f.source}</td>
						<td class="mono">{f.event_id}</td>
						<td class="text-right tabular-nums">{f.count}</td>
						<td class="text-xs text-muted whitespace-nowrap">{dateTime(f.first_seen)} – {dateTime(f.last_seen)}</td>
						<td><span class="pill {SEVERITY[f.severity]}">{f.severity}</span></td>
						<td class="mono text-dim">{f.device_ref ?? '–'}</td>
					</tr>
				{:else}
					<tr><td colspan="7" class="text-muted">Keine Befunde übermittelt.</td></tr>
				{/each}
			</tbody>
		</table>
	</div>
</section>

<section class="card mt-3 overflow-hidden">
	<h3 class="label px-5 pt-4">Geräte ({report.devices.length})</h3>
	<div class="overflow-x-auto">
		<table class="table">
			<thead><tr><th>ID</th><th>Klasse</th><th>Modell</th><th>Treiber</th><th>Datum</th><th>Problemcode</th></tr></thead>
			<tbody>
				{#each report.devices as d}
					<tr>
						<td class="mono text-dim">{d.id}</td>
						<td>{d.class}</td>
						<td class="mono">{#if d.model}{d.model.bus.toUpperCase()} {d.model.vendor_id}:{d.model.product_id}{#if d.model.subsystem_id}<span class="text-dim"> / {d.model.subsystem_id}</span>{/if}{:else}<span class="text-dim">–</span>{/if}</td>
						<td class="mono">{d.driver_version ?? '–'}</td>
						<td class="text-xs text-muted">{d.driver_date ?? '–'}</td>
						<td>
							{#if d.problem_code === null}<span class="text-dim">–</span>
							{:else if d.problem_code === 0}<span class="text-ok">0</span>
							{:else}<span class="pill text-warn bg-warn-dim">{d.problem_code}{d.problem_code === 22 ? ' · deaktiviert' : ''}</span>{/if}
						</td>
					</tr>
				{/each}
			</tbody>
		</table>
	</div>
</section>
