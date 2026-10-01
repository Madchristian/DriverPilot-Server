<script lang="ts">
	import Icon from '$lib/components/Icon.svelte';
	const steps = [
		{ icon: 'download', title: 'Installieren', text: 'Setup-ZIP laden, Zertifikat einmal prüfen und einrichten, Setup starten.' },
		{ icon: 'link', title: 'Koppeln', text: 'Mit dem Einladungslink von Christian bekommst du Serveradresse und Code.' },
		{ icon: 'chip', title: 'Bericht senden', text: 'Frischer Scan, Vorschau lesen, zustimmen. Nur das Gezeigte wird gesendet.' },
		{ icon: 'check', title: 'Antwort lesen', text: 'Christian prüft und schreibt dir Schritte, die du selbst ausführst.' }
	];
</script>

<svelte:head><title>DriverPilot · Hilfe von Christian</title></svelte:head>

<section class="relative overflow-hidden">
	<div class="absolute inset-0 -z-10 opacity-60" style="background: radial-gradient(60rem 30rem at 70% -10%, rgba(105,171,255,.18), transparent 60%), radial-gradient(40rem 24rem at 10% 10%, rgba(91,215,193,.12), transparent 60%);"></div>
	<div class="mx-auto max-w-5xl px-4 pt-16 pb-12 grid md:grid-cols-[1.4fr_1fr] gap-10 items-center">
		<div class="fade-in">
			<span class="pill text-accent bg-accent-dim">Für Freunde von Christian</span>
			<h1 class="mt-4 text-4xl sm:text-5xl font-semibold tracking-tight leading-[1.1]">
				Dein PC macht Ärger?<br /><span class="text-blue">Christian schaut drauf.</span>
			</h1>
			<p class="mt-5 text-lg text-muted max-w-xl">
				DriverPilot behält Hardware und Treiber deines Windows-PCs im Blick. Mit „Hilfe von Christian“ schickst du
				einen bereinigten Diagnosebericht und bekommst eine Antwort mit konkreten Schritten.
			</p>
			<div class="mt-8 flex flex-wrap gap-3">
				<a href="/downloads" class="btn btn-primary px-4 py-2.5"><Icon name="download" />DriverPilot laden</a>
				<a href="/anleitung" class="btn px-4 py-2.5"><Icon name="book" />Anleitung lesen</a>
			</div>
		</div>
		<div class="hidden md:flex justify-center fade-in">
			<img src="/logo.png" alt="DriverPilot-Logo" class="w-64 drop-shadow-[0_20px_60px_rgba(105,171,255,0.25)]" />
		</div>
	</div>
</section>

<section class="mx-auto max-w-5xl px-4 pb-16">
	<div class="grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
		{#each steps as step, i}
			<div class="card p-5">
				<div class="flex items-center gap-3">
					<span class="grid place-items-center size-9 rounded-xl bg-blue-dim text-blue"><Icon name={step.icon} /></span>
					<span class="text-xs text-dim font-mono">0{i + 1}</span>
				</div>
				<h2 class="mt-4 font-semibold">{step.title}</h2>
				<p class="mt-1.5 text-sm text-muted">{step.text}</p>
			</div>
		{/each}
	</div>

	<div class="mt-6 grid md:grid-cols-2 gap-3">
		<div class="card p-5 flex gap-4">
			<span class="grid place-items-center size-9 shrink-0 rounded-xl bg-accent-dim text-accent"><Icon name="shield" /></span>
			<div>
				<h2 class="font-semibold">Was gesendet wird</h2>
				<p class="mt-1.5 text-sm text-muted">
					Ausgewählte Hardwarefelder, Geräte mit bereinigter Modellkennung, gruppierte Systemereignisse und dein Text.
					Keine Gerätenamen, Seriennummern, Pfade oder IP-Adressen. Nach 7 Tagen wird alles gelöscht.
				</p>
				<a href="/datenschutz" class="mt-2 inline-block text-sm text-accent hover:underline">Datenschutzhinweis lesen</a>
			</div>
		</div>
		<div class="card p-5 flex gap-4">
			<span class="grid place-items-center size-9 shrink-0 rounded-xl bg-warn-dim text-warn"><Icon name="lock" /></span>
			<div>
				<h2 class="font-semibold">Nichts passiert von selbst</h2>
				<p class="mt-1.5 text-sm text-muted">
					DriverPilot führt keine Anweisungen vom Server aus. Du entscheidest bei jedem Schritt selbst, ob und wie du
					ihn umsetzt.
				</p>
			</div>
		</div>
	</div>
</section>
