#!/usr/bin/env bash
set -euo pipefail

site_url="http://127.0.0.1:8765/"
server_log="${TMPDIR:-/tmp}/rank-thru-laravel.log"
server_pid=""

cleanup() {
  status=$?

  if [[ -n "$server_pid" ]] && kill -0 "$server_pid" 2>/dev/null; then
    kill "$server_pid" 2>/dev/null || true
    wait "$server_pid" 2>/dev/null || true
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
BUILD_STATIC=1 npm run build
php artisan serve --host=127.0.0.1 --port=8765 > "$server_log" 2>&1 &
server_pid=$!
mkdir -p static-export

curl --fail --show-error --silent --retry 10 --retry-connrefused --retry-delay 1 \
  "$site_url" --output static-export/index.html

sed -i 's|http://127.0.0.1:8765/build/|/rankthrubikes/build/|g' static-export/index.html
cp -R public/build static-export/build
touch static-export/.nojekyll

grep -Fq '/rankthrubikes/build/' static-export/index.html
