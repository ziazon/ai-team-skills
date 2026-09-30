#!/usr/bin/env python3
"""directory_lint.py -- check a plugin folder against the directory's rules.

`claude plugin validate --strict` checks that a plugin is well-formed and
nothing more. The directory's own Validate step (in the developer portal)
also checks the rows of Anthropic's plugin pre-submission checklist:
https://claude.com/docs/plugins/pre-submission-checklist

This lint encodes the mechanical rows of that checklist, so a finding shows up
before a release instead of a review cycle after it. It is a local
approximation, not the portal: it cannot see other listings (so it cannot say
a name is taken or confusable), and its credential and download-and-run
checks are line heuristics. Run the portal's Validate before a first
submission all the same.

Each finding carries the checklist's result:
  BLOCK  the portal refuses the submission
  HOLD   an Anthropic reviewer must clear the version before it goes live
  WARN   shown, does not stop anything
  NOTE   information only
BLOCK and HOLD fail the run (exit 1): a hold costs a review cycle, which is
what this lint exists to save. Output names the file, the line and the rule,
never the line's text, so a credential on that line is not echoed.

Usage: directory_lint.py <plugin-dir>
"""

import json
import os
import re
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

KIB = 1024
MIB = 1024 * KIB
SEVERITY_ORDER = ("BLOCK", "HOLD", "WARN", "NOTE")

SYSTEM_FILES = {".ds_store", "thumbs.db", "desktop.ini"}
WINDOWS_DEVICES = {"con", "prn", "aux", "nul"} | {f"com{i}" for i in range(1, 10)} | {f"lpt{i}" for i in range(1, 10)}
RESERVED_NAMES = {"claude", "anthropic", "official", "plugin", "mcp", "test"}
OFFICIAL_WORDS = {"claude", "anthropic", "official"}
COMPONENT_DIRS = {"skills", "commands", "agents", "hooks"}
COMPONENT_KEYS = {"hooks", "mcpServers", "lspServers", "commands", "agents", "skills", "outputStyles"}
PACKAGE_SOURCE_CONFIGS = {".npmrc", ".yarnrc", ".yarnrc.yml", "bunfig.toml", "uv.toml", "pip.conf"}
LOCKFILES = {"package-lock.json", "npm-shrinkwrap.json", "bun.lock", "bun.lockb"}
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}
NAME_RE = re.compile(r"^[a-z0-9]([a-z0-9-]{0,62}[a-z0-9])?$")

# Launchers that download a package and run it, and how each spells a pin.
LAUNCHER_RE = re.compile(r"(?<![\w-])(npx|bunx|uvx|pnpm\s+dlx|yarn\s+dlx|pipx\s+run|uv\s+run)((?:\s+-{1,2}[\w-]+)*)\s+([^\s;|&'\"`)]+)")
NODE_PIN_RE = re.compile(r"^@?[^@\s]+@\d+\.\d+\.\d+([-+][\w.]+)?$")
PY_PIN_RE = re.compile(r"^[\w.\-\[\]]+==\d+(\.\d+)*$")
PIPE_TO_SHELL_RE = re.compile(r"\b(curl|wget)\b[^|\n]*\|\s*(sudo\s+)?(ba|z)?sh\b")

# Whole underscore-separated words, so MAX_TOKENS and AUTHOR are not credentials.
CREDENTIAL_NAME_RE = re.compile(r"(^|_)(TOKEN|SECRET|PASSWORD|PASSWD|CREDENTIALS?|AUTH|APIKEY|(API|ACCESS|PRIVATE)_KEY)(_|$)")
ENV_REF_RES = (
    re.compile(r"\$\{?([A-Z][A-Z0-9_]*)\}?"),
    re.compile(r"process\.env\.([A-Z][A-Z0-9_]*)"),
    re.compile(r"os\.environ(?:\.get)?\(?\[?[\"']([A-Z][A-Z0-9_]*)"),
    re.compile(r"os\.getenv\([\"']([A-Z][A-Z0-9_]*)"),
)
SEND_RE = re.compile(r"\bcurl\b|\bwget\b|https?://|Authorization|Bearer|fetch\(|requests\.|urllib|--header|(?<!\w)-H\s")
CREDENTIAL_FILE_RE = re.compile(
    r"(?:~|\$HOME|\$\{HOME\})/\.(s3cfg|netrc|npmrc|pypirc|git-credentials|aws/credentials|"
    r"docker/config\.json|config/gh/hosts\.yml|ssh/id_\w+)"
)
INLINE_SHELL_RE = re.compile(r"!`[^`\n]+`")
FENCE_RE = re.compile(r"^\s*(```|~~~)")


