import { adminLoad } from '$lib/server/backend';
import { run } from '$lib/server/actions';
import type { Actions, PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ locals }) => adminLoad(locals.user!, '/clients');

export const actions: Actions = {
	revoke: async ({ locals, request }) => {
		const form = await request.formData();
		return run(locals.user!, `/clients/${encodeURIComponent(String(form.get('id')))}/revoke`, {});
	}
};
