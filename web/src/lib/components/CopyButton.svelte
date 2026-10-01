<script lang="ts">
	import Icon from './Icon.svelte';
	let { text, label = 'Kopieren', class: cls = 'btn btn-sm' }: { text: string; label?: string; class?: string } = $props();
	let done = $state(false);

	async function copy() {
		try {
			await navigator.clipboard.writeText(text);
		} catch {
			const area = document.createElement('textarea');
			area.value = text;
			document.body.appendChild(area);
			area.select();
			document.execCommand('copy');
			area.remove();
		}
		done = true;
		setTimeout(() => (done = false), 1600);
	}
</script>

<button type="button" class={cls} onclick={copy}>
	<Icon name={done ? 'check' : 'copy'} class="size-3.5" />{done ? 'Kopiert' : label}
</button>