@dataclass(frozen=True)
class Finding:
    severity: str
    path: str
    line: Optional[int]
    message: str

    def render(self) -> str:
        where = self.path if self.line is None else f"{self.path}:{self.line}"
        return f"directory-lint: {self.severity} {where}: {self.message}"


def _sniff(data: bytes) -> str:
    """Return 'image', 'font', 'text' or 'binary'."""
    if data.startswith(b"\x89PNG\r\n\x1a\n") or data.startswith(b"\xff\xd8\xff") or data[:6] in (b"GIF87a", b"GIF89a"):
        return "image"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image"
    if data[:4] in (b"wOFF", b"wOF2", b"OTTO", b"ttcf", b"true", b"\x00\x01\x00\x00"):
        return "font"
    if b"\x00" in data[:8192]:
        return "binary"
    try:
        data.decode("utf-8")
    except UnicodeDecodeError:
        return "binary"
    return "text"


def check_case_collisions(paths: List[str]) -> List[Finding]:
    seen = {}
    found = []
    for p in sorted(paths):
        key = p.lower()
        if key in seen and seen[key] != p:
            found.append(Finding("BLOCK", p, None, f"differs from {seen[key]} only by capitalization"))
        seen.setdefault(key, p)
    return found


def _check_entry_name(rel: str, name: str) -> List[Finding]:
    found = []
    if name.lower() in SYSTEM_FILES or name == "__MACOSX":
        found.append(Finding("BLOCK", rel, None, "a macOS or Windows system file; remove it"))
    stem = name.split(".", 1)[0].lower()
    if ":" in name or name.endswith((".", " ")) or stem in WINDOWS_DEVICES:
        found.append(Finding("BLOCK", rel, None, "file name is not valid on Windows (colon, trailing dot/space, or a device name)"))
    return found


def _strip_fences(text: str) -> str:
    kept, fenced = [], False
    for line in text.splitlines():
        if FENCE_RE.match(line):
            fenced = not fenced
            continue
        if not fenced:
            kept.append(line)
    return "\n".join(kept)


def _scripts(value: str) -> set:
    scripts = set()
    for ch in value:
        if ch.isalpha():
            scripts.add(unicodedata.name(ch, "UNKNOWN").split(" ")[0])
    return scripts


