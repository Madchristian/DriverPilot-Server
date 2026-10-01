<script lang="ts">
	import { page } from '$app/state';
	let { children } = $props();
	const links = [
		{ href: '/anleitung', label: 'Anleitung' },
		{ href: '/downloads', label: 'Downloads' },
		{ href: '/datenschutz', label: 'Datenschutz' }
	];
</script>

<div class="min-h-dvh flex flex-col">
	<header class="sticky top-0 z-20 border-b border-line bg-bg/80 backdrop-blur">
		<div class="mx-auto max-w-5xl px-4 h-14 flex items-center gap-3 sm:gap-6">
			<a href="/" class="flex items-center gap-2.5 font-semibold tracking-tight shrink-0">
				<img src="/favicon.svg" alt="" class="size-7" />
				<span class="hidden sm:inline">DriverPilot</span>
			</a>
			<nav class="ml-auto flex items-center gap-0.5 sm:gap-1 text-sm">
				{#each links as link}
					<a
						href={link.href}
						class="rounded-lg px-2 sm:px-3 py-1.5 text-muted hover:text-fg hover:bg-surface-2 transition-colors"
						class:!text-accent={page.url.pathname.startsWith(link.href)}
						aria-current={page.url.pathname.startsWith(link.href) ? 'page' : undefined}>{link.label}</a
					>
				{/each}
			</nav>
		</div>
	</header>

	<main class="flex-1">
		{@render children()}
	</main>

	<footer class="border-t border-line">
		<div class="mx-auto max-w-5xl px-4 py-6 text-xs text-dim flex flex-wrap gap-x-6 gap-y-2">
			<span>Privater Dienst von Christian Strube für Freunde. Keine öffentliche Registrierung.</span>
			<a href="https://github.com/Madchristian/DriverPilot-Server" class="hover:text-muted">Quellcode (MIT)</a>
		</div>
	</footer>
</div>
