<script lang="ts">
	import { page } from '$app/state';
</script>

<svelte:head><title>{page.status} · DriverPilot</title></svelte:head>

<main class="min-h-dvh grid place-items-center px-4">
	<div class="card p-8 max-w-md text-center fade-in">
		<img src="/favicon.svg" alt="" class="size-14 mx-auto mb-4" />
		<p class="text-5xl font-semibold text-accent tabular-nums">{page.status}</p>
		<p class="mt-3 text-muted">{page.error?.message ?? 'Unbekannter Fehler'}</p>
		<a href="/" class="btn mt-6">Zur Startseite</a>
	</div>
</main>
