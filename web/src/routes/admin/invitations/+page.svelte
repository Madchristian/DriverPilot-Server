<script lang="ts">
	import { enhance } from '$app/forms';
	import Icon from '$lib/components/Icon.svelte';
	import CopyButton from '$lib/components/CopyButton.svelte';
	import Flash from '$lib/components/Flash.svelte';
	import { dateTime } from '$lib/format';
	let { data, form } = $props();
	const created = $derived((form as any)?.created ?? null);
	const message = $derived(
		created
			? `Hi${created.greeting ? ` ${created.greeting}` : ''}! Hier ist dein Zugang zur PC-Hilfe über DriverPilot. Öffne den Link und folge den drei Schritten:\n${created.link}\n\nDer Link gilt ${created.days === 1 ? 'einen Tag' : `${created.days} Tage`}. Bitte nicht weitergeben.`
			: ''
	);
	const canShare = typeof navigator !== 'undefined' && 'share' in navigator;
	function status(inv: any) {
		if (inv.revoked_at) return { label: 'widerrufen', tone: 'text-bad bg-bad-dim' };
		if (inv.expires_at <= data.now) return { label: 'abgelaufen', tone: 'text-muted bg-surface-3' };
		if (inv.uses >= inv.max_uses) return { label: 'verbraucht', tone: 'text-muted bg-surface-3' };
		return { label: 'aktiv', tone: 'text-ok bg-ok-dim' };
	}
</script>

<svelte:head><title>Einladungen · DriverPilot Admin</title></svelte:head>

<h1 class="text-2xl font-semibold tracking-tight mb-1">Einladungen</h1>
<p class="text-sm text-muted mb-6">Erzeuge einen Link und schick nur diesen an deinen Freund. Er führt durch Download, Installation und Koppeln.</p>

<div class="grid xl:grid-cols-[24rem_1fr] gap-6 items-start">
	<form method="POST" action="?/create" use:enhance class="card p-5 space-y-4">
		<div>
			<label class="label" for="greeting">Vorname in der Begrüßung</label>
			<input id="greeting" name="greeting" class="input" maxlength="40" placeholder="z. B. Max (optional)" />
		</div>
		<div>
			<label class="label" for="label">Bezeichnung (nur für dich)</label>
			<input id="label" name="label" class="input" maxlength="80" placeholder="z. B. Max, Gaming-PC" />
		</div>
		<div class="grid grid-cols-2 gap-3">
			<div>
				<label class="label" for="days">Gültig (Tage)</label>
				<input id="days" name="days" type="number" min="1" max="365" value="3" class="input" />
			</div>
			<div>
				<label class="label" for="max_uses">Einlösungen</label>
				<input id="max_uses" name="max_uses" type="number" min="1" max="500" value="1" class="input" />
			</div>
		</div>
		<button class="btn btn-primary w-full"><Icon name="link" />Einladungslink erzeugen</button>
		<p class="text-xs text-dim">Pro Freund reicht eine Einlösung. Für eine Gruppe mehr Einlösungen und längere Gültigkeit wählen.</p>
	</form>

	<div class="space-y-4 min-w-0">
		{#if form?.error}<Flash {form} />{/if}
		{#if created}
			<div class="card p-5 border-accent/40 fade-in">
				<div class="flex items-center gap-2 mb-3">
					<span class="grid place-items-center size-8 rounded-lg bg-accent-dim text-accent"><Icon name="check" /></span>
					<p class="font-semibold">Link für „{created.label}“ ist fertig</p>
				</div>
				<p class="text-sm text-muted mb-3">Der Link wird nur jetzt angezeigt. Schick ihn über einen privaten Kanal (Signal, iMessage, persönlich).</p>
				<code class="block input mono break-all text-accent">{created.link}</code>
				<div class="mt-3 flex flex-wrap gap-2">
					<CopyButton text={created.link} label="Link kopieren" class="btn btn-primary" />
					<CopyButton text={message} label="Nachricht kopieren" class="btn" />
					{#if canShare}
						<button type="button" class="btn" onclick={() => navigator.share({ title: 'DriverPilot-Einladung', text: message })}><Icon name="share" />Teilen</button>
					{/if}
				</div>
				<details class="mt-4">
					<summary class="text-xs text-dim cursor-pointer">Vorschau der Nachricht und Code einzeln</summary>
					<pre class="mt-2 whitespace-pre-wrap text-sm text-muted bg-bg rounded-lg p-3 border border-line">{message}</pre>
					<p class="mt-2 text-xs text-dim">Serveradresse <span class="mono">{created.base_url}</span> · Code <span class="mono">{created.code}</span></p>
				</details>
			</div>
		{:else if form?.message}
			<Flash {form} />
		{/if}

		<div class="card overflow-hidden">
			<div class="overflow-x-auto">
				<table class="table">
					<thead><tr><th>Bezeichnung</th><th>Status</th><th>Einlösungen</th><th>Gültig bis</th><th>Erstellt</th><th></th></tr></thead>
					<tbody>
						{#each data.invitations as inv (inv.id)}
							{@const st = status(inv)}
							<tr>
								<td class="font-medium">{inv.label}<span class="block text-xs text-dim">{inv.created_by}</span></td>
								<td><span class="pill {st.tone}">{st.label}</span></td>
								<td class="tabular-nums">{inv.uses} / {inv.max_uses}</td>
								<td class="text-xs text-muted whitespace-nowrap">{dateTime(inv.expires_at)}</td>
								<td class="text-xs text-muted whitespace-nowrap">{dateTime(inv.created_at)}</td>
								<td class="text-right">
									{#if st.label === 'aktiv'}
										<form method="POST" action="?/revoke" use:enhance><input type="hidden" name="id" value={inv.id} /><button class="btn btn-sm btn-danger">Widerrufen</button></form>
									{/if}
								</td>
							</tr>
						{:else}
							<tr><td colspan="6" class="text-muted">Noch keine Einladungen.</td></tr>
						{/each}
					</tbody>
				</table>
			</div>
		</div>
	</div>
</div>
