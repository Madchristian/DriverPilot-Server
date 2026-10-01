<script lang="ts">
	let { form }: { form: { ok?: boolean; message?: string; error?: string } | null | undefined } = $props();
</script>

{#if form?.error}
	<div class="fade-in rounded-xl border border-bad/30 bg-bad-dim px-4 py-3 text-sm text-bad" role="alert">{form.error}</div>
{:else if form?.message}
	<div class="fade-in rounded-xl border border-ok/30 bg-ok-dim px-4 py-3 text-sm text-ok" role="status">{form.message}</div>
{/if}
