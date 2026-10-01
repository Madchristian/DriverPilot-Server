import { publicApi } from '$lib/server/backend';
import type { PageServerLoad } from './$types';

export type FileEntry = { name: string; size: number; sha256: string; kind: string; description: string; version: string | null; mtime: number };

export const load: PageServerLoad = async ({ setHeaders }) => {
	const { files } = await publicApi<{ files: FileEntry[] }>('/downloads');
	setHeaders({ 'cache-control': 'public, max-age=60' });
	return { files };
};