def _check_manifest(root: Path) -> Tuple[List[Finding], dict]:
    rel = ".claude-plugin/plugin.json"
    path = root / rel
    if not path.is_file():
        return [Finding("BLOCK", rel, None, "no .claude-plugin/plugin.json in the plugin folder")], {}
    try:
        manifest = json.loads(path.read_text())
    except (ValueError, UnicodeDecodeError) as exc:
        return [Finding("BLOCK", rel, None, f"plugin.json is not valid JSON ({exc.__class__.__name__})")], {}
    if not isinstance(manifest, dict):
        return [Finding("BLOCK", rel, None, "plugin.json is not a JSON object")], {}

    found = []
    name = manifest.get("name")
    if not isinstance(name, str) or not name:
        found.append(Finding("BLOCK", rel, None, "name is missing"))
    elif not name.isascii():
        found.append(Finding("BLOCK", rel, None, "name has non-ASCII characters"))
    else:
        if not NAME_RE.match(name):
            found.append(Finding("WARN", rel, None, "name should be lowercase letters, digits and hyphens, starting and ending with a letter or digit"))
        if name.lower() in RESERVED_NAMES:
            found.append(Finding("BLOCK", rel, None, f"name {name!r} is a reserved word"))
        elif OFFICIAL_WORDS & set(name.lower().split("-")):
            found.append(Finding("HOLD", rel, None, "name contains a word that can present the plugin as official"))

    author = manifest.get("author")
    labels = {"displayName": manifest.get("displayName"), "author.name": author.get("name") if isinstance(author, dict) else None}
    for label, value in labels.items():
        if not isinstance(value, str):
            continue
        if any(unicodedata.category(ch) == "Cf" for ch in value):
            found.append(Finding("BLOCK", rel, None, f"{label} has an invisible character"))
        elif len(_scripts(value)) > 1:
            found.append(Finding("BLOCK", rel, None, f"{label} mixes writing systems"))

    for key in ("description", "author", "version"):
        if not manifest.get(key):
            found.append(Finding("WARN", rel, None, f"{key} is not set"))

    experimental = manifest.get("experimental")
    if isinstance(experimental, dict) and COMPONENT_KEYS & set(experimental):
        found.append(Finding("BLOCK", rel, None, "component keys belong at the top level, not inside experimental"))

    if manifest.get("hooks") in ("./hooks/hooks.json", "hooks/hooks.json"):
        found.append(Finding("WARN", rel, None, "hooks names hooks/hooks.json; Claude Code loads it automatically"))
    return found, manifest


def _check_readme_and_license(root: Path, manifest: dict) -> List[Finding]:
    found = []
    readmes = [p for p in root.iterdir() if p.is_file() and p.name.lower().startswith("readme")]
    if not readmes:
        found.append(Finding("BLOCK", "README.md", None, "README missing"))
    else:
        readme = sorted(readmes, key=lambda p: p.name != "README.md")[0]
        words = re.findall(r"[^\W_]+(?:['’-][^\W_]+)*", _strip_fences(readme.read_text(errors="replace")))
        if len(words) < 40:
            found.append(Finding("BLOCK", readme.name, None, f"README too short ({len(words)} words outside code; 40 needed)"))
    has_license_file = any(p.is_file() and p.name.lower().startswith(("license", "licence", "copying")) for p in root.iterdir())
    if not has_license_file and not manifest.get("license"):
        found.append(Finding("BLOCK", "LICENSE", None, "license missing: add a LICENSE file or set license in plugin.json"))
    return found


def _commands(node) -> List[str]:
    """Every command string a hook or server declaration would run."""
    out = []
    if isinstance(node, dict):
        cmd = node.get("command")
        if isinstance(cmd, str):
            args = node.get("args") if isinstance(node.get("args"), list) else []
            out.append(" ".join([cmd] + [str(a) for a in args]))
        for key, value in node.items():
            if key not in ("command", "args"):
                out.extend(_commands(value))
    elif isinstance(node, list):
        for value in node:
            out.extend(_commands(value))
    return out


def _check_mcp_servers(rel: str, servers) -> List[Finding]:
    found = []
    if not isinstance(servers, dict):
        return found
    for name, server in servers.items():
        if not isinstance(server, dict):
            found.append(Finding("BLOCK", rel, None, f"MCP server {name!r} is not an object"))
            continue
        if "url" in server or server.get("type") in ("http", "sse", "ws"):
            url = server.get("url", "")
            if server.get("type") not in ("http", "sse", "ws"):
                found.append(Finding("BLOCK", rel, None, f"remote MCP server {name!r} needs type http, sse or ws"))
            if not (url == "" or url.startswith(("https://", "wss://", "${user_config."))):
                found.append(Finding("BLOCK", rel, None, f"remote MCP server {name!r} URL is not https or wss"))
            if isinstance(url, str) and url.endswith((".mcpb", ".dxt")):
                found.append(Finding("BLOCK", rel, None, f"MCP server {name!r} fetches a bundle from a URL"))
            continue
        command = str(server.get("command", ""))
        args = [str(a) for a in server.get("args", [])] if isinstance(server.get("args"), list) else []
        if any(part.endswith((".mcpb", ".dxt")) for part in [command] + args):
            found.append(Finding("HOLD", rel, None, f"MCP server {name!r} is a .mcpb/.dxt bundle the validator does not inspect"))
        base = os.path.basename(command)
        if (base in ("bash", "sh", "zsh") and "-c" in args) or (base in ("python", "python3", "node") and ("-c" in args or "-e" in args)) \
                or (base in ("npm", "pnpm", "yarn", "bun") and "run" in args):
            found.append(Finding("HOLD", rel, None, f"MCP server {name!r} starts through a shell, inline program or package script"))
    return found


