"""TürkFin AI — Ana Uygulama v5.1 — Çizim araçları düzeltildi"""

import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import pandas_ta as ta
from fastapi import Body, FastAPI
from fastapi.responses import HTMLResponse, JSONResponse

from analyzer import (
    DEFAULT_INTERVAL,
    INTERVAL_MAP,
    INTRADAY_INTERVALS,
    df_to_chart_json,
    teknik_analiz,
)
from fon import (
    FON_PERIYOTLARI,
    FON_TIPLERI,
    get_fon_detay,
    get_fon_fiyat_gecmis,
    get_fon_listesi,
)
from kripto import get_kripto_analiz, get_kripto_fiyatlar
from notlar import get_not, kaydet_not, tum_notlar
from temettu import (
    cikar_takip_listesi,
    ekle_takip_listesi,
    get_amorti_suresi,
    get_temettu_ozet,
    get_temettu_sampiyonlari,
    get_temettu_takip_listesi,
    get_temettu_ucuzluk_skoru,
    get_yaklasan_temettular,
)

app = FastAPI(title="TürkFin AI")
FAVORILER: set = {"THYAO", "GARAN", "BIMAS"}
POPULER_HISSELER = [
    "THYAO",
    "GARAN",
    "AKBNK",
    "BIMAS",
    "EREGL",
    "FROTO",
    "KCHOL",
    "SISE",
    "TUPRS",
    "ISCTR",
    "ASELS",
    "MGROS",
    "VESTL",
    "PETKM",
    "ARCLK",
    "FENER",
    "KRDMD",
    "TCELL",
    "SAHOL",
    "SASA",
]

CSS = """<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@400;500;600&display=swap" rel="stylesheet">
<style>
:root{--bg:#0b0f1a;--surf:#131929;--surf2:#1a2235;--brd:#1e2d45;
      --txt:#e2e8f0;--muted:#64748b;--acc:#38bdf8;--green:#22c55e;--red:#ef4444;--amber:#f59e0b;}
*{box-sizing:border-box;margin:0;padding:0;}
body{font-family:'DM Sans',sans-serif;background:var(--bg);color:var(--txt);min-height:100vh;}
a{color:var(--acc);text-decoration:none;}
header{background:linear-gradient(135deg,#0f172a,#1e3a5f);border-bottom:1px solid var(--brd);
       padding:11px 22px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:7px;}
header h1{font-family:'Space Mono',monospace;font-size:1.05rem;color:var(--acc);}
nav{display:flex;gap:4px;flex-wrap:wrap;}
nav a{padding:5px 12px;border-radius:6px;font-size:.78rem;font-weight:500;
      background:var(--surf2);border:1px solid var(--brd);color:var(--txt);transition:all .15s;}
nav a:hover,nav a.active{background:var(--acc);color:#0b0f1a;border-color:var(--acc);}
.wrap{max-width:1500px;margin:0 auto;padding:18px 22px;}
h2{font-family:'Space Mono',monospace;font-size:.7rem;color:var(--muted);
   text-transform:uppercase;letter-spacing:2px;margin-bottom:10px;}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:10px;margin-bottom:24px;}
.card{background:var(--surf);border:1px solid var(--brd);border-radius:9px;padding:14px;
      cursor:pointer;transition:border-color .2s,transform .15s;}
.card:hover{border-color:var(--acc);transform:translateY(-2px);}
.sym{font-family:'Space Mono',monospace;font-size:.85rem;font-weight:700;color:var(--acc);}
.price{font-size:1.35rem;font-weight:600;margin:4px 0 2px;}
.chg{font-size:.8rem;font-weight:500;}
.sbar{background:var(--brd);border-radius:3px;height:3px;margin:7px 0 4px;overflow:hidden;}
.sfill{height:100%;border-radius:3px;}
.pill{display:inline-flex;align-items:center;padding:4px 10px;border-radius:5px;font-size:.73rem;
      font-weight:600;background:var(--surf2);border:1px solid var(--brd);color:var(--txt);
      cursor:pointer;text-decoration:none;transition:all .15s;white-space:nowrap;gap:3px;}
.pill:hover,.pill.on{background:var(--acc);color:#0b0f1a;border-color:var(--acc);}
.pills{display:flex;gap:4px;flex-wrap:wrap;margin-bottom:8px;}
.panel{background:var(--surf);border:1px solid var(--brd);border-radius:9px;padding:14px;margin-bottom:12px;}
table.ind{width:100%;border-collapse:collapse;}
table.ind td{padding:5px 3px;border-bottom:1px solid var(--brd);font-size:.76rem;}
table.ind td:first-child{color:var(--muted);}table.ind td:last-child{text-align:right;}
.sig-list{list-style:none;padding:0;}
.sig-list li{padding:5px 8px;background:var(--surf2);border-radius:5px;margin-bottom:4px;font-size:.74rem;}
.toolbar{display:flex;gap:5px;align-items:center;flex-wrap:wrap;background:var(--surf);
         border:1px solid var(--brd);border-radius:9px;padding:8px 12px;margin-bottom:7px;}
.tsep{width:1px;height:20px;background:var(--brd);flex-shrink:0;}
.cinfo{display:flex;gap:10px;font-size:.66rem;color:var(--muted);margin-bottom:5px;flex-wrap:wrap;}
.g3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:11px;}
.g2{display:grid;grid-template-columns:1fr 1fr;gap:11px;}
@media(max-width:900px){.g3,.g2{grid-template-columns:1fr!important;}}
/* Crosshair tooltip */
#draw-hint{position:fixed;bottom:12px;left:50%;transform:translateX(-50%);
           background:#1e2d45;color:#38bdf8;padding:6px 14px;border-radius:6px;
           font-size:.75rem;font-weight:600;display:none;z-index:999;border:1px solid #38bdf8;}
.note-ico{opacity:.35;font-size:.85rem;cursor:pointer;margin-left:4px;transition:opacity .15s;}
.note-ico:hover{opacity:.7;}
.note-ico.has{opacity:1;filter:drop-shadow(0 0 4px #38bdf8);}
.note-badge{display:inline-flex;align-items:center;gap:2px;font-size:.68rem;font-weight:700;
            background:linear-gradient(135deg,#0ea5e9,#38bdf8);color:#0b0f1a;
            padding:2px 6px;border-radius:20px;cursor:pointer;margin-left:4px;
            box-shadow:0 0 6px rgba(56,189,248,.4);transition:box-shadow .15s;}
.note-badge:hover{box-shadow:0 0 10px rgba(56,189,248,.7);}
#not-popup{display:none;position:fixed;z-index:2000;width:300px;
           background:var(--surf);border:1px solid var(--acc);border-radius:10px;
           padding:14px;box-shadow:0 8px 32px rgba(0,0,0,.6);}
#not-popup textarea{width:100%;background:var(--surf2);border:1px solid var(--brd);color:var(--txt);
           border-radius:7px;padding:9px;font-size:.82rem;resize:vertical;margin-top:7px;min-height:90px;}
#not-popup-overlay{display:none;position:fixed;inset:0;z-index:1999;}
</style>"""

LW = '<script src="https://unpkg.com/lightweight-charts@4.1.0/dist/lightweight-charts.standalone.production.js"></script>'


def nav_html(active=""):
    pages = [
        ("/", "📈 Hisseler"),
        ("/temettu", "💰 Temettü"),
        ("/fonlar", "🏦 Fonlar"),
        ("/kripto", "₿ Kripto"),
    ]
    return (
        "<header><h1>TürkFin AI</h1><nav>"
        + "".join(
            f'<a href="{u}" class="{"active" if active == u else ""}">{l}</a>'
            for u, l in pages
        )
        + "</nav></header>"
    )


def page(title, body, active="/"):
    return (
        f'<!DOCTYPE html><html lang="tr"><head><meta charset="UTF-8">'
        f'<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>{title} — TürkFin AI</title>{CSS}</head>"
        f"<body>{nav_html(active)}{body}"
        f'<div id="draw-hint"></div></body></html>'
    )


def tdr(label, val, unit=""):
    v = str(val) if val is not None else "—"
    return (
        f"<tr><td>{label}</td><td><b>{v}</b>"
        f'<span style="color:var(--muted);font-size:.7rem;margin-left:2px">{unit}</span></td></tr>'
    )


def skc(skor):
    return (
        "var(--green)" if skor >= 65 else "var(--red)" if skor <= 40 else "var(--amber)"
    )


def fiyat_goster(d) -> str:
    if d.fiyat is not None:
        return str(d.fiyat)
    return "Veri yok" if d.hata else "—"


def notlar_modal_html() -> str:
    return """
<div id="not-popup-overlay" onclick="closeNotPopup()"></div>
<div id="not-popup">
  <div style="display:flex;justify-content:space-between;align-items:center">
    <span style="font-family:'Space Mono',monospace;font-size:.8rem;color:var(--acc);font-weight:700">
      🗒️ <span id="not-popup-sym">—</span>
    </span>
    <button type="button" onclick="closeNotPopup()" style="background:none;border:none;color:var(--muted);font-size:1rem;cursor:pointer;line-height:1">✕</button>
  </div>
  <textarea id="not-popup-text" placeholder="Görüş, hedef fiyat, strateji notları…"></textarea>
  <div style="display:flex;justify-content:space-between;align-items:center;margin-top:8px">
    <small id="not-popup-ts" style="color:var(--muted);font-size:.65rem"></small>
    <div style="display:flex;gap:5px">
      <button type="button" class="pill" onclick="closeNotPopup()">İptal</button>
      <button type="button" class="pill on" onclick="saveNotPopup()">Kaydet</button>
    </div>
  </div>
</div>
<script>
let _notPopupSym=null;
function openNotModal(s,triggerEl){
  _notPopupSym=s.toUpperCase();
  const popup=document.getElementById('not-popup');
  const overlay=document.getElementById('not-popup-overlay');
  document.getElementById('not-popup-sym').textContent=_notPopupSym;
  popup.style.transform='';
  if(triggerEl){
    const rect=triggerEl.getBoundingClientRect();
    const vw=window.innerWidth, vh=window.innerHeight;
    const pw=300, ph=210;
    let left=rect.right+8, top=rect.top;
    if(left+pw>vw-8) left=rect.left-pw-8;
    if(top+ph>vh-8) top=vh-ph-8;
    if(left<8) left=8;
    popup.style.left=left+'px';
    popup.style.top=Math.max(8,top)+'px';
  } else {
    popup.style.left='50%'; popup.style.top='50%';
    popup.style.transform='translate(-50%,-50%)';
  }
  overlay.style.display='block';
  popup.style.display='block';
  fetch('/api/notlar/'+_notPopupSym).then(r=>r.json()).then(d=>{
    document.getElementById('not-popup-text').value=d.text||'';
    document.getElementById('not-popup-ts').textContent=d.updated?'Son: '+d.updated:'';
    document.getElementById('not-popup-text').focus();
  });
}
function closeNotPopup(){
  document.getElementById('not-popup').style.display='none';
  document.getElementById('not-popup-overlay').style.display='none';
  _notPopupSym=null;
}
function saveNotPopup(){
  if(!_notPopupSym)return;
  const text=document.getElementById('not-popup-text').value;
  fetch('/api/notlar/'+_notPopupSym,{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({text})})
  .then(r=>r.json()).then(()=>{
    closeNotPopup();
    if(typeof refreshPopuler==='function')refreshPopuler();
  });
}
document.addEventListener('keydown',e=>{if(e.key==='Escape')closeNotPopup();});
</script>
"""


