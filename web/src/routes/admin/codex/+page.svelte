<script lang="ts">
	import { onMount } from 'svelte';
	import { enhance } from '$app/forms';
	import { invalidateAll } from '$app/navigation';
	import Icon from '$lib/components/Icon.svelte';
	import Flash from '$lib/components/Flash.svelte';
	import CopyButton from '$lib/components/CopyButton.svelte';
	import Kpi from '$lib/components/Kpi.svelte';
	import { dateTime } from '$lib/format';
	let { data, form } = $props();
	const st = $derived(data.status);

	onMount(() => {
		const timer = setInterval(() => {
			if (data.status?.device?.state === 'pending') invalidateAll();
		}, 3000);
		return () => clearInterval(timer);
	});
</script>

<svelte:head><title>KI · DriverPilot Admin</title></svelte:head>

<h1 class="text-2xl font-semibold tracking-tight mb-1">KI-Entwürfe über ChatGPT</h1>
<p class="text-sm text-muted mb-6">Nur Fälle mit Zustimmung des Freundes gehen an ChatGPT. Jeder Entwurf wird von dir geprüft, bevor der Freund etwas sieht.</p>
<div class="mb-4"><Flash {form} /></div>

{#if !st}
	<div class="card p-6 text-muted">Adapter ist nicht aktiv (<span class="mono">DP_AI_PROVIDER={data.provider}</span>). Alle Fälle werden manuell bearbeitet.</div>
{:else}
	<div class="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
		<Kpi label="Anmeldung" value={st.logged_in ? 'aktiv' : 'fehlt'} tone={st.logged_in ? 'text-ok' : 'text-bad'} sub={st.email ? `${st.email}${st.plan ? ` · ${st.plan}` : ''}` : ''} />
		<Kpi label="Für Freunde angeboten" value={data.ai_offered ? 'ja' : 'nein'} tone={data.ai_offered ? 'text-ok' : 'text-warn'} />
		<Kpi label="Modell" value={data.model} />
		<Kpi label="Aufrufe heute" value={`${data.budget_used} / ${data.budget_total}`} />
	</div>

	<div class="grid lg:grid-cols-2 gap-3">
		<section class="card p-5">
			<h2 class="font-semibold mb-3">Status</h2>
			<dl class="grid grid-cols-[10rem_1fr] gap-y-1.5 text-sm">
				<dt class="text-dim">Token gültig bis</dt><dd>{dateTime(st.expires_at)}{#if st.expired}<span class="text-warn"> · wird beim nächsten Aufruf erneuert</span>{/if}</dd>
				<dt class="text-dim">Letzter Refresh</dt><dd>{dateTime(st.last_refresh)}</dd>
				<dt class="text-dim">Letzter Fehler</dt><dd class={st.last_error ? 'text-bad' : ''}>{st.last_error ?? '–'}</dd>
			</dl>
			<div class="mt-5 flex flex-wrap gap-2">
				{#if !st.logged_in}
					<form method="POST" action="?/login" use:enhance><button class="btn btn-primary"><Icon name="ai" />Mit ChatGPT anmelden</button></form>
				{:else}
					<form method="POST" action="?/logout" use:enhance={({ cancel }) => { if (!confirm('Abmelden und Tokendatei löschen?')) cancel(); }}>
						<button class="btn btn-danger">Abmelden</button>
					</form>
				{/if}
			</div>
			{#if st.device}
				<div class="mt-5 rounded-xl border border-line bg-bg/50 p-4">
					{#if st.device.state === 'pending'}
						<p class="text-sm text-muted">Öffne <a class="text-accent hover:underline" href={st.device.verification_url} target="_blank" rel="noopener">{st.device.verification_url}</a> und gib diesen Code ein:</p>
						<div class="mt-3 flex items-center gap-3">
							<span class="text-3xl font-semibold tracking-[0.2em] mono text-accent">{st.device.user_code}</span>
							<CopyButton text={st.device.user_code} />
						</div>
						<p class="mt-3 text-xs text-dim">Diese Seite merkt den Abschluss von selbst. Der Code gilt 15 Minuten.</p>
						<form method="POST" action="?/cancel" use:enhance class="mt-3"><button class="btn btn-sm">Abbrechen</button></form>
					{:else if st.device.state === 'done'}
						<p class="text-sm text-ok">Anmeldung abgeschlossen.</p>
					{:else}
						<p class="text-sm text-bad">{st.device.state}: {st.device.error ?? ''}</p>
					{/if}
				</div>
			{/if}
		</section>
		<section class="card p-5">
			<h2 class="font-semibold mb-1">auth.json der Codex-CLI übernehmen</h2>
			<p class="text-sm text-muted mb-3">Alternative zum Device-Login. Die Datei landet nur im Datenverzeichnis des Servers (0600).</p>
			<form method="POST" action="?/import" use:enhance class="space-y-3">
				<textarea name="auth_json" class="input mono min-h-36" placeholder="Inhalt von ~/.codex/auth.json" spellcheck="false"></textarea>
				<button class="btn">Übernehmen</button>
			</form>
		</section>
	</div>
	<p class="mt-6 text-xs text-dim">Ablauf: Bericht als reine Daten mit festen Anweisungen an ChatGPT (store=false), Antwort gegen Ergebnisschema und Belege geprüft, höchstens zwei Versuche je Fall, 300 s Timeout. „Das Modell für alle verbessern“ muss im ChatGPT-Konto aus sein.</p>
{/if}
