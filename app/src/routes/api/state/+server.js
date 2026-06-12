import { json } from '@sveltejs/kit';
import { getValidation, updateValidation, normHash } from '$lib/server/data.js';

const CLASSES = ['npc', 'item', 'building', 'small', 'terrain', 'part', 'unclear'];

// GET /api/state -> { npcOk: {hash:1}, overrides: {hash:cls} }
export async function GET() {
	return json(await getValidation());
}

// POST /api/state
//   { op: { kind: 'npcOk', hash, value: 1|null } }
//   { op: { kind: 'override', hash, value: cls|null } }
//   { merge: { npcOk: {...}, overrides: {...} } }
export async function POST({ request }) {
	let body;
	try {
		body = await request.json();
	} catch {
		return json({ error: 'invalid JSON' }, { status: 400 });
	}

	const state = await updateValidation((st) => {
		if (body.op) {
			const { kind, hash, value } = body.op;
			const h = normHash(hash || '');
			if (kind === 'npcOk') {
				if (value) st.npcOk[h] = 1;
				else delete st.npcOk[h];
			} else if (kind === 'override') {
				if (value && CLASSES.includes(value)) st.overrides[h] = value;
				else delete st.overrides[h];
			}
		}
		if (body.merge) {
			for (const [h, v] of Object.entries(body.merge.npcOk || {})) {
				if (v) st.npcOk[normHash(h)] = 1;
			}
			for (const [h, v] of Object.entries(body.merge.overrides || {})) {
				if (CLASSES.includes(v)) st.overrides[normHash(h)] = v;
			}
		}
	});

	return json({
		ok: true,
		npcOk: Object.keys(state.npcOk).length,
		overrides: Object.keys(state.overrides).length
	});
}
