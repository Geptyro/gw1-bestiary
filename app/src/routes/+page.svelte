<script>
	const CLASSES = ['npc', 'item', 'building', 'small', 'terrain', 'part', 'unclear'];
	const CAP = 1500;

	let models = $state([]);
	let meta = $state({});
	let known = $state({});
	let npcOk = $state({});
	let overrides = $state({});
	let loaded = $state(false);

	let q = $state('');
	let filterCls = $state('all');
	let savedMsg = $state('');
	let saveTimer;

	$effect(() => {
		load();
	});

	async function load() {
		const [m, st] = await Promise.all([
			fetch('/api/meta').then((r) => r.json()),
			fetch('/api/state').then((r) => r.json())
		]);
		models = m.models;
		meta = m.meta;
		known = m.known;
		npcOk = st.npcOk || {};
		overrides = st.overrides || {};
		loaded = true;
	}

	function clsOf(h) {
		return overrides[h] || meta[h]?.cls || 'unknown';
	}
	function nameOf(h) {
		return known[h]?.name || meta[h]?.name || '';
	}
	function tooltip(h) {
		const m = meta[h] || {};
		return `${h} — ${m.verts ?? '?'} verts, ${m.parts ?? '?'} parts, ${m.ntex ?? '?'} textures, height ${m.height ?? '?'}, npc-score ${m.score ?? '?'}`;
	}

	let counts = $derived.by(() => {
		const tot = { all: models.length, validated: 0 };
		for (const c of CLASSES) tot[c] = 0;
		for (const h of models) {
			const c = clsOf(h);
			tot[c] = (tot[c] || 0) + 1;
			if (npcOk[h]) tot.validated++;
		}
		return tot;
	});

	let filtered = $derived.by(() => {
		const t = q.trim().toLowerCase();
		return models.filter((h) => {
			if (filterCls === 'validated') {
				if (!npcOk[h]) return false;
			} else if (filterCls !== 'all' && clsOf(h) !== filterCls) return false;
			return !t || h.toLowerCase().includes(t) || nameOf(h).toLowerCase().includes(t);
		});
	});

	let shown = $derived(filtered.slice(0, CAP));

	function flash(msg) {
		savedMsg = msg;
		clearTimeout(saveTimer);
		saveTimer = setTimeout(() => (savedMsg = ''), 1500);
	}

	async function toggleValidated(h) {
		const value = npcOk[h] ? null : 1;
		if (value) npcOk[h] = 1;
		else delete npcOk[h];
		try {
			const r = await fetch('/api/state', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ op: { kind: 'npcOk', hash: h, value } })
			});
			const j = await r.json();
			flash(`saved ✓ (${j.npcOk} validated)`);
		} catch {
			flash('SAVE FAILED — is the server running?');
		}
	}
</script>

<div class="bar">
	<input placeholder="filter hash or name" bind:value={q} />
	<span class="chips">
		{#each ['all', 'validated', ...CLASSES] as c (c)}
			<button class="chip" class:on={filterCls === c} onclick={() => (filterCls = c)}>
				{c}
				{counts[c] || 0}
			</button>
		{/each}
	</span>
	<span class="count">
		{#if loaded}
			{filtered.length} shown{filtered.length > CAP ? ` (capped at ${CAP})` : ''}
		{:else}
			loading…
		{/if}
	</span>
	<span class="saved">{savedMsg}</span>
</div>

<div class="grid">
	{#each shown as h (h)}
		<div
			class="c"
			class:ok={npcOk[h]}
			title={tooltip(h)}
			onclick={() => toggleValidated(h)}
			onkeydown={(e) => e.key === 'Enter' && toggleValidated(h)}
			role="button"
			tabindex="0"
		>
			<span class="tick">✓</span>
			<img class="sprite" loading="lazy" alt={h} src="/sprites/model_{h}_gwmb.png" />
			<div class="k" class:manual={overrides[h]}>{clsOf(h)}{overrides[h] ? ' ✎' : ''}</div>
			<div class="n">{nameOf(h)}</div>
			<div class="h">{h}</div>
		</div>
	{/each}
</div>

<footer>click a card to toggle its validated (real NPC) state — saves to the server instantly</footer>

<style>
	.bar {
		position: sticky;
		top: 41px;
		background: #1c1c20;
		padding: 8px 10px;
		display: flex;
		gap: 10px;
		align-items: center;
		flex-wrap: wrap;
		z-index: 2;
	}
	input {
		width: 220px;
	}
	.chips {
		display: flex;
		gap: 6px;
		flex-wrap: wrap;
	}
	.chip.on {
		background: #2d6cdf;
		border-color: #5b93f5;
	}
	.count {
		font-size: 12px;
		color: #aaa;
	}
	.saved {
		color: #7c7;
		font-size: 12px;
	}
	.grid {
		padding: 10px 10px 40px;
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
		gap: 8px;
	}
	.c {
		background: #3a3a42;
		border-radius: 8px;
		padding: 6px;
		text-align: center;
		position: relative;
		cursor: pointer;
	}
	.c.ok {
		outline: 3px solid #2fbf5f;
	}
	.c .tick {
		display: none;
		position: absolute;
		top: 8px;
		left: 8px;
		font-size: 20px;
		color: #2fbf5f;
		text-shadow: 0 0 4px #000;
	}
	.c.ok .tick {
		display: block;
	}
	img.sprite {
		width: 100%;
		background: #4a4a52;
		border-radius: 4px;
	}
	.k {
		font-size: 10px;
		color: #9ad;
		text-transform: uppercase;
	}
	.k.manual {
		color: #f9a;
	}
	.n {
		font-size: 12px;
		color: #ffd87a;
		min-height: 15px;
	}
	.h {
		font-size: 11px;
		color: #aaa;
	}
	footer {
		position: fixed;
		bottom: 0;
		left: 0;
		right: 0;
		background: #1c1c20;
		padding: 6px 10px;
		font-size: 12px;
		color: #aaa;
	}
</style>
