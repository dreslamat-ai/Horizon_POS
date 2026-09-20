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
from frappe.utils import flt

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


def _generate_unique_ean13():
	"""حلقة التوليد المشتركة — يستخدمها الطلب اليدوي من ديالوج الطباعة
	وHook الإنشاء التلقائي معًا، بلا تكرار منطق."""
	for _attempt in range(20):
		body = EAN13_INTERNAL_PREFIX + "".join(str(random.randint(0, 9)) for _ in range(10))
		candidate = body + str(_ean13_checksum(body))
		if not frappe.db.exists("Item Barcode", {"barcode": candidate}):
			return candidate
	return None


@frappe.whitelist()
def generate_ean13_barcode():
	"""يولّد باركود EAN-13 فريد (بادئة الاستخدام الداخلي ٢٠) غير
	مستخدَم من قبل — يُتحقَّق من التفرد فعليًا في قاعدة البيانات قبل
	إرجاعه، لا يُفترَض العشوائية كافية وحدها."""
	candidate = _generate_unique_ean13()
	if not candidate:
		frappe.throw(_("تعذّر توليد باركود فريد، حاول مرة أخرى"))
	return candidate


def _auto_barcode_candidates(doc):
	"""باركودان يتولَّدان معًا دائمًا بأمر صريح من المالك (٢٠ سبتمبر
	٢٠٢٦): رقمي (EAN-13) وحرفي (كود الصنف نفسه) — الاختيار بينهما
	يبقى للكاشير وقت الطباعة (قائمة الباركودات المسجَّلة في الديالوج)،
	لا وقت إنشاء الصنف."""
	ean = _generate_unique_ean13()
	code = doc.item_code or doc.name
	return [c for c in (ean, code) if c]


def _add_item_barcode_rows(item_name, values):
	existing = set(
		frappe.get_all("Item Barcode", filters={"parent": item_name}, pluck="barcode")
	)
	added = []
	for value in values:
		if value in existing:
			continue
		barcode_row = frappe.new_doc("Item Barcode")
		barcode_row.update(
			{
				"parent": item_name,
				"parenttype": "Item",
				"parentfield": "barcodes",
				"barcode": value,
			}
		)
		barcode_row.insert(ignore_permissions=True)
		existing.add(value)
		added.append(value)
	return added


def auto_generate_barcode_on_insert(doc, method=None):
	"""Hook على Item.after_insert — بأمر صريح من المالك (١٩ سبتمبر
	٢٠٢٦، وتعديل ٢٠ سبتمبر: باركودان معًا لا خيار واحد): كل صنف جديد
	قابل للبيع فعليًا يولَّد له باركودان تلقائيًا (رقمي وحرفي) بلا
	استثناء ولا خانة تفعيل، بما في ذلك أي عميل مستقبلي على Horizon
	SaaS لا سترة فقط. التوليد وقت الإنشاء فقط — لا وقت الطباعة.

	مستثنى عمدًا: أصناف القوالب (has_variants=1) — غير قابلة للبيع
	مباشرة، ومصنف عنده باركود بالفعل (لو أُدخل يدويًا وقت الإنشاء) —
	لا نكرّر ولا نتجاوزه بالكامل، لكن لو كان عنده باركود واحد بس
	(نادر جدًا وقت after_insert) هذا الشرط يمنع أي إضافة إطلاقًا،
	بقصد: عدم التدخل في أي إدخال يدوي حصل فعلاً."""
	if doc.get("has_variants"):
		return
	if doc.get("barcodes"):
		return
	candidates = _auto_barcode_candidates(doc)
	if not candidates:
		frappe.log_error(
			"تعذّر توليد باركود تلقائي فريد لصنف جديد", f"auto barcode: {doc.name}"
		)
		return
	_add_item_barcode_rows(doc.name, candidates)


@frappe.whitelist()
def generate_barcode_for_existing_item(item_code):
	"""زر يدوي في فورم الصنف — لأصناف قديمة اتسجَّلت قبل تفعيل
	التوليد التلقائي. يضيف أيّ من الباركودين (رقمي/حرفي) غير موجود
	بعد بين باركودات الصنف الحالية — لو الصنف عنده باركود يدوي مختلف
	تمامًا، يضيف الاثنين الجدد بجانبه لا بدلًا منه."""
	item = frappe.get_doc("Item", item_code)
	if item.get("has_variants"):
		frappe.throw(_("أصناف القوالب (لها متغيّرات) لا تُطبع لها باركود مباشرة"))
	candidates = _auto_barcode_candidates(item)
	added = _add_item_barcode_rows(item.name, candidates)
	if not added:
		frappe.throw(_("هذا الصنف عنده الباركودان المولَّدان تلقائيًا مسجَّلان بالفعل"))
	return {"barcodes": added}


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


