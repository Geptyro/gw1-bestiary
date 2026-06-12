<script>
	import favicon from '$lib/assets/favicon.svg';
	import { page } from '$app/state';

	let { children } = $props();
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
	<title>GW1 sprite library</title>
</svelte:head>

<header>
	<b>GW1 sprites</b>
	<nav>
		<a href="/" class:on={page.url.pathname === '/'}>gallery</a>
		<a href="/link" class:on={page.url.pathname === '/link'}>link</a>
	</nav>
</header>

{@render children()}

<style>
	:global(body) {
		background: #26262c;
		color: #ddd;
		font-family: system-ui, sans-serif;
		margin: 0;
	}
	:global(input) {
		background: #333;
		border: 1px solid #555;
		color: #eee;
		padding: 6px 10px;
		border-radius: 6px;
	}
	:global(button) {
		background: #444;
		border: 1px solid #666;
		color: #eee;
		padding: 5px 10px;
		border-radius: 14px;
		cursor: pointer;
		font-size: 12px;
	}
	header {
		position: sticky;
		top: 0;
		background: #1c1c20;
		padding: 8px 12px;
		display: flex;
		gap: 14px;
		align-items: center;
		z-index: 3;
		border-bottom: 1px solid #333;
	}
	nav {
		display: flex;
		gap: 8px;
	}
	nav a {
		color: #8cf;
		text-decoration: none;
		font-size: 13px;
		padding: 3px 10px;
		border-radius: 12px;
		border: 1px solid transparent;
	}
	nav a.on {
		background: #2d6cdf;
		border-color: #5b93f5;
		color: #fff;
	}
</style>
