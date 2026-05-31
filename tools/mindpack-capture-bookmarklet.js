/*
Mindpack visible-chat export bookmarklet source.

Best-effort behavior:
- Exports selected text if the user selected text.
- Otherwise exports visible text from main/article/body.
- Downloads a local Markdown file.
- Makes no network requests.
- Does not include the full page URL by default.

Limitations:
- May miss collapsed, unloaded, virtualized, image-only, or attachment content.
- May include UI chrome.
- Does not bypass provider permissions or official export flows.
*/

(() => {
  const now = new Date().toISOString();
  const host = location.hostname || "local";
  const selected = window.getSelection ? String(window.getSelection()).trim() : "";
  const captureMode = selected ? "selection" : "visible-page";
  let text = selected;

  if (!text) {
    const root = document.querySelector("main, [role='main'], article") || document.body;
    const clone = root.cloneNode(true);

    clone
      .querySelectorAll(
        "script, style, noscript, svg, canvas, button, input, textarea, select, nav, header, footer, [aria-hidden='true']"
      )
      .forEach((node) => node.remove());

    text = clone.innerText || "";
  }

  text = text
    .split("\n")
    .map((line) => line.replace(/\s+/g, " ").trim())
    .filter(Boolean)
    .filter((line, index, lines) => index === 0 || line !== lines[index - 1])
    .join("\n");

  const header = [
    "---",
    "mindpack_export: visible-chat.v0",
    `exported_at: ${JSON.stringify(now)}`,
    `source_host: ${JSON.stringify(host)}`,
    `capture_mode: ${JSON.stringify(captureMode)}`,
    "source_url_redacted: true",
    "---",
    "",
    "<!--",
    "Best-effort visible-text export. Review locally before ingestion.",
    "Add explicit ontology tags like Concept:, Must:, Avoid:, Prefer:, Preference:, Claim:, or Case: to lines you want Mindpack to extract.",
    "-->",
    "",
  ].join("\n");

  const blob = new Blob([header + text + "\n"], {
    type: "text/markdown;charset=utf-8",
  });

  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);

  const safeHost = host.replace(/[^a-z0-9.-]+/gi, "-").slice(0, 80) || "chat";
  link.download = `mindpack-visible-chat-${safeHost}-${now.slice(0, 10)}.md`;

  document.body.appendChild(link);
  link.click();

  setTimeout(() => {
    URL.revokeObjectURL(link.href);
    link.remove();
  }, 1000);
})();
