import { redirect } from '@sveltejs/kit';
import { adminLoad } from '$lib/server/backend';
import { run } from '$lib/server/actions';
import type { Actions, PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ locals, params }) => adminLoad(locals.user!, `/cases/${encodeURIComponent(params.id)}`);

function parseContent(form: FormData) {
	try {
		return JSON.parse(String(form.get('content') ?? ''));
	} catch {
		return null;
	}
}

export const actions: Actions = {
	validate: async ({ locals, params, request }) => {
		const content = parseContent(await request.formData());
		return run(locals.user!, `/cases/${params.id}/validate`, { content }).then((r: any) => (r.data ? { ok: true, problems: r.data.problems, hints: r.data.hints } : r));
	},
	draft: async ({ locals, params, request }) => {
		const form = await request.formData();
		return run(locals.user!, `/cases/${params.id}/draft`, { content: parseContent(form), ai_assisted: form.get('ai_assisted') === '1' });
	},
	release: async ({ locals, params, request }) => {
		const form = await request.formData();
		return run(locals.user!, `/cases/${params.id}/release`, { draft_id: String(form.get('draft_id') ?? ''), version: Number(form.get('version')) });
	},
	takeover: async ({ locals, params, request }) => {
		const form = await request.formData();
		return run(locals.user!, `/cases/${params.id}/take-over`, { version: Number(form.get('version')) });
	},
	retry: async ({ locals, params, request }) => {
		const form = await request.formData();
		return run(locals.user!, `/cases/${params.id}/retry`, { version: Number(form.get('version')) });
	},
	delete: async ({ locals, params }) => {
		const result: any = await run(locals.user!, `/cases/${params.id}/delete`, {});
		if (result?.ok) redirect(303, '/admin');
		return result;
	}
};
