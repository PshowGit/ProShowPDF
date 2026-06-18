import os, struct
os.environ["QT_QPA_PLATFORM"] = "offscreen"
from PySide6.QtGui import QGuiApplication, QImage, QPainter
from PySide6.Qtsvg import QSvgRenderer if False else None  # placeholder
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtCore import QByteArray, QBuffer, Qt

app = QGuiApplication([])

SVG = """<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 256 256'>
  <defs>
    <linearGradient id='bg' x1='0' y1='0' x2='1' y2='1'>
      <stop offset='0' stop-color='#7c5cff'/>
      <stop offset='1' stop-color='#4a8cff'/>
    </linearGradient>
  </defs>
  <rect x='8' y='8' width='240' height='240' rx='54' fill='url(#bg)'/>
  <path d='M88 56 H150 L182 88 V196 a10 10 0 0 1 -10 10 H88 a10 10 0 0 1 -10 -10 V66 a10 10 0 0 1 10 -10 Z' fill='#ffffff'/>
  <path d='M150 56 V82 a6 6 0 0 0 6 6 H182 Z' fill='#c9d4ff'/>
  <rect x='98' y='104' width='62' height='8' rx='4' fill='#dbe1f5'/>
  <rect x='98' y='122' width='46' height='8' rx='4' fill='#e6eaf7'/>
  <rect x='86' y='150' width='88' height='34' rx='9' fill='url(#bg)'/>
  <text x='130' y='173' font-family='Segoe UI, Arial, sans-serif' font-size='22' font-weight='800' fill='#ffffff' text-anchor='middle'>PDF</text>
</svg>"""

with open("proshowpdf/resources/icons/app_icon.svg", "w", encoding="utf-8") as f:
    f.write(SVG)

renderer = QSvgRenderer(QByteArray(SVG.encode("utf-8")))

def png_for(size):
    img = QImage(size, size, QImage.Format.Format_ARGB32)
    img.fill(Qt.GlobalColor.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
    renderer.render(p)
    p.end()
    ba = QByteArray(); buf = QBuffer(ba); buf.open(QBuffer.OpenModeFlag.WriteOnly)
    img.save(buf, "PNG"); buf.close()
    return bytes(ba.data())

sizes = [256, 128, 64, 48, 32, 16]
imgs = [(s, png_for(s)) for s in sizes]

# Assemble ICO embedding PNGs
n = len(imgs)
out = struct.pack('<HHH', 0, 1, n)
offset = 6 + 16 * n
entries = b''; datas = b''
for s, png in imgs:
    entries += struct.pack('<BBBBHHII', s & 0xFF, s & 0xFF, 0, 0, 1, 32, len(png), offset)
    offset += len(png); datas += png
ico = out + entries + datas
with open("proshowpdf/resources/ProShowPDF.ico", "wb") as f:
    f.write(ico)

# preview
with open("_icon_preview.png", "wb") as f:
    f.write(png_for(256))
print("ICO written:", len(ico), "bytes;", n, "sizes:", sizes)
