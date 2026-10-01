declare global {
	namespace App {
		interface Locals {
			user: string | null;
		}
		interface Error {
			message: string;
		}
	}
}

declare module '*.md?raw' {
	const content: string;
	export default content;
}

export {};
