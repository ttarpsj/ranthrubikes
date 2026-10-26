#!/usr/bin/env bash
set -euo pipefail
rm -rf static-export
BUILD_STATIC=1 npm run build
php artisan serve --host=127.0.0.1 --port=8765 > /tmp/rank-thru-laravel.log 2>&1 &
server_pid=$!
trap 'kill $server_pid 2>/dev/null || true' EXIT
sleep 2
mkdir -p static-export
curl --fail --silent http://127.0.0.1:8765/ > static-export/index.html
sed -i 's|http://127.0.0.1:8765/build/|/rankthrubikes/build/|g' static-export/index.html
cp -R public/build static-export/build
touch static-export/.nojekyll