def hisse_card_html(
    d, sembol: str, not_metin: str = "", show_remove: bool = False
) -> str:
    rc = "var(--red)" if (d.degisim or 0) < 0 else "var(--green)"
    ok = "▼" if (d.degisim or 0) < 0 else "▲"
    fav = "❤️" if sembol in FAVORILER else "♡"
    sc = skc(d.skor)
    macd_ok = "▲" if d.macd and d.macd_signal and d.macd > d.macd_signal else "▼"
    bb = f"%{d.bb_yuzde}" if d.bb_yuzde else "—"
    has_note = bool((not_metin or "").strip())
    if has_note:
        note_html = (
            f'<span class="note-badge" '
            f"onclick=\"event.stopPropagation();openNotModal('{sembol}',this)\" "
            f'title="Not var – düzenle">🗒️ NOT</span>'
        )
    else:
        note_html = (
            f'<span class="note-ico" '
            f"onclick=\"event.stopPropagation();openNotModal('{sembol}',this)\" "
            f'title="Not ekle">📝</span>'
        )
    remove_btn = (
        (
            f"<span onclick=\"event.stopPropagation();removeHisse('{sembol}')\" "
            f'title="Listeden çıkar" style="cursor:pointer;color:var(--muted);font-size:.8rem;'
            f'margin-left:4px;opacity:.5;transition:opacity .15s" '
            f"onmouseover=\"this.style.opacity=1;this.style.color='var(--red)'\" "
            f"onmouseout=\"this.style.opacity=.5;this.style.color='var(--muted)'\">✕</span>"
        )
        if show_remove
        else ""
    )
    return (
        f'<div class="card" data-skor="{d.skor or 0}" data-sembol="{sembol}" '
        f"onclick=\"window.location='/hisse/{sembol}'\">"
        f'<div style="display:flex;justify-content:space-between;margin-bottom:5px">'
        f'<span class="sym">{d.sembol}</span>'
        f'<span style="display:flex;align-items:center;gap:2px">'
        f'<span onclick="event.stopPropagation();tFav(\'{sembol}\',this)" style="cursor:pointer">{fav}</span>'
        f"{note_html}{remove_btn}"
        f"</span></div>"
        f'<div class="price">{fiyat_goster(d)} <small style="font-size:.8rem;color:var(--muted)">TL</small></div>'
        f'<div class="chg" style="color:{rc}">{ok} %{d.degisim or 0}</div>'
        f'<div style="display:flex;gap:6px;font-size:.68rem;color:var(--muted);margin-top:5px;flex-wrap:wrap">'
        f'<span>RSI <b style="color:var(--txt)">{d.rsi or "—"}</b></span>'
        f"<span>MACD <b>{macd_ok}</b></span>"
        f"<span>BB <b>{bb}</b></span></div>"
        f'<div class="sbar"><div class="sfill" style="width:{d.skor}%;background:{sc}"></div></div>'
        f'<div style="font-size:.74rem;font-weight:600;color:{sc}">{d.tavsiye} '
        f'<small style="color:var(--muted)">{d.skor}/100</small></div></div>'
    )


_POPULER_CACHE: Dict[str, Any] = {"ts": 0.0, "rows": []}
_POPULER_CACHE_TTL = 60  # saniye


