import { error } from '@sveltejs/kit';
import { cfg } from './config';

export class BackendError extends Error {
	constructor(
		public status: number,
		message: string
	) {
		super(message);
	}
}

async function parse(res: Response): Promise<any> {
	const text = await res.text();
	try {
		return text ? JSON.parse(text) : {};
	} catch {
		return { error: `Ungültige Antwort (${res.status})` };
	}
}

/** Aufruf der internen Admin-API mit gemeinsamem Token und dem Authentik-Benutzer als Akteur. */
export async function adminApi<T = any>(actor: string, path: string, body?: unknown): Promise<T> {
	let res: Response;
	try {
		res = await fetch(`${cfg.adminApiUrl}/admin-api${path}`, {
			method: body === undefined ? 'GET' : 'POST',
			headers: {
				Authorization: `Bearer ${cfg.adminApiToken}`,
				'X-DP-Actor': actor,
				'Content-Type': 'application/json',
				Accept: 'application/json'
			},
			body: body === undefined ? undefined : JSON.stringify(body),
			signal: AbortSignal.timeout(30_000)
		});
	} catch {
		throw new BackendError(503, 'Server nicht erreichbar.');
	}
	const data = await parse(res);
	if (!res.ok) throw new BackendError(res.status, data.error ?? `Fehler ${res.status}`);
	return data as T;
}

/** Fuer load-Funktionen: Backend-Fehler als SvelteKit-Fehlerseite. */
export async function adminLoad<T = any>(actor: string, path: string): Promise<T> {
	try {
		return await adminApi<T>(actor, path);
	} catch (e) {
		if (e instanceof BackendError) error(e.status === 401 ? 502 : e.status, e.status === 401 ? 'Admin-API lehnt ab (Token prüfen).' : e.message);
		throw e;
	}
}

/** Oeffentliche Daten der Python-API (Downloads, Datenschutzhinweis). */
export async function publicApi<T = any>(path: string): Promise<T> {
	try {
		const res = await fetch(`${cfg.apiUrl}/public-api${path}`, { signal: AbortSignal.timeout(15_000) });
		if (!res.ok) throw new Error(String(res.status));
		return (await res.json()) as T;
	} catch {
		error(503, 'Der Server ist gerade nicht erreichbar. Bitte später erneut versuchen.');
	}
}
