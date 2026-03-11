#!/usr/bin/env bash
set -euo pipefail

# ─────────────────────────────────────────────────────────
# Code Modernization Plugin — Installer
#
# Installs the plugin into a target project directory.
#
# Usage:
#   ./install.sh                    # Install into current directory
#   ./install.sh /path/to/project   # Install into specified directory
#   ./install.sh --dry-run          # Show what would be installed
# ─────────────────────────────────────────────────────────

PLUGIN_DIR="$(cd "$(dirname "$0")" && pwd)"
TARGET_DIR=""
DRY_RUN=false

# Parse arguments
for arg in "$@"; do
    case "$arg" in
        --dry-run) DRY_RUN=true ;;
        --help|-h)
            echo "Usage: $0 [TARGET_DIR] [--dry-run]"
            echo ""
            echo "Installs the Code Modernization Plugin into the target project."
            echo ""
            echo "What gets installed:"
            echo "  .claude/commands/   — 8 slash commands (/modernize, /codemap, /elicit, etc.)"
            echo "  .claude/agents/     — 4 subagents (code-analyzer, cobol-documenter, etc.)"
            echo "  .claude/hooks.json  — Validation hooks (merged into settings.json)"
            echo "  .modernization/     — Python scripts (analyzer, graph store, scorer, etc.)"
            echo "  artifacts/          — Output directory for generated artifacts"
            echo "  modernization.config.json — Project configuration (from template)"
            echo "  CLAUDE.md           — Project guide (from template, if none exists)"
            exit 0
            ;;
        *)
            TARGET_DIR="$arg"
            ;;
    esac
done

# Default to current directory if no target specified
TARGET_DIR="${TARGET_DIR:-.}"

TARGET_DIR="$(cd "$TARGET_DIR" 2>/dev/null && pwd || echo "$TARGET_DIR")"

echo "╔══════════════════════════════════════════════════╗"
echo "║   Code Modernization Plugin — Installer          ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""
echo "  Plugin source: $PLUGIN_DIR"
echo "  Target:        $TARGET_DIR"
echo ""

if [ "$DRY_RUN" = true ]; then
    echo "  [DRY RUN] — No files will be modified."
    echo ""
fi

# ─── Helper functions ───────────────────────────────────

