#!/usr/bin/env bash
set -euo pipefail

site_url="http://127.0.0.1:8765/"
server_log="${TMPDIR:-/tmp}/rank-thru-laravel.log"
server_pid=""
hot_file="public/hot"
hot_backup=""

cleanup() {
  status=$?

  if [[ -n "$server_pid" ]] && kill -0 "$server_pid" 2>/dev/null; then
    kill "$server_pid" 2>/dev/null || true
    wait "$server_pid" 2>/dev/null || true
  fi
  if [[ -n "$hot_backup" ]] && [[ -f "$hot_backup" ]]; then
    mv "$hot_backup" "$hot_file"
  fi

  if [[ "$status" -ne 0 ]]; then
    echo "Static export failed. Laravel server output follows:" >&2
    cat "$server_log" >&2 || true
  fi

  exit "$status"
}

trap cleanup EXIT

# GitHub Actions checks out no .env file. Laravel needs an encryption key to
# render a request, so generate one for this ephemeral static-export process.
if [[ -z "${APP_KEY:-}" ]]; then
  export APP_KEY="base64:$(php -r 'echo base64_encode(random_bytes(32));')"
fi
export APP_ENV=production
export APP_DEBUG=false
export APP_URL="$site_url"

rm -rf static-export
python3 scripts/sync_products.py
BUILD_STATIC=1 npm run build

# A Herd/Vite development session leaves public/hot behind. Blade gives that
# file precedence over the production manifest, so set it aside while pages
# are rendered for the static GitHub Pages artifact and restore it on exit.
if [[ -f "$hot_file" ]]; then
  hot_backup="${TMPDIR:-/tmp}/rank-thru-vite-hot-$$"
  mv "$hot_file" "$hot_backup"
fi

php artisan serve --host=127.0.0.1 --port=8765 > "$server_log" 2>&1 &
server_pid=$!
mkdir -p static-export

curl --fail --show-error --silent --retry 10 --retry-connrefused --retry-delay 1 \
  "$site_url" --output static-export/index.html
mkdir -p static-export/shop static-export/data
curl --fail --show-error --silent --retry 10 --retry-connrefused --retry-delay 1 \
  "${site_url}shop" --output static-export/shop/index.html
cp data/*.json static-export/data/
cp -R public/images static-export/images
find public -maxdepth 1 -type f \( -iname '*.mp4' -o -iname '*.webm' -o -iname '*.mov' \) -exec cp {} static-export/ \;

export_page() {
  local path="$1"
  local destination="static-export/${path}/index.html"
  mkdir -p "$(dirname "$destination")"
  curl --fail --show-error --silent --retry 10 --retry-connrefused --retry-delay 1 \
    "${site_url}${path}" --output "$destination"
}

for story in enric-mas-the-triumph-of-perseverance sea-otter-europe-2026 how-to-dress-for-winter-cycling; do
  export_page "stories/${story}"
done

for ride in brevet-nights-5 komorebi-gravel-social-ride trek-driftless-getaway cycle-cross-derby-night 3t-esmorzar-amb-forquilla social-ride-fito-velodrom; do
  export_page "rides/${ride}"
done

for page in faqs orders shipping-delivery returns-exchanges size-guide community-events about-project privacy-policy terms-conditions accessibility; do
  export_page "information/${page}"
done

find static-export -name '*.html' -print0 | xargs -0 sed -i \
  -e 's|href="/|href="/ranthrubikes/|g' \
  -e 's|src="/|src="/ranthrubikes/|g' \
  -e 's|="/images/|="/ranthrubikes/images/|g' \
  -e 's|="/data/|="/ranthrubikes/data/|g' \
  -e 's|http://127.0.0.1:8765/|/ranthrubikes/|g'
cp -R public/build static-export/build
touch static-export/.nojekyll

grep -Fq '/ranthrubikes/build/' static-export/index.html
grep -Fq '/ranthrubikes/build/' static-export/shop/index.html
! grep -R -Fq '/rankthrubikes/' static-export
! grep -R -Fq '="/images/' static-export --include='*.html'
! grep -R -Fq '="/data/' static-export --include='*.html'
test "$(python3 -c 'import json; print(len(json.load(open("static-export/data/products.json"))["products"]))')" -ge 0
