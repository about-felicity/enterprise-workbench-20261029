"""从 HTML 文件中提取所有 Tailwind 类名，生成对应的 CSS 规则"""
import re
import os

HTML_FILE = os.path.join(os.path.dirname(__file__), "index.html")

with open(HTML_FILE, "r", encoding="utf-8") as f:
    html = f.read()

# 提取所有 class="..." 中的类名
classes = set()
for m in re.finditer(r'class="([^"]*)"', html):
    for c in m.group(1).split():
        c = c.strip()
        if c:
            classes.add(c)

# 移除自定义类（我们有单独定义的）
custom = {"card","btn","btn-primary","btn-success","btn-danger","btn-warning",
           "btn-outline","btn-sm","input","select","table","badge","badge-green",
           "badge-blue","badge-yellow","badge-red","badge-gray","modal-overlay",
           "modal","tabs","tab","active","stat-card","stat-value","stat-label",
           "spin","sidebar","nav-item","page","empty-state","admin-only",
           "font-medium","font-semibold","font-bold"}
tw_classes = sorted(c for c in classes if c not in custom and c != "")

print(f"Found {len(tw_classes)} unique Tailwind classes")

# 生成 CSS
css_lines = ["/* 自动生成的 Tailwind CSS 工具类 */"]

# 定义已知的 Tailwind 类 → CSS 映射
rules = {
    # Display
    "block": "display:block", "inline-block": "display:inline-block",
    "inline-flex": "display:inline-flex", "flex": "display:flex",
    "inline": "display:inline", "grid": "display:grid", "hidden": "display:none",
    "contents": "display:contents",
    # Position
    "absolute": "position:absolute", "relative": "position:relative",
    "fixed": "position:fixed", "inset-0": "inset:0",
    "bottom-0": "bottom:0", "right-0": "right:0", "top-0": "top:0",
    # Flex
    "flex-1": "flex:1 1 0%", "flex-col": "flex-direction:column",
    "flex-wrap": "flex-wrap:wrap",
    "items-center": "align-items:center",
    "justify-center": "justify-content:center",
    "justify-between": "justify-content:space-between",
    "justify-end": "justify-content:flex-end",
    # Grid
    "grid-cols-1": "grid-template-columns:repeat(1,1fr)",
    "grid-cols-2": "grid-template-columns:repeat(2,1fr)",
    # Sizing
    "w-full": "width:100%", "w-5": "width:20px",
    "w-10": "width:2.5rem", "w-16": "width:4rem",
    "h-10": "height:2.5rem", "h-16": "height:4rem", "h-5": "height:20px",
    "min-h-screen": "min-height:100vh",
    "max-w-md": "max-width:28rem",
    "w-\\[240px\\]": "width:240px",
    "min-w-\\[240px\\]": "min-width:240px",
    "min-w-\\[200px\\]": "min-width:200px",
    "max-w-\\[150px\\]": "max-width:150px",
    # Spacing
    "p-3": "padding:0.75rem", "p-4": "padding:1rem",
    "p-5": "padding:1.25rem", "p-6": "padding:1.5rem",
    "p-8": "padding:2rem",
    "px-5": "padding-left:1.25rem;padding-right:1.25rem",
    "py-2": "padding-top:0.5rem;padding-bottom:0.5rem",
    "py-3": "padding-top:0.75rem;padding-bottom:0.75rem",
    "pt-3": "padding-top:0.75rem",
    "pr-2": "padding-right:0.5rem",
    "mb-1": "margin-bottom:0.25rem", "mb-4": "margin-bottom:1rem",
    "mb-6": "margin-bottom:1.5rem", "mt-1": "margin-top:0.25rem",
    "mt-auto": "margin-top:auto", "mx-auto": "margin:0 auto",
    "gap-1": "gap:0.25rem", "gap-2": "gap:0.5rem",
    "gap-3": "gap:0.75rem", "gap-4": "gap:1rem",
    "gap-6": "gap:1.5rem",
    # Space between
    "space-y-2": "", "space-y-3": "", "space-y-4": "",
    # Typography
    "text-xs": "font-size:0.75rem", "text-sm": "font-size:0.875rem",
    "text-base": "font-size:1rem", "text-lg": "font-size:1.125rem",
    "text-xl": "font-size:1.25rem", "text-2xl": "font-size:1.5rem",
    "font-bold": "font-weight:700", "font-semibold": "font-weight:600",
    "font-medium": "font-weight:500",
    "text-center": "text-align:center", "leading-none": "line-height:1",
    "whitespace-nowrap": "white-space:nowrap",
    # Text colors
    "text-white": "color:#fff",
    "text-gray-300": "color:#d1d5db", "text-gray-400": "color:#9ca3af",
    "text-gray-500": "color:#6b7280", "text-gray-600": "color:#4b5563",
    "text-gray-700": "color:#374151", "text-gray-800": "color:#1f2937",
    "text-blue-500": "color:#3b82f6", "text-blue-600": "color:#2563eb",
    "text-green-600": "color:#059669", "text-indigo-600": "color:#4f46e5",
    "text-red-500": "color:#ef4444",
    # Backgrounds
    "bg-white": "background:#fff",
    "bg-gray-50": "background:#f9fafb", "bg-gray-100": "background:#f3f4f6",
    "bg-gray-200": "background:#e5e7eb",
    "bg-blue-500": "background:#3b82f6", "bg-blue-600": "background:#2563eb",
    "bg-green-500": "background:#10b981", "bg-red-500": "background:#ef4444",
    "bg-yellow-500": "background:#f59e0b",
    "bg-indigo-50": "background:#eef2ff",
    # Gradient
    "bg-gradient-to-br": "background-image:linear-gradient(to bottom right,var(--tw-g-from),var(--tw-g-to))",
    "from-blue-50": "--tw-g-from:#eff6ff", "to-indigo-100": "--tw-g-to:#e0e7ff",
    # Borders
    "border": "border:1px solid #e5e7eb",
    "border-b": "border-bottom:1px solid #e5e7eb",
    "border-t": "border-top:1px solid #e5e7eb",
    "border-gray-50": "border-color:#f9fafb",
    "border-gray-600": "border-color:#4b5563",
    "rounded": "border-radius:0.25rem",
    "rounded-lg": "border-radius:0.5rem",
    "rounded-xl": "border-radius:0.75rem",
    "rounded-2xl": "border-radius:1rem",
    "rounded-full": "border-radius:9999px",
    # Shadows
    "shadow-sm": "box-shadow:0 1px 2px rgba(0,0,0,0.05)",
    "shadow-lg": "box-shadow:0 10px 15px -3px rgba(0,0,0,0.1)",
    # Overflow
    "overflow-auto": "overflow:auto", "overflow-hidden": "overflow:hidden",
    "overflow-y-auto": "overflow-y:auto",
    "truncate": "overflow:hidden;text-overflow:ellipsis;white-space:nowrap",
    # Transition
    "transition-all": "transition:all 0.2s",
    "transition": "transition:all 0.15s",
    # Cursor
    "cursor-pointer": "cursor:pointer",
    # Z-index
    "z-50": "z-index:50", "z-10": "z-index:10",
    # Hover states
    "hover\\:bg-gray-700": "",  # handled below
    # Opacity in border
    "border-gray-700\\/50": "border-color:rgba(55,65,81,0.5)",
    # Neg margins
    "-mr-2": "margin-right:-0.5rem",
    # Width/height auto
    "w-auto": "width:auto",
    # Special border styles
    "border-l": "border-left:1px solid #e5e7eb",
    "border-l-4": "border-left-width:4px",
}

# Output CSS
for cls in tw_classes:
    if cls == "hover\\:bg-gray-700":
        css_lines.append(".hover\\:bg-gray-700:hover{background:#374151}")
        continue
    if cls == "space-y-2":
        css_lines.append(".space-y-2>*+*{margin-top:0.5rem}")
        continue
    if cls == "space-y-3":
        css_lines.append(".space-y-3>*+*{margin-top:0.75rem}")
        continue
    if cls == "space-y-4":
        css_lines.append(".space-y-4>*+*{margin-top:1rem}")
        continue
    
    if cls in rules:
        css_lines.append(f".{cls}{{{rules[cls]}}}")
    else:
        print(f"  [未知] {cls}")

result = "\n".join(css_lines)
print(f"\nGenerated {len(css_lines)} CSS rules")
print(result[:200] + "...")