def _check_runtime_json(root: Path, manifest: dict) -> Tuple[List[Finding], List[Tuple[str, str]]]:
    """hooks.json and .mcp.json structure; returns findings and (path, command) pairs."""
    found, commands = [], []
    hooks_path = root / "hooks" / "hooks.json"
    if hooks_path.is_file():
        try:
            hooks = json.loads(hooks_path.read_text())
        except ValueError:
            hooks = None
            found.append(Finding("BLOCK", "hooks/hooks.json", None, "hooks.json is invalid JSON"))
        if hooks is not None:
            if not isinstance(hooks, dict) or not isinstance(hooks.get("hooks"), dict):
                found.append(Finding("BLOCK", "hooks/hooks.json", None, "hooks.json needs a top-level hooks object"))
            else:
                for url in re.findall(r'"url"\s*:\s*"([^"]*)"', json.dumps(hooks)):
                    if not url.startswith("https://"):
                        found.append(Finding("BLOCK", "hooks/hooks.json", None, "an HTTP hook URL is not https"))
                commands += [("hooks/hooks.json", c) for c in _commands(hooks)]
    mcp_path = root / ".mcp.json"
    if mcp_path.is_file():
        try:
            mcp = json.loads(mcp_path.read_text())
        except ValueError:
            mcp = None
            found.append(Finding("BLOCK", ".mcp.json", None, ".mcp.json can't be parsed"))
        if isinstance(mcp, dict):
            found += _check_mcp_servers(".mcp.json", mcp.get("mcpServers", {}))
            commands += [(".mcp.json", c) for c in _commands(mcp)]
    if isinstance(manifest.get("mcpServers"), dict):
        found += _check_mcp_servers(".claude-plugin/plugin.json", manifest["mcpServers"])
    for key in ("hooks", "mcpServers"):
        if isinstance(manifest.get(key), (dict, list)):
            commands += [(".claude-plugin/plugin.json", c) for c in _commands(manifest[key])]
    return found, commands


def _launcher_findings(rel: str, line: Optional[int], text: str, runtime: bool) -> List[Finding]:
    found = []
    for match in LAUNCHER_RE.finditer(text):
        launcher = re.sub(r"\s+", " ", match.group(1))
        package = match.group(3)
        if not runtime:
            found.append(Finding("WARN", rel, line, f"download-and-run example ({launcher}); fine in docs, held if a hook or server runs it"))
            continue
        if launcher == "uv run":
            pinned = bool(re.search(r"--(locked|frozen)\b", text))
        elif launcher in ("uvx", "pipx run"):
            pinned = bool(PY_PIN_RE.match(package))
        else:
            pinned = bool(NODE_PIN_RE.match(package))
        if pinned:
            found.append(Finding("HOLD", rel, line, f"runs a pinned {launcher} package; a reviewer always checks these"))
        else:
            found.append(Finding("BLOCK", rel, line, f"{launcher} package is not pinned to an exact version"))
    if not runtime and PIPE_TO_SHELL_RE.search(text):
        found.append(Finding("WARN", rel, line, "download-and-run example (pipes a download into a shell)"))
    return found


