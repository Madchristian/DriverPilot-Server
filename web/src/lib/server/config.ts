import { env } from '$env/dynamic/private';

function list(value: string | undefined): string[] {
	return (value ?? '')
		.split(',')
		.map((item) => item.trim().toLowerCase())
		.filter(Boolean);
}

/** Laufzeitkonfiguration aus der Umgebung (siehe compose.yml und .env.example). */
export const cfg = {
	/** Python-API (Vertrag, Downloads, oeffentliche Daten) im Docker-Netz. */
	apiUrl: (env.DP_API_URL ?? 'http://127.0.0.1:8140').replace(/\/$/, ''),
	/** Interne Admin-JSON-API im Docker-Netz. */
	adminApiUrl: (env.DP_ADMIN_API_URL ?? 'http://127.0.0.1:8141').replace(/\/$/, ''),
	adminApiToken: env.DP_ADMIN_API_TOKEN ?? '',
	/** Hostnamen, unter denen die Admin-Ansicht laeuft (Wurzel leitet auf /admin). */
	adminHosts: list(env.ADMIN_HOSTS),
	/** Proxys, deren Authentik-Header gelten (IPv4 oder IPv4/CIDR). */
	adminTrustedProxies: list(env.ADMIN_TRUSTED_PROXIES),
	adminGroup: env.ADMIN_GROUP ?? 'Homelab-Admins',
	/** Nur lokale Entwicklung: Admin ohne Proxy, wenn keine Proxys konfiguriert sind. */
	devUser: env.ADMIN_DEV_USER ?? '',
	publicBaseUrl: (env.DP_PUBLIC_BASE_URL ?? 'https://driverpilot.cstrube.de').replace(/\/$/, '')
};
