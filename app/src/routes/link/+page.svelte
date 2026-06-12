<script>
	const WIKI = 'https://wiki.guildwars.com/api.php';

	let meta = $state({});
	let known = $state({});
	let npcOk = $state({});
	let links = $state({});
	let loaded = $state(false);

	let idx = $state(0);
	let q = $state('');
	let results = $state([]);
	let searching = $state(false);
	let savedMsg = $state('');
	let dismissed = $state({});
	let searchEl;
	let saveTimer;
	let debounceTimer;
	let searchToken = 0;

	$effect(() => {
		load();
	});

	async function load() {
		const [m, st, lk] = await Promise.all([
			fetch('/api/meta').then((r) => r.json()),
			fetch('/api/state').then((r) => r.json()),
			fetch('/api/links').then((r) => r.json())
		]);
		meta = m.meta;
		known = m.known;
		npcOk = st.npcOk || {};
		links = lk || {};
		loaded = true;
		searchEl?.focus();
	}

	// validated models, sorted by hash
	let validated = $derived(Object.keys(npcOk).sort((a, b) => a.localeCompare(b)));
	let ci = $derived(Math.min(idx, Math.max(0, validated.length - 1)));
	let cur = $derived(validated.length ? validated[ci] : null);
	let curMeta = $derived(cur ? meta[cur] || {} : {});
	let curLinks = $derived(cur ? links[cur] || [] : []);
	let linkedCount = $derived(validated.filter((h) => (links[h] || []).length > 0).length);

	let suggestion = $derived.by(() => {
		if (!cur || curLinks.length || dismissed[cur]) return null;
		const k = known[cur];
		return k?.name && k?.wiki ? { title: k.name, url: k.wiki } : null;
	});

	function prev() {
		idx = Math.max(0, ci - 1);
		resetSearch();
	}
	function next() {
		idx = Math.min(validated.length - 1, ci + 1);
		resetSearch();
	}
	function resetSearch() {
		q = '';
		results = [];
		searchToken++;
		clearTimeout(debounceTimer);
	}

	function flash(msg) {
		savedMsg = msg;
		clearTimeout(saveTimer);
		saveTimer = setTimeout(() => (savedMsg = ''), 1500);
	}

	async function persist(hash, list) {
		try {
			const r = await fetch('/api/links', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ hash, links: list })
			});
			const j = await r.json();
			flash(`saved ✓ (${j.totalLinked} models linked)`);
		} catch {
			flash('SAVE FAILED — is the server running?');
		}
	}

	function attach(item) {
		if (!cur || !item) return;
		const list = [...(links[cur] || [])];
		if (!list.some((l) => l.url === item.url)) {
			list.push({ title: item.title, url: item.url });
			links[cur] = list;
			persist(cur, list);
		}
	}

	function removeLink(i) {
		if (!cur) return;
		const list = [...(links[cur] || [])];
		list.splice(i, 1);
		links[cur] = list;
		persist(cur, list);
	}

	function onInput() {
		clearTimeout(debounceTimer);
		debounceTimer = setTimeout(doSearch, 250);
	}

	// MediaWiki API, called directly from the browser (origin=* CORS)
	async function doSearch() {
		const term = q.trim();
		const tok = ++searchToken;
		if (!term) {
			results = [];
			return;
		}
		searching = true;
		try {
			const os = await (
				await fetch(
					`${WIKI}?action=opensearch&search=${encodeURIComponent(term)}&limit=8&format=json&origin=*`
				)
			).json();
			if (tok !== searchToken) return;
			const titles = os[1] || [];
			const urls = os[3] || [];
			if (!titles.length) {
				results = [];
				return;
			}
			// one batch call to enrich all titles with thumbnails + canonical urls
			const qr = await (
				await fetch(
					`${WIKI}?action=query&titles=${encodeURIComponent(titles.join('|'))}&prop=pageimages%7Cinfo&piprop=thumbnail&pithumbsize=120&inprop=url&format=json&origin=*`
				)
			).json();
			if (tok !== searchToken) return;
			const pages = Object.values(qr.query?.pages || {});
			const normMap = {};
			for (const n of qr.query?.normalized || []) normMap[n.from] = n.to;
			results = titles.map((t, i) => {
				const p = pages.find((pg) => pg.title === (normMap[t] || t));
				return {
					title: t,
					url:
						p?.fullurl ||
						urls[i] ||
						`https://wiki.guildwars.com/wiki/${encodeURIComponent(t.replaceAll(' ', '_'))}`,
					thumb: p?.thumbnail?.source || null
				};
			});
		} catch {
			if (tok === searchToken) results = [];
		} finally {
			if (tok === searchToken) searching = false;
		}
	}

	function onWindowKey(e) {
		if (e.key === '/' && document.activeElement !== searchEl) {
			e.preventDefault();
			searchEl?.focus();
			return;
		}
		if (document.activeElement === searchEl) return;
		if (e.key === 'ArrowLeft') {
			e.preventDefault();
			prev();
		} else if (e.key === 'ArrowRight') {
			e.preventDefault();
			next();
		}
	}

	function onSearchKey(e) {
		if (e.key === 'Enter' && results.length) {
			attach(results[0]);
			resetSearch();
		} else if (e.key === 'Escape') {
			searchEl?.blur();
		}
	}
