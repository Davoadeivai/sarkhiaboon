import re, zipfile, shutil, os, sys
src = sys.argv[1]
tmp = "_patch_tmp"
if os.path.exists(tmp): shutil.rmtree(tmp)
os.makedirs(tmp)
with zipfile.ZipFile(src) as z: z.extractall(tmp)
pth = os.path.join(tmp, "word", "document.xml")
c = open(pth, encoding="utf-8").read()
open(pth, "w", encoding="utf-8").write(re.sub(r'(<w:sectPr[^>]*>)', r'\1<w:bidi/>', c))
os.remove(src)
zf = zipfile.ZipFile(src, "w", zipfile.ZIP_DEFLATED)
for root, d, files in os.walk(tmp):
    for f in files:
        full = os.path.join(root, f)
        zf.write(full, os.path.relpath(full, tmp))
zf.close()
shutil.rmtree(tmp)
print("patched", src)