install_dir() {
    local src="$1" dst="$2" label="$3"
    if [ "$DRY_RUN" = true ]; then
        echo "  [DRY] Would copy $src → $dst"
        return
    fi
    mkdir -p "$dst"
    cp -R "$src"/* "$dst"/ 2>/dev/null || true
    # Remove .DS_Store files
    find "$dst" -name ".DS_Store" -delete 2>/dev/null || true
    echo "  ✓ $label"
}

install_file() {
    local src="$1" dst="$2" label="$3"
    if [ "$DRY_RUN" = true ]; then
        echo "  [DRY] Would copy $src → $dst"
        return
    fi
    mkdir -p "$(dirname "$dst")"
    cp "$src" "$dst"
    echo "  ✓ $label"
}

install_template() {
    local src="$1" dst="$2" label="$3"
    if [ -f "$dst" ]; then
        echo "  ⊘ $label (already exists, skipping)"
        return
    fi
    if [ "$DRY_RUN" = true ]; then
        echo "  [DRY] Would create $dst from template"
        return
    fi
    mkdir -p "$(dirname "$dst")"
    cp "$src" "$dst"
    echo "  ✓ $label (created from template)"
}

# ─── Install ────────────────────────────────────────────

echo "Installing..."
echo ""

# 1. Slash commands
echo "  Slash commands:"
install_dir "$PLUGIN_DIR/commands" "$TARGET_DIR/.claude/commands" "    /modernize, /codemap, /elicit, /query-slices, /claim-slice, /migrate, /validate, /batch"

# 2. Subagents
echo "  Subagents:"
install_dir "$PLUGIN_DIR/agents" "$TARGET_DIR/.claude/agents" "    code-analyzer, cobol-documenter, golden-dataset-builder, migration-scorer"

# 3. Hooks — merge into existing settings.json
echo "  Hooks:"
if [ "$DRY_RUN" = true ]; then
    echo "  [DRY] Would merge hooks into .claude/settings.json"
else
    SETTINGS_FILE="$TARGET_DIR/.claude/settings.json"
    HOOKS_FILE="$PLUGIN_DIR/hooks/hooks.json"

    if [ -f "$SETTINGS_FILE" ]; then
        if grep -q '"hooks"' "$SETTINGS_FILE" 2>/dev/null; then
            echo "  ⚠ $SETTINGS_FILE already has hooks. Review and merge manually."
            cp "$HOOKS_FILE" "$TARGET_DIR/.claude/hooks-modernization.json"
            echo "    Hooks saved to .claude/hooks-modernization.json for manual merge."
        else
            cp "$HOOKS_FILE" "$TARGET_DIR/.claude/hooks-modernization.json"
            echo "  ✓ Hooks saved to .claude/hooks-modernization.json"
            echo "    To activate: merge into .claude/settings.json"
        fi
    else
        mkdir -p "$TARGET_DIR/.claude"
        cp "$HOOKS_FILE" "$SETTINGS_FILE"
        echo "  ✓ Created .claude/settings.json with hooks"
    fi
fi

# 4. Python scripts
echo "  Scripts:"
install_dir "$PLUGIN_DIR/scripts" "$TARGET_DIR/.modernization/scripts" "    codemap, graph, validation scripts → .modernization/scripts/"

# 5. Artifacts directory
echo "  Artifacts:"
if [ "$DRY_RUN" = true ]; then
    echo "  [DRY] Would create artifacts/"
else
    mkdir -p "$TARGET_DIR/artifacts"
    touch "$TARGET_DIR/artifacts/.gitkeep"
    echo "  ✓ Created artifacts/ directory"
fi

# 6. Config file (from template, only if not present)
echo "  Configuration:"
install_template "$PLUGIN_DIR/templates/modernization.config.template.json" \
    "$TARGET_DIR/modernization.config.json" \
    "    modernization.config.json"

# 7. Semantic diff rules template
install_template "$PLUGIN_DIR/templates/semantic-diff-rules.template.json" \
    "$TARGET_DIR/artifacts/semantic-diff-rules.json" \
    "    artifacts/semantic-diff-rules.json"

# 8. Slice manifest schema (reference)
install_file "$PLUGIN_DIR/templates/slice-manifest.schema.json" \
    "$TARGET_DIR/.modernization/schemas/slice-manifest.schema.json" \
    "    Slice manifest schema → .modernization/schemas/"

# 9. CLAUDE.md (from template, only if not present)
echo "  Project guide:"
install_template "$PLUGIN_DIR/templates/CLAUDE.md.template" \
    "$TARGET_DIR/CLAUDE.md" \
    "    CLAUDE.md"

# ─── Done ───────────────────────────────────────────────

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║   Installation complete!                          ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""
echo "  Next steps:"
echo "  1. Edit modernization.config.json with your project details"
echo "  2. Run: /codemap                    (discover your codebase)"
echo "  3. Run: /elicit orientation          (interview stakeholders)"
echo "  4. Run: /modernize                   (full pipeline)"
echo ""
echo "  Available commands:"
echo "    /modernize      — Full orchestration pipeline"
echo "    /codemap        — Codebase discovery (shallow/deep)"
echo "    /elicit         — Stakeholder interviews (6 sessions)"
echo "    /query-slices   — View migration slices"
echo "    /claim-slice    — Claim a slice for migration"
echo "    /migrate        — Migrate a claimed slice"
echo "    /validate       — Run validation & scoring"
echo "    /batch          — Bulk migration operations"
echo ""
