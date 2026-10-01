import { adminLoad } from '$lib/server/backend';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ locals }) => adminLoad(locals.user!, '/audit');
