from pathlib import Path

path = Path("_site/index.html")
html = path.read_text(encoding="utf-8")

script = r'''
<script id="bt-import-screenshot-paste">
(() => {
  "use strict";
  document.addEventListener("paste", event => {
    const modal = document.querySelector(".bt-import-modal");
    if (!modal) return;
    const item = [...(event.clipboardData?.items || [])].find(x => String(x.type || "").startsWith("image/"));
    if (!item) return;
    const blob = item.getAsFile();
    if (!blob) return;
    const input = modal.querySelector('input[type="file"][accept*="image"]') || modal.querySelector('input[type="file"]');
    if (!input) return;
    event.preventDefault();
    try {
      const ext = String(blob.type || "").includes("jpeg") ? "jpg" : "png";
      const pastedFile = new File([blob], `snipping-tool-${Date.now()}.${ext}`, { type: blob.type || "image/png" });
      const transfer = new DataTransfer();
      transfer.items.add(pastedFile);
      input.files = transfer.files;
      input.dispatchEvent(new Event("change", { bubbles: true }));
      const progress = modal.querySelector(".bt-import-progress");
      if (progress) progress.textContent = "Screenshot pasted. Ready to scan.";
    } catch (err) {
      console.error("Screenshot paste failed", err);
      const progress = modal.querySelector(".bt-import-progress");
      if (progress) progress.textContent = "Could not paste that screenshot. Use the file picker instead.";
    }
  }, true);
})();
</script>
'''

marker = "</body>"
if marker not in html:
    raise SystemExit("Could not find body close")
html = html.replace(marker, script + "\n" + marker, 1)
path.write_text(html, encoding="utf-8")
print("Applied Import Screenshot paste patch")
