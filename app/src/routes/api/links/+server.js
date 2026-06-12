import { json } from '@sveltejs/kit';
import { getLinks, setLinks, normHash } from '$lib/server/data.js';

// GET /api/links -> { "0xHASH": [{title,url}, ...], ... }
export async function GET() {
	return json(await getLinks());
}

// POST /api/links { hash, links: [{title,url}, ...] }
// Replaces the full link list for that hash (empty list removes the entry).
export async function POST({ request }) {
	let body;
	try {
		body = await request.json();
	} catch {
		return json({ error: 'invalid JSON' }, { status: 400 });
	}
	if (!body.hash || !Array.isArray(body.links)) {
		return json({ error: 'expected { hash, links: [] }' }, { status: 400 });
	}
	const clean = body.links
		.filter((l) => l && typeof l.title === 'string' && typeof l.url === 'string')
		.map((l) => ({ title: l.title, url: l.url }));

	const all = await setLinks(body.hash, clean);
	return json({
		ok: true,
		hash: normHash(body.hash),
		links: all[normHash(body.hash)] || [],
		totalLinked: Object.keys(all).length
	});
}