def populer_hisseler_sorted(force: bool = False) -> List[Tuple[int, str, Any]]:
    now = time.time()
    if (
        not force
        and _POPULER_CACHE["rows"]
        and now - _POPULER_CACHE["ts"] < _POPULER_CACHE_TTL
    ):
        return _POPULER_CACHE["rows"]

    def _analiz(sembol: str):
        d = teknik_analiz(sembol)
        return (d.skor if d.skor is not None else 0, sembol, d)

    with ThreadPoolExecutor(max_workers=8) as pool:
        rows = list(pool.map(_analiz, POPULER_HISSELER))
    rows.sort(key=lambda x: (x[2].fiyat is None, -x[0]))
    _POPULER_CACHE["rows"] = rows
    _POPULER_CACHE["ts"] = now
    return rows


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ORTAK GRAFİK JS — çizim araçları mousedown ile düzeltildi
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def build_chart_js(api_url: str, is_intra: bool, with_indicators: bool = True) -> str:
    """
    Python f-string mekanizmasını iptal ederek süslü parantez kilitlenmelerini
    ve SyntaxError hatalarını kökten çözen, güvenli grafik motoru.
    """
    # API URL'sini JavaScript tarafına güvenle aktarmak için HTML data attribute kullanıyoruz
    return f"""
    <div id="chart-data-bridge" data-url="{api_url}" style="display:none;"></div>
    <script>
    (function() {{
        // API URL'sini köprü elementten çekiyoruz (f-string karmaşası bitti)
        const bridgeEl = document.getElementById('chart-data-bridge');
        const chartDataUrl = bridgeEl ? bridgeEl.getAttribute('data-url') : "/api/chart-data";

        const chartContainer = document.getElementById('main-chart');
        if (!chartContainer) {{
            console.error("main-chart container elemanı sayfada bulunamadı!");
            return;
        }}

        const mainChartH = chartContainer.clientHeight || parseInt(getComputedStyle(chartContainer).height, 10) || 260;

        function resizeAllCharts() {{
            const w = chartContainer.clientWidth || chartContainer.offsetWidth;
            if (!w || w < 10) return;
            chart.applyOptions({{ width: w }});
            if (volumeChart) volumeChart.applyOptions({{ width: w }});
            if (rsiChart) rsiChart.applyOptions({{ width: w }});
            if (macdChart) macdChart.applyOptions({{ width: w }});
            chart.timeScale().fitContent();
        }}

        function scheduleChartResize() {{
            resizeAllCharts();
            requestAnimationFrame(resizeAllCharts);
            setTimeout(resizeAllCharts, 50);
            setTimeout(resizeAllCharts, 200);
        }}

        window.addEventListener('resize', resizeAllCharts);
        if (typeof ResizeObserver !== 'undefined') {{
            new ResizeObserver(() => resizeAllCharts()).observe(chartContainer);
        }}

        // 1. Ana Grafik Kurulumu
        const chart = LightweightCharts.createChart(chartContainer, {{
            width: Math.max(chartContainer.clientWidth, 300),
            height: mainChartH,
            layout: {{ background: {{ type: 'solid', color: '#131722' }}, textColor: '#d1d4dc' }},
            grid: {{ vertLines: {{ color: '#242a35' }}, horzLines: {{ color: '#242a35' }} }},
            rightPriceScale: {{ autoScale: true, mode: 0, borderColor: '#2a2e39' }},
            timeScale: {{ borderColor: '#2a2e39', timeVisible: true }},
            handleScroll: {{ mouseWheel: true, pressedMouseButton: true }},
            handleScale: {{ axisPressedMouseMove: true, mouseWheel: true }}
        }});

        const candleSeries = chart.addCandlestickSeries({{
            upColor: '#26a69a', downColor: '#ef5350', borderVisible: false, wickUpColor: '#26a69a', wickDownColor: '#ef5350'
        }});
        const lineSeries = chart.addLineSeries({{
            color: '#38bdf8', lineWidth: 2, visible: false, lastValueVisible: true, priceLineVisible: false
        }});
        const areaSeries = chart.addAreaSeries({{
            lineColor: '#38bdf8', topColor: 'rgba(56, 189, 248, 0.45)', bottomColor: 'rgba(56, 189, 248, 0.02)',
            lineWidth: 2, visible: false, lastValueVisible: true, priceLineVisible: false
        }});
        let activePriceSeries = candleSeries;
        let currentChartType = 'candle';

        let volumeChart = null, volumeSeries = null;
        let rsiChart = null, rsiSeries = null;
        let macdChart = null, macdLine = null, macdSignal = null, macdHist = null;

        const seriesInstances = {{
            'sma20': null, 'sma50': null, 'sma200': null, 'ema20': null, 'supertrend': null,
            'ichimoku_tenkan': null, 'ichimoku_kijun': null, 'ichimoku_spanA': null, 'ichimoku_spanB': null,
            'ichimoku_kumo': null,
            'bbu': null, 'bbm': null, 'bbl': null
        }};

        // Ichimoku Kumo — Span A/B arası dolgu (yeşil/kırmızı bulut)
        function buildKumoCloud(spanAData, spanBData) {{
            const bMap = new Map(spanBData.map(d => [d.time, d.value]));
            const cloud = [];
            spanAData.forEach(d => {{
                const b = bMap.get(d.time);
                if (b !== undefined) cloud.push({{ time: d.time, a: d.value, b }});
            }});
            return cloud;
        }}

        class KumoCloudPrimitive {{
            constructor() {{
                this._cloud = [];
                this._visible = false;
                this._paneViews = [new KumoPaneView(this)];
            }}
            setCloud(cloud) {{ this._cloud = cloud; this.updateAllViews(); }}
            setVisible(v) {{ this._visible = v; this.updateAllViews(); }}
            attached(param) {{
                this._chart = param.chart;
                this._series = param.series;
                this._requestUpdate = param.requestUpdate;
            }}
            paneViews() {{ return this._paneViews; }}
            updateAllViews() {{
                this._paneViews.forEach(v => v.update());
                if (this._requestUpdate) this._requestUpdate();
            }}
        }}

        class KumoPaneView {{
            constructor(source) {{ this._source = source; this._renderer = new KumoRenderer(this); }}
            update() {{}}
            renderer() {{
                return (this._source._visible && this._source._cloud.length) ? this._renderer : null;
            }}
            zOrder() {{ return 'bottom'; }}
        }}

        class KumoRenderer {{
            constructor(view) {{ this._view = view; }}
            drawBackground(target) {{ this._draw(target, true); }}
            draw(target) {{ this._draw(target, false); }}
            _draw(target, isBg) {{
                const src = this._view._source;
                const cloud = src._cloud;
                const series = src._series;
                const chart = src._chart;
                if (!cloud.length || !series || !chart) return;

                const KUMO_BULL_FILL = 'rgba(38, 166, 154, 0.58)';
                const KUMO_BEAR_FILL = 'rgba(239, 83, 80, 0.58)';
                const KUMO_BULL_EDGE = 'rgba(46, 204, 113, 0.95)';
                const KUMO_BEAR_EDGE = 'rgba(255, 82, 82, 0.95)';

                target.useBitmapCoordinateSpace(scope => {{
                    const ctx = scope.context;
                    const hpr = scope.horizontalPixelRatio;
                    const vpr = scope.verticalPixelRatio;
                    const ts = chart.timeScale();

                    if (isBg) {{
                        for (let i = 0; i < cloud.length; i++) {{
                            const p = cloud[i];
                            const x = ts.timeToCoordinate(p.time);
                            if (x === null) continue;
                            const yA = series.priceToCoordinate(p.a);
                            const yB = series.priceToCoordinate(p.b);
                            if (yA === null || yB === null) continue;

                            let halfW = 4;
                            if (i > 0) {{
                                const xPrev = ts.timeToCoordinate(cloud[i - 1].time);
                                if (xPrev !== null) halfW = Math.max(halfW, (x - xPrev) / 2);
                            }}
                            if (i < cloud.length - 1) {{
                                const xNext = ts.timeToCoordinate(cloud[i + 1].time);
                                if (xNext !== null) halfW = Math.max(halfW, (xNext - x) / 2);
                            }}

                            const bx = Math.round(x * hpr);
                            const bw = Math.max(2, Math.round(halfW * 2 * hpr));
                            const top = Math.round(Math.min(yA, yB) * vpr);
                            const h = Math.max(1, Math.round(Math.abs(yA - yB) * vpr));
                            ctx.fillStyle = (p.a >= p.b) ? KUMO_BULL_FILL : KUMO_BEAR_FILL;
                            ctx.fillRect(bx - Math.floor(bw / 2), top, bw, h);
                        }}
                        return;
                    }}

                    ctx.lineWidth = Math.max(1, Math.floor(2 * vpr));
                    const drawEdge = (pick, color) => {{
                        ctx.strokeStyle = color;
                        ctx.beginPath();
                        let started = false;
                        for (let i = 0; i < cloud.length; i++) {{
                            const p = cloud[i];
                            const x = ts.timeToCoordinate(p.time);
                            const y = series.priceToCoordinate(pick(p));
                            if (x === null || y === null) {{ started = false; continue; }}
                            const bx = Math.round(x * hpr);
                            const by = Math.round(y * vpr);
                            if (!started) {{ ctx.moveTo(bx, by); started = true; }}
                            else ctx.lineTo(bx, by);
                        }}
                        ctx.stroke();
                    }};
                    drawEdge(p => p.a, KUMO_BULL_EDGE);
                    drawEdge(p => p.b, KUMO_BEAR_EDGE);
                }});
            }}
        }}

        let currentTool = 'pan';
        let drawingPoints = [];
        let activeDrawings = [];

        // 2. Veriyi API'den Çekip Doldurma Katmanı
        fetch(chartDataUrl).then(r => r.json()).then(data => {{
            if (!data || !data.candles || data.candles.length === 0) return;

            candleSeries.setData(data.candles);
            const closeLineData = data.candles.map(c => ({{ time: c.time, value: c.close }}));
            lineSeries.setData(closeLineData);
            areaSeries.setData(closeLineData);
            const validTimes = new Set(data.candles.map(c => c.time));

            const getCleanData = (arr) => {{
                if (!arr || !Array.isArray(arr) || arr.length === 0) return [];
                return arr.filter(d => d && d.time && validTimes.has(d.time) && d.value !== null && d.value !== undefined && !isNaN(d.value));
            }};

            // HACİM PANELİ
            const volData = getCleanData(data.volume || data.Volume);
            const volCont = document.getElementById('vol-container');
            if (volCont && volData.length > 0) {{
                volCont.style.display = 'block';
                volumeChart = LightweightCharts.createChart(volCont, {{
                    width: chartContainer.clientWidth, height: 70,
                    layout: {{ background: {{ type: 'solid', color: '#131722' }}, textColor: '#d1d4dc' }},
                    grid: {{ vertLines: {{ color: '#242a35' }}, horzLines: {{ color: '#242a35' }} }},
                    rightPriceScale: {{ autoScale: true, visible: false }}, timeScale: {{ visible: false }}
                }});

                volumeSeries = volumeChart.addHistogramSeries({{ priceFormat: {{ type: 'volume' }} }});

                const coloredVolData = volData.map(d => {{
                    const candle = data.candles.find(c => c.time === d.time);
                    let color = '#26a69a';
                    if (candle && candle.close < candle.open) {{
                        color = '#ef5350';
                    }}
                    return {{ time: d.time, value: d.value, color: color }};
                }});

                volumeSeries.setData(coloredVolData);
                chart.timeScale().subscribeVisibleTimeRangeChange(tr => volumeChart.timeScale().setVisibleRange(tr));
            }}

            // RSI PANELİ
            const rsiData = getCleanData(data.RSI || data.rsi);
            const rsiCont = document.getElementById('rsi-container');
            if (rsiCont && rsiData.length > 0) {{
                rsiChart = LightweightCharts.createChart(rsiCont, {{
                    width: chartContainer.clientWidth, height: 65,
                    layout: {{ background: {{ type: 'solid', color: '#131722' }}, textColor: '#d1d4dc' }},
                    grid: {{ vertLines: {{ color: '#242a35' }}, horzLines: {{ color: '#242a35' }} }},
                    rightPriceScale: {{ autoScale: true, borderColor: '#2a2e39' }}, timeScale: {{ visible: false }}
                }});
                rsiSeries = rsiChart.addLineSeries({{ color: '#f2a900', lineWidth: 1.5 }});
                rsiSeries.setData(rsiData);
                chart.timeScale().subscribeVisibleTimeRangeChange(tr => rsiChart.timeScale().setVisibleRange(tr));
            }}

            // MACD PANELİ
            const mLineData = getCleanData(data.MACD_12_26_9 || data.macd);
            const mSigData = getCleanData(data.MACDs_12_26_9 || data.macds);
            const mHistRaw = getCleanData(data.MACDh_12_26_9 || data.macdh);
            const macdCont = document.getElementById('macd-container');
            if (macdCont && mLineData.length > 0 && mSigData.length > 0) {{
                macdChart = LightweightCharts.createChart(macdCont, {{
                    width: chartContainer.clientWidth, height: 75,
                    layout: {{ background: {{ type: 'solid', color: '#131722' }}, textColor: '#d1d4dc' }},
                    grid: {{ vertLines: {{ color: '#242a35' }}, horzLines: {{ color: '#242a35' }} }}
                }});
                macdLine = macdChart.addLineSeries({{ color: '#2962FF', lineWidth: 1.5 }});
                macdSignal = macdChart.addLineSeries({{ color: '#FF6D00', lineWidth: 1.5 }});
                macdHist = macdChart.addHistogramSeries({{ color: '#26a69a' }});
                macdLine.setData(mLineData);
                macdSignal.setData(mSigData);
                if (mHistRaw.length > 0) {{
                    macdHist.setData(mHistRaw.map(d => ({{
                        time: d.time, value: d.value, color: d.value >= 0 ? '#26a69a' : '#ef5350'
                    }})));
                }}
                chart.timeScale().subscribeVisibleTimeRangeChange(tr => macdChart.timeScale().setVisibleRange(tr));
            }}

            const setupLine = (key, rawData, options) => {{
                const clean = getCleanData(rawData);
                if (clean.length > 0) {{
                    seriesInstances[key] = chart.addLineSeries(options);
                    seriesInstances[key].setData(clean);
                }}
            }};

            setupLine('sma20', data.SMA_20, {{ color: '#2962FF', lineWidth: 1, visible: false }});
            setupLine('sma50', data.SMA_50, {{ color: '#FFd700', lineWidth: 1, visible: false }});
            setupLine('sma200', data.SMA_200, {{ color: '#f50057', lineWidth: 1.5, visible: false }});
            setupLine('ema20', data.EMA_20, {{ color: '#4CAF50', lineWidth: 1, visible: false }});

            // SUPERTREND
            const stClean = getCleanData(data.SUPERTREND || data.supertrend);
            if (stClean.length > 0) {{
                seriesInstances['supertrend'] = chart.addLineSeries({{ lineWidth: 2, visible: false }});
                const coloredSt = stClean.map(d => {{
                    const candle = data.candles.find(c => c.time === d.time);
                    return {{
                        time: d.time, value: d.value,
                        color: (candle && candle.close >= d.value) ? '#26a69a' : '#ef5350'
                    }};
                }});
                seriesInstances['supertrend'].setData(coloredSt);
            }}

            // ICHIMOKU — Tenkan/Kijun çizgileri + Kumo bulut dolgusu
            const iTenkan = getCleanData(data.ichi_tenkan || data.ICHIMOKU_TENKAN);
            const iKijun = getCleanData(data.ichi_kijun || data.ICHIMOKU_KIJUN);
            const iSpanA = getCleanData(data.ichi_spanA || data.ICHIMOKU_SSA);
            const iSpanB = getCleanData(data.ichi_spanB || data.ICHIMOKU_SSB);

            if (iTenkan.length > 0) {{
                const kumoCloud = buildKumoCloud(iSpanA, iSpanB);
                const hasKumoFill = kumoCloud.length > 1;

                seriesInstances['ichimoku_tenkan'] = chart.addLineSeries({{
                    color: '#00E5FF', lineWidth: 1.5, visible: false, title: 'Tenkan', lastValueVisible: false
                }});
                seriesInstances['ichimoku_kijun'] = chart.addLineSeries({{
                    color: '#FF5252', lineWidth: 1.5, visible: false, title: 'Kijun', lastValueVisible: false
                }});
                seriesInstances['ichimoku_spanA'] = chart.addLineSeries({{
                    color: 'rgba(38, 166, 154, 0.95)',
                    lineWidth: hasKumoFill ? 0 : 2,
                    visible: false, title: 'Senkou A', lastValueVisible: false
                }});
                seriesInstances['ichimoku_spanB'] = chart.addLineSeries({{
                    color: 'rgba(239, 83, 80, 0.95)',
                    lineWidth: hasKumoFill ? 0 : 2,
                    visible: false, title: 'Senkou B', lastValueVisible: false
                }});

                seriesInstances['ichimoku_tenkan'].setData(iTenkan);
                seriesInstances['ichimoku_kijun'].setData(iKijun);
                seriesInstances['ichimoku_spanA'].setData(iSpanA);
                seriesInstances['ichimoku_spanB'].setData(iSpanB);

                if (hasKumoFill && seriesInstances['ichimoku_spanA'].attachPrimitive) {{
                    const kumoPrim = new KumoCloudPrimitive();
                    kumoPrim.setCloud(kumoCloud);
                    seriesInstances['ichimoku_spanA'].attachPrimitive(kumoPrim);
                    seriesInstances['ichimoku_kumo'] = kumoPrim;
                }}
            }}

            // BOLLINGER BANTLARI
            setupLine('bbu', data.BB_upper || data.BBU_20_20, {{ color: '#00E5FF', lineWidth: 1.5, visible: false, title: 'BB Üst' }});
            setupLine('bbm', data.BB_middle || data.BBM_20_20, {{ color: '#2962FF', lineWidth: 1, lineStyle: 2, visible: false, title: 'BB Orta' }});
            setupLine('bbl', data.BB_lower || data.BBL_20_20, {{ color: '#00E5FF', lineWidth: 1.5, visible: false, title: 'BB Alt' }});

            scheduleChartResize();
        }}).catch(err => console.error('Grafik verisi yüklenemedi:', err));

        if (document.readyState === 'complete') scheduleChartResize();
        else window.addEventListener('load', scheduleChartResize);
        window.addEventListener('pageshow', scheduleChartResize);

        // 3. GLOBAL GÖSTERGE BUTON KONTROLLERİ (Toggle)
        window.toggleInd = function(key) {{
            const btn = document.getElementById('ind-' + key);
            if (!btn) return;
            const isCurrentlyOn = btn.classList.contains('on');

            if (key === 'vol' || key === 'rsi' || key === 'macd') {{
                const el = document.getElementById(key + '-container');
                const lbl = document.getElementById(key + '-label');
                if (el) el.style.display = isCurrentlyOn ? 'none' : 'block';
                if (lbl) lbl.style.display = isCurrentlyOn ? 'none' : 'block';
            }} else if (key === 'bb') {{
                ['bbu', 'bbm', 'bbl'].forEach(k => {{
                    if (seriesInstances[k]) seriesInstances[k].applyOptions({{ visible: !isCurrentlyOn }});
                }});
            }} else if (key === 'ichimoku') {{
                const show = !isCurrentlyOn;
                ['ichimoku_tenkan', 'ichimoku_kijun', 'ichimoku_spanA', 'ichimoku_spanB'].forEach(k => {{
                    if (seriesInstances[k]) seriesInstances[k].applyOptions({{ visible: show }});
                }});
                if (seriesInstances['ichimoku_kumo']) seriesInstances['ichimoku_kumo'].setVisible(show);
            }} else if (seriesInstances[key]) {{
                seriesInstances[key].applyOptions({{ visible: !isCurrentlyOn }});
            }}

            if (isCurrentlyOn) btn.classList.remove('on'); else btn.classList.add('on');
        }};

        // Grafik tipi: mum / çizgi / alan
        window.setChartType = function(type) {{
            if (!['candle', 'line', 'area'].includes(type)) return;
            currentChartType = type;
            candleSeries.applyOptions({{ visible: type === 'candle' }});
            lineSeries.applyOptions({{ visible: type === 'line' }});
            areaSeries.applyOptions({{ visible: type === 'area' }});
            activePriceSeries = type === 'line' ? lineSeries : (type === 'area' ? areaSeries : candleSeries);
            ['candle', 'line', 'area'].forEach(t => {{
                const btn = document.getElementById('btn-' + t);
                if (btn) btn.classList.toggle('on', t === type);
            }});
        }};

        // 4. Çizim araçları — Trend çizgisi & Fib düzeltme
        window.setDrawTool = function(toolName) {{
            if (currentTool === toolName) toolName = 'pan';
            currentTool = toolName;
            drawingPoints = [];

            ['trendline', 'fib'].forEach(t => {{
                const el = document.getElementById('tool-' + t);
                if (el) el.classList.toggle('on', toolName === t);
            }});

            const canScroll = (toolName === 'pan');
            chart.applyOptions({{ handleScroll: canScroll, handleScale: canScroll }});

            const hint = document.getElementById('draw-hint');
            if (hint) {{
                if (toolName === 'trendline') {{
                    hint.textContent = 'Trend çizgisi: 2 noktaya tıklayın (başlangıç → bitiş)';
                    hint.style.display = 'block';
                }} else if (toolName === 'fib') {{
                    hint.textContent = 'Fib düzeltme: 2 noktaya tıklayın (dip ↔ tepe)';
                    hint.style.display = 'block';
                }} else {{
                    hint.style.display = 'none';
                }}
            }}
        }};

        window.clearDrawings = function() {{
            activeDrawings.forEach(item => {{
                const list = item.seriesList || [item.series || item];
                list.forEach(s => {{ try {{ chart.removeSeries(s); }} catch(e) {{}} }});
            }});
            activeDrawings = [];
            drawingPoints = [];
            window.setDrawTool('pan');
        }};

        chart.subscribeClick(param => {{
            if (currentTool === 'pan' || !param.time || !param.point) return;
            const price = activePriceSeries.coordinateToPrice(param.point.y);
            if (price === null || price === undefined || isNaN(price)) return;
            drawingPoints.push({{ time: param.time, value: price }});

            if (currentTool === 'trendline' && drawingPoints.length === 2) {{
                const p1 = drawingPoints[0], p2 = drawingPoints[1];
                const trendLine = chart.addLineSeries({{
                    color: '#FFEA00', lineWidth: 2, lineStyle: 0,
                    title: 'Trend', lastValueVisible: false, priceLineVisible: false
                }});
                trendLine.setData([p1, p2]);
                activeDrawings.push({{ type: 'trendline', series: trendLine }});
                window.setDrawTool('pan');
            }}

            if (currentTool === 'fib' && drawingPoints.length === 2) {{
                const pA = drawingPoints[0], pB = drawingPoints[1];
                const tLo = pA.time < pB.time ? pA.time : pB.time;
                const tHi = pA.time < pB.time ? pB.time : pA.time;
                const fibDefs = [
                    {{ lvl: 0,    label: '0%',    color: '#9e9e9e' }},
                    {{ lvl: 0.236, label: '23.6%', color: '#ef5350' }},
                    {{ lvl: 0.382, label: '38.2%', color: '#ff9800' }},
                    {{ lvl: 0.5,   label: '50%',   color: '#ffeb3b' }},
                    {{ lvl: 0.618, label: '61.8%', color: '#4caf50' }},
                    {{ lvl: 0.786, label: '78.6%', color: '#00bcd4' }},
                    {{ lvl: 1,    label: '100%',  color: '#9e9e9e' }},
                ];
                const fibSeries = [];
                fibDefs.forEach(f => {{
                    const priceLvl = pA.value + (pB.value - pA.value) * f.lvl;
                    const fLine = chart.addLineSeries({{
                        color: f.color, lineWidth: 1, lineStyle: 2,
                        title: 'Fib ' + f.label, lastValueVisible: false, priceLineVisible: true
                    }});
                    fLine.setData([{{ time: tLo, value: priceLvl }}, {{ time: tHi, value: priceLvl }}]);
                    fibSeries.push(fLine);
                }});
                activeDrawings.push({{ type: 'fib', seriesList: fibSeries }});
                window.setDrawTool('pan');
            }}
        }});
    }})();
    </script>
    """


