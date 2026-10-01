import { marked } from 'marked';
import source from '$lib/content/anleitung.md?raw';
import type { PageServerLoad } from './$types';

const slug = (text: string) =>
	text
		.toLowerCase()
		.replace(/<[^>]+>/g, '')
		.replace(/[^a-z0-9äöüß]+/g, '-')
		.replace(/^-|-$/g, '');

// Eigene Datei aus dem Repo, kein Fremdinhalt: HTML-Ausgabe von marked ist hier unbedenklich.
const renderer = new marked.Renderer();
const toc: { id: string; text: string }[] = [];
renderer.heading = ({ text, depth }) => {
	const id = slug(text);
	if (depth === 2) toc.push({ id, text });
	return `<h${depth} id="${id}">${text}</h${depth}>`;
};
renderer.link = ({ href, text }) => {
	const download = href.startsWith('/downloads/') && href.length > '/downloads/'.length;
	return `<a href="${href}"${download ? ' data-sveltekit-reload download' : ''}>${text}</a>`;
};
const html = marked.parse(source, { renderer, async: false }) as string;

export const load: PageServerLoad = () => ({ html, toc });
