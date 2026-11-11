/** Add the shared workbench theme to a standalone module document. */
export function themedDocument(html, module, requestUrl) {
  const path = new URL(requestUrl).pathname.replace(/^\/geo_monitor(?=\/)/, "");
  const directories = path.split("/").slice(1, -1).filter(Boolean).length;
  const relative = "../".repeat(directories) || "./";
  return html.replace(/<html\b/i, `<html data-workbench="${module}"`)
    .replace(/<\/head>/i, `<link rel="stylesheet" href="${relative}workbench-theme.css"></head>`);
}
