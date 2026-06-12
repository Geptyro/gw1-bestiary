// Data layer for the GW1 sprite library admin tool.
// Reads/writes the EXACT files shared with the Python tools — formats must not change.
import fs from 'node:fs';
import fsp from 'node:fs/promises';
import path from 'node:path';

// out/ directory lives next to the app/ directory
function findOut() {
	if (process.env.GW1_OUT) return process.env.GW1_OUT;
	const candidates = [
		path.resolve(process.cwd(), '..', 'out'),
		'/workspace/pro/gw1-bestiary/out'
	];
	for (const c of candidates) {
		if (fs.existsSync(path.join(c, 'classifications.csv'))) return c;
	}
	return candidates[0];
}

export const OUT_DIR = findOut();
export const SCAN_DIR = path.join(OUT_DIR, 'scan');
const CLASSIFICATIONS = path.join(OUT_DIR, 'classifications.csv');
const KNOWN_NAMES = path.join(OUT_DIR, 'known_names.csv');
const VALIDATION = path.join(OUT_DIR, 'validation.json');
const LINKS = path.join(OUT_DIR, 'links.json');

/** Canonical hash form: "0x" + uppercase hex (matches scan filenames). */
export function normHash(h) {
	return '0x' + String(h).trim().replace(/^0x/i, '').toUpperCase();
}

// ---------- mtime-checked in-memory cache ----------
const cache = new Map();
async function cachedParse(file, parse) {
	const st = await fsp.stat(file).catch(() => null);
	if (!st) return parse(null);
	const hit = cache.get(file);
	if (hit && hit.mtime === st.mtimeMs) return hit.value;
	const text = await fsp.readFile(file, 'utf8');
	const value = parse(text);
	cache.set(file, { mtime: st.mtimeMs, value });
	return value;
}

// classifications.csv: hash,cls,source,name,icon,score,verts,parts,ntex,height
export async function getClassifications() {
	return cachedParse(CLASSIFICATIONS, (text) => {
		const meta = {};
		if (!text) return meta;
		for (const line of text.split(/\r?\n/).slice(1)) {
			const p = line.split(',');
			if (p.length < 5 || !p[0]) continue;
			meta[normHash(p[0])] = {
				cls: p[1],
				source: p[2],
				name: p[3] || '',
				icon: p[4] || '',
				score: parseFloat(p[5]) || 0,
				verts: p[6] || '?',
				parts: p[7] || '?',
				ntex: p[8] || '?',
				height: p[9] || '?'
			};
		}
		return meta;
	});
}

// known_names.csv: hash,name,wiki
export async function getKnownNames() {
	return cachedParse(KNOWN_NAMES, (text) => {
		const known = {};
		if (!text) return known;
		for (const line of text.split(/\r?\n/).slice(1)) {
			const p = line.split(',');
			if (p.length < 2 || !p[0]) continue;
			known[normHash(p[0])] = { name: p[1] || '', wiki: (p[2] || '').trim() };
		}
		return known;
	});
}

// scan/ directory listing -> sorted canonical hashes (cached on dir mtime)
let scanCache = { mtime: -1, value: [] };
export async function getModels() {
	const st = await fsp.stat(SCAN_DIR).catch(() => null);
	if (!st) return [];
	if (scanCache.mtime === st.mtimeMs) return scanCache.value;
	const files = await fsp.readdir(SCAN_DIR);
	const models = files
		.filter((f) => /^model_0x[0-9A-Fa-f]+_gwmb\.png$/.test(f))
		.map((f) => normHash(f.slice('model_'.length, -'_gwmb.png'.length)))
		.sort((a, b) => a.localeCompare(b));
	scanCache = { mtime: st.mtimeMs, value: models };
	return models;
}

// ---------- JSON state files (read + atomic write) ----------
async function readJson(file, fallback) {
	try {
		return JSON.parse(await fsp.readFile(file, 'utf8'));
	} catch {
		return fallback;
	}
}

async function writeJsonAtomic(file, obj) {
	const tmp = `${file}.tmp-${process.pid}-${Date.now()}`;
	await fsp.writeFile(tmp, JSON.stringify(obj), 'utf8');
	await fsp.rename(tmp, file);
}

// serialize writers per file so concurrent POSTs cannot interleave
const locks = new Map();
function withLock(key, fn) {
	const prev = locks.get(key) || Promise.resolve();
	const next = prev.then(fn, fn);
	locks.set(
		key,
		next.catch(() => {})
	);
	return next;
}

export async function getValidation() {
	const v = await readJson(VALIDATION, {});
	return { npcOk: v.npcOk || {}, overrides: v.overrides || {} };
}

/** mutate: (state) => void; returns the new state */
export function updateValidation(mutate) {
	return withLock(VALIDATION, async () => {
		const state = await getValidation();
		mutate(state);
		await writeJsonAtomic(VALIDATION, state);
		return state;
	});
}

export async function getLinks() {
	return readJson(LINKS, {});
}

/** Replace the link list for one hash; empty list removes the key. */
export function setLinks(hash, list) {
	return withLock(LINKS, async () => {
		const links = await getLinks();
		const h = normHash(hash);
		if (Array.isArray(list) && list.length > 0) links[h] = list;
		else delete links[h];
		await writeJsonAtomic(LINKS, links);
		return links;
	});
}
