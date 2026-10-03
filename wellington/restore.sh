#!/usr/bin/env bash
# A folder selects its newest webui-*.sqlite3 or webui.db, including subfolders.
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
compose_file="$script_dir/docker-compose.custom.yaml"
backup_path=''
check_only=false

usage() {
    echo 'Usage: restore.sh BACKUP_FILE_OR_FOLDER [--check-only] [--compose-file PATH]'
}

while (($#)); do
    case "$1" in
        --compose-file)
            [[ $# -ge 2 ]] || { echo '--compose-file requires a path.' >&2; exit 1; }
            compose_file="$2"
            shift 2
            ;;
        --check-only) check_only=true; shift ;;
        -h|--help) usage; exit 0 ;;
        --)
            shift
            [[ $# -eq 1 && -z "$backup_path" ]] || { usage >&2; exit 1; }
            backup_path="$1"
            shift
            ;;
        -*) echo "Unknown argument: $1" >&2; exit 1 ;;
        *)
            [[ -z "$backup_path" ]] || { usage >&2; exit 1; }
            backup_path="$1"
            shift
            ;;
    esac
done

[[ -n "$backup_path" ]] || { usage >&2; exit 1; }
if [[ -d "$backup_path" ]]; then
    backup_path="$(cd "$backup_path" && pwd)"
    selected=''
    # Bash's timestamp comparison works on both Linux and macOS; no GNU stat
    # or sort extensions are required. Null delimiters preserve spaces/newlines.
    while IFS= read -r -d '' candidate; do
        if [[ -z "$selected" || "$candidate" -nt "$selected" ]] ||
            [[ ! "$candidate" -ot "$selected" && "$candidate" > "$selected" ]]; then
            selected="$candidate"
        fi
    done < <(find "$backup_path" -type f \( -name 'webui-*.sqlite3' -o -name 'webui.db' \) -print0)
    [[ -n "$selected" ]] || { echo 'No OpenWebUI database backups found in the specified folder.' >&2; exit 1; }
    backup_path="$selected"
fi
[[ -f "$backup_path" ]] || { echo "Backup file not found: $backup_path" >&2; exit 1; }
backup_dir="$(cd "$(dirname "$backup_path")" && pwd)"
backup_name="$(basename "$backup_path")"
echo "Selected backup: $backup_dir/$backup_name"

compose() { docker compose -f "$compose_file" "$@"; }
compose build open-webui-backup
helper=(run --rm --no-deps --volume "$backup_dir:/restore-input:ro"
    --entrypoint python open-webui-backup /restore.py "/restore-input/$backup_name")
compose "${helper[@]}" --check-only
if $check_only; then exit 0; fi

running="$(compose ps --status running --services)"
restart=()
while IFS= read -r service; do
    case "$service" in
        open-webui|open-webui-backup) restart+=("$service") ;;
    esac
done <<< "$running"

restart_services() {
    local status=$?
    trap - EXIT
    if ((${#restart[@]})); then
        if ! compose start "${restart[@]}"; then
            echo 'Could not restart the services; start them with Docker Compose.' >&2
            if [[ $status -eq 0 ]]; then status=1; fi
        fi
    fi
    exit "$status"
}
trap restart_services EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
compose stop open-webui-backup open-webui
compose "${helper[@]}"
# Run cleanup before reporting success, and preserve errors from service restart.
if ((${#restart[@]})); then compose start "${restart[@]}"; fi
trap - EXIT INT TERM
echo 'Restore completed. A safety backup of the previous database was saved in manual/ if it existed.'