def _code_spans(line: str, fenced: bool) -> List[str]:
    return [line] if fenced else re.findall(r"`([^`\n]+)`", line)


def _check_text_file(rel: str, text: str, image_names: list, is_component: bool, runtime: bool) -> List[Finding]:
    found = []
    fenced = False
    for number, line in enumerate(text.splitlines(), start=1):
        if FENCE_RE.match(line):
            fenced = not fenced
            continue
        found += _launcher_findings(rel, number, line, runtime)
        if SEND_RE.search(line):
            for pattern in ENV_REF_RES:
                for var in pattern.findall(line):
                    if CREDENTIAL_NAME_RE.search(var):
                        found.append(Finding("HOLD", rel, number, f"sends ${var}, a credential from the user's machine; ask for it through userConfig"))
        if CREDENTIAL_FILE_RE.search(line):
            found.append(Finding("HOLD", rel, number, "reads a credential file from the user's machine"))
        if image_names and any(pattern.search(span) for span in _code_spans(line, fenced) for pattern in image_names):
            found.append(Finding("HOLD", rel, number, "a bundled image is named in code; show it with Markdown image syntax instead"))
        if is_component and INLINE_SHELL_RE.search(line):
            found.append(Finding("NOTE", rel, number, "inline shell span (!`...`) runs when the skill loads"))
    return found


def _check_front_matter(rel: str, text: str) -> List[Finding]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return [Finding("WARN", rel, None, "no front matter; add one with a description")]
    try:
        end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    except StopIteration:
        return [Finding("BLOCK", rel, 1, "front matter is never closed with ---")]
    block = lines[1:end]
    for i, line in enumerate(block):
        m = re.match(r"^description:\s*(.*)$", line)
        if not m:
            continue
        value = m.group(1).strip()
        following = next((l for l in block[i + 1:] if l.strip()), "")
        if value.startswith("[") or (not value and following.lstrip().startswith("- ")):
            return [Finding("BLOCK", rel, i + 2, "description must be a single text value, not a list")]
        return []
    return [Finding("WARN", rel, None, "front matter has no description")]


