#!/bin/sh
set -eu

usage() {
    echo "Usage: $0 DESTINATION [PYTHON]" >&2
    exit 2
}

[ "$#" -ge 1 ] && [ "$#" -le 2 ] || usage
destination=$1
python_command=${2:-python3}

case "$destination" in
    /*) target=$destination ;;
    *) target=$PWD/$destination ;;
esac

[ ! -e "$target" ] || {
    echo "Destination already exists. Choose a new installation path: $target" >&2
    exit 1
}

script_directory=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
set -- "$script_directory"/project_infra-*.whl
[ "$#" -eq 1 ] && [ -f "$1" ] || {
    echo "Keep exactly one project_infra wheel beside this installer." >&2
    exit 1
}
wheel=$1

"$python_command" -c "import sys; assert sys.version_info >= (3, 11), 'Python 3.11+ required'"
"$python_command" -m venv "$target/.venv"
"$target/.venv/bin/python" -m pip install --no-index --no-deps "$wheel"

cat > "$target/project-infra" <<'EOF'
#!/bin/sh
set -eu
launcher_directory=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec "$launcher_directory/.venv/bin/project-infra" "$@"
EOF
cat > "$target/project-infra-desktop" <<'EOF'
#!/bin/sh
set -eu
launcher_directory=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec "$launcher_directory/.venv/bin/project-infra-desktop" "$@"
EOF
chmod +x "$target/project-infra" "$target/project-infra-desktop"

"$target/project-infra" --version
echo "Installed locally. Run from your project directory:"
echo "  '$target/project-infra' init"
echo "  '$target/project-infra' serve --port 8765"
echo "Optional desktop launcher (requires Tk):"
echo "  '$target/project-infra-desktop'"
