"""สร้าง HTML report จากผลคำนวณ"""
from jinja2 import Template

_TEMPLATE = Template("""\
{% macro c(v, ob, os_) %}{% if v is none %}-{% elif v >= ob %}<span style="background:#e53935;color:#fff;border-radius:5px;padding:2px 7px;font-weight:700">{{ "%.0f"|format(v) }}</span>{% elif v <= os_ %}<span style="background:#22c55e;color:#fff;border-radius:5px;padding:2px 7px;font-weight:700">{{ "%.0f"|format(v) }}</span>{% else %}<span style="color:#888">{{ "%.0f"|format(v) }}</span>{% endif %}{% endmacro %}
{% macro chg(label, v) %}<span style="color:#999">{{ label }}</span> {% if v is none %}<span style="color:#bbb">-</span>{% else %}<span style="color:{{ pct_color(v) }}">{{ fmt_pct(v) }}</span>{% endif %}{% endmacro %}
{% macro stoch_line(label, s) %}{% if s.stoch_k is none or s.stoch_d is none %}<div><span style="color:#777">{{ label }}</span> -</div>{% else %}{% set bull = s.stoch_bias == "bull" %}{% set bear = s.stoch_bias == "bear" %}<div style="white-space:nowrap"><span style="color:#777">{{ label }}</span> <span style="color:{{ '#1e8e3e' if bull else '#c0392b' if bear else '#888' }};font-weight:700">{{ 'Bull' if bull else 'Bear' if bear else 'Flat' }}{% if s.stoch_cross == "up" %} ↑{% elif s.stoch_cross == "down" %} ↓{% endif %}</span> <span style="color:#777">K</span> {{ c(s.stoch_k, 80, 20) }} <span style="color:#777">/ D</span> {{ c(s.stoch_d, 80, 20) }}</div>{% endif %}{% endmacro %}
<div style="font-family:-apple-system,Segoe UI,Roboto,sans-serif;max-width:680px;margin:auto;color:#1a1a1a">
  <h2 style="margin-bottom:4px">📊 มูลค่าพอร์ตรวม</h2>
  <div style="color:#666;font-size:13px;margin-bottom:12px">{{ asof }}</div>

  <div style="background:#f5f7fa;border-radius:10px;padding:16px;margin-bottom:16px">
    <div style="font-size:28px;font-weight:700">฿{{ "{:,.0f}".format(totals.total_value) }}</div>
    {% if totals.fx_ok %}
    <div style="color:#555;font-size:13px;margin-top:6px">
      หุ้นไทย ฿{{ "{:,.0f}".format(totals.thb_value) }} ·
      หุ้นเมกา ${{ "{:,.0f}".format(totals.usd_value) }} → ฿{{ "{:,.0f}".format(totals.usd_value * totals.usdthb) }}
      (เรท {{ "%.2f"|format(totals.usdthb) }} ฿/$)
    </div>
    {% else %}
    <div style="color:#c0392b;font-size:13px;margin-top:6px">
      ⚠️ ดึงเรท USD→THB ไม่ได้ — ยอดรวมนับเฉพาะหุ้นไทย (เมกา ${{ "{:,.0f}".format(totals.usd_value) }} ยังไม่รวม)
    </div>
    {% endif %}
    <div style="margin-top:8px;font-size:15px;font-weight:600;color:{{ '#1e8e3e' if totals.total_pl >= 0 else '#c0392b' }}">
      {{ '+' if totals.total_pl >= 0 else '' }}฿{{ "{:,.0f}".format(totals.total_pl) }}
      ({{ '+' if totals.total_pl >= 0 else '' }}{{ "%.1f"|format(totals.total_pl_pct) }}%) จากต้นทุน
    </div>
    {% if changes and changes.d1.pct is not none %}
    {% set d1baht = changes.d1.diff|round %}{# เครื่องหมายและสีตามยอดบาทที่แสดงจริง วันที่นิ่งสนิทจึงไม่เขียว #}
    <div style="margin-top:6px;font-size:13px;color:#555">
      วันนี้ <span style="font-weight:600;color:{{ '#1e8e3e' if d1baht > 0 else '#c0392b' if d1baht < 0 else '#888' }}">{{ '+' if d1baht > 0 else '-' if d1baht < 0 else '' }}฿{{ "{:,.0f}".format(changes.d1.diff|abs) }} ({{ fmt_pct(changes.d1.pct) }})</span>
      · {{ chg("1W", changes.w1.pct) }} · {{ chg("1M", changes.m1.pct) }}
    </div>
    {% endif %}
    {% if failed %}
    <div style="margin-top:8px;color:#c0392b;font-size:12px;font-weight:600">
      ⚠️ ยอดรวมนี้ยังไม่รวม {{ failed|length }} ตัวที่ดึงข้อมูลไม่ได้ ({{ failed|join(", ") }})
    </div>
    {% endif %}
  </div>

  <table style="width:100%;border-collapse:collapse;font-size:13px">
    <thead>
      <tr style="text-align:left;color:#666;border-bottom:2px solid #eee">
        <th style="padding:6px 4px">หุ้น</th>
        <th style="padding:6px 4px;text-align:right">ราคา</th>
        <th style="padding:6px 4px;text-align:right">P/L</th>
        <th style="padding:6px 4px">Stoch</th>
        <th style="padding:6px 4px">RSI(1D/1W)</th>
      </tr>
    </thead>
    <tbody>
    {% for r in rows %}
      <tr style="border-bottom:1px solid #f0f0f0">
        <td style="padding:6px 4px;font-weight:600">{{ r.name or r.ticker }}
          {% if r.xd_days is not none %}<span style="background:#fff3cd;color:#856404;border-radius:4px;padding:1px 5px;font-size:11px">XD {{ r.xd_days }}d</span>{% endif %}
        </td>
        <td style="padding:6px 4px;text-align:right;white-space:nowrap">{{ "%.2f"|format(r.price) }} {{ r.currency }}
          {% if r.changes %}<div style="font-size:11px;margin-top:2px">{{ chg("1D", r.changes.d1) }} {{ chg("1W", r.changes.w1) }} {{ chg("1M", r.changes.m1) }}</div>{% endif %}
        </td>
        <td style="padding:6px 4px;text-align:right;color:{{ '#1e8e3e' if r.pl >= 0 else '#c0392b' }}">
          {{ '+' if r.pl >= 0 else '' }}{{ "%.1f"|format(r.pl_pct) }}%
        </td>
        <td style="padding:6px 4px">{{ stoch_line("1D", r.signals.d1) }}{{ stoch_line("1W", r.signals.w1) }}</td>
        <td style="padding:6px 4px">{{ c(r.signals.d1.rsi, 70, 30) }} / {{ c(r.signals.w1.rsi, 70, 30) }}</td>
      </tr>
    {% endfor %}
    </tbody>
  </table>

  {% if xd_failed %}
  <div style="margin-top:10px;color:#856404;font-size:12px">
    ⚠️ เช็ควัน XD ไม่ได้ {{ xd_failed|length }} ตัว ({{ xd_failed|join(", ") }}) — badge XD ของตัวที่ว่าอาจหายไป ไม่ได้แปลว่าไม่มีปันผล
  </div>
  {% endif %}

  {% if high_volume_rows %}
  <h3 style="margin:24px 0 4px">⚠️ High Volume</h3>
  <div style="color:#666;font-size:12px;margin-bottom:10px">Volume ล่าสุด ≥ 2x ค่าเฉลี่ย 20 วันก่อนหน้า — ตรวจข่าว/งบ/รายการพิเศษก่อนตัดสินใจ</div>
  <table style="width:100%;border-collapse:collapse;font-size:12px">
    <thead><tr style="text-align:left;color:#666;border-bottom:2px solid #eee">
      <th style="padding:5px 4px">หุ้น</th>
      <th style="padding:5px 4px;text-align:right">Vol / Avg20</th>
      <th style="padding:5px 4px;text-align:right">ราคาเปลี่ยน</th>
      <th style="padding:5px 4px;text-align:right">มูลค่าถือ</th>
    </tr></thead>
    <tbody>
    {% for r in high_volume_rows %}
      <tr style="border-bottom:1px solid #f0f0f0">
        <td style="padding:5px 4px;font-weight:600">{{ r.ticker }}</td>
        <td style="padding:5px 4px;text-align:right">{{ "{:,.0f}".format(r.latest_volume) }} / {{ "{:,.0f}".format(r.avg_volume_20) }} ({{ "%.1f"|format(r.volume_ratio) }}x)</td>
        <td style="padding:5px 4px;text-align:right;color:{{ pct_color(r.price_change_pct) if r.price_change_pct is not none else '#888' }}">
          {{ fmt_pct(r.price_change_pct) if r.price_change_pct is not none else "-" }}
        </td>
        <td style="padding:5px 4px;text-align:right">{{ "{:,.0f}".format(r.position_value) }} {{ r.currency }}</td>
      </tr>
    {% endfor %}
    </tbody>
  </table>
  {% endif %}

  {% if failed %}
  <div style="margin-top:14px;color:#c0392b;font-size:12px">
    ⚠️ ดึงข้อมูลไม่ได้: {{ failed|join(", ") }}
  </div>
  {% endif %}

  <h3 style="margin:24px 0 4px">🏛️ ความเคลื่อนไหวผู้บริหาร/ผู้ถือหุ้นใหญ่</h3>
  <div style="color:#666;font-size:12px;margin-bottom:10px">แบบ 59 / 246-2 — ที่ ก.ล.ต. รับเอกสาร{% if sec_period %} {{ sec_period }}{% endif %}</div>

  {% if sec_failed %}
  <div style="background:#fff3cd;color:#856404;border-radius:6px;padding:8px 12px;font-size:12px;margin-bottom:10px">
    ⚠️ ดึงข้อมูล ก.ล.ต. ไม่สำเร็จ {{ sec_failed|length }} รายการ: {{ sec_failed[:4]|join(", ") }}{% if sec_failed|length > 4 %} …{% endif %}
  </div>
  {% endif %}

  {% set f59 = insider_rows|selectattr("form","equalto","59")|list %}
  {% set f246 = insider_rows|selectattr("form","equalto","246")|list %}

  {% if not insider_rows and sec_failed %}
  <div style="color:#856404;font-size:13px;padding:8px 0">ตรวจข้อมูล ก.ล.ต. ไม่ครบ — ดู warning ด้านบน</div>
  {% elif not insider_rows %}
  <div style="color:#888;font-size:13px;padding:8px 0">ไม่มีรายงานใหม่</div>
  {% endif %}

  {% if f59 %}
  <div style="font-size:12px;font-weight:600;color:#555;margin:8px 0 4px">กรรมการ/ผู้บริหาร (แบบ 59)</div>
  <table style="width:100%;border-collapse:collapse;font-size:12px">
    <thead><tr style="text-align:left;color:#666;border-bottom:2px solid #eee">
      <th style="padding:5px 4px">หุ้น</th><th style="padding:5px 4px">ชื่อ</th>
      <th style="padding:5px 4px">รายการ</th><th style="padding:5px 4px;text-align:right">จำนวน</th>
      <th style="padding:5px 4px;text-align:right">ราคา</th><th style="padding:5px 4px">วันที่</th>
    </tr></thead>
    <tbody>
    {% for r in f59 %}
      <tr style="border-bottom:1px solid #f0f0f0">
        <td style="padding:5px 4px;font-weight:600">{% if r.source_url %}<a href="{{ r.source_url }}" style="color:#1a1a1a;text-decoration:none">{{ r.symbol }}</a>{% else %}{{ r.symbol }}{% endif %}
          <div style="color:#777;font-weight:400;font-size:11px">{{ r.security_type or "-" }}</div>
        </td>
        <td style="padding:5px 4px">{{ r.name }}</td>
        <td style="padding:5px 4px;font-weight:600;color:{{ act_color(r.action) }}">{{ r.action }}</td>
        <td style="padding:5px 4px;text-align:right">{{ "{:,.0f}".format(r.shares) if r.shares is not none else "-" }}</td>
        <td style="padding:5px 4px;text-align:right">{{ "%.2f"|format(r.price) if r.price is not none else "-" }}</td>
        <td style="padding:5px 4px;white-space:nowrap">{{ r.txn_date }}</td>
      </tr>
    {% endfor %}
    </tbody>
  </table>
  {% endif %}

  {% if f246 %}
  <div style="font-size:12px;font-weight:600;color:#555;margin:14px 0 4px">ผู้ถือหุ้นใหญ่ (แบบ 246-2 — % การถือครอง)</div>
  <table style="width:100%;border-collapse:collapse;font-size:12px">
    <thead><tr style="text-align:left;color:#666;border-bottom:2px solid #eee">
      <th style="padding:5px 4px">หุ้น</th><th style="padding:5px 4px">ชื่อ</th>
      <th style="padding:5px 4px">รายการ</th><th style="padding:5px 4px;text-align:right">% เปลี่ยน</th>
      <th style="padding:5px 4px;text-align:right">% หลัง</th><th style="padding:5px 4px">วันที่</th>
    </tr></thead>
    <tbody>
    {% for r in f246 %}
      <tr style="border-bottom:1px solid #f0f0f0">
        <td style="padding:5px 4px;font-weight:600">{{ r.symbol }}</td>
        <td style="padding:5px 4px">{{ r.name }}</td>
        <td style="padding:5px 4px;font-weight:600;color:{{ act_color(r.action) }}">{{ r.action }}</td>
        <td style="padding:5px 4px;text-align:right">{{ "%.2f"|format(r.pct_change) if r.pct_change is not none else "-" }}</td>
        <td style="padding:5px 4px;text-align:right">{{ "%.2f"|format(r.pct_after) if r.pct_after is not none else "-" }}</td>
        <td style="padding:5px 4px;white-space:nowrap">{{ r.txn_date }}</td>
      </tr>
    {% endfor %}
    </tbody>
  </table>
  {% endif %}
</div>
""")


