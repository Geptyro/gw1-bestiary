import { json } from '@sveltejs/kit';
import { getClassifications, getKnownNames, getModels } from '$lib/server/data.js';

// GET /api/meta -> { models: [hash...], meta: {hash:{...}}, known: {hash:{name,wiki}} }
export async function GET() {
	const [models, meta, known] = await Promise.all([
		getModels(),
		getClassifications(),
		getKnownNames()
	]);
	return json({ models, meta, known });
}