# ── HTML Yardımcıları ────────────────────────────────────────────────────────
def toolbar_html(pills_html: str, show_ind: bool = True) -> str:
    ind_row = ""
    if show_ind:
        ind_row = """<div class="toolbar" style="margin-top:6px">
  <span style="font-size:.67rem;color:var(--muted);margin-right:3px">Göstergeler:</span>
  <button class="pill on"  id="ind-bb"     onclick="toggleInd('bb')">BB</button>
  <button class="pill on"  id="ind-sma20"  onclick="toggleInd('sma20')">SMA20</button>
  <button class="pill on"  id="ind-sma50"  onclick="toggleInd('sma50')">SMA50</button>
  <button class="pill"     id="ind-sma200" onclick="toggleInd('sma200')">SMA200</button>
  <button class="pill on"  id="ind-ema20"  onclick="toggleInd('ema20')">EMA20</button>
  <button class="pill on"  id="ind-vol"    onclick="toggleInd('vol')">Hacim</button>
  <button class="pill on"  id="ind-rsi"    onclick="toggleInd('rsi')">RSI</button>
  <button class="pill on"  id="ind-macd"   onclick="toggleInd('macd')">MACD</button>
</div>"""
    return f"""<div class="toolbar">
  {pills_html}
  <div class="tsep"></div>
  <button class="pill on" id="btn-candle" onclick="setChartType('candle')">🕯 Mum</button>
  <button class="pill"    id="btn-line"   onclick="setChartType('line')">📈 Çizgi</button>
  <button class="pill"    id="btn-area"   onclick="setChartType('area')">🌊 Alan</button>
  <div class="tsep"></div>
  <button class="pill" id="tool-trendline" onclick="setDrawTool('trendline')">📏 Trend Çizgisi</button>
  <button class="pill" id="tool-fib" onclick="setDrawTool('fib')">🌀 Fib Düzeltme</button>
  <button class="pill" onclick="clearDrawings()">🗑 Çizimleri Temizle</button>
</div>{ind_row}"""


# ── GRAFİK CONTAINER MOTORU (SIĞMA SORUNUNU ÇÖZEN ALAN) ─────────────────────
def chart_divs(h=260):
    """
    JavaScript (vol-container) ve Bollinger/Trend araçlarıyla tam senkronize,
    kimlik hataları giderilmiş nihai container yapısı.
    """
    return f"""
    <div id="main-chart" style="position:relative; width:100%; height:{h}px; margin-top:8px; border-radius:5px; overflow:hidden;"></div>

    <div id="vol-label" style="font-size:.65rem; color:var(--muted); margin-top:4px; display:block;">Hacim</div>
    <div id="vol-container" style="position:relative; width:100%; height:70px; border-radius:5px; overflow:hidden; display:block; margin-bottom:4px;"></div>

    <div id="rsi-label" style="font-size:.65rem; color:var(--muted); margin-top:4px; display:none;">RSI (14)</div>
    <div id="rsi-container" style="position:relative; width:100%; height:65px; border-radius:5px; overflow:hidden; display:none; margin-bottom:4px;"></div>

    <div id="macd-label" style="font-size:.65rem; color:var(--muted); margin-top:4px; display:none;">MACD (12,26,9)</div>
    <div id="macd-container" style="position:relative; width:100%; height:75px; border-radius:5px; overflow:hidden; display:none;"></div>
    """


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SAYFALAR
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@app.get("/api/notlar/{sembol}")
async def api_get_not(sembol: str):
    row = get_not(sembol) or {}
    return JSONResponse(
        {
            "sembol": sembol.upper(),
            "text": row.get("text", ""),
            "updated": row.get("updated"),
        }
    )


@app.post("/api/notlar/{sembol}")
async def api_save_not(sembol: str, payload: dict = Body(default={})):
    return JSONResponse(kaydet_not(sembol, payload.get("text", "")))


@app.get("/api/temettu-takip")
async def api_temettu_takip():
    return JSONResponse({"hisseler": get_temettu_takip_listesi()})


@app.post("/api/temettu-takip/{sembol}")
async def api_ekle_temettu_takip(sembol: str):
    sonuc = ekle_takip_listesi(sembol)
    return JSONResponse({"success": sonuc, "hisseler": get_temettu_takip_listesi()})


@app.delete("/api/temettu-takip/{sembol}")
async def api_cikar_temettu_takip(sembol: str):
    sonuc = cikar_takip_listesi(sembol)
    return JSONResponse({"success": sonuc, "hisseler": get_temettu_takip_listesi()})


@app.get("/api/populer-hisseler")
async def api_populer_hisseler():
    not_map = tum_notlar()
    return JSONResponse(
        {
            "hisseler": [
                {
                    "sembol": s,
                    "skor": sk,
                    "html": hisse_card_html(d, s, not_map.get(s, ""), show_remove=True),
                }
                for sk, s, d in populer_hisseler_sorted()
            ]
        }
    )


@app.get("/", response_class=HTMLResponse)
async def ana_sayfa():
    not_map = tum_notlar()
    cards = "".join(
        hisse_card_html(d, s, not_map.get(s, ""), show_remove=True)
        for _, s, d in populer_hisseler_sorted()
    )
    fav_html = (
        "".join(
            f'<div class="card" onclick="window.location=\'/hisse/{f}\'"><span class="sym">{f}</span></div>'
            for f in sorted(FAVORILER)
        )
        or "<p style='color:var(--muted)'>Henüz favori eklenmedi.</p>"
    )

    js = """
<script>
function getInput(){return (document.getElementById('hisse-input').value||'').trim().toUpperCase();}
function goToHisse(){var s=getInput();if(s)window.location='/hisse/'+s;else document.getElementById('hisse-input').focus();}
async function addTemettuTakip(){
  var s=getInput();
  if(!s){document.getElementById('hisse-input').focus();return;}
  try{
    var r=await fetch('/api/temettu-takip/'+s,{method:'POST'});
    var d=await r.json();
    var list=(d&&Array.isArray(d.hisseler))?d.hisseler:[];
    if(d.success||list.includes(s))alert(s+' temettü takip listesine eklendi.');
    else alert('Hisse zaten takip listesinde veya eklenemedi.');
  }catch(e){console.error(e);alert('Sunucuya ulasilamiyor');}
}
function tFav(s,el){fetch('/toggle_favorite/'+s,{method:'POST'}).then(r=>r.json()).then(d=>{el.textContent=d.is_fav?'\u2764\ufe0f':'\u2661';});}
async function refreshPopuler(){
  try{
    var r=await fetch('/api/populer-hisseler');
    var data=await r.json();
    var grid=document.getElementById('populer-grid');
    if(grid&&data.hisseler)grid.innerHTML=data.hisseler.map(h=>h.html).join('');
  }catch(e){console.warn('Liste guncellenemedi',e);}
}
async function addHisse(){
  var s=getInput();
  if(!s){document.getElementById('hisse-input').focus();return;}
  document.getElementById('hisse-input').value='';
  var btn=document.getElementById('btn-hisse-ekle');
  if(btn){btn.textContent='Ekleniyor…';btn.disabled=true;}
  try{
    var r=await fetch('/add_hisse/'+s,{method:'POST'});
    var d=await r.json();
    if(d.status==='ok'){
      var grid=document.getElementById('populer-grid');
      if(grid&&d.card_html){
        // Zaten listede ise kart varsa flash yap, yoksa sona ekle
        var existing=grid.querySelector('[data-sembol="'+s+'"]');
        if(existing){
          existing.style.transition='box-shadow .3s';
          existing.style.boxShadow='0 0 0 2px #38bdf8';
          setTimeout(function(){existing.style.boxShadow='';},1200);
        } else {
          var tmp=document.createElement('div');
          tmp.innerHTML=d.card_html;
          var newCard=tmp.firstElementChild;
          newCard.style.opacity='0';
          newCard.style.transition='opacity .3s';
          grid.appendChild(newCard);
          requestAnimationFrame(function(){newCard.style.opacity='1';});
        }
      }
    } else {
      alert(d.message||'Eklenemedi');
    }
  }catch(e){console.error(e);alert('Sunucuya ulasilamiyor');}
  finally{
    if(btn){btn.textContent='+ Hisse Listesine Ekle';btn.disabled=false;}
  }
}
async function removeHisse(s){
  var grid=document.getElementById('populer-grid');
  if(grid){
    var card=grid.querySelector('[data-sembol="'+s+'"]');
    if(card){card.style.transition='opacity .2s';card.style.opacity='0';setTimeout(function(){card.remove();},220);}
  }
  try{await fetch('/remove_hisse/'+s,{method:'POST'});}catch(e){console.error(e);}
}
setInterval(refreshPopuler,60000);
document.addEventListener('visibilitychange',function(){if(document.visibilityState==='visible')refreshPopuler();});
</script>"""

    body = (
        '<div class="wrap">'
        '<div style="margin-bottom:16px;display:flex;gap:8px;flex-wrap:wrap;align-items:center">'
        '<input id="hisse-input"'
        ' style="flex:1;min-width:180px;max-width:360px;background:var(--surf2);border:1px solid var(--brd);'
        'color:var(--txt);padding:9px 14px;border-radius:7px;font-size:14px;outline:none"'
        ' placeholder="Sembol yaz: THYAO, EREGL\u2026" maxlength="10"'
        ' oninput="this.value=this.value.toUpperCase()"'
        " onkeypress=\"if(event.key==='Enter')goToHisse()\">"
        '<button class="pill" onclick="goToHisse()" style="padding:9px 14px">Hisse Ara</button>'
        '<button id="btn-hisse-ekle" class="pill on" onclick="addHisse()" style="padding:9px 14px">+ Hisse Listesine Ekle</button>'
        "</div>"
        f'<h2>\u2b50 Favorilerim</h2><div class="grid">{fav_html}</div>'
        '<h2>Hisse Listesi <small style="font-weight:400;color:var(--muted);font-size:.7rem">'
        "(skora g\u00f6re \u2014 \u2715 ile \u00e7\u0131kar)</small></h2>"
        f'<div class="grid" id="populer-grid">{cards}</div>'
        "</div>" + js + notlar_modal_html()
    )
    return page("BIST Hisseler", body, "/")


