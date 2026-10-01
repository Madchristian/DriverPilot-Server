<script lang="ts">
	let { label, value, sub = '', tone = 'text-fg' }: { label: string; value: string | number; sub?: string; tone?: string } = $props();
</script>

<div class="card p-4 flex flex-col gap-1 min-w-0">
	<span class="label mb-0">{label}</span>
	<span class="text-2xl font-semibold tabular-nums leading-tight {tone}">{value}</span>
	{#if sub}<span class="text-[11px] text-muted truncate">{sub}</span>{/if}
</div>
