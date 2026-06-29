"""สร้าง HTML report จากผลคำนวณ"""
from jinja2 import Template

_TEMPLATE = Template("""\
{% macro c(v, ob, os_) %}{% if v is none %}-{% elif v >= ob %}<span style="background:#e53935;color:#fff;border-radius:5px;padding:2px 7px;font-weight:700">{{ "%.0f"|format(v) }}</span>{% elif v <= os_ %}<span style="background:#22c55e;color:#fff;border-radius:5px;padding:2px 7px;font-weight:700">{{ "%.0f"|format(v) }}</span>{% else %}<span style="color:#888">{{ "%.0f"|format(v) }}</span>{% endif %}{% endmacro %}
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
        <th style="padding:6px 4px">Stoch(1D/1W)</th>
        <th style="padding:6px 4px">RSI(1D/1W)</th>
      </tr>
    </thead>
    <tbody>
    {% for r in rows %}
      <tr style="border-bottom:1px solid #f0f0f0">
        <td style="padding:6px 4px;font-weight:600">{{ r.ticker }}
          {% if r.xd_days is not none %}<span style="background:#fff3cd;color:#856404;border-radius:4px;padding:1px 5px;font-size:11px">XD {{ r.xd_days }}d</span>{% endif %}
        </td>
        <td style="padding:6px 4px;text-align:right">{{ "%.2f"|format(r.price) }} {{ r.currency }}</td>
        <td style="padding:6px 4px;text-align:right;color:{{ '#1e8e3e' if r.pl >= 0 else '#c0392b' }}">
          {{ '+' if r.pl >= 0 else '' }}{{ "%.1f"|format(r.pl_pct) }}%
        </td>
        <td style="padding:6px 4px">{{ c(r.signals.d1.stoch_k, 80, 20) }} / {{ c(r.signals.w1.stoch_k, 80, 20) }}</td>
        <td style="padding:6px 4px">{{ c(r.signals.d1.rsi, 70, 30) }} / {{ c(r.signals.w1.rsi, 70, 30) }}</td>
      </tr>
    {% endfor %}
    </tbody>
  </table>

  {% if failed %}
  <div style="margin-top:14px;color:#c0392b;font-size:12px">
    ⚠️ ดึงข้อมูลไม่ได้: {{ failed|join(", ") }}
  </div>
  {% endif %}

  <h3 style="margin:24px 0 4px">🏛️ ความเคลื่อนไหวผู้บริหาร/ผู้ถือหุ้นใหญ่</h3>
  <div style="color:#666;font-size:12px;margin-bottom:10px">แบบ 59 / 246-2 — ที่ ก.ล.ต. รับเอกสาร{% if sec_period %} {{ sec_period }}{% endif %}</div>

  {% if sec_failed %}
  <div style="background:#fff3cd;color:#856404;border-radius:6px;padding:8px 12px;font-size:12px;margin-bottom:10px">
    ⚠️ ดึงข้อมูล ก.ล.ต. ไม่สำเร็จบางส่วน: {{ sec_failed|join(", ") }}
  </div>
  {% endif %}

  {% set f59 = insider_rows|selectattr("form","equalto","59")|list %}
  {% set f246 = insider_rows|selectattr("form","equalto","246")|list %}

  {% if not insider_rows %}
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
        <td style="padding:5px 4px;font-weight:600">{% if r.source_url %}<a href="{{ r.source_url }}" style="color:#1a1a1a;text-decoration:none">{{ r.symbol }}</a>{% else %}{{ r.symbol }}{% endif %}</td>
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


_TEMPLATE.globals["act_color"] = _act_color


def render(asof, totals, rows, failed, insider_rows=None, sec_failed=None, sec_period=""):
    return _TEMPLATE.render(asof=asof, totals=totals, rows=rows, failed=failed,
                            insider_rows=insider_rows or [], sec_failed=sec_failed or [],
                            sec_period=sec_period)
