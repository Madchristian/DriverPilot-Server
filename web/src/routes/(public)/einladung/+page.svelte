<script lang="ts">
	import { onMount } from 'svelte';
	import Icon from '$lib/components/Icon.svelte';
	import CopyButton from '$lib/components/CopyButton.svelte';
	import { size } from '$lib/format';
	let { data } = $props();

	const KEY = 'driverpilot-invite';
	let code = $state<string | null>(null);
	let name = $state<string | null>(null);
	let ready = $state(false);

	onMount(() => {
		// Der Code steht im Fragment (#...). Browser schicken das Fragment nie an einen Server.
		// Nach dem Lesen entfernen wir es aus der Adresszeile und dem Verlauf.
		const params = new URLSearchParams(location.hash.slice(1));
		const fromHash = params.get('c');
		if (fromHash && /^[A-Za-z0-9_-]{22,128}$/.test(fromHash)) {
			code = fromHash;
			name = params.get('n');
			try {
				sessionStorage.setItem(KEY, JSON.stringify({ code, name }));
			} catch {}
			history.replaceState(null, '', location.pathname);
		} else {
			try {
				const stored = JSON.parse(sessionStorage.getItem(KEY) ?? 'null');
				if (stored?.code) ({ code, name } = stored);
			} catch {}
		}
		ready = true;
	});
</script>

<svelte:head><title>Einladung · DriverPilot</title></svelte:head>

<div class="mx-auto max-w-3xl px-4 py-10">
	{#if !ready}
		<div class="card p-8 text-muted">Einladung wird geladen …</div>
	{:else if !code}
		<div class="card p-8 fade-in">
			<span class="grid place-items-center size-10 rounded-xl bg-warn-dim text-warn"><Icon name="alert" /></span>
			<h1 class="mt-4 text-2xl font-semibold">Der Link ist unvollständig</h1>
			<p class="mt-2 text-muted">
				Im Link fehlt der Einladungscode. Öffne den Link bitte noch einmal genau so, wie Christian ihn dir geschickt hat, oder
				frag ihn nach einem neuen.
			</p>
		</div>
	{:else}
		<div class="fade-in">
			<span class="pill text-accent bg-accent-dim">Einladung von Christian</span>
			<h1 class="mt-4 text-3xl sm:text-4xl font-semibold tracking-tight">
				{name ? `Hallo ${name}!` : 'Hallo!'} So bekommst du Hilfe für deinen PC.
			</h1>
			<p class="mt-3 text-muted">Drei Schritte, danach kannst du Christian aus DriverPilot heraus einen Diagnosebericht schicken.</p>
		</div>

		<ol class="mt-8 space-y-3">
			<li class="card p-5 sm:p-6 fade-in">
				<div class="flex items-start gap-4">
					<span class="grid place-items-center size-8 shrink-0 rounded-full bg-blue-dim text-blue font-semibold text-sm">1</span>
					<div class="min-w-0 flex-1">
						<h2 class="font-semibold">DriverPilot herunterladen</h2>
						<p class="mt-1 text-sm text-muted">Die Setup-ZIP enthält das Setup, Christians Zertifikat und eine Anleitung dazu.</p>
						{#if data.setup}
							<a href="/downloads/{data.setup.name}" data-sveltekit-reload download class="btn btn-primary mt-4"><Icon name="download" />Setup-ZIP laden ({size(data.setup.size)})</a>
						{:else}
							<a href="/downloads" class="btn mt-4">Zu den Downloads</a>
						{/if}
					</div>
				</div>
			</li>
			<li class="card p-5 sm:p-6 fade-in">
				<div class="flex items-start gap-4">
					<span class="grid place-items-center size-8 shrink-0 rounded-full bg-blue-dim text-blue font-semibold text-sm">2</span>
					<div class="min-w-0 flex-1">
						<h2 class="font-semibold">Installieren</h2>
						<p class="mt-1 text-sm text-muted">
							ZIP entpacken, den Zertifikat-Fingerabdruck mit Christian abgleichen, Zertifikat einrichten und das Setup starten.
							Die genauen Klicks stehen in der Anleitung.
						</p>
						<a href="/anleitung#1-installation" class="btn mt-4" target="_blank" rel="noopener"><Icon name="book" />Installationsanleitung</a>
					</div>
				</div>
			</li>
			<li class="card p-5 sm:p-6 fade-in border-accent/30">
				<div class="flex items-start gap-4">
					<span class="grid place-items-center size-8 shrink-0 rounded-full bg-accent-dim text-accent font-semibold text-sm">3</span>
					<div class="min-w-0 flex-1">
						<h2 class="font-semibold">In DriverPilot koppeln</h2>
						<p class="mt-1 text-sm text-muted">„Hilfe von Christian“ öffnen, „Koppeln“ wählen und diese beiden Angaben eintragen:</p>
						<div class="mt-4 grid gap-3">
							<div>
								<span class="label">Serveradresse</span>
								<div class="flex gap-2">
									<code class="input mono flex-1 truncate">{data.serverUrl}</code>
									<CopyButton text={data.serverUrl} class="btn" />
								</div>
							</div>
							<div>
								<span class="label">Einladungscode</span>
								<div class="flex gap-2">
									<code class="input mono flex-1 break-all text-accent">{code}</code>
									<CopyButton text={code} class="btn" />
								</div>
							</div>
						</div>
						<p class="mt-4 text-xs text-dim">
							Der Code gilt nur begrenzt und meist nur einmal. Nach dem Koppeln hat DriverPilot einen eigenen Zugang für 30 Tage;
							den Code brauchst du dann nicht mehr. Gib ihn nicht weiter.
						</p>
					</div>
				</div>
			</li>
		</ol>

		<p class="mt-8 text-sm text-muted">
			Fragen? Schreib Christian. Was bei einem Bericht gesendet wird, steht im <a href="/datenschutz" class="text-accent hover:underline">Datenschutzhinweis</a>.
		</p>
	{/if}
</div>
