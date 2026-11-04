<?php

use Illuminate\Support\Facades\Route;

Route::get('/', function () {
    return view('rank');
});
Route::view('/shop', 'shop');
Route::get('/rides/{slug}', function (string $slug) {
    $ride = config('rides')[$slug] ?? null;
    abort_unless($ride, 404);

    return view($ride['landing'] ?? false ? 'rides.komorebi' : 'rides.show', compact('ride', 'slug'));
})->where('slug', '[a-z0-9-]+')->name('rides.show');
Route::get('/information/{page}', function (string $page) {
    $pages = [
        'faqs' => ['title' => 'FAQs', 'copy' => ['This demonstration storefront does not process purchases or customer accounts. Product availability, sizing, and service details are illustrative unless otherwise stated.', 'For project questions, use the contact section on the homepage.']],
        'orders' => ['title' => 'Orders', 'copy' => ['Ran Thru Bikes is a demonstration storefront. Ordering and order tracking are not available.']],
        'shipping-delivery' => ['title' => 'Shipping & Delivery', 'copy' => ['This demonstration storefront does not offer shipping or delivery. Fulfilment terms will be published only if the project becomes operational.']],
        'returns-exchanges' => ['title' => 'Returns & Exchanges', 'copy' => ['This demonstration storefront does not process purchases, returns, or exchanges. Any future policy requires completion before retail operations begin.']],
        'size-guide' => ['title' => 'Size Guide', 'copy' => ['Sizing information in this demonstration catalog may be incomplete. Confirm manufacturer guidance before relying on any fit information.']],
        'community-events' => ['title' => 'Community Events', 'copy' => ['No community events are currently scheduled through this demonstration storefront.']],
        'about-project' => ['title' => 'About the Project', 'copy' => ['Ran Thru Bikes is a concept storefront exploring a considered approach to cycling retail, equipment, stories, and community.', 'The site is a demonstration only and is not an active retailer.']],
        'privacy-policy' => ['title' => 'Privacy Policy', 'copy' => ['This is a demonstration placeholder, not a complete privacy policy. Before collecting personal data or operating commercially, a project-specific policy must be reviewed and published.']],
        'terms-conditions' => ['title' => 'Terms & Conditions', 'copy' => ['This is a demonstration placeholder, not legally binding terms. Terms of sale and site use must be completed before the project operates as a retailer.']],
        'accessibility' => ['title' => 'Accessibility', 'copy' => ['Ran Thru Bikes aims to make this demonstration experience usable with keyboard navigation and readable contrast. Accessibility work is ongoing; formal conformance information has not been published.']],
    ];
    abort_unless(isset($pages[$page]), 404);
    return view('information', ['page' => $pages[$page]]);
})->where('page', '[a-z-]+')->name('information.show');
Route::get('/stories/{slug}', function (string $slug) {
    $stories = config('stories');
    abort_unless(isset($stories[$slug]), 404);
    return view('stories.show', ['story' => $stories[$slug]]);
})->where('slug', '[a-z0-9-]+');
Route::get('/data/products.json', function () {
    $catalog = base_path('data/products.json');
    abort_unless(is_file($catalog), 404);
    return response()->file($catalog, ['Content-Type' => 'application/json; charset=utf-8']);
});
Route::get('/data/taxonomy.json', function () {
    $taxonomy = base_path('data/taxonomy.json');
    abort_unless(is_file($taxonomy), 404);
    return response()->file($taxonomy, ['Content-Type' => 'application/json; charset=utf-8']);
});
