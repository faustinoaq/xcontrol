#!/usr/bin/env bash
set -euo pipefail
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
bin="${HOME}/.local/bin"
skill="${CODEX_HOME:-$HOME/.codex}/skills/xcontrol"
mkdir -p "$bin" "$(dirname "$skill")"
for name in xc xcontrol; do
  if [[ -e "$bin/$name" || -L "$bin/$name" ]]; then
    [[ "$(readlink -f "$bin/$name")" == "$root/bin/xc" ]] || { echo "Refusing to overwrite $bin/$name" >&2; exit 1; }
  fi
done
if [[ -e "$skill" || -L "$skill" ]]; then
  [[ "$(readlink -f "$skill")" == "$root/skills/xcontrol" ]] || { echo "Refusing to overwrite $skill" >&2; exit 1; }
fi
ln -sfn "$root/bin/xc" "$bin/xc"
ln -sfn "$root/bin/xc" "$bin/xcontrol"
ln -sfn "$root/skills/xcontrol" "$skill"
echo "Installed xc, xcontrol, and the skill (linked for Codex). Add $bin to PATH if needed."