</script>

<svelte:window onkeydown={onWindowKey} />

<div class="bar">
	<span class="progress">
		{#if loaded}
			<b>{linkedCount}</b> of <b>{validated.length}</b> linked
		{:else}
			loading…
		{/if}
	</span>
	<span class="pos">{validated.length ? `model ${ci + 1} / ${validated.length}` : ''}</span>
	<span class="saved">{savedMsg}</span>
</div>

{#if !loaded}
	<p class="empty">loading…</p>
{:else if !cur}
	<p class="empty">no validated models yet — validate some NPCs in the <a href="/">gallery</a> first</p>
{:else}
	<div class="panes">
		<div class="left">
			<img class="sprite" alt={cur} src="/sprites/model_{cur}_gwmb.png" />
			<div class="hash">{cur}</div>
			{#if known[cur]?.name || curMeta.name}
				<div class="name">{known[cur]?.name || curMeta.name}</div>
			{/if}
			<div class="stats">
				{curMeta.cls || 'unknown'} — {curMeta.verts ?? '?'} verts, {curMeta.parts ?? '?'} parts,
				{curMeta.ntex ?? '?'} textures, height {curMeta.height ?? '?'}, npc-score {curMeta.score ?? '?'}
			</div>
			<div class="navbtns">
				<button onclick={prev} disabled={ci === 0}>← prev</button>
				<button onclick={next} disabled={ci === validated.length - 1}>next →</button>
			</div>
			<div class="hint">←/→ prev/next when search not focused — / focuses search</div>
		</div>

		<div class="right">
			<div class="chips">
				{#each curLinks as l, i (l.url)}
					<span class="chip linkchip">
						<a href={l.url} target="_blank" rel="noreferrer">{l.title}</a>
						<button class="x" title="remove" onclick={() => removeLink(i)}>×</button>
					</span>
				{/each}
				{#if suggestion}
					<span class="chip suggest">
						<button class="acc" title="attach suggested link" onclick={() => attach(suggestion)}>
							suggested: {suggestion.title} ✓
						</button>
						<button class="x" title="dismiss" onclick={() => (dismissed[cur] = true)}>×</button>
					</span>
				{/if}
				{#if !curLinks.length && !suggestion}
					<span class="nolinks">no wiki links yet</span>
				{/if}
			</div>

			<input
				bind:this={searchEl}
				bind:value={q}
				oninput={onInput}
				onkeydown={onSearchKey}
				placeholder="search wiki.guildwars.com… (Enter attaches first result)"
			/>

			<div class="results">
				{#if searching}
					<div class="status">searching…</div>
				{:else if q.trim() && !results.length}
					<div class="status">no results</div>
				{/if}
				{#each results as r, i (r.url)}
					<button class="result" class:first={i === 0} onclick={() => attach(r)}>
						{#if r.thumb}
							<img class="thumb" alt="" src={r.thumb} />
						{:else}
							<span class="thumb placeholder">?</span>
						{/if}
						<span class="title">{r.title}</span>
					</button>
				{/each}
			</div>
		</div>
	</div>
{/if}

<style>
	.bar {
		position: sticky;
		top: 41px;
		background: #1c1c20;
		padding: 8px 12px;
		display: flex;
		gap: 16px;
		align-items: center;
		z-index: 2;
		font-size: 13px;
	}
	.progress b {
		color: #ffd87a;
	}
	.pos {
		color: #aaa;
		font-size: 12px;
	}
	.saved {
		color: #7c7;
		font-size: 12px;
	}
	.empty {
		padding: 30px;
		color: #aaa;
	}
	.empty a {
		color: #8cf;
	}
	.panes {
		display: flex;
		gap: 20px;
		padding: 16px;
		align-items: flex-start;
	}
	.left {
		flex: none;
		width: 540px;
		background: #3a3a42;
		border-radius: 10px;
		padding: 14px;
		text-align: center;
	}
	img.sprite {
		width: 512px;
		max-width: 100%;
		image-rendering: auto;
		background: #4a4a52;
		border-radius: 6px;
	}
	.hash {
		font-size: 14px;
		color: #aaa;
		margin-top: 8px;
	}
	.name {
		font-size: 15px;
		color: #ffd87a;
		margin-top: 2px;
	}
	.stats {
		font-size: 12px;
		color: #9ad;
		margin-top: 6px;
	}
	.navbtns {
		display: flex;
		gap: 10px;
		justify-content: center;
		margin-top: 12px;
	}
	.navbtns button {
		font-size: 14px;
		padding: 6px 16px;
	}
	.navbtns button:disabled {
		opacity: 0.4;
		cursor: default;
	}
	.hint {
		font-size: 11px;
		color: #777;
		margin-top: 10px;
	}
	.right {
		flex: 1;
		min-width: 0;
	}
	.chips {
		display: flex;
		gap: 8px;
		flex-wrap: wrap;
		margin-bottom: 10px;
		min-height: 30px;
		align-items: center;
	}
	.chip {
		display: inline-flex;
		align-items: center;
		gap: 4px;
		background: #444;
		border: 1px solid #666;
		border-radius: 14px;
		padding: 3px 6px 3px 12px;
		font-size: 13px;
	}
	.chip.linkchip {
		background: #1d4a2c;
		border-color: #2fbf5f;
	}
	.chip.linkchip a {
		color: #ffd87a;
		text-decoration: none;
	}
	.chip.suggest {
		background: transparent;
		border: 1px dashed #888;
	}
	.chip .acc {
		background: none;
		border: none;
		color: #9ad;
		padding: 2px 4px;
		font-size: 13px;
	}
	.chip .x {
		background: none;
		border: none;
		color: #f88;
		font-size: 15px;
		padding: 0 4px;
		line-height: 1;
	}
	.nolinks {
		color: #777;
		font-size: 12px;
	}
	input {
		width: 100%;
		max-width: 480px;
		box-sizing: border-box;
		font-size: 14px;
	}
	.results {
		margin-top: 10px;
		display: flex;
		flex-direction: column;
		gap: 6px;
		max-width: 480px;
	}
	.status {
		color: #888;
		font-size: 12px;
		padding: 4px 2px;
	}
	.result {
		display: flex;
		align-items: center;
		gap: 10px;
		background: #3a3a42;
		border: 1px solid #555;
		border-radius: 8px;
		padding: 6px 10px;
		text-align: left;
		font-size: 14px;
		color: #eee;
	}
	.result.first {
		border-color: #5b93f5;
	}
	.result:hover {
		background: #44444e;
	}
	.thumb {
		width: 48px;
		height: 48px;
		object-fit: cover;
		border-radius: 6px;
		background: #4a4a52;
		flex: none;
	}
	.thumb.placeholder {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		color: #777;
		font-size: 20px;
	}
	.title {
		color: #ffd87a;
	}
</style>
