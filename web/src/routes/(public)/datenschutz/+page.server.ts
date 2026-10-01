import { publicApi } from '$lib/server/backend';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async () => {
	const notice = await publicApi<{ version: string; text: string }>('/privacy');
	const [title, ...paragraphs] = notice.text.split(/\n\s*\n/).map((p) => p.trim()).filter(Boolean);
	return { version: notice.version, title, paragraphs };
};