def _act_color(action):
    """ซื้อ/ได้มา = เขียว, ขาย/จำหน่าย = แดง, อื่นๆ (โอน/สิ้นสุด) = เทา"""
    a = action or ""
    if "ซื้อ" in a or "ได้มา" in a:
        return "#1e8e3e"
    if "ขาย" in a or "จำหน่าย" in a:
        return "#c0392b"
    return "#888"


def _fmt_pct(v):
    """ปัดเศษ % ที่จุดแสดงผลจุดเดียว — ปัด -0.04% แล้วได้ -0.0 ซึ่งต้องไม่ขึ้นเป็นลบในเมล"""
    v = round(v, 1)
    return f"{v:+.1f}%" if v else "0.0%"


def _pct_color(v):
    v = round(v, 1)  # ปัดก่อนเทียบ ไม่งั้น -0.04% ที่แสดงเป็น 0.0% จะโดนทาสีแดง
    return "#1e8e3e" if v > 0 else "#c0392b" if v < 0 else "#888"


_TEMPLATE.globals["act_color"] = _act_color
_TEMPLATE.globals["fmt_pct"] = _fmt_pct
_TEMPLATE.globals["pct_color"] = _pct_color


def render(asof, totals, rows, failed, insider_rows=None, sec_failed=None, sec_period="",
           high_volume_rows=None, xd_failed=None, changes=None):
    return _TEMPLATE.render(asof=asof, totals=totals, rows=rows, failed=failed,
                            insider_rows=insider_rows or [], sec_failed=sec_failed or [],
                            sec_period=sec_period, high_volume_rows=high_volume_rows or [],
                            xd_failed=xd_failed or [], changes=changes)