@app.get("/hisse/{sembol}", response_class=HTMLResponse)
async def hisse_detay(sembol: str, interval: str = DEFAULT_INTERVAL):
    sembol = sembol.upper().strip()
    d = teknik_analiz(sembol, interval)
    temettu = get_temettu_ozet(sembol)
    fav = "❤️" if sembol in FAVORILER else "♡"
    sc = skc(d.skor)
    rc = "#ef4444" if (d.degisim or 0) < 0 else "#22c55e"

    iv_pills = "".join(
        f'<a class="pill {"on" if k == interval else ""}" href="/hisse/{sembol}?interval={k}">{lbl}</a>'
        for k, (*_, lbl) in INTERVAL_MAP.items()
    )

    the_js = build_chart_js(
        f"/api/chart/{sembol}?interval={interval}",
        interval in INTRADAY_INTERVALS,
        with_indicators=True,
    )

    inds = (
        tdr("RSI (14)", d.rsi)
        + tdr("MACD", d.macd)
        + tdr("Sinyal", d.macd_signal)
        + tdr("Hist", d.macd_hist)
        + tdr("BB Üst", d.bb_upper, "TL")
        + tdr("BB Orta", d.bb_middle, "TL")
        + tdr("BB Alt", d.bb_lower, "TL")
        + tdr("BB Konum", f"%{d.bb_yuzde}" if d.bb_yuzde else None)
        + tdr("SMA20", d.sma20, "TL")
        + tdr("SMA50", d.sma50, "TL")
        + tdr("SMA200", d.sma200, "TL")
        + tdr("EMA20", d.ema20, "TL")
        + tdr("Hacim Oran", f"{d.hacim_oran}x" if d.hacim_oran else None)
        + tdr("Destek", d.destek, "TL")
        + tdr("Direnç", d.direnc, "TL")
        + tdr("⚡ Supertrend", getattr(d, "supertrend", "—"))
        + tdr("🌸 Ichimoku Kijun", getattr(d, "ichimoku_kijun", "—"))
    )

    sigs = (
        "".join(f"<li>{s}</li>" for s in d.sinyaller)
        or "<li style='color:var(--muted)'>—</li>"
    )

    t_rows = ""
    for t in temettu.get("gecmis", []):
        vr = "var(--green)" if t.get("verim_yuzde") else "var(--muted)"
        vs = "%" + str(t["verim_yuzde"]) if t.get("verim_yuzde") else "—"
        t_rows += (
            f"<tr><td>{t['tarih']}</td><td style='text-align:right'>{t['tutar']} TL</td>"
            f"<td style='text-align:right;color:{vr}'>{vs}</td></tr>"
        )

    ort_v = (
        ("%" + str(temettu.get("ortalama_verim")))
        if temettu.get("ortalama_verim")
        else "—"
    )

    # app.get("/hisse/{sembol}") altındaki hisse_toolbar alanını bu temiz buton yapısıyla değiştirin:
    hisse_toolbar = f"""<div class="toolbar" style="margin-top:6px; display:flex; gap:4px; flex-wrap:wrap;">
  <span style="font-size:.67rem;color:var(--muted);margin-right:3px;align-self:center">Göstergeler:</span>
  <button class="pill"  id="ind-bb"         onclick="toggleInd('bb')">BB</button>
  <button class="pill"  id="ind-sma20"      onclick="toggleInd('sma20')">SMA20</button>
  <button class="pill"  id="ind-sma50"      onclick="toggleInd('sma50')">SMA50</button>
  <button class="pill"  id="ind-sma200"     onclick="toggleInd('sma200')">SMA200</button>
  <button class="pill"  id="ind-ema20"      onclick="toggleInd('ema20')">EMA20</button>
  <button class="pill"  id="ind-vol"        onclick="toggleInd('vol')">Hacim</button>
  <button class="pill"  id="ind-rsi"        onclick="toggleInd('rsi')">RSI</button>
  <button class="pill"  id="ind-macd"       onclick="toggleInd('macd')">MACD</button>
  <button class="pill"  id="ind-supertrend" onclick="toggleInd('supertrend')">⚡ Supertrend</button>
  <button class="pill"  id="ind-ichimoku"   onclick="toggleInd('ichimoku')">🌸 Ichimoku</button>
</div>"""

    # Hacim, RSI ve MACD alt kutularının sayfa ilk yüklendiğinde gizli kalması için
    # chart_divs fonksiyonunun çıktısını dikeyde display:none ile gizliyoruz.
    # Bu gizleme JavaScript butonuna ilk tıklandığı an 'block' durumuna dönerek açılacaktır.

    body = f"""{LW}
<div class="wrap">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:12px;flex-wrap:wrap;gap:8px">
    <div>
      <div style="font-family:'Space Mono',monospace;font-size:1.6rem;color:var(--acc);font-weight:700">
        {d.sembol} <button id="fav-btn" onclick="tFav('{sembol}')"
          style="background:none;border:none;font-size:17px;cursor:pointer;vertical-align:middle;margin-left:4px">{fav}</button>
      </div>
      <div style="font-size:1.7rem;font-weight:600;margin:2px 0">
        {fiyat_goster(d)} <small style="font-size:.85rem;color:var(--muted)">TL</small></div>
      <div style="color:{rc};font-size:.88rem;font-weight:500">{"▼" if (d.degisim or 0) < 0 else "▲"} %{d.degisim or 0}</div>
      <div style=\"display:flex;gap:8px;flex-wrap:wrap;margin-top:10px\">
        <button id=\"btn-detay-hisse-ekle\" class=\"pill on\" onclick=\"hisseListesineEkle('{sembol}')\">+ Hisse Listesine Ekle</button>
        <a href=\"/\" class=\"pill\">← Listeye Dön</a>
      </div>
    </div>
    <div style="text-align:center;background:var(--surf);border:1px solid var(--brd);border-radius:9px;padding:11px 18px">
      <div style="font-size:1.9rem;font-weight:700;font-family:'Space Mono',monospace;color:{sc}">{d.skor}</div>
      <div style="color:var(--muted);font-size:.67rem;margin-bottom:2px">Bileşik Skor /100</div>
      <div style="font-size:.9rem;font-weight:700;color:{sc}">{d.tavsiye}</div>
    </div>
  </div>
  {toolbar_html(iv_pills, show_ind=False)}
  {hisse_toolbar}
  {chart_divs(h=260)}
  <div class="g3">
    <div class="panel"><h2>Teknik İndikatörler</h2><table class="ind">{inds}</table></div>
    <div class="panel"><h2>Sinyaller</h2><ul class="sig-list">{sigs}</ul></div>
    <div class="panel">
      <h2>Temettü</h2>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:5px;margin-bottom:9px">
        <div style="background:var(--surf2);border-radius:6px;padding:8px;text-align:center">
          <div style="color:var(--muted);font-size:.65rem;margin-bottom:2px">Ödeme</div>
          <div style="font-size:1.15rem;font-weight:700">{temettu.get("odeme_sayisi", "—")}</div>
        </div>
        <div style="background:var(--surf2);border-radius:6px;padding:8px;text-align:center">
          <div style="color:var(--muted);font-size:.65rem;margin-bottom:2px">Ort. Verim</div>
          <div style="font-size:1.15rem;font-weight:700;color:var(--green)">{ort_v}</div>
        </div>
      </div>
      <table style="width:100%;border-collapse:collapse;font-size:.72rem">
        <tr style="color:var(--muted);font-size:.65rem">
          <th style="text-align:left;padding:3px">Tarih</th>
          <th style="text-align:right;padding:3px">Tutar</th>
          <th style="text-align:right;padding:3px">Verim</th>
        </tr>
        {t_rows or '<tr><td colspan="3" style="color:var(--muted);padding:5px 0">Veri yok</td></tr>'}
      </table>
    </div>
  </div>
  <div class="panel" id="notlar-panel" style="margin-top:12px">
    <h2>📝 Görüş & Notlarım</h2>
    <textarea id="not-inline-text" rows="5" placeholder="Bu hisse hakkında görüşünüz, hedef fiyat, strateji…"
      style="width:100%;background:var(--surf2);border:1px solid var(--brd);color:var(--txt);border-radius:7px;padding:10px;font-size:.85rem;resize:vertical"></textarea>
    <div style="display:flex;justify-content:space-between;align-items:center;margin-top:8px">
      <small id="not-inline-ts" style="color:var(--muted);font-size:.68rem"></small>
      <button type="button" class="pill on" onclick="saveNotInline()">Kaydet</button>
    </div>
  </div>
</div>
{the_js}
<script>
function tFav(s){{fetch("/toggle_favorite/"+s,{{method:"POST"}}).then(r=>r.json())
  .then(d=>{{document.getElementById("fav-btn").textContent=d.is_fav?"❤️":"♡";}});}}
function hisseListesineEkle(s){{
  const btn=document.getElementById(\"btn-detay-hisse-ekle\");
  if(btn){{btn.disabled=true;btn.textContent=\"Ekleniyor…\";}}
  fetch(\"/add_hisse/\"+s,{{method:\"POST\"}})
    .then(r=>r.json())
    .then(d=>{{
      if(d.status===\"ok\"){{
        if(btn)btn.textContent=d.already?\"✓ Hisse Listesinde\":\"✓ Hisse Listesine Eklendi\";
      }}else{{
        if(btn)btn.textContent=\"+ Hisse Listesine Ekle\";
        alert(d.message||\"Eklenemedi\");
      }}
    }})
    .catch(()=>{{
      if(btn)btn.textContent=\"+ Hisse Listesine Ekle\";
      alert(\"Sunucuya ulasilamiyor\");
    }})
    .finally(()=>{{if(btn)btn.disabled=false;}});
}}
const NOT_SEMBOL="{sembol}";
function loadNotInline(){{
  fetch("/api/notlar/"+NOT_SEMBOL).then(r=>r.json()).then(d=>{{
    document.getElementById("not-inline-text").value=d.text||"";
    document.getElementById("not-inline-ts").textContent=d.updated?"Son güncelleme: "+d.updated:"";
  }});
}}
function saveNotInline(){{
  const text=document.getElementById("not-inline-text").value;
  fetch("/api/notlar/"+NOT_SEMBOL,{{method:"POST",headers:{{"Content-Type":"application/json"}},
    body:JSON.stringify({{text}})}}).then(r=>r.json()).then(d=>{{
    document.getElementById("not-inline-ts").textContent=d.updated?"Son güncelleme: "+d.updated:"Kaydedildi";
  }});
}}
loadNotInline();
</script>
{notlar_modal_html()}"""
    return page(sembol, body, "/")


@app.get("/api/chart/{sembol}")
async def chart_api(sembol: str, interval: str = DEFAULT_INTERVAL):
    sonuc = teknik_analiz(sembol.upper(), interval)
    if sonuc.df is None or sonuc.df.empty:
        return JSONResponse({"candles": [], "volume": []})
    return JSONResponse(df_to_chart_json(sonuc.df, interval))


