#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "$0")/.." && pwd)"
compose_file="$repo_root/docker-compose.local.yml"
log_root="$repo_root/logs/docker"

mkdir -p "$log_root"

services=()
if [[ $# -gt 0 ]]; then
  services=("$@")
else
  while IFS= read -r service; do
    services+=("$service")
  done < <(docker compose -f "$compose_file" config --services)
fi

echo "Writing container logs under $log_root"

for service in "${services[@]}"; do
  log_file="$log_root/$service.log"
  : > "$log_file"
  docker compose -f "$compose_file" logs -f --no-color "$service" >> "$log_file" 2>&1 &
  echo "$service -> $log_file"
done

wait