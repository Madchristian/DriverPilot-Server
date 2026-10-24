<script lang="ts">
	// hardware_details (Berichtsschema 1.1). null = Bereich nicht erfasst, nie „unauffällig“.
	let { details }: { details: any } = $props();
	const cpu = $derived(details.cpu);
	const memory = $derived(details.memory);
	const gpus = $derived(details.gpus);
	const storage = $derived(details.storage);
	const platform = $derived(details.platform);

	const POWER_PLAN: Record<string, string> = {
		balanced: 'Ausbalanciert',
		high_performance: 'Höchstleistung',
		power_saver: 'Energiesparmodus',
		ultimate_performance: 'Ultimative Leistung',
		custom: 'eigener Plan'
	};
	const HEALTH_TONE: Record<string, string> = {
		healthy: 'text-ok bg-ok-dim',
		warning: 'text-warn bg-warn-dim',
		unhealthy: 'text-bad bg-bad-dim',
		unknown: 'text-muted bg-surface-3'
	};
	const yesNo = (value: boolean | null) => (value === null ? null : value ? 'an' : 'aus');
	const unit = (value: number | null, suffix: string) => (value === null ? null : `${value} ${suffix}`);
	const gb = (mb: number | null) => (mb === null ? null : mb >= 1024 ? `${Math.round(mb / 1024)} GB` : `${mb} MB`);
	const pair = (current: number | null, max: number | null, suffix: string) =>
		current === null && max === null ? null : `${current ?? '?'} / ${max ?? '?'} ${suffix}`;
	const xmp = (m: any) => m.configured_mts !== null && m.rated_mts !== null && m.configured_mts > m.rated_mts;
	const freeShare = $derived(
		storage && storage.system_size_gb && storage.system_free_gb !== null ? storage.system_free_gb / storage.system_size_gb : null
	);
	const cpuRows = $derived([
		['Kerne / Threads', cpu ? [cpu.cores, cpu.threads].map((v) => v ?? '?').join(' / ') : null],
		['Nenntakt', cpu ? unit(cpu.max_clock_mhz, 'MHz') : null],
		['Firmware', platform?.firmware_mode?.toUpperCase() ?? null],
		['Secure Boot', platform ? yesNo(platform.secure_boot) : null],
		['Energieplan', platform?.power_plan ? POWER_PLAN[platform.power_plan] ?? platform.power_plan : null],
		['GPU-Planung', platform ? yesNo(platform.hardware_gpu_scheduling) : null],
		['Laufzeit', platform ? unit(platform.uptime_hours, 'h') : null]
	]);
</script>

