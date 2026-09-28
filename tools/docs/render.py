from playwright.sync_api import sync_playwright
import sys
src, out = sys.argv[1], sys.argv[2]
with sync_playwright() as p:
    b = p.chromium.launch()
    page = b.new_page()
    page.goto("file://" + src)
    page.wait_for_timeout(500)
    page.pdf(path=out, format="A4", margin={"top": "18mm", "bottom": "18mm", "left": "16mm", "right": "16mm"},
             print_background=True, display_header_footer=True,
             header_template="<div></div>",
             footer_template='<div style="font-size:8px;width:100%;text-align:center;color:#94a3b8"><span class="pageNumber"></span> / <span class="totalPages"></span></div>')
    b.close()
