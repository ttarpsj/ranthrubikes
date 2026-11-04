<!doctype html>
<html lang="en">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>{{ $story['title'] }} — Ran Thru Bikes</title>

        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link
            href="https://fonts.googleapis.com/css2?family=DM+Mono&family=Manrope:wght@400;500;600;700;800&display=swap"
            rel="stylesheet"
        >

        @vite(['resources/css/app.css', 'resources/js/app.js'])
    </head>
    <body class="story-page">
        <header class="story-nav">
            <a href="/" class="logo">RAN <b>THRU</b></a>
            <a href="/#journal">STORIES</a>
        </header>

        <main class="story">
            <a class="story-back" href="/#journal">← BACK TO STORIES</a>

            <header class="story-intro">
                <p class="eyebrow">
                    {{ strtoupper($story['category']) }} · {{ $story['date'] }}
                </p>
                <h1>{{ $story['title'] }}</h1>
            </header>

            <img class="story-hero" src="{{ $story['hero'] }}" alt="">

            <article class="story-copy">
                @foreach ($story['blocks'] as $block)
                    @if ($block['type'] === 'heading')
                        <h2>{{ $block['text'] }}</h2>
                    @elseif ($block['type'] === 'image')
                        <img src="{{ $block['src'] }}" alt="">
                    @elseif ($block['type'] === 'kit')
                        <section class="kit">
                            <header>
                                <b>RECOMMENDED KIT</b>
                                <span>{{ $block['temperature'] }}</span>
                            </header>

                            @foreach ($block['rows'] as $label => $items)
                                <div>
                                    <strong>{{ $label }}</strong>
                                    <p>
                                        @foreach ($items as $item)
                                            <a href="{{ $item[1] }}" target="_blank" rel="noopener">
                                                {{ $item[0] }}
                                            </a>
                                        @endforeach
                                    </p>
                                </div>
                            @endforeach
                        </section>
                    @else
                        <p>{{ $block['text'] }}</p>
                    @endif
                @endforeach
            </article>
        </main>

        @include('components.footer')
    </body>
</html>