@app.get("/temettu", response_class=HTMLResponse)
async def temettu_sayfasi():
    yaklasan = get_yaklasan_temettular()[:20]
    sampiyonlar = get_temettu_sampiyonlari(limit=10, period="year")

    # Şampiyonlar kartları
    cards = ""
    for s in sampiyonlar:
        cards += (
            f'<div class="card" onclick="window.location=\'/temettu/{s["sembol"]}\'">'
            f'<span class="sym">{s["sembol"]}</span>'
            f'<div style="font-size:.72rem;color:var(--muted);margin:3px 0 2px">5Y Toplam</div>'
            f'<div style="font-weight:600;font-size:.8rem">{s["toplam_5y"]} TL</div>'
            f'<div style="margin-top:4px;display:flex;gap:4px;flex-wrap:wrap">'
            f'<span style="background:#22c55e20;color:var(--green);padding:2px 6px;border-radius:20px;font-size:.67rem;font-weight:600">Verim: %{s["verim"]}</span>'
            f"</div></div>"
        )

    # Takvim tablosu
    t_rows = ""
    for t in (yaklasan or [])[:20]:
        h = t.get("hisse", "?")
        tarih = t.get("Temettü Tarihi", "-")
        tutar = t.get("Temettü", "-")
        t_rows += (
            f"<tr><td style='padding:5px 8px;border-bottom:1px solid var(--brd)'>"
            f"<a href='/temettu/{h}' style='font-family:Space Mono,monospace;color:var(--acc);font-weight:700'>{h}</a>"
            f"</td><td style='padding:5px 8px;border-bottom:1px solid var(--brd);font-size:.75rem'>{tarih}</td>"
            f"<td style='padding:5px 8px;border-bottom:1px solid var(--brd);font-size:.75rem'>{tutar}</td></tr>"
        )
    if not t_rows:
        t_rows = "<tr><td colspan='3' style='padding:14px;color:var(--muted);text-align:center'>Takvim verisi alınamadı</td></tr>"

    # Takip listesi
    takip_listesi = get_temettu_takip_listesi()
    takip_cards = ""
    for s in takip_listesi:
        oz = get_temettu_ozet(s)
        ov = ("%" + str(oz["ortalama_verim"])) if oz.get("ortalama_verim") else "—"
        takip_cards += (
            f'<div class="card" onclick="window.location=\'/temettu/{s}\'">'
            f'<span class="sym">{s}</span>'
            f'<div style="font-size:.72rem;color:var(--muted);margin:3px 0 2px">Son ödeme</div>'
            f'<div style="font-weight:600;font-size:.8rem">{oz.get("son_temettu", "—")}</div>'
            f'<div style="margin-top:4px;display:flex;gap:4px;flex-wrap:wrap">'
            f'<span style="background:#22c55e20;color:var(--green);padding:2px 6px;border-radius:20px;font-size:.67rem;font-weight:600">Ort.{ov}</span>'
            f'<span style="background:#f59e0b20;color:var(--amber);padding:2px 6px;border-radius:20px;font-size:.67rem;font-weight:600">{oz.get("odeme_sayisi", 0)} öd.</span>'
            f'<span onclick="event.stopPropagation();cikarTakip(\'{s}\')" style="background:#ef444420;color:var(--red);padding:2px 6px;border-radius:20px;font-size:.67rem;font-weight:600;cursor:pointer">Çıkar</span>'
            f"</div></div>"
        )
    if not takip_cards:
        takip_cards = "<div style='grid-column:1/-1;padding:20px;color:var(--muted);text-align:center;background:var(--surf);border:1px solid var(--brd);border-radius:9px'>Takip listesi boş. Hisse detayından ekleyebilirsiniz.</div>"

    body = (
        f'<div class="wrap">'
        f'<div style="margin-bottom:14px;display:flex;gap:8px;flex-wrap:wrap;align-items:center">'
        f'<input id="temettu-hisse-input"'
        f' style="flex:1;min-width:180px;max-width:360px;background:var(--surf2);border:1px solid var(--brd);'
        f'color:var(--txt);padding:9px 14px;border-radius:7px;font-size:14px;outline:none"'
        f' placeholder="Temettü hissesi ara: THYAO, TUPRS…" maxlength="10"'
        f' oninput="this.value=this.value.toUpperCase()"'
        f" onkeypress=\"if(event.key===\\'Enter\\')temettuAra()\">"
        f'<button class="pill" onclick="temettuAra()" style="padding:9px 14px">🔎 Hisse Ara</button>'
        f'<button class="pill on" onclick="takipListesineEkle()" style="padding:9px 14px">+ Takip Listesine Ekle</button>'
        f"</div>"
        f'<div class="g2">'
        f'<div><h2>🏆 Yılın Temettü Şampiyonları</h2><div class="grid">{cards}</div></div>'
        f"<div><h2>📅 Yaklaşan Temettü Tarihleri</h2>"
        f'<div style="background:var(--surf);border:1px solid var(--brd);border-radius:9px;overflow:hidden;margin-bottom:12px">'
        f'<table style="width:100%;border-collapse:collapse"><thead><tr style="background:var(--surf2)">'
        f'<th style="text-align:left;padding:7px 8px;font-size:.67rem;color:var(--muted)">HİSSE</th>'
        f'<th style="text-align:left;padding:7px 8px;font-size:.67rem;color:var(--muted)">TARİH</th>'
        f'<th style="text-align:left;padding:7px 8px;font-size:.67rem;color:var(--muted)">TUTAR</th>'
        f"</tr></thead><tbody>{t_rows}</tbody></table></div></div>"
        f"</div>"
        f'<h2>⭐ Temettü Takip Listesi</h2><div class="grid">{takip_cards}</div></div>'
        "<script>"
        'function temettuInputDeger(){return (document.getElementById("temettu-hisse-input").value||"").trim().toUpperCase();}'
        "function temettuAra(){"
        "  var s=temettuInputDeger();"
        '  if(!s){document.getElementById("temettu-hisse-input").focus();return;}'
        '  window.location="/temettu/"+s;'
        "}"
        "function takipListesineEkle(){"
        "  var s=temettuInputDeger();"
        '  if(!s){document.getElementById("temettu-hisse-input").focus();return;}'
        '  fetch("/api/temettu-takip/"+s,{method:"POST"})'
        "    .then(r=>r.json())"
        "    .then(d=>{"
        "      var list=(d&&Array.isArray(d.hisseler))?d.hisseler:[];"
        "      if(d.success||list.includes(s)){location.reload();}"
        '      else{alert("Hisse zaten takip listesinde veya eklenemedi.");}'
        "    })"
        '    .catch(()=>alert("İstek gönderilemedi."));'
        "}"
        "function cikarTakip(s){"
        '  fetch("/api/temettu-takip/"+s,{method:"DELETE"})'
        "    .then(r=>r.json())"
        "    .then(d=>{if(d.success)location.reload();});"
        "}"
        "</script>"
    )
    return page("Temettü", body, "/temettu")


@app.get("/temettu/{sembol}", response_class=HTMLResponse)
async def temettu_hisse_detay(sembol: str):
    sembol = sembol.upper()
    ozet = get_temettu_ozet(sembol)
    gecmis = ozet.get("gecmis", [])
    takip_listesi = get_temettu_takip_listesi()
    takipta = sembol in takip_listesi

    # Ek metrikler
    ucuzluk_skoru = get_temettu_ucuzluk_skoru(sembol)
    amorti_suresi = get_amorti_suresi(sembol)

    # Temettü geçmişi tablosu
    gecmis_rows = ""
    for g in gecmis:
        gecmis_rows += f"<tr><td style='padding:5px 8px;border-bottom:1px solid var(--brd)'>{g['tarih']}</td>"
        gecmis_rows += f"<td style='padding:5px 8px;border-bottom:1px solid var(--brd)'>{g['tutar']} TL</td>"
        gecmis_rows += f"<td style='padding:5px 8px;border-bottom:1px solid var(--brd)'>{g['verim_yuzde']}%</td></tr>"
    if not gecmis_rows:
        gecmis_rows = "<tr><td colspan='3' style='padding:14px;color:var(--muted);text-align:center'>Temettü geçmişi bulunamadı</td></tr>"

    # Takip butonu
    takip_btn = (
        f'<button class="pill on" onclick="cikarTakip(\'{sembol}\')">Takipten Çıkar</button>'
        if takipta
        else f'<button class="pill" onclick="ekleTakip(\'{sembol}\')">Takip Listesine Ekle</button>'
    )

    body = f"""<div class="wrap">
        <div style="margin-bottom:14px">
            <div style="font-family:'Space Mono',monospace;font-size:1.4rem;color:var(--acc);font-weight:700">{sembol}</div>
            <div style="color:var(--muted);margin-bottom:8px;font-size:.79rem">Temettü Analizi</div>
            <div style="display:flex;gap:8px;margin-bottom:12px">{takip_btn} <a href="/temettu" class="pill">← Listeye Dön</a></div>
        </div>

        <div class="g2">
            <div class="panel">
                <h2>📊 Temettü Özeti</h2>
                <table class="ind">
                    {tdr("Son Temettü", ozet.get("son_temettu", "—"))}
                    {tdr("5Y Toplam", ozet.get("toplam_5y", "—"), "TL")}
                    {tdr("Ortalama Verim", ozet.get("ortalama_verim", "—"), "%")}
                    {tdr("Ödeme Sayısı", ozet.get("odeme_sayisi", 0))}
                    {tdr("Ucuzluk Skoru", ucuzluk_skoru if ucuzluk_skoru else "—")}
                    {tdr("Amorti Süresi", f"{amorti_suresi} yıl" if amorti_suresi else "—")}
                </table>
            </div>

            <div class="panel">
                <h2>💰 Temettü Geçmişi</h2>
                <div style="background:var(--surf);border:1px solid var(--brd);border-radius:9px;overflow:hidden">
                    <table style="width:100%;border-collapse:collapse">
                        <thead><tr style="background:var(--surf2)">
                            <th style="text-align:left;padding:7px 8px;font-size:.67rem;color:var(--muted)">TARİH</th>
                            <th style="text-align:left;padding:7px 8px;font-size:.67rem;color:var(--muted)">TUTAR</th>
                            <th style="text-align:left;padding:7px 8px;font-size:.67rem;color:var(--muted)">VERİM</th>
                        </tr></thead>
                        <tbody>{gecmis_rows}</tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>
    <script>
    function ekleTakip(s) {{
        fetch('/api/temettu-takip/' + s, {{method: 'POST'}})
            .then(r => r.json())
            .then(d => {{ if(d.success) location.reload(); }});
    }}
    function cikarTakip(s) {{
        fetch('/api/temettu-takip/' + s, {{method: 'DELETE'}})
            .then(r => r.json())
            .then(d => {{ if(d.success) location.reload(); }});
    }}
    </script>
    """
    return page(f"Temettü {sembol}", body, "/temettu")


