# -*- coding: utf-8 -*-
# Copyright (c) 2026, Horizon and contributors
# For license information, please see license.txt

"""طباعة باركود الأصناف — مسارَان مستقلّان بطلب صريح من المالك:

١) ملصقات حرارية عبر QZ Tray (ZPL خام يُرسَل لطابعة Zebra ونحوها).
٢) صفحة A4 عادية مقسَّمة لشبكة باركودات، تُطبع من أي طابعة مكتبية
   عبر معاينة طباعة المتصفح العادية — بلا أي اعتماد على QZ Tray.

القيمة المرمَّزة: باركود Item Barcode المسجَّل لو موجود، وإلا item_code
نفسه — معظم أصناف سترة الحقيقية بلا باركود مصنع مسجَّل (مقاسٌ فعليًا
وقت البناء)، فكود الصنف الداخلي هو البديل العملي المستخدَم في تجارة
التجزئة حين لا يوجد باركود مطبوع من المورد.
"""

import io
import json
import random

import barcode
import frappe
from barcode.writer import SVGWriter
from frappe import _

# مقاسات شائعة لملصقات ملابس/تجزئة (عرض × ارتفاع مم) — نقطة بداية لا
# قائمة مغلقة؛ "مخصَّص" في الواجهة يسمح بأي قيمة غير هذه.
LABEL_PRESETS_MM = {
	"50x30": (50, 30),
	"40x30": (40, 30),
	"40x25": (40, 25),
	"30x20": (30, 20),
	"25x15": (25, 15),
}

A4_WIDTH_MM = 210
A4_HEIGHT_MM = 297
A4_MARGIN_MM = 8

# بادئة ٢٠ محجوزة رسميًا في معيار GS1 لـ"استخدام داخل الشركة" — مناسبة
# لباركود مولَّد آليًا لا يُقصَد توزيعه لمتاجر أو أنظمة خارجية.
EAN13_INTERNAL_PREFIX = "20"


def _resolve_barcode_value(item_code):
	row = frappe.get_all(
		"Item Barcode", filters={"parent": item_code}, fields=["barcode"], limit=1
	)
	return row[0].barcode if row else item_code


def _ean13_checksum(digits_12):
	# رقم التحقق القياسي لـEAN-13: المواضع الفردية (0-indexed) ×٣،
	# الزوجية ×١، ثم إكمال المجموع لأقرب عشرة. مُتحقَّق فعليًا بمقارنته
	# برقم EAN حقيقي موجود في بيانات سترة (6225000467217).
	total = sum(int(d) * (3 if i % 2 == 1 else 1) for i, d in enumerate(digits_12))
	return (10 - (total % 10)) % 10


@frappe.whitelist()
def generate_ean13_barcode():
	"""يولّد باركود EAN-13 فريد (بادئة الاستخدام الداخلي ٢٠) غير
	مستخدَم من قبل — يُتحقَّق من التفرد فعليًا في قاعدة البيانات قبل
	إرجاعه، لا يُفترَض العشوائية كافية وحدها."""
	for _attempt in range(20):
		body = EAN13_INTERNAL_PREFIX + "".join(str(random.randint(0, 9)) for _ in range(10))
		candidate = body + str(_ean13_checksum(body))
		if not frappe.db.exists("Item Barcode", {"barcode": candidate}):
			return candidate
	frappe.throw(_("تعذّر توليد باركود فريد، حاول مرة أخرى"))


@frappe.whitelist()
def get_item_barcodes(item_code):
	"""كل الباركودات المسجَّلة لصنف معيّن — الصنف ممكن يكون له أكتر
	من باركود واحد (مقاسات/عبوات مختلفة مثلًا)."""
	return frappe.get_all(
		"Item Barcode", filters={"parent": item_code}, fields=["barcode", "barcode_type"]
	)


@frappe.whitelist()
def add_item_barcode(item_code, barcode_value):
	"""يسجّل باركود جديد (يدوي أو مولَّد) على الصنف بشكل دائم — مش
	استخدام لمرة واحدة وقت الطباعة فقط."""
	barcode_value = (barcode_value or "").strip()
	if not barcode_value:
		frappe.throw(_("قيمة الباركود فارغة"))
	existing = frappe.db.exists("Item Barcode", {"barcode": barcode_value})
	if existing:
		owner_item = frappe.db.get_value("Item Barcode", existing, "parent")
		if owner_item != item_code:
			frappe.throw(_("الباركود {0} مسجَّل بالفعل على صنف آخر ({1})").format(barcode_value, owner_item))
		return {"barcode": barcode_value, "already_existed": True}

	item = frappe.get_doc("Item", item_code)
	item.append("barcodes", {"barcode": barcode_value})
	item.save(ignore_permissions=True)
	return {"barcode": barcode_value, "already_existed": False}


@frappe.whitelist()
def remove_item_barcode(item_code, barcode_value):
	"""يشيل باركودًا مسجَّلًا غلط من الصنف — تصحيح إدخال يدوي خاطئ."""
	item = frappe.get_doc("Item", item_code)
	item.barcodes = [row for row in item.barcodes if row.barcode != barcode_value]
	item.save(ignore_permissions=True)
	return {"removed": barcode_value}


