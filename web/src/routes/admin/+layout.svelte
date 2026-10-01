<script lang="ts">
	import { page } from '$app/state';
	import Icon from '$lib/components/Icon.svelte';
	let { data, children } = $props();
	let open = $state(false);
	const nav = [
		{ href: '/admin', label: 'Fälle', icon: 'cases', exact: true },
		{ href: '/admin/invitations', label: 'Einladungen', icon: 'invite' },
		{ href: '/admin/clients', label: 'Zugänge', icon: 'clients' },
		{ href: '/admin/codex', label: 'KI (ChatGPT)', icon: 'ai' },
		{ href: '/admin/releases', label: 'Releases', icon: 'releases' },
		{ href: '/admin/audit', label: 'Audit', icon: 'audit' }
	];
	const active = (item: { href: string; exact?: boolean }) =>
		item.exact ? page.url.pathname === item.href || page.url.pathname.startsWith('/admin/cases') : page.url.pathname.startsWith(item.href);
</script>

<div class="min-h-dvh lg:grid lg:grid-cols-[15rem_1fr]">
	<aside class="hidden lg:flex flex-col border-r border-line bg-surface/60 px-3 py-4 sticky top-0 h-dvh">
		<a href="/admin" class="flex items-center gap-2.5 px-2 mb-6">
			<img src="/favicon.svg" alt="" class="size-8" />
			<span class="leading-tight"><span class="font-semibold block">DriverPilot</span><span class="text-[11px] text-dim">Ferndiagnose · Admin</span></span>
		</a>
		<nav class="flex flex-col gap-0.5">
			{#each nav as item}
				<a href={item.href} class="nav-link" aria-current={active(item) ? 'page' : undefined}><Icon name={item.icon} />{item.label}</a>
			{/each}
		</nav>
		<div class="mt-auto px-2 pt-4 border-t border-line text-xs text-dim">
			Angemeldet als <span class="text-muted">{data.user}</span>
			<a href="/" class="block mt-2 hover:text-muted">Öffentliche Seite</a>
		</div>
	</aside>

	<header class="lg:hidden sticky top-0 z-20 flex items-center gap-3 border-b border-line bg-bg/85 backdrop-blur px-4 h-14">
		<button class="btn btn-sm" aria-label="Menü" onclick={() => (open = !open)}><Icon name="menu" /></button>
		<img src="/favicon.svg" alt="" class="size-7" />
		<span class="font-semibold">DriverPilot Admin</span>
	</header>
	{#if open}
		<nav class="lg:hidden border-b border-line bg-surface px-3 py-2 flex flex-col gap-0.5">
			{#each nav as item}
				<a href={item.href} class="nav-link" aria-current={active(item) ? 'page' : undefined} onclick={() => (open = false)}><Icon name={item.icon} />{item.label}</a>
			{/each}
		</nav>
	{/if}

	<main class="min-w-0 px-4 sm:px-6 py-6 max-w-[1400px]">
		{@render children()}
	</main>
</div>
