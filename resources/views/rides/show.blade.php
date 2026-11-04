<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{{ $ride['title'] }} — Ran Thru Bikes</title><link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link href="https://fonts.googleapis.com/css2?family=DM+Mono&family=Manrope:wght@400;500;600;700;800&display=swap" rel="stylesheet">@vite(['resources/css/app.css', 'resources/js/app.js'])</head>
<body class="ride-page"><header class="ride-nav"><a href="/" class="logo">RAN <b>THRU</b></a><a href="/#top">HOME</a></header><main class="ride-shell"><a class="ride-back" href="/#top">← BACK TO RIDES</a><div class="ride-layout"><article class="ride-content"><div class="ride-hero {{ empty($ride['hero']) ? 'ride-hero--placeholder' : '' }}">
@if (!empty($ride['hero']))
<img src="{{ $ride['hero'] }}" alt="{{ $ride['title'] }}">
@else
<span>RAN THRU RIDES</span>
@endif
</div><p class="ride-kicker">{{ $ride['date'] }} · {{ $ride['location'] }}</p><h1>{{ $ride['title'] }}</h1>
@if (!empty($ride['organizer']))
<p class="ride-organizer">ORGANISED BY {{ $ride['organizer'] }}</p>
@endif
@if (!empty($ride['intro']))
<p class="ride-lede">{{ $ride['intro'] }}</p>
@endif
@foreach (($ride['body'] ?? []) as $paragraph)
<p>{{ $paragraph }}</p>
@endforeach
@if (!empty($ride['schedule']))
<section><h2>SCHEDULE</h2><ol class="ride-schedule">@foreach ($ride['schedule'] as $item)<li>{{ $item }}</li>@endforeach</ol></section>
@endif
</article><aside class="ride-details"><h2>EVENT DETAILS</h2>
@foreach (['When' => $ride['date'], 'Where' => $ride['where'] ?? $ride['location'], 'Format' => $ride['format'] ?? null, 'Distance' => $ride['distance'] ?? null, 'Elevation' => $ride['elevation'] ?? null, 'Going' => $ride['going'] ?? null] as $label => $value)
@if ($value)
<div><small>{{ $label }}</small><strong>{{ $value }}</strong></div>
@endif
@endforeach
@if (!empty($ride['prizes']))
<section class="ride-prizes"><h3>CUP PRIZES</h3><p>Every ride earns points. The more points you finish with, the better your chances.</p><ul>@foreach ($ride['prizes'] as $prize)<li>{{ $prize }}</li>@endforeach</ul><a href="{{ $ride['prize_url'] }}" target="_blank" rel="noopener">SEE PRIZES AND DRAW RULES ↗</a></section>
@endif
</aside></div></main>@include('components.footer')</body></html>
