import sys; sys.path.insert(0, "/home/claude/work/kaio/docs")
from common import font_css
from playwright.sync_api import sync_playwright
OR = "#E9A23B"; BL = "#3B82F6"
marks = {
"1 · Ringed planet": lambda c: f'''
 <circle cx="40" cy="40" r="17" fill="{c}"/>
 <ellipse cx="40" cy="40" rx="34" ry="12" fill="none" stroke="{c}" stroke-width="3.2" transform="rotate(-25 40 40)" opacity=".75"/>
 <circle cx="69" cy="26.5" r="5" fill="{OR}"/>''',
"2 · Decision fork": lambda c: f'''
 <path d="M10 60 A40 40 0 0 1 40 18" fill="none" stroke="{c}" stroke-width="4" stroke-linecap="round" opacity=".55"/>
 <circle cx="40" cy="18" r="6.5" fill="{OR}"/>
 <path d="M40 18 L66 12" stroke="{c}" stroke-width="4" stroke-linecap="round"/>
 <path d="M40 18 L60 46" stroke="{c}" stroke-width="4" stroke-linecap="round"/>
 <path d="M60 6 L68 12 L59 17" fill="none" stroke="{c}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>
 <path d="M52 44 L61 47 L64 38" fill="none" stroke="{c}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>
 <path d="M48 70 h24" stroke="{c}" stroke-width="4" stroke-linecap="round" opacity=".55"/>''',
"3 · K-orbit monogram": lambda c: f'''
 <rect x="18" y="8" width="9" height="64" rx="2" fill="{c}"/>
 <path d="M27 42 L58 10" stroke="{c}" stroke-width="9" stroke-linecap="round"/>
 <path d="M37 33 L62 70" stroke="{c}" stroke-width="9" stroke-linecap="round"/>
 <ellipse cx="40" cy="40" rx="36" ry="11" fill="none" stroke="{OR}" stroke-width="3" transform="rotate(-20 40 40)"/>
 <circle cx="74" cy="28" r="4.5" fill="{OR}"/>''',
"4 · Lotus of orbits": lambda c: f'''
 <g fill="none" stroke="{c}" stroke-width="3" opacity=".85">
  <ellipse cx="40" cy="40" rx="34" ry="11"/>
  <ellipse cx="40" cy="40" rx="34" ry="11" transform="rotate(60 40 40)"/>
  <ellipse cx="40" cy="40" rx="34" ry="11" transform="rotate(120 40 40)"/></g>
 <circle cx="40" cy="40" r="9" fill="{c}"/>
 <circle cx="74" cy="40" r="5" fill="{OR}"/>''',
"5 · Filtered downlink": lambda c: f'''
 <circle cx="40" cy="12" r="6.5" fill="{OR}"/>
 <path d="M40 22 L18 66 M40 22 L62 66" stroke="{c}" stroke-width="3" stroke-linecap="round" opacity=".45"/>
 <circle cx="30" cy="38" r="3.5" fill="{c}" opacity=".3"/><circle cx="48" cy="34" r="3.5" fill="{c}" opacity=".3"/>
 <circle cx="40" cy="48" r="4.5" fill="{c}"/><circle cx="34" cy="58" r="3.5" fill="{c}" opacity=".3"/>
 <path d="M8 72 A60 60 0 0 1 72 72" fill="none" stroke="{c}" stroke-width="4" stroke-linecap="round"/>''',
}
def tile(name, fn, dark):
    bg, ink, sub = ("#0B1020", "#F1F4FA", "#8C97AC") if dark else ("#FFFFFF", "#121A2B", "#55617A")
    return f'''<div style="background:{bg};border-radius:14px;padding:26px 18px 16px;display:flex;flex-direction:column;align-items:center;gap:10px;border:1px solid #D6DCE6">
 <div style="display:flex;align-items:center;gap:14px"><svg width="80" height="80" viewBox="0 0 80 80">{fn(ink)}</svg>
 <span style="font:700 40px 'Space Grotesk';letter-spacing:.12em;color:{ink}">KAIO</span></div>
 <div style="font:500 13px 'Space Grotesk';color:{sub}">{name}</div></div>'''
cols = "".join(f'<div style="display:flex;flex-direction:column;gap:12px">{tile(n,f,False)}{tile(n,f,True)}</div>' for n,f in marks.items())
html = f"<html><head><style>{font_css()} body{{margin:0;background:#EEF1F6;padding:20px;font-family:'Space Grotesk'}}</style></head><body><div style='display:grid;grid-template-columns:repeat(5,1fr);gap:14px;width:1460px'>{cols}</div></body></html>"
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width":1500,"height":420}, device_scale_factor=2)
    pg.set_content(html); pg.wait_for_timeout(400); pg.screenshot(path="logo_options.png", full_page=True); b.close()
