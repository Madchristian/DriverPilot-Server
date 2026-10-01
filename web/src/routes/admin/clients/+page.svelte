<script lang="ts">
	import { enhance } from '$app/forms';
	import Flash from '$lib/components/Flash.svelte';
	import { dateTime, short } from '$lib/format';
	let { data, form } = $props();
</script>

<svelte:head><title>Zugänge · DriverPilot Admin</title></svelte:head>

<h1 class="text-2xl font-semibold tracking-tight mb-1">Zugänge</h1>
<p class="text-sm text-muted mb-6">Jede eingelöste Einladung ist ein eigener Zugang für 30 Tage. Ein Widerruf wirkt beim nächsten Request, auch für bestehende Fälle.</p>
<div class="mb-4"><Flash {form} /></div>

<div class="card overflow-hidden">
	<div class="overflow-x-auto">
		<table class="table">
			<thead><tr><th>Zugang</th><th>Status</th><th>Fälle</th><th>Gültig bis</th><th>Erstellt</th><th></th></tr></thead>
			<tbody>
				{#each data.clients as cl (cl.id)}
					{@const active = !cl.revoked_at && cl.expires_at > data.now}
					<tr>
						<td class="font-medium">{cl.label}<span class="block mono text-dim">{short(cl.id)}</span></td>
						<td>
							{#if cl.revoked_at}<span class="pill text-bad bg-bad-dim">widerrufen</span>
							{:else if !active}<span class="pill text-muted bg-surface-3">abgelaufen</span>
							{:else}<span class="pill text-ok bg-ok-dim">aktiv</span>{/if}
						</td>
						<td class="tabular-nums">{cl.case_count}</td>
						<td class="text-xs text-muted whitespace-nowrap">{dateTime(cl.expires_at)}</td>
						<td class="text-xs text-muted whitespace-nowrap">{dateTime(cl.created_at)}</td>
						<td class="text-right">
							{#if active}
								<form method="POST" action="?/revoke" use:enhance={({ cancel }) => { if (!confirm(`Zugang „${cl.label}“ widerrufen?`)) cancel(); }}>
									<input type="hidden" name="id" value={cl.id} /><button class="btn btn-sm btn-danger">Widerrufen</button>
								</form>
							{/if}
						</td>
					</tr>
				{:else}
					<tr><td colspan="6" class="text-muted">Noch keine Zugänge.</td></tr>
				{/each}
			</tbody>
		</table>
	</div>
</div>
