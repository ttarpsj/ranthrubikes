const shopIndex = location.pathname.indexOf('/shop');
const base = shopIndex >= 0 ? `${location.pathname.slice(0, shopIndex)}/`.replace(/\/+/g, '/') : '/';
const root = document.querySelector('[data-shop-root]');
const grid = document.querySelector('[data-product-grid]');
const catalogState = document.querySelector('[data-catalog-state]');
const count = document.querySelector('[data-result-count]');
const title = document.querySelector('[data-results-title]');
const filterGroups = document.querySelector('[data-filter-groups]');
const filterPanel = document.querySelector('[data-filter-panel]');
const loadMore = document.querySelector('[data-load-more]');
const activeFilters = document.querySelector('[data-active-filters]');
const pageSize = 12;
let products = [];
let taxonomy = null;
let visibleCount = pageSize;

const safe = value => String(value ?? '').replace(/[&<>"']/g, character => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[character]));
const money = cents => new Intl.NumberFormat('en-US', {style:'currency', currency:'USD'}).format((Number(cents) || 0) / 100);
const normalized = value => String(value ?? '').trim().toLowerCase();
const assetUrl = value => {
    if (!value) return '';
    if (/^(https?:|data:|blob:)/i.test(value)) return value;
    return `${base.replace(/\/$/, '')}/${value.replace(/^\//, '')}`;
};
const unique = values => [...new Set(values.filter(Boolean).map(value => String(value).trim()).filter(Boolean))].sort((a,b) => a.localeCompare(b));
const currentPrice = product => product.is_sale && Number(product.sale_price_cents) >= 0 ? Number(product.sale_price_cents) : Number(product.price_cents) || 0;
const selected = (params, key) => (params.get(key) || '').split(',').filter(Boolean);
const productHref = slug => `?product=${encodeURIComponent(slug)}`;

function config() {
    try { return JSON.parse(document.querySelector('#shop-config')?.textContent || '{}'); }
    catch { return {}; }
}

function initHero() {
    const settings = config();
    const media = document.querySelector('[data-hero-media]');
    if (!media) return;
    if (settings.hero_video) {
        const video = document.createElement('video');
        Object.assign(video, {muted:true, autoplay:true, loop:true, playsInline:true});
        video.src = assetUrl(settings.hero_video);
        video.addEventListener('error', () => video.remove());
        media.append(video);
    } else if (settings.hero_image) {
        const image = new Image();
        image.alt = '';
        image.src = assetUrl(settings.hero_image);
        image.addEventListener('error', () => image.remove());
        media.append(image);
    }
}

const topCategories = () => taxonomy?.top_level || [];
const topCategory = id => topCategories().find(item => item.id === id);
const clothingBranch = product => {
    const subtype = product.subtype_id;
    if ((taxonomy?.clothing?.lifestyle || []).some(item => item.id === subtype)) return 'lifestyle';
    if ((taxonomy?.clothing?.accessories || []).some(item => item.id === subtype)) return 'accessories';
    return null;
};
const topMatch = (product, id) => {
    const item = topCategory(id);
    if (!item) return true;
    if (item.kind === 'tag') return (product.tags || []).includes(id);
    if (item.kind === 'sale') return product.is_sale === true && Number(product.sale_price_cents) < Number(product.price_cents);
    if (item.kind === 'brand') return Boolean(product.brand);
    return product.category_id === id;
};

function renderCategories() {
    const settings = config();
    const track = document.querySelector('[data-category-track]');
    const active = new URLSearchParams(location.search).get('category') || '';
    track.innerHTML = topCategories().map(item => {
        const image = settings.category_images?.[item.id];
        const available = products.some(product => topMatch(product,item.id));
        return `<button class="category-tile${active===item.id?' active':''}${available?'':' unavailable'}" data-category="${item.id}" aria-disabled="${available?'false':'true'}"><span class="category-image">${image?`<img src="${safe(assetUrl(image))}" alt="" loading="lazy">`:''}</span><b>${safe(item.label)}</b></button>`;
    }).join('');
    track.querySelectorAll('img').forEach(image => image.addEventListener('error', () => image.remove()));
    track.querySelectorAll('[data-category]').forEach(button => button.addEventListener('click', () => {
        const params = new URLSearchParams(location.search);
        params.delete('product');
        if (params.get('category') === button.dataset.category) {
            params.delete('category');
            if (topCategory(button.dataset.category)?.kind === 'category') { params.delete('branch'); params.delete('subtype'); }
        } else {
            params.set('category', button.dataset.category);
            if (topCategory(button.dataset.category)?.kind === 'category') {
                params.delete('catalog_category');
                if (button.dataset.category !== 'clothing') { params.delete('branch'); params.delete('subtype'); }
            }
        }
        navigate(params);
    }));
}

function filterData() {
    const categories = topCategories().filter(item => item.kind === 'category').map(item => ({id:item.id,label:item.label}));
    const brands = unique(products.map(product => product.brand));
    const sizes = unique(products.flatMap(product => product.variants || []).map(variant => variant.size));
    return {categories, brands, sizes};
}

function checkboxGroup(label, key, values, params, availability=() => true) {
    if (!values.length) return '';
    const chosen = selected(params, key);
    return `<fieldset class="filter-group"><legend>${label}<span>⌄</span></legend><div>${values.map(item => {const value=typeof item==='string'?item:item.id,labelText=typeof item==='string'?item:item.label,enabled=availability(value)||chosen.includes(value);return `<label class="${enabled?'':'disabled'}"><input type="checkbox" data-filter="${key}" value="${safe(value)}" ${chosen.includes(value)?'checked':''} ${enabled?'':'disabled'}><span>${safe(labelText)}</span></label>`}).join('')}</div></fieldset>`;
}

function clothingFilters(params) {
    const activeCategories = selected(params,'catalog_category');
    if (params.get('category') !== 'clothing' && !activeCategories.includes('clothing')) return '';
    const branches = [
        {id:'men',label:'Men'}, {id:'women',label:'Women'},
        {id:'lifestyle',label:'Lifestyle'}, {id:'accessories',label:'Accessories'},
    ];
    const chosen = selected(params,'branch');
    const branchAvailable = branch => candidateAvailable('branch',branch,params);
    let output = checkboxGroup('Clothing','branch',branches,params,branchAvailable);
    if (chosen.length) {
        const subtypeMap = new Map();
        chosen.forEach(branch => (taxonomy.clothing[branch] || []).forEach(item => subtypeMap.set(item.id,item)));
        const subtypeAvailable = subtype => candidateAvailable('subtype',subtype,params);
        output += checkboxGroup('Product type','subtype',[...subtypeMap.values()],params,subtypeAvailable);
    }
    return output;
}

function renderFilters() {
    const params = new URLSearchParams(location.search);
    const data = filterData();
    const categoryAvailable = id => candidateAvailable('catalog_category',id,params);
    const dynamicSubtypes = unique(products.filter(product => ['equipment','components','bikes-frames'].includes(product.category_id)).map(product => product.subtype_id)).map(id => ({id,label:products.find(product=>product.subtype_id===id)?.product_type||id}));
    const activeTop = params.get('category');
    const showDynamicSubtype = ['equipment','components','bikes-frames'].includes(activeTop) || selected(params,'catalog_category').some(id => ['equipment','components','bikes-frames'].includes(id));
    const categoryGroup = topCategory(activeTop)?.kind === 'category' ? '' : checkboxGroup('Category','catalog_category',data.categories,params,categoryAvailable);
    filterGroups.innerHTML = categoryGroup
        + clothingFilters(params)
        + (showDynamicSubtype ? checkboxGroup('Product type','subtype',dynamicSubtypes,params,id=>candidateAvailable('subtype',id,params)) : '')
        + checkboxGroup('Brand','brand',data.brands,params,value=>candidateAvailable('brand',value,params))
        + checkboxGroup('Size','size',data.sizes,params,value=>candidateAvailable('size',value,params))
        + `<fieldset class="filter-group"><legend>Price range<span>⌄</span></legend><div class="price-filter"><label>Min <input type="number" min="0" step="1" data-price="min" value="${safe(params.get('min')||'')}"></label><label>Max <input type="number" min="0" step="1" data-price="max" value="${safe(params.get('max')||'')}"></label></div></fieldset>`
        + `<fieldset class="filter-group"><legend>Availability<span>⌄</span></legend><div><label><input type="checkbox" data-boolean="availability" ${params.get('availability')==='in-stock'?'checked':''}><span>In stock</span></label></div></fieldset>`
        + `<fieldset class="filter-group"><legend>Sale status<span>⌄</span></legend><div><label><input type="checkbox" data-boolean="sale" ${params.get('sale')==='1'?'checked':''}><span>On sale</span></label></div></fieldset>`;
    filterGroups.querySelectorAll('input[type=checkbox][data-filter]').forEach(input => input.addEventListener('change', updateFilters));
    filterGroups.querySelectorAll('[data-boolean]').forEach(input => input.addEventListener('change', updateFilters));
    filterGroups.querySelectorAll('[data-price]').forEach(input => input.addEventListener('change', updateFilters));
}

function updateFilters() {
    const params = new URLSearchParams(location.search);
    ['catalog_category','branch','subtype','brand','size'].forEach(key => {
        const values = [...filterGroups.querySelectorAll(`[data-filter="${key}"]:checked`)].map(input => input.value);
        values.length ? params.set(key, values.join(',')) : params.delete(key);
    });
    if (params.get('category') !== 'clothing' && !selected(params,'catalog_category').includes('clothing')) {
        params.delete('branch');
        params.delete('subtype');
    }
    const branches = selected(params,'branch');
    const validSubtypeIds = new Set(branches.flatMap(branch => (taxonomy.clothing[branch]||[]).map(item=>item.id)));
    if (params.has('subtype') && branches.length && selected(params,'subtype').some(value => !validSubtypeIds.has(value))) params.delete('subtype');
    const availability = filterGroups.querySelector('[data-boolean="availability"]');
    const sale = filterGroups.querySelector('[data-boolean="sale"]');
    availability?.checked ? params.set('availability','in-stock') : params.delete('availability');
    sale?.checked ? params.set('sale','1') : params.delete('sale');
    ['min','max'].forEach(key => {
        const value = filterGroups.querySelector(`[data-price="${key}"]`)?.value;
        value !== '' ? params.set(key,value) : params.delete(key);
    });
    params.delete('product');
    navigate(params);
}

function matchesFilters(product, params) {
    const category = params.get('category') || '';
    const categories = selected(params,'catalog_category');
    const branches = selected(params,'branch');
    const brands = selected(params,'brand').map(normalized);
    const subtypes = selected(params,'subtype');
    const sizes = selected(params,'size').map(normalized);
    const min = params.has('min') ? Number(params.get('min')) * 100 : null;
    const max = params.has('max') ? Number(params.get('max')) * 100 : null;
    const price = currentPrice(product);
    const productSizes = (product.variants || []).map(variant => normalized(variant.size));
    const branchMatches = !branches.length || branches.some(branch => branch==='men'||branch==='women' ? (product.audiences||[]).includes(branch) : clothingBranch(product)===branch);
    return topMatch(product,category)
        && (!categories.length || categories.includes(product.category_id))
        && branchMatches
        && (!brands.length || brands.includes(normalized(product.brand)))
        && (!subtypes.length || subtypes.includes(product.subtype_id))
        && (!sizes.length || sizes.some(size => productSizes.includes(size)))
        && (min === null || price >= min) && (max === null || price <= max)
        && (params.get('availability') !== 'in-stock' || product.available)
        && (params.get('sale') !== '1' || product.is_sale === true);
}

function candidateAvailable(key, value, params) {
    const candidate = new URLSearchParams(params);
    candidate.set(key,value);
    if (key === 'catalog_category' && value !== 'clothing') { candidate.delete('branch'); candidate.delete('subtype'); }
    if (key === 'branch') candidate.delete('subtype');
    return products.some(product => matchesFilters(product,candidate));
}

function filteredProducts() {
    const params = new URLSearchParams(location.search);
    let result = products.filter(product => matchesFilters(product,params));
    const sort = params.get('sort') || 'featured';
    result.sort((a,b) => sort === 'price-asc' ? currentPrice(a)-currentPrice(b)
        : sort === 'price-desc' ? currentPrice(b)-currentPrice(a)
        : sort === 'name' ? a.name.localeCompare(b.name)
        : sort === 'newest' ? String(b.created_at||'').localeCompare(String(a.created_at||''))
        : (a.featured_rank ?? 999999)-(b.featured_rank ?? 999999) || a.name.localeCompare(b.name));
    return result;
}

function imageMarkup(image, name, eager=false) {
    if (!image?.url) return '<span class="product-image-fallback" aria-label="Image unavailable"></span>';
    return `<img src="${safe(assetUrl(image.url))}" alt="${safe(image.alt_text||name)}" ${eager?'':'loading="lazy"'}>`;
}

function productCard(product) {
    const variants = product.variants || [];
    const sizes = unique(variants.map(variant => variant.size));
    const price = currentPrice(product);
    return `<article class="catalog-card" data-product data-keywords="${safe(normalized(`${product.name} ${product.brand} ${product.category} ${product.product_type}`))}"><a href="${productHref(product.slug)}" aria-label="View ${safe(product.name)}"><div class="catalog-card-image">${product.is_new?'<i>NEW ARRIVAL</i>':''}${product.is_sale?'<i class="sale-badge">SALE</i>':''}${imageMarkup(product.images?.[0],product.name)}</div><div class="catalog-card-copy"><small>${safe(product.brand||product.category||'Ran Thru')}</small><h3>${safe(product.name)}</h3>${product.is_sale?`<p><strong>${money(price)}</strong> <del>${money(product.price_cents)}</del></p>`:`<p><strong>${money(product.price_cents)}</strong></p>`}<span>${sizes.length?safe(sizes.join(' · ')):(product.available?'Available':'Unavailable')}</span></div></a></article>`;
}

function bindImageFallbacks(scope=document) {
    scope.querySelectorAll('.catalog-card-image img,.product-gallery img,.category-image img').forEach(image => image.addEventListener('error', () => image.remove(), {once:true}));
}

function renderCatalog() {
    const params = new URLSearchParams(location.search);
    const slug = params.get('product');
    if (slug) return renderProduct(slug);
    document.querySelector('[data-shop-results]').hidden = false;
    const result = filteredProducts();
    const label = topCategory(params.get('category'))?.label || 'All products';
    title.textContent = label;
    count.textContent = `${result.length} product${result.length===1?'':'s'}`;
    document.querySelector('[data-sort]').value = params.get('sort') || 'featured';
    catalogState.textContent = result.length ? '' : products.length ? 'No products match these filters.' : 'The catalog is currently empty.';
    grid.innerHTML = result.slice(0,visibleCount).map(productCard).join('');
    grid.hidden = !result.length;
    loadMore.hidden = visibleCount >= result.length;
    bindImageFallbacks(grid);
    renderActiveFilters(params);
}

function valueLabel(key, value) {
    if (key === 'category' || key === 'catalog_category') return topCategory(value)?.label || value;
    if (key === 'branch') return ({men:'Men',women:'Women',lifestyle:'Lifestyle',accessories:'Accessories'})[value] || value;
    if (key === 'subtype') {
        for (const branch of Object.values(taxonomy?.clothing || {})) {
            const match = branch.find(item => item.id === value);
            if (match) return match.label;
        }
        return products.find(product => product.subtype_id === value)?.product_type || value;
    }
    if (key === 'availability') return 'In stock';
    if (key === 'sale') return 'On sale';
    if (key === 'min') return `Min ${money(Number(value) * 100)}`;
    if (key === 'max') return `Max ${money(Number(value) * 100)}`;
    return value;
}

function renderActiveFilters(params = new URLSearchParams(location.search)) {
    if (!activeFilters) return;
    const chips = [];
    ['category','catalog_category','branch','subtype','brand','size','availability','sale','min','max'].forEach(key => {
        if (!params.has(key)) return;
        const values = ['catalog_category','branch','subtype','brand','size'].includes(key) ? selected(params,key) : [params.get(key)];
        values.forEach(value => chips.push({key,value,label:valueLabel(key,value)}));
    });
    activeFilters.innerHTML = chips.map(chip => `<button type="button" data-remove-filter="${safe(chip.key)}" data-remove-value="${safe(chip.value)}">${safe(chip.label)} <span aria-hidden="true">×</span><span class="sr-only">Remove filter</span></button>`).join('');
    activeFilters.hidden = chips.length === 0;
    activeFilters.querySelectorAll('[data-remove-filter]').forEach(button => button.addEventListener('click', () => {
        const next = new URLSearchParams(location.search);
        const key = button.dataset.removeFilter;
        const values = selected(next,key).filter(value => value !== button.dataset.removeValue);
        values.length ? next.set(key,values.join(',')) : next.delete(key);
        if (key === 'category' && topCategory(button.dataset.removeValue)?.kind === 'category') { next.delete('branch'); next.delete('subtype'); }
        if (key === 'branch') {
            const valid = new Set(selected(next,'branch').flatMap(branch => (taxonomy.clothing[branch] || []).map(item => item.id)));
            const subtypes = selected(next,'subtype').filter(value => valid.has(value));
            subtypes.length ? next.set('subtype',subtypes.join(',')) : next.delete('subtype');
        }
        navigate(next);
    }));
}

function renderProduct(slug) {
    const product = products.find(item => item.slug === slug);
    const results = document.querySelector('[data-shop-results]');
    if (!product) {
        results.innerHTML = '<div class="shop-error"><h2>Product unavailable.</h2><p>This product may have been removed or is no longer active.</p><a href="?">Return to shop</a></div>';
        return;
    }
    const variants = product.variants || [];
    const gallery = (product.images || []).length ? product.images.map((image,index) => `<div class="product-gallery-image">${imageMarkup(image,product.name,index===0)}</div>`).join('') : '<div class="product-gallery-image"><span class="product-image-fallback"></span></div>';
    const action = product.checkout_url && product.available ? `<a class="btn" href="${safe(product.checkout_url)}">CHECKOUT ↗</a>` : `<p class="availability">${product.available?'Contact us to order.':'Currently unavailable.'}</p>`;
    results.innerHTML = `<a class="product-back" href="?">← Back to shop</a><article class="product-detail"><div class="product-gallery">${gallery}</div><div class="product-info"><p class="eyebrow">${safe(product.brand||product.category)}</p><h2>${safe(product.name)}</h2><p class="product-description">${safe(product.description)}</p><div class="product-price">${product.is_sale?`<strong>${money(currentPrice(product))}</strong><del>${money(product.price_cents)}</del>`:`<strong>${money(product.price_cents)}</strong>`}</div>${variants.length?`<div class="variant-list"><h3>Variants</h3>${variants.map(variant=>`<div><span>${safe([variant.size,variant.color].filter(Boolean).join(' / ')||variant.sku)}</span><span>${variant.stock_quantity>0?`${variant.stock_quantity} in stock`:'Unavailable'}</span></div>`).join('')}</div>`:'<p>Variant details coming soon.</p>'}${action}</div></article>`;
    bindImageFallbacks(results);
}

function navigate(params) {
    visibleCount = pageSize;
    history.pushState({},'',`${location.pathname}${params.toString()?`?${params}`:''}`);
    renderCategories(); renderFilters(); renderCatalog();
}

function wireControls() {
    document.querySelector('[data-sort]').addEventListener('change', event => {const params=new URLSearchParams(location.search);params.set('sort',event.target.value);navigate(params)});
    document.querySelector('[data-clear-filters]').addEventListener('click', () => {const params=new URLSearchParams();const sort=new URLSearchParams(location.search).get('sort');if(sort)params.set('sort',sort);navigate(params)});
    document.querySelector('[data-filter-open]').addEventListener('click', () => filterPanel.classList.add('open'));
    document.querySelector('[data-filter-close]').addEventListener('click', () => filterPanel.classList.remove('open'));
    loadMore.addEventListener('click', () => {visibleCount += pageSize;renderCatalog()});
    addEventListener('popstate', () => {visibleCount=pageSize;renderCategories();renderFilters();renderCatalog()});
}

async function loadCatalog() {
    initHero(); wireControls();
    try {
        const [catalogResponse,taxonomyResponse] = await Promise.all([
            fetch(`${base}data/products.json`, {headers:{Accept:'application/json'}}),
            fetch(`${base}data/taxonomy.json`, {headers:{Accept:'application/json'}}),
        ]);
        if (!catalogResponse.ok) throw new Error(`Catalog request failed (${catalogResponse.status})`);
        if (!taxonomyResponse.ok) throw new Error(`Taxonomy request failed (${taxonomyResponse.status})`);
        const [payload,taxonomyPayload] = await Promise.all([catalogResponse.json(),taxonomyResponse.json()]);
        if (!payload || !Array.isArray(payload.products)) throw new Error('Catalog JSON is malformed');
        if (!taxonomyPayload || !Array.isArray(taxonomyPayload.top_level) || !taxonomyPayload.clothing) throw new Error('Taxonomy JSON is malformed');
        taxonomy = taxonomyPayload;
        products = payload.products.filter(product => product && product.slug && product.name && Number.isFinite(Number(product.price_cents)));
        renderCategories(); renderFilters(); renderCatalog();
    } catch (error) {
        console.error(error);
        catalogState.innerHTML = '<strong>We could not load the collection.</strong><span>Please refresh the page or try again later.</span>';
        grid.hidden = true; count.textContent = '';
    }
}

if (root) loadCatalog();