def _resolve_item_rate(item_code, price_list, standard_rate):
	"""السعر المطبوع على الملصق — أولوية لقائمة الأسعار الفعلية
	المستخدَمة في نقطة البيع (POS Profile.selling_price_list)، لأن
	standard_rate على الصنف نادرًا ما يُملأ في الإعداد التجاري الحقيقي
	(اكتُشف فعليًا: صفر لأصناف سترة رغم وجود سعر بيع حقيقي في القائمة).
	standard_rate يبقى احتياطيًا فقط لو الصنف بلا سعر في القائمة."""
	if price_list:
		price_list_rate = frappe.db.get_value(
			"Item Price",
			{"item_code": item_code, "price_list": price_list, "selling": 1},
			"price_list_rate",
		)
		if price_list_rate:
			return flt(price_list_rate)
	return flt(standard_rate)


def _parse_items(items, price_list=None):
	"""items يوصل كـJSON من الواجهة: [{"item_code", "qty", "barcode_value"?}].
	barcode_value يوصل صراحةً من الديالوج (الكاشير اختار من بين عدّة
	باركودات مسجَّلة، أو أدخل واحدًا يدويًا) — الاعتماد على أول باركود
	مسجَّل تلقائيًا احتياطي فقط للنداء المباشر بلا واجهة."""
	if isinstance(items, str):
		items = json.loads(items)
	parsed = []
	for row in items:
		item_code = row.get("item_code")
		qty = int(row.get("qty") or 1)
		if not item_code or qty < 1:
			continue
		item_name, standard_rate = frappe.db.get_value(
			"Item", item_code, ["item_name", "standard_rate"]
		) or (item_code, 0)
		parsed.append(
			{
				"item_code": item_code,
				"item_name": item_name or item_code,
				"qty": qty,
				"rate": _resolve_item_rate(item_code, price_list, standard_rate),
				"barcode_value": row.get("barcode_value") or _resolve_barcode_value(item_code),
			}
		)
	return parsed


@frappe.whitelist()
def get_barcode_preview_html(
	item_code, barcode_value, label_width_mm=50, label_height_mm=30,
	show_price=0, show_company=0, company_name=None, price_list=None,
):
	"""معاينة حيّة لملصق واحد — تتحدّث في ديالوج الطباعة مع كل تغيير
	(صنف، باركود مختار، مقاس، خيار سعر/شركة) بلا حاجة لفتح نافذة
	طباعة فعلية. أسماء الأصناف مقصورة على posa-preview- عمدًا حتى لا
	تتعارض مع أي كلاس بنفس الاسم في صفحة POS Profile نفسها."""
	item_name, standard_rate = frappe.db.get_value(
		"Item", item_code, ["item_name", "standard_rate"]
	) or (item_code, 0)
	rate = _resolve_item_rate(item_code, price_list, standard_rate)

	show_price = int(show_price)
	show_company = int(show_company)
	company_name_safe = frappe.utils.escape_html((company_name or "")[:40])

	label_width_mm = float(label_width_mm)
	label_height_mm = float(label_height_mm)
	svg = _barcode_svg(barcode_value, module_height_mm=max(6, label_height_mm - 14))
	name_line = frappe.utils.escape_html((item_name or item_code)[:32])

	company_html = (
		f'<div class="posa-preview-company">{company_name_safe}</div>'
		if show_company and company_name_safe
		else ""
	)
	price_html = f'<div class="posa-preview-price">{rate:.2f}</div>' if show_price else ""

	return f"""
<style>
  .posa-preview-wrap {{ display: flex; justify-content: center; padding: 8px 0; }}
  .posa-preview-cell {{
    box-sizing: border-box;
    border: 1px dashed #999;
    width: {label_width_mm}mm; height: {label_height_mm}mm;
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    overflow: hidden; padding: 1mm; font-family: sans-serif;
  }}
  .posa-preview-name {{ font-size: 2.4mm; text-align: center; direction: rtl; }}
  .posa-preview-barcode svg {{ max-width: 100%; }}
  .posa-preview-code {{ font-size: 2mm; letter-spacing: 0.3mm; }}
  .posa-preview-company {{ font-size: 2mm; text-align: center; direction: rtl; opacity: .8; }}
  .posa-preview-price {{ font-size: 2.6mm; font-weight: bold; margin-top: 0.5mm; }}
</style>
<div class="posa-preview-wrap">
  <div class="posa-preview-cell">
    {company_html}
    <div class="posa-preview-name">{name_line}</div>
    <div class="posa-preview-barcode">{svg}</div>
    <div class="posa-preview-code">{barcode_value}</div>
    {price_html}
  </div>
</div>
"""


