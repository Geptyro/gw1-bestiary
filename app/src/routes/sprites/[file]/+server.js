import path from 'node:path';
import fsp from 'node:fs/promises';
import { createReadStream } from 'node:fs';
import { Readable } from 'node:stream';
import { error } from '@sveltejs/kit';
import { SCAN_DIR } from '$lib/server/data.js';

// GET /sprites/model_0xHASH_gwmb.png — streams the PNG from out/scan
export async function GET({ params }) {
	const name = params.file;
	if (!/^model_0x[0-9A-Fa-f]+_gwmb\.png$/.test(name)) throw error(404, 'not found');

	const file = path.join(SCAN_DIR, name);
	const st = await fsp.stat(file).catch(() => null);
	if (!st || !st.isFile()) throw error(404, 'not found');

	return new Response(Readable.toWeb(createReadStream(file)), {
		headers: {
			'Content-Type': 'image/png',
			'Content-Length': String(st.size),
			'Cache-Control': 'public, max-age=3600'
		}
	});
}
