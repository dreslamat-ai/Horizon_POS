# -*- coding: utf-8 -*-
# Copyright (c) 2026, Horizon and contributors
# For license information, please see license.txt

import base64
import os
import subprocess
import tempfile

import frappe
from frappe import _
from PIL import Image, ImageOps

# ESC/POS raster commands address dots in bytes, so the printable width in
# dots must be a multiple of 8. These are the two common thermal widths —
# NOT derived from mm/dpi (that lands off the 8-dot grid, e.g. 575 vs 576).
WIDTH_DOTS_BY_PAPER = {
	"58mm": 384,
	"80mm": 576,
}


@frappe.whitelist()
def get_receipt_raster(doctype, docname, print_format="Horizon POS", paper="80mm"):
	"""Render a POS receipt to a 1-bit PNG raster image (base64) for thermal
	printing via QZ Tray.

	Rendering happens server-side (wkhtmltoimage) rather than in the cashier's
	browser (html2canvas) so Arabic shaping is deterministic and independent of
	whatever fonts happen to be installed on the till — measured and confirmed
	2026-09-16, see memory horizon-pos-print-format-fixes-and-raster-decision.
	"""
	if paper not in WIDTH_DOTS_BY_PAPER:
		frappe.throw(_("Unknown paper size: {0}").format(paper))

	frappe.has_permission(doctype, doc=docname, ptype="print", throw=True)

	html = frappe.get_print(doctype, docname, print_format=print_format)

	width_px = WIDTH_DOTS_BY_PAPER[paper]

	# frappe.get_print emits asset links like /assets/frappe/... (a web path,
	# not a filesystem path). A root-relative href ignores <base> entirely
	# per URL-resolution rules, so the fix is a direct textual rewrite to
	# the real path on disk rather than a <base> tag.
	sites_path = os.path.join(frappe.utils.get_bench_path(), "sites")
	html = html.replace('href="/assets/', 'href="file://%s/assets/' % sites_path)
	html = html.replace("href='/assets/", "href='file://%s/assets/" % sites_path)
	html = html.replace('src="/assets/', 'src="file://%s/assets/' % sites_path)
	html = html.replace("src='/assets/", "src='file://%s/assets/" % sites_path)

	full_html = (
		"<html><head><meta charset='utf-8'>"
		"<style>body{direction:rtl;margin:0;padding:0;width:%dpx}"
		"img{max-width:100%%}</style></head><body>%s</body></html>"
	) % (width_px, html)

	with tempfile.TemporaryDirectory(prefix="horizon_receipt_") as tmp_dir:
		html_path = os.path.join(tmp_dir, "receipt.html")
		png_path = os.path.join(tmp_dir, "receipt.png")

		with open(html_path, "w", encoding="utf-8") as f:
			f.write(full_html)

		result = subprocess.run(
			[
				"wkhtmltoimage",
				"--width", str(width_px),
				"--disable-smart-width",
				"--quality", "100",
				"--enable-local-file-access",
				"--load-error-handling", "ignore",
				html_path,
				png_path,
			],
			capture_output=True,
			timeout=30,
		)

		if not os.path.exists(png_path):
			frappe.throw(
				_("Failed to render receipt image: rc={0} stderr={1} stdout={2}").format(
					result.returncode,
					result.stderr.decode("utf-8", errors="ignore")[-800:],
					result.stdout.decode("utf-8", errors="ignore")[-300:],
				)
			)

		image = Image.open(png_path).convert("L")

	# Crop trailing/leading blank rows — wkhtmltoimage renders a page-sized
	# canvas with a fixed minimum height regardless of content length, which
	# would otherwise feed several inches of blank paper after every receipt.
	inverted = ImageOps.invert(image)
	bbox = inverted.getbbox()
	if bbox:
		image = image.crop((0, 0, image.width, bbox[3] + 8))

	# 1-bit monochrome: raster ESC/POS wants black/white dots, and it drops
	# the payload roughly 20x versus 24-bit RGB over a till's connection.
	image = image.convert("1")

	buf = tempfile.SpooledTemporaryFile()
	image.save(buf, format="PNG")
	buf.seek(0)
	png_bytes = buf.read()
	buf.close()

	return {
		"image_base64": base64.b64encode(png_bytes).decode("ascii"),
		"width_px": width_px,
		"height_px": image.height,
	}
