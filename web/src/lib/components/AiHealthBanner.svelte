<script lang="ts">
	import Icon from '$lib/components/Icon.svelte';
	type AiHealth = { offered: boolean; needs_login: boolean; last_error: string | null };
	let { ai, failedRun = false }: { ai: AiHealth | undefined; failedRun?: boolean } = $props();
	const show = $derived(!!ai && (ai.needs_login || (failedRun && !ai.offered)));
</script>

{#if show && ai}
	<div class="card mb-4 flex flex-wrap items-center gap-3 border-bad/30 bg-bad-dim px-4 py-3" role="alert">
		<div class="min-w-0 flex-1 text-sm">
			<p class="font-semibold text-bad">
				{ai.needs_login ? 'ChatGPT-Anmeldung abgelaufen – KI-Entwürfe sind aus.' : 'KI-Anbieter nicht verfügbar.'}
			</p>
			<p class="text-muted">
				Neue Fälle landen bis zur erneuten Anmeldung direkt bei dir zur manuellen Prüfung.
				{#if failedRun}Danach kannst du hier einen KI-Neuversuch starten.{/if}
			</p>
			{#if ai.last_error}<p class="mt-1 text-xs mono text-dim">{ai.last_error}</p>{/if}
		</div>
		<a href="/admin/codex" class="btn btn-primary"><Icon name="ai" />Neu anmelden</a>
	</div>
{/if}
