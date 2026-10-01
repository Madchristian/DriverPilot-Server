import { publicApi } from '$lib/server/backend';
import { cfg } from '$lib/server/config';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async () => {
	let setup: { name: string; version: string | null; size: number } | null = null;
	try {
		const { files } = await publicApi<{ files: { name: string; kind: string; version: string | null; size: number }[] }>('/downloads');
		setup = files.find((f) => f.kind === 'setup') ?? null;
	} catch {
		setup = null;
	}
	return { setup, serverUrl: cfg.publicBaseUrl };
};
