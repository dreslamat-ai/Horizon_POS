# -*- coding: utf-8 -*-
# Copyright (c) 2026, Horizon and contributors
# For license information, please see license.txt

"""Server-side counterpart of QZ Tray's setCertificatePromise/setSignaturePromise.

One Horizon-owned key pair is used across every tenant's till (a vendor
distributing to many clients signs with its own key, not a per-client one —
see memory horizon-pos-print-format-fixes-and-raster-decision.md). This means
a single compromised till exposes the cert for all tenants; that's an accepted
tradeoff of the design, not an oversight.

Whether installing this self-signed cert as a trusted root on the till
(authcert.override, per qz.io/docs/provisioning) actually suppresses QZ
Tray's prompt is UNVERIFIED — no real till has been tested yet. Treat that
claim as open until confirmed on hardware.
"""

import base64
import os

import frappe
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

KEY_DIR = os.path.join(frappe.utils.get_bench_path(), "config", "horizon_qz")
PRIVATE_KEY_PATH = os.path.join(KEY_DIR, "private-key.pem")
CERTIFICATE_PATH = os.path.join(KEY_DIR, "digital-certificate.txt")


@frappe.whitelist()
def get_qz_certificate():
	"""Public certificate served to qz.security.setCertificatePromise. Not secret."""
	with open(CERTIFICATE_PATH, "r", encoding="utf-8") as f:
		return f.read()


@frappe.whitelist()
def sign_qz_request(to_sign):
	"""Sign the exact string QZ Tray sends (a SHA256 hex digest of the request,
	computed client-side — not the request itself). Must be signed verbatim as
	UTF-8: no parsing, no re-serialization. RSA/SHA512/PKCS1v15 matches QZ
	Tray 2.1+'s setSignatureAlgorithm("SHA512").
	"""
	with open(PRIVATE_KEY_PATH, "rb") as f:
		private_key = serialization.load_pem_private_key(f.read(), password=None)

	signature = private_key.sign(
		to_sign.encode("utf-8"),
		padding.PKCS1v15(),
		hashes.SHA512(),
	)
	return base64.b64encode(signature).decode("ascii")
