#!/usr/bin/env bash
# Manual snapshots are saved in OPENWEBUI_BACKUP_DIR/manual and never pruned.
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
compose_file="$script_dir/docker-compose.custom.yaml"

while (($#)); do
    case "$1" in
        --compose-file)
            [[ $# -ge 2 ]] || { echo '--compose-file requires a path.' >&2; exit 1; }
            compose_file="$2"
            shift 2
            ;;
        -h|--help)
            echo 'Usage: backup.sh [--compose-file PATH]'
            exit 0
            ;;
        *) echo "Unknown argument: $1" >&2; exit 1 ;;
    esac
done

docker compose -f "$compose_file" build open-webui-backup
docker compose -f "$compose_file" run --rm --no-deps open-webui-backup --manual
echo 'Manual backup completed. No previous backups were deleted.'
