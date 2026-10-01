import type { RequestEvent } from '@sveltejs/kit';
import { cfg } from './config';

const USER_RE = /^[A-Za-z0-9@._+-]{1,80}$/;

function ipv4ToInt(ip: string): number | null {
	const parts = ip.split('.');
	if (parts.length !== 4) return null;
	let value = 0;
	for (const part of parts) {
		if (!/^\d{1,3}$/.test(part)) return null;
		const n = Number(part);
		if (n > 255) return null;
		value = value * 256 + n;
	}
	return value;
}

export function normalizeIp(address: string): string {
	return address.replace(/^::ffff:/i, '').trim().toLowerCase();
}

export function ipAllowed(address: string, allowed: string[]): boolean {
	const ip = normalizeIp(address);
	const value = ipv4ToInt(ip);
	for (const entry of allowed) {
		if (!entry.includes('/')) {
			if (entry === ip) return true;
			continue;
		}
		const [base, bitsText] = entry.split('/');
		const baseValue = ipv4ToInt(base);
		const bits = Number(bitsText);
		if (value === null || baseValue === null || !(bits >= 0 && bits <= 32)) continue;
		const mask = bits === 0 ? 0 : (0xffffffff << (32 - bits)) >>> 0;
		if (((value & mask) >>> 0) === ((baseValue & mask) >>> 0)) return true;
	}
	return false;
}

/**
 * Admin-Identitaet: nur wenn der Request direkt vom konfigurierten Pi-Traefik kommt und
 * Authentik einen Benutzer der Admin-Gruppe meldet. Sonst null.
 */
export function adminUser(event: RequestEvent): string | null {
	let peer = '';
	try {
		peer = event.getClientAddress();
	} catch {
		return null;
	}
	if (cfg.adminTrustedProxies.length === 0) {
		return cfg.devUser && USER_RE.test(cfg.devUser) ? cfg.devUser : null;
	}
	if (!ipAllowed(peer, cfg.adminTrustedProxies)) return null;
	const user = (event.request.headers.get('x-authentik-username') ?? '').trim();
	const groups = (event.request.headers.get('x-authentik-groups') ?? '').split('|').map((g) => g.trim());
	if (!USER_RE.test(user) || !groups.includes(cfg.adminGroup)) return null;
	return user;
}
