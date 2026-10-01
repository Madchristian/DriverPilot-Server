import { redirect, type Handle } from '@sveltejs/kit';
import { cfg } from '$lib/server/config';
import { adminUser } from '$lib/server/identity';

function requestHost(request: Request, url: URL): string {
	return (request.headers.get('x-forwarded-host') ?? url.host).split(',')[0].trim().toLowerCase();
}

export const handle: Handle = async ({ event, resolve }) => {
	const path = event.url.pathname;
	const isAdmin = path === '/admin' || path.startsWith('/admin/');
	event.locals.user = null;

	if (cfg.adminHosts.includes(requestHost(event.request, event.url)) && path === '/') {
		redirect(303, '/admin');
	}

	if (isAdmin) {
		const user = adminUser(event);
		if (!user) {
			return new Response('Zugriff verweigert.', {
				status: 403,
				headers: { 'content-type': 'text/plain; charset=utf-8', 'cache-control': 'no-store' }
			});
		}
		event.locals.user = user;
	}

	const response = await resolve(event);
	response.headers.set('X-Content-Type-Options', 'nosniff');
	response.headers.set('Referrer-Policy', 'same-origin');
	response.headers.set('X-Robots-Tag', 'noindex, nofollow');
	response.headers.set('Permissions-Policy', 'camera=(), microphone=(), geolocation=()');
	if (isAdmin || path.startsWith('/einladung')) response.headers.set('Cache-Control', 'no-store');
	return response;
};