@frappe.whitelist()
def get_label_presets():
	return {"presets": LABEL_PRESETS_MM}


@frappe.whitelist()
def get_barcode_zpl(
	items, label_width_mm=50, label_height_mm=30, dpi=203,
	show_price=0, show_company=0, company_name=None, price_list=None,
):
	"""يولّد نص ZPL خام لقائمة أصناف — نسخة واحدة لكل قيمة qty.
	السعر واسم الشركة اختياريان بطلب صريح من المالك (٢٠ سبتمبر ٢٠٢٦) —
	المستخدم يقرر وقت الطباعة لا افتراضًا ثابتًا."""
	parsed = _parse_items(items, price_list=price_list)
	if not parsed:
		frappe.throw(_("لا يوجد صنف صالح للطباعة"))

	show_price = int(show_price)
	show_company = int(show_company)
	company_name = (company_name or "").replace("^", "").replace("~", "")[:28]

	dpi = int(dpi)
	width_dots = round(float(label_width_mm) / 25.4 * dpi)
	height_dots = round(float(label_height_mm) / 25.4 * dpi)
	barcode_height_dots = max(30, height_dots - 70)

	labels = []
	for row in parsed:
		# ^BY يضبط عرض الشرطة الواحدة، ^BCN باركود Code128 اتجاه عادي.
		name_line = row["item_name"][:28].replace("^", "").replace("~", "")
		extra_lines = ""
		y = 36 + barcode_height_dots + 14
		if show_company and company_name:
			extra_lines += f"^FO16,{y}^A0N,16,16^FD{company_name}^FS"
			y += 20
		if show_price:
			price_line = f"{row['rate']:.2f}".replace("^", "").replace("~", "")
			extra_lines += f"^FO16,{y}^A0N,18,18^FD{price_line}^FS"
		label_zpl = (
			"^XA"
			f"^PW{width_dots}"
			f"^LL{height_dots}"
			f"^FO16,10^A0N,20,20^FD{name_line}^FS"
			f"^FO16,36^BY2^BCN,{barcode_height_dots},N,N,N^FD{row['barcode_value']}^FS"
			f"{extra_lines}"
			"^XZ"
		)
		labels.append(label_zpl * row["qty"])

	return {"zpl": "".join(labels), "label_count": sum(r["qty"] for r in parsed)}


@frappe.whitelist()
def get_barcode_a4_html(
	items, label_width_mm=50, label_height_mm=30,
	show_price=0, show_company=0, company_name=None, price_list=None,
):
	"""يولّد صفحة HTML قائمة بذاتها — شبكة باركودات بحجم A4، جاهزة
	للطباعة المباشرة من نافذة متصفح جديدة (window.print()). السعر
	واسم الشركة اختياريان بطلب صريح من المالك (٢٠ سبتمبر ٢٠٢٦)."""
	parsed = _parse_items(items, price_list=price_list)
	if not parsed:
		frappe.throw(_("لا يوجد صنف صالح للطباعة"))

	show_price = int(show_price)
	show_company = int(show_company)
	company_name = frappe.utils.escape_html((company_name or "")[:40])

	label_width_mm = float(label_width_mm)
	label_height_mm = float(label_height_mm)
	usable_width = A4_WIDTH_MM - (2 * A4_MARGIN_MM)
	columns = max(1, int(usable_width // label_width_mm))

	cells = []
	for row in parsed:
		svg = _barcode_svg(row["barcode_value"], module_height_mm=max(6, label_height_mm - 14))
		name_line = frappe.utils.escape_html(row["item_name"][:32])
		company_html = f'<div class="label-company" dir="rtl">{company_name}</div>' if show_company and company_name else ""
		price_html = f'<div class="label-price">{row["rate"]:.2f}</div>' if show_price else ""
		for _copy in range(row["qty"]):
			cells.append(
				f'<div class="label-cell" style="width:{label_width_mm}mm;height:{label_height_mm}mm">'
				f'{company_html}'
				f'<div class="label-name">{name_line}</div>'
				f'<div class="label-barcode">{svg}</div>'
				f'<div class="label-code">{row["barcode_value"]}</div>'
				f'{price_html}'
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
  .label-company {{ font-size: 2mm; text-align: center; direction: rtl; opacity: .8; }}
  .label-price {{ font-size: 2.6mm; font-weight: bold; margin-top: 0.5mm; }}
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