{#snippet missing(label: string)}
	<p class="text-sm text-dim">{label} nicht erfasst.</p>
{/snippet}

<div class="grid lg:grid-cols-[1fr_1.4fr] gap-3 mt-3">
	<section class="card p-5">
		<h3 class="label">CPU und Plattform</h3>
		{#if cpu || platform}
			<dl class="grid grid-cols-[8rem_1fr] gap-x-3 gap-y-1.5 text-sm">
				{#each cpuRows as [key, value]}
					<dt class="text-dim">{key}</dt>
					<dd>{#if value}{value}{:else}<span class="text-dim">–</span>{/if}</dd>
				{/each}
			</dl>
		{:else}
			{@render missing('CPU und Plattform')}
		{/if}
	</section>

	<section class="card p-5 overflow-hidden">
		<h3 class="label">Arbeitsspeicher{memory?.slots_total ? ` · ${memory.modules.length} von ${memory.slots_total} Steckplätzen` : ''}</h3>
		{#if memory}
			<div class="overflow-x-auto -mx-5">
				<table class="table">
					<thead><tr><th>Steckplatz</th><th>Größe</th><th>Typ</th><th>MT/s (Nenn / eingestellt)</th><th>Modul</th></tr></thead>
					<tbody>
						{#each memory.modules as m}
							<tr>
								<td class="mono">{m.slot ?? '–'}</td>
								<td class="tabular-nums">{gb(m.capacity_mb) ?? '–'}</td>
								<td class="uppercase">{m.type ?? '–'}</td>
								<td class="tabular-nums whitespace-nowrap">
									{m.rated_mts ?? '?'} / {m.configured_mts ?? '?'}
									{#if xmp(m)}<span class="pill text-warn bg-warn-dim ml-1" title="Eingestellt über Nenngeschwindigkeit">XMP/EXPO</span>{/if}
								</td>
								<td class="text-xs text-muted">{[m.manufacturer, m.part_number].filter(Boolean).join(' · ') || '–'}</td>
							</tr>
						{:else}
							<tr><td colspan="5" class="text-muted">Keine Module gemeldet.</td></tr>
						{/each}
					</tbody>
				</table>
			</div>
		{:else}
			{@render missing('Arbeitsspeicher')}
		{/if}
	</section>
</div>

<section class="card p-5 mt-3">
	<h3 class="label">Grafikkarten</h3>
	{#if gpus === null}
		{@render missing('Grafikkarten')}
	{:else}
		<div class="grid xl:grid-cols-2 gap-3">
			{#each gpus as g}
				<div class="rounded-xl border border-line bg-bg/50 p-4">
					<p class="font-semibold">{g.name ?? 'Unbekannte Grafikkarte'} <span class="chip ml-1">{g.vendor}</span></p>
					<p class="text-xs text-muted mt-0.5">{[gb(g.vram_mb) && `${gb(g.vram_mb)} VRAM`, g.driver_version && `Treiber ${g.driver_version}`].filter(Boolean).join(' · ') || '–'}</p>
					{#if g.telemetry}
						{@const t = g.telemetry}
						<p class="text-xs text-dim mt-3 mb-1">Momentaufnahme beim Scan (meist Leerlauf)</p>
						<dl class="grid grid-cols-[9rem_1fr] gap-x-3 gap-y-1 text-sm">
							<dt class="text-dim">Temperatur / Lüfter</dt><dd>{unit(t.temperature_c, '°C') ?? '–'} · {unit(t.fan_percent, '%') ?? '–'}</dd>
							<dt class="text-dim">GPU-Takt</dt><dd>{pair(t.graphics_clock_mhz, t.graphics_clock_max_mhz, 'MHz') ?? '–'}</dd>
							<dt class="text-dim">Speichertakt</dt><dd>{pair(t.memory_clock_mhz, t.memory_clock_max_mhz, 'MHz') ?? '–'}</dd>
							<dt class="text-dim">Leistung</dt><dd>{unit(t.power_draw_w, 'W') ?? '–'}</dd>
							<dt class="text-dim">Power-Limit</dt>
							<dd>
								{unit(t.power_limit_w, 'W') ?? '–'}
								<span class="text-dim">(Standard {unit(t.power_limit_default_w, 'W') ?? '?'}, max. {unit(t.power_limit_max_w, 'W') ?? '?'})</span>
								{#if t.power_limit_w !== null && t.power_limit_default_w !== null && t.power_limit_w > t.power_limit_default_w}<span class="pill text-warn bg-warn-dim ml-1">angehoben</span>{/if}
							</dd>
							<dt class="text-dim">PCIe</dt><dd>Gen {pair(t.pcie_gen_current, t.pcie_gen_max, '')} · x{pair(t.pcie_width_current, t.pcie_width_max, '')}</dd>
						</dl>
					{:else}
						<p class="text-xs text-dim mt-3">Keine Telemetrie (kein NVIDIA-Treiber oder nvidia-smi ohne Antwort).</p>
					{/if}
				</div>
			{:else}
				<p class="text-sm text-muted">Keine physische Grafikkarte gemeldet.</p>
			{/each}
		</div>
	{/if}
</section>

<section class="card mt-3 overflow-hidden">
	<h3 class="label px-5 pt-4">
		Laufwerke
		{#if storage}
			<span class="normal-case font-normal text-muted">
				· System {storage.system_free_gb ?? '?'} von {storage.system_size_gb ?? '?'} GB frei
				{#if freeShare !== null && freeShare < 0.1}<span class="pill text-warn bg-warn-dim ml-1">knapp</span>{/if}
				· Auslagerungsdatei {gb(storage.pagefile_mb) ?? 'keine/unbekannt'}
			</span>
		{/if}
	</h3>
	{#if storage}
		<div class="overflow-x-auto">
			<table class="table">
				<thead><tr><th>Modell</th><th>Art</th><th>Bus</th><th class="text-right">Größe</th><th>Zustand</th><th>Firmware</th><th>System</th></tr></thead>
				<tbody>
					{#each storage.disks as d}
						<tr>
							<td>{d.model ?? '–'}</td>
							<td class="uppercase">{d.media === 'unspecified' ? '–' : d.media}</td>
							<td class="uppercase">{d.bus}</td>
							<td class="text-right tabular-nums">{d.size_gb !== null ? `${d.size_gb} GB` : '–'}</td>
							<td><span class="pill {HEALTH_TONE[d.health]}">{d.health}</span></td>
							<td class="mono text-xs">{d.firmware ?? '–'}</td>
							<td>{d.system_disk === null ? '–' : d.system_disk ? 'ja' : ''}</td>
						</tr>
					{:else}
						<tr><td colspan="7" class="text-muted">Keine Laufwerke gemeldet.</td></tr>
					{/each}
				</tbody>
			</table>
		</div>
	{:else}
		<div class="px-5 pb-4">{@render missing('Laufwerke')}</div>
	{/if}
</section>
