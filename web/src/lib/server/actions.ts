import { fail } from '@sveltejs/kit';
import { adminApi, BackendError } from './backend';

/** Fuehrt einen Admin-API-Aufruf in einer Form-Action aus und liefert {message} oder fail({error}). */
export async function run(actor: string, path: string, body: unknown, extra: Record<string, unknown> = {}) {
	try {
		const data = await adminApi(actor, path, body);
		return { ok: true, message: data.message ?? 'Erledigt.', ...extra, data };
	} catch (e) {
		if (e instanceof BackendError) return fail(e.status >= 500 ? 502 : 400, { ok: false, error: e.message });
		throw e;
	}
}
