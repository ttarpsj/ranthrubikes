const drawer = document.querySelector('[data-mobile]');

if (drawer) {
    const head = drawer.querySelector('.drawer-head')?.outerHTML || '';
    const fallbackPrimary = drawer.querySelector('.drawer-primary')?.innerHTML || '';
    const utility = drawer.querySelector('.drawer-secondary')?.outerHTML || '';
    const rides = [
        ['05 NOV · GIRONA', 'BREVET NIGHTS 5', 'brevet-nights-5'],
        ['07 NOV · PRATS DE LLUÇANÈS', 'KOMOREBI GRAVEL SOCIAL RIDE', 'komorebi-gravel-social-ride'],
        ['14 NOV · LA CROSSE', 'TREK DRIFTLESS GETAWAY', 'trek-driftless-getaway'],
        ['20 NOV · CHICAGO', 'CYCLE CROSS DERBY NIGHT', 'cycle-cross-derby-night'],
    ];
    const escapeHtml = value => String(value ?? '').replace(/[&<>"']/g, character => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[character]));
    const shopIndex = location.pathname.indexOf('/shop');
    const siteBase = shopIndex >= 0 ? `${location.pathname.slice(0,shopIndex)}/`.replace(/\/+/g,'/') : (location.pathname.endsWith('/') ? location.pathname : `${location.pathname}/`).replace(/\/+/g,'/');
    const shopUrl = `${siteBase}shop`;
    const filterUrl = params => `${shopUrl}?${new URLSearchParams(params).toString()}`;

    function taxonomyLinks(taxonomy) {
        if (!taxonomy?.top_level || !taxonomy?.clothing) return fallbackPrimary;
        return taxonomy.top_level.map(item => {
            if (item.id !== 'clothing') return `<a href="${filterUrl({category:item.id})}">${escapeHtml(item.label)} <span aria-hidden="true">→</span></a>`;
            const branches = [['men','Men'],['women','Women'],['lifestyle','Lifestyle'],['accessories','Accessories']];
            const nested = branches.map(([id,label]) => `<details class="drawer-taxonomy-branch"><summary aria-expanded="false"><span>${label}</span><i aria-hidden="true">+</i></summary><div><a class="drawer-branch-link" href="${filterUrl({category:'clothing',branch:id})}">All ${label}</a>${(taxonomy.clothing[id] || []).map(type => `<a href="${filterUrl({category:'clothing',branch:id,subtype:type.id})}">${escapeHtml(type.label)}</a>`).join('')}</div></details>`).join('');
            return `<details class="drawer-taxonomy"><summary aria-expanded="false"><span>${escapeHtml(item.label)}</span><i aria-hidden="true">+</i></summary><div class="drawer-taxonomy-content"><a class="drawer-branch-link" href="${filterUrl({category:'clothing'})}">All Clothing</a>${nested}</div></details>`;
        }).join('');
    }

    function render(primary) {
        drawer.innerHTML = `${head}<div class="drawer-tabs" role="tablist" aria-label="Menu sections"><button class="active" role="tab" aria-selected="true" data-drawertab="products">Products</button><button role="tab" aria-selected="false" data-drawertab="rides">Rides</button></div><div data-drawerpanel="products"><nav class="drawer-primary" aria-label="Product categories">${primary}</nav>${utility}</div><nav class="drawer-rides" data-drawerpanel="rides" hidden aria-label="Rides">${rides.map(([date,title,slug]) => `<a class="drawer-ride" href="${siteBase}rides/${slug}"><span class="drawer-ride-thumb" aria-hidden="true">RIDE</span><span><small>${date}</small><b>${title}</b></span></a>`).join('')}</nav>`;
        drawer.querySelectorAll('[data-drawertab]').forEach(tab => tab.addEventListener('click', () => {
            drawer.querySelectorAll('[data-drawertab]').forEach(item => {
                const active = item === tab;
                item.classList.toggle('active',active);
                item.setAttribute('aria-selected',String(active));
            });
            drawer.querySelectorAll('[data-drawerpanel]').forEach(panel => panel.hidden = panel.dataset.drawerpanel !== tab.dataset.drawertab);
        }));
        drawer.querySelectorAll('details').forEach(details => details.addEventListener('toggle', () => details.querySelector(':scope > summary')?.setAttribute('aria-expanded',String(details.open))));
        const close = () => document.querySelector('[data-menu]')?.click();
        drawer.querySelector('[data-menuclose]')?.addEventListener('click', close);
        drawer.querySelectorAll('a').forEach(link => link.addEventListener('click', close));
    }

    render(fallbackPrimary);
    fetch(`${siteBase}data/taxonomy.json`, {headers:{Accept:'application/json'}})
        .then(response => response.ok ? response.json() : Promise.reject(new Error(`Taxonomy request failed (${response.status})`)))
        .then(taxonomy => render(taxonomyLinks(taxonomy)))
        .catch(error => console.warn('Using fallback drawer navigation.',error));
}
