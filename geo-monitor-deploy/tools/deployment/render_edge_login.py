"""Embed the workbench login page in the edge auth service's Python source."""

import argparse
import ast
import base64
import hashlib
import re
import sys
from pathlib import Path


LOGIN_POLICY = (
    "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; "
    "base-uri 'none'; frame-ancestors 'none'"
)
CSP_HEADER = re.compile(
    r'^(\s*self\.send_header\("Content-Security-Policy", )("[^"\n]+")(\))$',
    re.MULTILINE,
)


def render_page(template: str, dashboard: Path) -> str:
    theme = (dashboard / "public/workbench-theme.css").read_text(encoding="utf-8")
    logo = (dashboard / "app/WorkbenchLogo.tsx").read_text(encoding="utf-8")
    tokens = re.search(r"^:root\[data-workbench\]\s*\{[^}]*\}", theme, re.MULTILINE)
    svg = re.search(r"<svg\b.*?</svg>", logo, re.DOTALL)
    if not tokens or not svg:
        raise ValueError("Workbench theme tokens or logo are missing")
    for field in ("theme", "logo", "error", "next"):
        if template.count("{" + field + "}") != 1:
            raise ValueError(f"Expected one login template field for {field}")
    return template.replace("{theme}", tokens[0]).replace("{logo}", svg[0].replace("className=", "class="))


def update_source(source: str, page: str) -> str:
    assignments = [
        node.value for node in ast.parse(source).body
        if isinstance(node, ast.Assign)
        and len(node.targets) == 1
        and isinstance(node.targets[0], ast.Name)
        and node.targets[0].id == "LOGIN_HTML"
    ]
    if len(assignments) != 1 or not isinstance(ast.literal_eval(assignments[0]), str):
        raise ValueError("Expected one LOGIN_HTML string in the edge auth service")
    original = ast.get_source_segment(source, assignments[0])
    literal = '"""' + page.replace("\\", "\\\\").replace('"""', r'\"\"\"') + '"""'
    if not original or source.count(original) != 1 or ast.literal_eval(literal) != page:
        raise ValueError("Could not safely replace the login template")
    source = source.replace(original, literal, 1)

    scripts = re.findall(r"<script>(.*?)</script>", page, re.DOTALL)
    if len(scripts) != 1:
        raise ValueError("Expected one inline login script")
    script_hash = base64.b64encode(hashlib.sha256(scripts[0].encode("utf-8")).digest()).decode("ascii")
    policy = f"{LOGIN_POLICY}; script-src 'sha256-{script_hash}'; img-src data:"
    headers = list(CSP_HEADER.finditer(source))
    if len(headers) != 1 or not ast.literal_eval(headers[0][2]).startswith(LOGIN_POLICY):
        raise ValueError("Unexpected edge login Content Security Policy")
    start, end = headers[0].span(2)
    return source[:start] + '"' + policy + '"' + source[end:]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("auth", type=Path, help="Edge auth Python source")
    parser.add_argument("dashboard", type=Path, help="Dashboard directory containing app and public")
    parser.add_argument("template", type=Path, help="Workbench login HTML template")
    args = parser.parse_args()
    page = render_page(args.template.read_text(encoding="utf-8"), args.dashboard)
    source = update_source(args.auth.read_text(encoding="utf-8"), page)
    sys.stdout.buffer.write(source.encode("utf-8"))


if __name__ == "__main__":
    main()