def _barcode_svg(value, module_height_mm=10, quiet_zone_mm=1):
	code128 = barcode.get_barcode_class("code128")
	writer = SVGWriter()
	rendered = code128(value, writer=writer)
	buf = io.BytesIO()
	rendered.write(
		buf,
		options={
			"module_height": module_height_mm,
			"font_size": 0,
			"quiet_zone": quiet_zone_mm,
			"write_text": False,
		},
	)
	return buf.getvalue().decode("utf-8")


def _parse_items(items):
	"""items يوصل كـJSON من الواجهة: [{"item_code", "qty", "barcode_value"?}].
	barcode_value يوصل صراحةً من الديالوج (الكاشير اختار من بين عدّة
	باركودات مسجَّلة، أو أدخل واحدًا يدويًا، أو ولَّد واحدًا تلقائيًا) —
	الاعتماد على أول باركود مسجَّل تلقائيًا احتياطي فقط للنداء المباشر
	بلا واجهة."""
	if isinstance(items, str):
		items = json.loads(items)
	parsed = []
	for row in items:
		item_code = row.get("item_code")
		qty = int(row.get("qty") or 1)
		if not item_code or qty < 1:
			continue
		item_name = frappe.db.get_value("Item", item_code, "item_name") or item_code
		parsed.append(
			{
				"item_code": item_code,
				"item_name": item_name,
				"qty": qty,
				"barcode_value": row.get("barcode_value") or _resolve_barcode_value(item_code),
			}
		)
	return parsed


@frappe.whitelist()
def get_label_presets():
	return {"presets": LABEL_PRESETS_MM}


@frappe.whitelist()
def get_barcode_zpl(items, label_width_mm=50, label_height_mm=30, dpi=203):
	"""يولّد نص ZPL خام لقائمة أصناف — نسخة واحدة لكل قيمة qty."""
	parsed = _parse_items(items)
	if not parsed:
		frappe.throw(_("لا يوجد صنف صالح للطباعة"))

	dpi = int(dpi)
	width_dots = round(float(label_width_mm) / 25.4 * dpi)
	height_dots = round(float(label_height_mm) / 25.4 * dpi)
	barcode_height_dots = max(30, height_dots - 70)

	labels = []
	for row in parsed:
		# ^BY يضبط عرض الشرطة الواحدة، ^BCN باركود Code128 اتجاه عادي.
		name_line = row["item_name"][:28].replace("^", "").replace("~", "")
		label_zpl = (
			"^XA"
			f"^PW{width_dots}"
			f"^LL{height_dots}"
			f"^FO16,10^A0N,20,20^FD{name_line}^FS"
			f"^FO16,36^BY2^BCN,{barcode_height_dots},N,N,N^FD{row['barcode_value']}^FS"
			"^XZ"
		)
		labels.append(label_zpl * row["qty"])

	return {"zpl": "".join(labels), "label_count": sum(r["qty"] for r in parsed)}


@frappe.whitelist()
def get_barcode_a4_html(items, label_width_mm=50, label_height_mm=30):
	"""يولّد صفحة HTML قائمة بذاتها — شبكة باركودات بحجم A4، جاهزة
	للطباعة المباشرة من نافذة متصفح جديدة (window.print())."""
	parsed = _parse_items(items)
	if not parsed:
		frappe.throw(_("لا يوجد صنف صالح للطباعة"))

	label_width_mm = float(label_width_mm)
	label_height_mm = float(label_height_mm)
	usable_width = A4_WIDTH_MM - (2 * A4_MARGIN_MM)
	columns = max(1, int(usable_width // label_width_mm))

	cells = []
	for row in parsed:
		svg = _barcode_svg(row["barcode_value"], module_height_mm=max(6, label_height_mm - 14))
		name_line = frappe.utils.escape_html(row["item_name"][:32])
		for _copy in range(row["qty"]):
			cells.append(
				f'<div class="label-cell" style="width:{label_width_mm}mm;height:{label_height_mm}mm">'
				f'<div class="label-name">{name_line}</div>'
				f'<div class="label-barcode">{svg}</div>'
				f'<div class="label-code">{row["barcode_value"]}</div>'
				"</div>"
			)

	html = f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<title>{_("طباعة باركود")}</title>
<style>
  @page {{ size: A4; margin: {A4_MARGIN_MM}mm; }}
  body {{ margin: 0; font-family: sans-serif; }}
  .grid {{
    display: grid;
    grid-template-columns: repeat({columns}, {label_width_mm}mm);
    gap: 2mm;
  }}
  .label-cell {{
    box-sizing: border-box;
    border: 0.2mm dashed #999;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    overflow: hidden;
    padding: 1mm;
    page-break-inside: avoid;
  }}
  .label-name {{ font-size: 2.4mm; text-align: center; direction: rtl; }}
  .label-barcode svg {{ max-width: 100%; }}
  .label-code {{ font-size: 2mm; letter-spacing: 0.3mm; }}
  @media print {{
    .no-print {{ display: none; }}
  }}
</style>
</head>
<body>
  <div class="no-print" style="padding:4mm">
    <button onclick="window.print()">{_("طباعة")}</button>
  </div>
  <div class="grid">
    {''.join(cells)}
  </div>
</body>
</html>"""

	return html
