<script lang="ts">
	import { STATUS } from '$lib/format';
	let { status, reason = null }: { status: string; reason?: string | null } = $props();
	const info = $derived(STATUS[status] ?? { label: status, tone: 'text-muted bg-surface-3' });
</script>

<span class="pill {info.tone}" title={reason ?? undefined}>
	<span class="size-1.5 rounded-full bg-current"></span>{info.label}{#if reason}<span class="font-normal opacity-80">· {reason}</span>{/if}
</span>
