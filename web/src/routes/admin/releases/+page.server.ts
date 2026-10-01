import { adminLoad } from '$lib/server/backend';
import { run } from '$lib/server/actions';
import type { Actions, PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ locals }) => adminLoad(locals.user!, '/releases');

export const actions: Actions = {
	fetch: async ({ locals, request }) => {
		const form = await request.formData();
		return run(locals.user!, '/releases/fetch', { tag: String(form.get('tag') ?? '').trim() });
	}
};
