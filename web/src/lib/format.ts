const TZ = 'Europe/Berlin';

export function dateTime(value: string | null | undefined): string {
	if (!value) return '–';
	const d = new Date(value);
	if (Number.isNaN(d.getTime())) return value;
	return d.toLocaleString('de-DE', { timeZone: TZ, day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' });
}

export function relative(value: string | null | undefined, now: string | number | Date = Date.now()): string {
	if (!value) return '–';
	const then = new Date(value).getTime();
	const ref = new Date(now).getTime();
	if (Number.isNaN(then)) return value;
	const diff = Math.round((then - ref) / 1000);
	const abs = Math.abs(diff);
	const fmt = new Intl.RelativeTimeFormat('de', { numeric: 'auto' });
	if (abs < 60) return fmt.format(diff, 'second');
	if (abs < 3600) return fmt.format(Math.round(diff / 60), 'minute');
	if (abs < 86400) return fmt.format(Math.round(diff / 3600), 'hour');
	return fmt.format(Math.round(diff / 86400), 'day');
}

export function size(bytes: number): string {
	if (bytes >= 1 << 20) return `${(bytes / (1 << 20)).toFixed(1).replace('.', ',')} MB`;
	if (bytes >= 1 << 10) return `${Math.round(bytes / (1 << 10))} KB`;
	return `${bytes} B`;
}

export function short(id: string | null | undefined, n = 8): string {
	return id ? id.slice(0, n) : '–';
}

export const STATUS: Record<string, { label: string; tone: string }> = {
	queued: { label: 'Warteschlange', tone: 'text-blue bg-blue-dim' },
	analyzing: { label: 'KI analysiert', tone: 'text-violet bg-violet-dim' },
	awaiting_review: { label: 'Wartet auf Prüfung', tone: 'text-warn bg-warn-dim' },
	released: { label: 'Freigegeben', tone: 'text-ok bg-ok-dim' },
	analysis_failed: { label: 'Analyse fehlgeschlagen', tone: 'text-bad bg-bad-dim' }
};

export const CATEGORY: Record<string, string> = {
	wow_crash: 'WoW-Absturz',
	pc_freeze: 'PC friert ein',
	graphics_reset: 'Grafikreset',
	performance: 'Leistung',
	network: 'Netzwerk',
	addon_error: 'Addon-Fehler',
	other: 'Sonstiges'
};

export const SEVERITY: Record<string, string> = {
	critical: 'text-bad bg-bad-dim',
	error: 'text-bad bg-bad-dim',
	warning: 'text-warn bg-warn-dim',
	info: 'text-muted bg-surface-3'
};

export const RISK: Record<string, { label: string; tone: string }> = {
	read_only: { label: 'nur lesen', tone: 'text-ok bg-ok-dim' },
	reversible_change: { label: 'rückgängig machbar', tone: 'text-warn bg-warn-dim' },
	expert_only: { label: 'nur für Experten', tone: 'text-bad bg-bad-dim' }
};

export const PRIVILEGES: Record<string, string> = {
	none: 'keine Rechte nötig',
	standard_user: 'normaler Benutzer',
	administrator: 'Administrator'
};

export const OUTCOME: Record<string, string> = {
	improved: 'besser',
	unchanged: 'unverändert',
	worse: 'schlechter',
	not_tried: 'nicht probiert'
};
