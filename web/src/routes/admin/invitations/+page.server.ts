import { fail } from '@sveltejs/kit';
import { adminApi, adminLoad, BackendError } from '$lib/server/backend';
import { run } from '$lib/server/actions';
import { cfg } from '$lib/server/config';
import type { Actions, PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ locals }) => adminLoad(locals.user!, '/invitations');

export const actions: Actions = {
	create: async ({ locals, request }) => {
		const form = await request.formData();
		const greeting = String(form.get('greeting') ?? '').trim().slice(0, 40);
		try {
			const created = await adminApi(locals.user!, '/invitations', {
				label: String(form.get('label') ?? ''),
				days: Number(form.get('days') ?? 1),
				max_uses: Number(form.get('max_uses') ?? 1)
			});
			// Code und Name stehen im Fragment: Browser schicken das nie an einen Server.
			const params = new URLSearchParams({ c: created.code });
			if (greeting) params.set('n', greeting);
			const link = `${cfg.publicBaseUrl}/einladung#${params.toString()}`;
			return { ok: true, created: { ...created, link, greeting } };
		} catch (e) {
			if (e instanceof BackendError) return fail(400, { ok: false, error: e.message });
			throw e;
		}
	},
	revoke: async ({ locals, request }) => {
		const form = await request.formData();
		return run(locals.user!, `/invitations/${encodeURIComponent(String(form.get('id')))}/revoke`, {});
	}
};