def lint(root: Path) -> List[Finding]:
    root = Path(root)
    found: List[Finding] = []
    files, entries, total = [], [], 0

    for dirpath, dirnames, filenames in os.walk(root):
        base = Path(dirpath)
        if base == root and ".git" in dirnames:
            dirnames.remove(".git")
        for name in list(dirnames) + filenames:
            path = base / name
            rel = path.relative_to(root).as_posix()
            entries.append(rel)
            found += _check_entry_name(rel, name)
            if path.is_symlink():
                found.append(Finding("BLOCK", rel, None, "a symbolic link; commit a regular file or folder instead"))
                if name in dirnames:
                    dirnames.remove(name)
            elif name in filenames:
                files.append(rel)
                total += path.stat().st_size

    found += check_case_collisions(entries)
    if len(entries) >= 10000:
        found.append(Finding("BLOCK", ".", None, f"{len(entries)} files and folders; the directory needs fewer than 10,000"))
    if total > 256 * MIB:
        found.append(Finding("BLOCK", ".", None, "over 256 MiB unpacked"))
    if len(files) > 512:
        found.append(Finding("HOLD", ".", None, f"{len(files)} files; more than 512 is held for a reviewer"))

    manifest_findings, manifest = _check_manifest(root)
    found += manifest_findings
    found += _check_readme_and_license(root, manifest)
    runtime_findings, commands = _check_runtime_json(root, manifest)
    found += runtime_findings
    for rel, command in commands:
        found += _launcher_findings(rel, None, command, runtime=True)

    for entry in entries:
        top = entry.split("/", 1)[0]
        if "/" not in entry and top.lower() in COMPONENT_DIRS and top != top.lower() and (root / top).is_dir():
            found.append(Finding("BLOCK", entry, None, f"component folder must be spelled {top.lower()}/"))
    skills_dir = root / "skills"
    if skills_dir.is_dir():
        for skill in sorted(p for p in skills_dir.iterdir() if p.is_dir() and not p.is_symlink()):
            names = [p.name for p in skill.iterdir()]
            if "SKILL.md" not in names and any(n.lower() == "skill.md" for n in names):
                found.append(Finding("BLOCK", f"skills/{skill.name}", None, "skill file must be spelled SKILL.md"))

    # Bounded by non-name characters, so icon.svg does not match favicon.svg.
    image_names = [re.compile(r"(?<![\w.-])" + re.escape(Path(f).name) + r"(?![\w.-])")
                   for f in files if Path(f).suffix.lower() in IMAGE_EXTS]
    for rel in files:
        path = root / rel
        data = path.read_bytes()
        kind = _sniff(data)
        size = len(data)
        if size > 5 * MIB:
            found.append(Finding("BLOCK", rel, None, "over 5 MiB"))
        if kind in ("image", "font") or rel.lower().endswith(".svg"):
            continue
        if size > 256 * KIB:
            found.append(Finding("HOLD", rel, None, "over 256 KiB; the validator will not inspect it"))
        if kind == "binary":
            found.append(Finding("HOLD", rel, None, "a binary file other than an image or font"))
            continue
        text = data.decode("utf-8")
        parts = rel.split("/")
        is_component = parts[0] in ("skills", "commands", "agents") and rel.endswith(".md")
        runtime = parts[0] == "hooks" and not rel.endswith(".json")
        found += _check_text_file(rel, text, image_names, is_component, runtime)
        if parts[-1] == ".gitattributes":
            for number, line in enumerate(text.splitlines(), start=1):
                for attr in ("export-ignore", "export-subst", "filter="):
                    if attr in line:
                        found.append(Finding("BLOCK", rel, number, f".gitattributes uses {attr.rstrip('=')}"))
        if (parts[0] == "skills" and parts[-1] == "SKILL.md") or (parts[0] in ("commands", "agents") and rel.endswith(".md")):
            found += _check_front_matter(rel, text)

    has_launcher = any(f.path in (".mcp.json", "hooks/hooks.json", ".claude-plugin/plugin.json") or f.path.startswith("hooks/")
                       for f in found if "pinned" in f.message)
    has_install = (root / "package.json").is_file() or any(re.search(r"\b(npm|pnpm|yarn|bun|pip)\s+(install|add|i)\b", c) for _, c in commands)
    for rel in files:
        if Path(rel).name in PACKAGE_SOURCE_CONFIGS:
            if has_launcher:
                found.append(Finding("BLOCK", rel, None, "sets a package source while the plugin runs a launcher"))
            elif has_install:
                found.append(Finding("HOLD", rel, None, "install may use a custom registry or package source"))
    if (root / "package.json").is_file() and any((root / lock).is_file() for lock in LOCKFILES):
        found.append(Finding("HOLD", "package.json", None, "dependencies install from a lockfile when a user installs the plugin"))

    unique = list(dict.fromkeys(found))
    return sorted(unique, key=lambda f: (SEVERITY_ORDER.index(f.severity), f.path, f.line or 0))


def main(argv: List[str]) -> int:
    if len(argv) != 1 or not Path(argv[0]).is_dir():
        print("usage: directory_lint.py <plugin-dir>", file=sys.stderr)
        return 2
    root = Path(argv[0])
    found = lint(root)
    for finding in found:
        print(finding.render(), file=sys.stderr if finding.severity in ("BLOCK", "HOLD") else sys.stdout)
    counts = {s: sum(1 for f in found if f.severity == s) for s in SEVERITY_ORDER}
    if counts["BLOCK"] or counts["HOLD"]:
        print(f"directory-lint: REFUSED -- {counts['BLOCK']} blocking, {counts['HOLD']} held, "
              f"{counts['WARN']} warning(s)", file=sys.stderr)
        return 1
    print(f"directory-lint: clean -- {counts['WARN']} warning(s), {counts['NOTE']} note(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