@app.get("/fonlar", response_class=HTMLResponse)
async def fonlar_sayfasi(tip: str = "YAT", siralama: str = "getiri1y", tur: str = ""):
    tip = tip.upper() if tip.upper() in FON_TIPLERI else "YAT"

    # Fon listesini çek
    fonlar = get_fon_listesi(tip)

    # Tür filtresi
    tur_listesi = sorted({f["tur"] for f in fonlar if f["tur"]})
    if tur:
        fonlar = [f for f in fonlar if f["tur"] == tur]

    # Sıralama
    SIRALAMA_ALANLARI = [
        "getiri1a",
        "getiri3a",
        "getiri6a",
        "getiri1y",
        "getiriyb",
        "getiri3y",
        "getiri5y",
    ]
    if siralama not in SIRALAMA_ALANLARI:
        siralama = "getiri1y"
    fonlar_sirali = sorted(
        fonlar, key=lambda f: (f.get(siralama) is None, -(f.get(siralama) or 0))
    )

    # ── Tip seçici tabs ──────────────────────────────────────────────────────
    tip_tabs = "".join(
        f'<a href="/fonlar?tip={k}&siralama={siralama}&tur={tur}" '
        f'class="pill{" on" if tip == k else ""}">{v}</a>'
        for k, v in FON_TIPLERI.items()
    )

    # ── Dönem sıralama butonları ─────────────────────────────────────────────
    donem_pills = "".join(
        f'<a href="/fonlar?tip={tip}&siralama={alan}&tur={tur}" '
        f'class="pill{" on" if siralama == alan else ""}">{etiket}</a>'
        for alan, etiket, _ in FON_PERIYOTLARI
    )

    # ── Tür filtre dropdown (select) ─────────────────────────────────────────
    tur_opts = '<option value="">Tüm Türler</option>' + "".join(
        f'<option value="{t}"{" selected" if tur == t else ""}>{t}</option>'
        for t in tur_listesi
    )
    tur_select = (
        f"<select onchange=\"window.location='/fonlar?tip={tip}&siralama={siralama}&tur='+(this.value)\" "
        f'style="background:var(--surf2);border:1px solid var(--brd);color:var(--txt);'
        f'padding:7px 10px;border-radius:7px;font-size:.78rem;cursor:pointer">'
        f"{tur_opts}</select>"
    )

    # ── Fon satırları (tablo) ────────────────────────────────────────────────
    def getiri_td(val):
        if val is None:
            return '<td style="color:var(--muted);text-align:right">—</td>'
        rc = "var(--green)" if val >= 0 else "var(--red)"
        ok = "▲" if val >= 0 else "▼"
        return f'<td style="color:{rc};text-align:right;font-weight:600">{ok} %{val:.2f}</td>'

    def risk_badge(r):
        try:
            rv = int(r)
        except Exception:
            return "—"
        colors = [
            "#22c55e",
            "#84cc16",
            "#eab308",
            "#f97316",
            "#ef4444",
            "#dc2626",
            "#991b1b",
        ]
        c = colors[min(rv - 1, 6)] if rv else "var(--muted)"
        return f'<span style="background:{c}22;color:{c};padding:2px 7px;border-radius:10px;font-size:.67rem;font-weight:700">{rv}</span>'

    satirlar = ""
    for i, f in enumerate(fonlar_sirali[:500]):  # maksimum 500 satır göster
        zs = "background:var(--surf2)" if i % 2 == 0 else ""
        satirlar += (
            f'<tr style="cursor:pointer;{zs}" onclick="window.location=\'/fon/{f["kod"]}\'">'
            f'<td style="padding:7px 10px;font-family:Space Mono,monospace;color:var(--acc);font-weight:700">{f["kod"]}</td>'
            f'<td style="padding:7px 10px;font-size:.75rem;max-width:260px">{f["unvan"][:50]}</td>'
            f'<td style="padding:7px 10px;font-size:.68rem;color:var(--muted)">{f["tur"] or "—"}</td>'
            + getiri_td(f.get("getiri1a"))
            + getiri_td(f.get("getiri3a"))
            + getiri_td(f.get("getiri6a"))
            + getiri_td(f.get("getiri1y"))
            + getiri_td(f.get("getiriyb"))
            + getiri_td(f.get("getiri3y"))
            + getiri_td(f.get("getiri5y"))
            + f'<td style="text-align:center;padding:7px 8px">{risk_badge(f.get("risk"))}</td>'
            + "</tr>"
        )

    if not satirlar:
        satirlar = "<tr><td colspan='11' style='padding:24px;text-align:center;color:var(--muted)'>Veri bulunamadı</td></tr>"

    def th(label, alan):
        active = siralama == alan
        col = "var(--acc)" if active else "var(--muted)"
        return (
            f'<th style="padding:7px 8px;font-size:.64rem;text-align:right;cursor:pointer;color:{col};white-space:nowrap" '
            f"onclick=\"window.location='/fonlar?tip={tip}&siralama={alan}&tur={tur}'\">"
            f"{'▼ ' if active else ''}{label}</th>"
        )

    tablo = f"""
    <div style="overflow-x:auto;border-radius:9px;border:1px solid var(--brd);background:var(--surf)">
      <table style="width:100%;border-collapse:collapse;font-size:.8rem">
        <thead>
          <tr style="background:var(--surf2);border-bottom:1px solid var(--brd)">
            <th style="padding:7px 10px;text-align:left;font-size:.64rem;color:var(--muted)">KOD</th>
            <th style="padding:7px 10px;text-align:left;font-size:.64rem;color:var(--muted)">FON ADI</th>
            <th style="padding:7px 10px;text-align:left;font-size:.64rem;color:var(--muted)">TÜR</th>
            {th("1A", "getiri1a")}
            {th("3A", "getiri3a")}
            {th("6A", "getiri6a")}
            {th("1Y", "getiri1y")}
            {th("YB", "getiriyb")}
            {th("3Y", "getiri3y")}
            {th("5Y", "getiri5y")}
            <th style="padding:7px 8px;font-size:.64rem;text-align:center;color:var(--muted)">RİSK</th>
          </tr>
        </thead>
        <tbody>{satirlar}</tbody>
      </table>
    </div>"""

    body = f"""
<div class="wrap">
  <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:14px">
    {tip_tabs}
    <span style="flex:1"></span>
    {tur_select}
  </div>
  <div style="display:flex;gap:6px;flex-wrap:wrap;align-items:center;margin-bottom:12px">
    <span style="font-size:.68rem;color:var(--muted);margin-right:2px">Getiriye Göre Sırala:</span>
    {donem_pills}
  </div>
  <div style="font-size:.68rem;color:var(--muted);margin-bottom:8px">
    {len(fonlar_sirali)} fon listeleniyor{" (ilk 500)" if len(fonlar_sirali) > 500 else ""}
    &nbsp;·&nbsp; Kaynak: TEFAS
  </div>
  {tablo}
</div>"""
    return page("Fonlar", body, "/fonlar")


@app.get("/fon/{kod}", response_class=HTMLResponse)
async def fon_detay_sayfasi(kod: str, periyod: int = 12):
    kod = kod.upper()
    d = get_fon_detay(kod)

    # Periyod seçici
    periyod_secenekleri = [
        (1, "1A"),
        (3, "3A"),
        (6, "6A"),
        (12, "1Y"),
        (36, "3Y"),
        (60, "5Y"),
    ]
    periyod_pills = "".join(
        f'<a class="pill{" on" if p == periyod else ""}" href="/fon/{kod}?periyod={p}">{lbl}</a>'
        for p, lbl in periyod_secenekleri
    )

    # Fiyat geçmişi
    gecmis = get_fon_fiyat_gecmis(kod, periyod)
    gun_deg = None
    if gecmis and len(gecmis) >= 2:
        ilk = gecmis[0]["value"]
        son = gecmis[-1]["value"]
        gun_deg = round((son - ilk) / ilk * 100, 2) if ilk else None

    rc = "var(--green)" if (gun_deg or 0) >= 0 else "var(--red)"
    ok = "▲" if (gun_deg or 0) >= 0 else "▼"
    lbl_map = {
        1: "1 Aylık",
        3: "3 Aylık",
        6: "6 Aylık",
        12: "1 Yıllık",
        36: "3 Yıllık",
        60: "5 Yıllık",
    }
    donem_lbl = lbl_map.get(periyod, f"{periyod}A")

    # Getiri rozetleri (fon listesinden al)
    getiri_satirlari = ""
    for alan, etiket, _ in FON_PERIYOTLARI:
        # İsim eşleştirmesi: getiri1a → get_fon_detay döndürmüyor;
        # fon listesinden çekmeye gerek yok, fon_getiri endpoint'inden zaten geliyor.
        pass

    # Detay kartı
    def fmt_para(v):
        if v is None:
            return "—"
        try:
            m = float(v)
            if m >= 1e9:
                return f"{m / 1e9:.2f} Milyar TL"
            if m >= 1e6:
                return f"{m / 1e6:.2f} Milyon TL"
            return f"{m:,.2f} TL"
        except Exception:
            return str(v)

    hata_html = ""
    if d.get("hata"):
        hata_html = f'<div style="background:var(--surf2);border:1px solid var(--brd);border-radius:6px;padding:8px;color:var(--red);font-size:.74rem;margin-bottom:10px">⚠️ {d["hata"]}</div>'

    detay_satirlar = ""
    for label, key, fmt in [
        ("Son Fiyat", "son_fiyat", lambda v: f"{v:.6f} TL"),
        ("Günlük Getiri", "gunluk_getiri", lambda v: f"%{v:.2f}"),
        ("Portföy Büyüklüğü", "port_buyukluk", fmt_para),
        ("Kategori", "kategori", str),
        ("Sıralama", "derece", lambda v: f"{v}/{d.get('sayi', '?')}"),
        ("Yatırımcı Sayısı", "yatirimci", lambda v: f"{int(v):,}"),
        ("Pazar Payı", "pazar_payi", lambda v: f"%{v:.2f}"),
    ]:
        val = d.get(key)
        if val is None:
            continue
        try:
            formatted = fmt(val)
        except Exception:
            formatted = str(val)
        # Günlük getiriye renk
        if key == "gunluk_getiri":
            try:
                gv = float(val)
                col = "var(--green)" if gv >= 0 else "var(--red)"
                formatted = f'<span style="color:{col}">{"▲" if gv >= 0 else "▼"} %{abs(gv):.2f}</span>'
            except Exception:
                pass
        detay_satirlar += f'<tr><td style="padding:6px 10px;color:var(--muted);font-size:.75rem">{label}</td><td style="padding:6px 10px;font-weight:600;font-size:.8rem">{formatted}</td></tr>'

    # Chart JS (line grafik)
    chart_data_json = __import__("json").dumps(gecmis)
    chart_js = f"""
<script>
(function(){{
  var LWC = window.LightweightCharts;
  if (!LWC) {{ console.error('LWC yok'); return; }}
  var container = document.getElementById('fon-chart');
  if (!container) return;
  var chart = LWC.createChart(container, {{
    width: container.clientWidth,
    height: 320,
    layout: {{ background: {{ type: 'solid', color: '#131722' }}, textColor: '#d1d4dc' }},
    grid: {{ vertLines: {{ color: '#242a35' }}, horzLines: {{ color: '#242a35' }} }},
    rightPriceScale: {{ autoScale: true }},
    timeScale: {{ borderColor: '#2a2e39', timeVisible: false }},
    handleScroll: {{ mouseWheel: true, pressedMouseButton: true }},
    handleScale: {{ axisPressedMouseMove: true, mouseWheel: true }},
  }});
  var series = chart.addAreaSeries({{
    lineColor: '#38bdf8',
    topColor: '#38bdf833',
    bottomColor: '#38bdf805',
    lineWidth: 2,
    priceFormat: {{ type: 'price', precision: 6, minMove: 0.000001 }},
  }});
  var data = {chart_data_json};
  series.setData(data);
  chart.timeScale().fitContent();
  if (typeof ResizeObserver !== 'undefined') {{
    new ResizeObserver(function() {{ chart.resize(container.clientWidth, 320); }}).observe(container);
  }}
}}());
</script>"""

    body = f"""{LW}
<div class="wrap">
  <div style="display:flex;align-items:flex-start;gap:18px;flex-wrap:wrap;margin-bottom:16px">
    <div style="flex:1;min-width:200px">
      <div style="font-family:'Space Mono',monospace;font-size:1.3rem;color:var(--acc);font-weight:700">{kod}</div>
      <div style="color:var(--txt);font-size:.88rem;margin:3px 0 8px;line-height:1.4">{d.get("unvan", "")}</div>
      {hata_html}
      <div style="font-size:1.65rem;font-weight:600">{f"{d['son_fiyat']:.6f}" if d.get("son_fiyat") else "—"} <small style="font-size:.8rem;color:var(--muted)">TL</small></div>
      {f'<div style="color:{rc};font-size:.88rem;font-weight:500;margin-top:3px">{ok} %{abs(gun_deg):.2f} ({donem_lbl})</div>' if gun_deg is not None else ""}
    </div>
    <div style="background:var(--surf);border:1px solid var(--brd);border-radius:9px;overflow:hidden">
      <table style="border-collapse:collapse;min-width:260px">
        {detay_satirlar}
      </table>
    </div>
  </div>

  <div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:10px">
    {periyod_pills}
  </div>

  <div id="fon-chart" style="width:100%;height:320px;border-radius:7px;overflow:hidden;background:#131722"></div>

  <div style="margin-top:14px">
    <a href="/fonlar" class="pill">← Fonlara Dön</a>
  </div>
</div>
{chart_js}"""
    return page(f"Fon {kod}", body, "/fonlar")


