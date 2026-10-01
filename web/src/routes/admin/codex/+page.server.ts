import { adminLoad } from '$lib/server/backend';
import { run } from '$lib/server/actions';
import type { Actions, PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ locals }) => adminLoad(locals.user!, '/codex');

const action = (name: string) => async ({ locals, request }: any) => {
	const form = await request.formData();
	return run(locals.user!, `/codex/${name}`, name === 'import' ? { auth_json: String(form.get('auth_json') ?? '') } : {});
};

export const actions: Actions = {
	login: action('login'),
	cancel: action('cancel'),
	logout: action('logout'),
	import: action('import')
};
