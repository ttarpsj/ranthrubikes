<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <meta name="description" content="Shop the Ran Thru Bikes collection.">
    <title>Shop — Ran Thru Bikes</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=DM+Mono&family=Manrope:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    @vite(['resources/css/app.css','resources/js/app.js','resources/js/shop.js'])
</head>
<body class="shop-page">
<div class="announcement">INDEPENDENT CYCLING. SELECTED WITH PURPOSE.</div>
<header id="top" class="shop-header">
    <div class="nav-brand"><button class="nav-toggle" data-menu aria-label="Open menu" aria-expanded="false"><span></span><span></span></button><a href="../" class="logo">RAN <b>THRU</b></a></div>
    <nav aria-label="Primary navigation"><a href="../#bikes">BIKES</a><a href="../#frames">FRAMESETS</a><a href="../#components">COMPONENTS</a><a href="../#equipment">EQUIPMENT</a><a href="../#builds">CUSTOM BUILDS</a><a href="../#workshop">WORKSHOP</a></nav>
    <div class="nav-actions"><button class="search-button" data-search aria-label="Search"><span></span></button></div>
</header>
<div class="nav-scrim" data-navscrim></div>
<aside class="mobile-nav" data-mobile aria-hidden="true" aria-label="Site navigation">
    <div class="drawer-head"><button class="drawer-close" data-menuclose aria-label="Close menu">×</button><a href="../" class="drawer-logo">RAN <b>THRU</b></a></div>
    <nav class="drawer-primary"><a href="?category=new-arrivals">New arrivals <span>→</span></a><a href="?category=ran-thru-collection">Ran Thru Collection <span>→</span></a><a href="?category=clothing">Clothing <span>→</span></a><a href="?category=equipment">Equipment <span>→</span></a><a href="?category=components">Components <span>→</span></a><a href="?category=bikes-frames">Bikes &amp; frames <span>→</span></a><a href="?category=brands">Brands <span>→</span></a><a href="?category=sale">Sale <span>→</span></a></nav>
    <nav class="drawer-secondary"><a href="../#about">Ran Thru app</a><a href="../#builds">Bike program</a><a href="../#workshop">Workshops</a><a href="../#about">Second life</a><a href="../#contact">Contact</a><a href="?">Account</a></nav>
</aside>
<div class="searchbox" data-searchbox><button data-close>×</button><label>SEARCH THE COLLECTION<input data-query placeholder="Search products"></label><div data-results></div></div>

<main id="shop" data-shop-root aria-live="polite">
    <section class="shop-hero" data-shop-hero><div class="shop-hero-media" data-hero-media></div><div class="shop-hero-copy"><p>RAN THRU / STORE</p><h1>SHOP</h1></div></section>
    <section class="shop-categories" aria-label="Shop categories"><div class="category-track" data-category-track></div></section>
    <section class="shop-results" data-shop-results>
        <div class="shop-results-head"><div><p class="eyebrow">CATALOG</p><h2 data-results-title>All products</h2></div><div class="shop-results-controls"><button data-filter-open>Filters</button><label>Sort by <select data-sort><option value="featured">Featured</option><option value="newest">Newest</option><option value="price-asc">Price: Low to High</option><option value="price-desc">Price: High to Low</option><option value="name">Name: A to Z</option></select></label><span data-result-count></span></div></div><div class="active-filters" data-active-filters></div>
        <div class="shop-layout">
            <aside class="catalog-filters" data-filter-panel><div class="filter-panel-head"><strong>FILTERS</strong><button data-filter-close aria-label="Close filters">×</button></div><div data-filter-groups></div><button class="clear-filters" data-clear-filters>Clear filters</button></aside>
            <div><div class="catalog-state" data-catalog-state>Loading collection…</div><div class="catalog-grid" data-product-grid></div><button class="load-more" data-load-more hidden>Load more</button></div>
        </div>
    </section>
</main>
@include('components.footer')
<script type="application/json" id="shop-config">@json(config('shop'))</script>
</body>
</html>