@app.get("/api/fon/{kod}")
async def fon_chart_api(kod: str, periyod: int = 12):
    data = get_fon_fiyat_gecmis(kod.upper(), periyod)
    return JSONResponse({"data": data})


@app.get("/kripto", response_class=HTMLResponse)
async def kripto_sayfasi():
    fiyatlar = get_kripto_fiyatlar()
    cards = ""
    for k in fiyatlar:
        deg = k.get("degisim_24h") or 0
        rc = "var(--green)" if deg >= 0 else "var(--red)"
        ok = "▲" if deg >= 0 else "▼"
        pm = f"{k['piyasa_degeri']:,}" if k.get("piyasa_degeri") else "—"
        cards += (
            f'<div class="card" onclick="window.location=\'/kripto/{k["sembol"]}\'">'
            f'<span class="sym">{k["sembol"]}</span>'
            f'<div class="price">{k.get("fiyat") or "—"} <small style="font-size:.75rem;color:var(--muted)">TL</small></div>'
            f'<div class="chg" style="color:{rc}">{ok} %{deg} (24s)</div>'
            f'<div style="color:var(--muted);font-size:.67rem;margin-top:4px">Piyasa: {pm} TL</div></div>'
        )
    body = (
        f'<div class="wrap"><h2>₿ Kripto Para — TL Bazlı</h2><div class="grid">{cards}</div>'
        f'<p style="font-size:.69rem;color:var(--muted)">Veri: CoinGecko API</p></div>'
    )
    return page("Kripto", body, "/kripto")


# ── YENİ KRİPTO ENGINE VE SAYFA ENTEGRASYONU (BURAYI YAPIŞTIRIN) ───────────────────


def kripto_df_to_chart_json(df: pd.DataFrame) -> Dict:
    """Kripto verilerini Lightweight Charts için tam uyumlu JSON formatına çevirir"""
    df = df.copy().dropna(subset=["close"])

    cols = [
        "RSI",
        "SMA_20",
        "SMA_50",
        "SMA_200",
        "EMA_20",
        "BB_upper",
        "BB_middle",
        "BB_lower",
        "MACD_12_26_9",
        "MACDs_12_26_9",
        "MACDh_12_26_9",
        "SUPERTREND",
        "ICHIMOKU_TENKAN",
        "ICHIMOKU_KIJUN",
        "ICHIMOKU_SSA",
        "ICHIMOKU_SSB",
    ]

    result = {"candles": [], "volume": [], **{c: [] for c in cols}}

    for _, row in df.iterrows():
        t = int(row["time"])
        result["candles"].append(
            {
                "time": t,
                "open": round(float(row["open"]), 2),
                "high": round(float(row["high"]), 2),
                "low": round(float(row["low"]), 2),
                "close": round(float(row["close"]), 2),
            }
        )
        if "volume" in row and pd.notna(row["volume"]):
            result["volume"].append({"time": t, "value": int(row["volume"])})

        for c in cols:
            if c in row and pd.notna(row[c]):
                result[c].append({"time": t, "value": round(float(row[c]), 4)})
    return result


@app.get("/kripto", response_class=HTMLResponse)
async def kripto_sayfasi():
    fiyatlar = get_kripto_fiyatlar()
    cards = ""
    for k in fiyatlar:
        deg = k.get("degisim_24h") or 0
        rc = "var(--green)" if deg >= 0 else "var(--red)"
        ok = "▲" if deg >= 0 else "▼"
        pm = f"{k['piyasa_degeri']:,}" if k.get("piyasa_degeri") else "—"

        cards += (
            f'<div class="card" onclick="window.location=\'/kripto/{k["sembol"]}\'">'
            f'<span class="sym">{k["sembol"]}</span>'
            f'<div class="price">{k.get("fiyat") or "—"} <small style="font-size:.75rem;color:var(--muted)">USD</small></div>'
            f'<div class="chg" style="color:{rc}">{ok} %{deg} (24s)</div>'
            f'<div style="color:var(--muted);font-size:.67rem;margin-top:4px">Piyasa: ${pm}</div></div>'
        )

    body = f'<div class="wrap"><h2>₿ Popüler Kripto Paralar</h2><div class="grid">{cards}</div></div>'
    return page("Kripto Paralar", body, "/kripto")


@app.get("/kripto/{sembol}", response_class=HTMLResponse)
async def kripto_detay(sembol: str, gun: int = 90):
    sembol = sembol.upper().strip()
    d = get_kripto_analiz(sembol, gun=gun)
    if d.get("hata"):
        return page(
            "Hata",
            f'<div class="wrap"><p style="color:var(--red)">{d["hata"]}</p></div>',
            "/kripto",
        )

    sc = skc(d["skor"])
    rc = "#ef4444" if (d["degisim_24h"] or 0) < 0 else "#22c55e"

    # Grafik URL'si ve JS motoru çağrısı
    the_js = build_chart_js(
        f"/api/kripto/chart/{sembol}?gun={gun}", False, with_indicators=True
    )

    # Detay tablosu satırları
    inds = (
        tdr("RSI (14)", d["rsi"])
        + tdr("MACD", d["macd"])
        + tdr("Sinyal", d["macd_signal"])
        + tdr("Supertrend", d["supertrend"])
        + tdr("Trend Yönü", d["supertrend_yon"])
        + tdr("SMA50", d["sma50"], "USD")
        + tdr("SMA200", d["sma200"], "USD")
        + tdr("Ichimoku Tenkan", d["ichimoku_tenkan"], "USD")
        + tdr("Ichimoku Kijun", d["ichimoku_kijun"], "USD")
    )

    sigs = (
        "".join(f"<li>{s}</li>" for s in d["sinyaller"])
        or "<li style='color:var(--muted)'>Sinyal yok</li>"
    )

    # Kriptoya özel Supertrend ve Ichimoku buton barları
    kripto_toolbar = f"""<div class="toolbar" style="margin-top:6px">
  <span style="font-size:.67rem;color:var(--muted);margin-right:3px">Göstergeler:</span>
  <button class="pill on"  id="ind-bb"         onclick="toggleInd('bb')">BB</button>
  <button class="pill on"  id="ind-sma20"      onclick="toggleInd('sma20')">SMA20</button>
  <button class="pill on"  id="ind-sma50"      onclick="toggleInd('sma50')">SMA50</button>
  <button class="pill"     id="ind-sma200"     onclick="toggleInd('sma200')">SMA200</button>
  <button class="pill on"  id="ind-ema20"      onclick="toggleInd('ema20')">EMA20</button>
  <button class="pill on"  id="ind-vol"        onclick="toggleInd('vol')">Hacim</button>
  <button class="pill on"  id="ind-rsi"        onclick="toggleInd('rsi')">RSI</button>
  <button class="pill on"  id="ind-macd"       onclick="toggleInd('macd')">MACD</button>
  <button class="pill on"  id="ind-supertrend" onclick="toggleInd('supertrend')">⚡ Supertrend</button>
  <button class="pill"     id="ind-ichimoku"   onclick="toggleInd('ichimoku')">🌸 Ichimoku</button>
</div>"""

    # Gün seçimi hap butonları (Pills)
    gun_pills = "".join(
        f'<a class="pill {"on" if g == gun else ""}" href="/kripto/{sembol}?gun={g}">{lbl}</a>'
        for g, lbl in [
            (7, "1H"),
            (14, "2H"),
            (30, "1A"),
            (90, "3A"),
            (180, "6A"),
            (365, "1Y"),
        ]
    )

    body = f"""{LW}
<div class="wrap">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:12px;flex-wrap:wrap;gap:8px">
    <div>
      <div style="font-family:'Space Mono',monospace;font-size:1.6rem;color:var(--acc);font-weight:700">{d["sembol"]}</div>
      <div style="font-size:1.7rem;font-weight:600;margin:2px 0">{d["fiyat"] or "—"} <small style="font-size:.85rem;color:var(--muted)">USD</small></div>
      <div style="color:{rc};font-size:.88rem;font-weight:500">{"▼" if (d["degisim_24h"] or 0) < 0 else "▲"} %{d["degisim_24h"] or 0}</div>
    </div>
    <div style="text-align:center;background:var(--surf);border:1px solid var(--brd);border-radius:9px;padding:11px 18px">
      <div style="font-size:1.9rem;font-weight:700;font-family:'Space Mono',monospace;color:{sc}">{d["skor"]}</div>
      <div style="color:var(--muted);font-size:.67rem;margin-bottom:2px">Bileşik Skor /100</div>
      <div style="font-size:.9rem;font-weight:700;color:{sc}">{d["tavsiye"]}</div>
    </div>
  </div>
  {toolbar_html(gun_pills, show_ind=False)}
  {kripto_toolbar}
  {chart_divs(h=400)}
  <div class="g2">
    <div class="panel"><h2>Kripto Teknik Göstergeler</h2><table class="ind">{inds}</table></div>
    <div class="panel"><h2>Sinyaller & Trend Dünyası</h2><ul class="sig-list">{sigs}</ul></div>
  </div>
  <div style="margin-top:12px"><a href="/kripto" style="font-size:.79rem">← Kriptoya Dön</a></div>
</div>
{the_js}"""
    return page(sembol, body, "/kripto")


@app.get("/api/kripto/chart/{sembol}")
async def kripto_chart_api(sembol: str, gun: int = 90):
    d = get_kripto_analiz(sembol.upper(), gun=gun)
    if "_df" not in d or d["_df"].empty:
        return JSONResponse({"candles": [], "volume": []})
    return JSONResponse(kripto_df_to_chart_json(d["_df"]))


@app.post("/add_hisse/{sembol}")
async def add_hisse(sembol: str):
    global POPULER_HISSELER
    s = sembol.upper().strip()
    if not s:
        return JSONResponse({"status": "error", "message": "Geçersiz sembol"})
    already = s in POPULER_HISSELER
    if not already:
        POPULER_HISSELER.append(s)
        _POPULER_CACHE["ts"] = 0.0
        _POPULER_CACHE["rows"] = []
    # Yeni hisse için analiz yap ve kart HTML döndür
    try:
        d = teknik_analiz(s)
        not_map = tum_notlar()
        card_html = hisse_card_html(d, s, not_map.get(s, ""), show_remove=True)
    except Exception:
        card_html = (
            f'<div class="card" data-sembol="{s}" data-skor="0">'
            f'<span class="sym">{s}</span>'
            f'<div style="color:var(--muted);font-size:.75rem;margin-top:6px">Veri yükleniyor…</div>'
            f"</div>"
        )
    return JSONResponse(
        {"status": "ok", "sembol": s, "already": already, "card_html": card_html}
    )


@app.post("/remove_hisse/{sembol}")
async def remove_hisse(sembol: str):
    global POPULER_HISSELER
    s = sembol.upper().strip()
    if s in POPULER_HISSELER:
        POPULER_HISSELER.remove(s)
        _POPULER_CACHE["ts"] = 0.0  # cache'i sıfırla
    return JSONResponse({"status": "ok", "sembol": s})


@app.post("/toggle_favorite/{sembol}")
async def toggle_favorite(sembol: str):
    global FAVORILER
    sembol = sembol.upper()
    if sembol in FAVORILER:
        FAVORILER.remove(sembol)
        is_fav = False
    else:
        FAVORILER.add(sembol)
        is_fav = True
    return {"status": "ok", "is_fav": is_fav}


if __name__ == "__main__":
    import uvicorn

    print("🚀 TürkFin AI → http://127.0.0.1:8000")
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
