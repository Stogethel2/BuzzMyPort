"""สร้าง HTML report จากผลคำนวณ"""
from jinja2 import Template

_TEMPLATE = Template("""\
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
        <th style="padding:6px 4px">RSI(1D/1W)</th>
        <th style="padding:6px 4px">สัญญาณ</th>
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
        <td style="padding:6px 4px">{{ r.signals.d1.rsi }} / {{ r.signals.w1.rsi }}</td>
        <td style="padding:6px 4px">
          {% if r.signals.d1.cross == 'golden' %}<span style="color:#1e8e3e">▲ 1D golden</span>
          {% elif r.signals.d1.cross == 'dead' %}<span style="color:#c0392b">▼ 1D dead</span>{% endif %}
          {% if r.signals.w1.cross == 'golden' %}<span style="color:#1e8e3e">▲ 1W golden</span>
          {% elif r.signals.w1.cross == 'dead' %}<span style="color:#c0392b">▼ 1W dead</span>{% endif %}
        </td>
      </tr>
    {% endfor %}
    </tbody>
  </table>

  {% if failed %}
  <div style="margin-top:14px;color:#c0392b;font-size:12px">
    ⚠️ ดึงข้อมูลไม่ได้: {{ failed|join(", ") }}
  </div>
  {% endif %}
</div>
""")


def render(asof, totals, rows, failed):
    return _TEMPLATE.render(asof=asof, totals=totals, rows=rows, failed=failed)
