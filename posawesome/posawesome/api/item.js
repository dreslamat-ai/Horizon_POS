// Copyright (c) 2026, Horizon and contributors
// For license information, please see license.txt

frappe.ui.form.on('Item', {
	refresh: function (frm) {
		// زر يدوي — للأصناف القديمة التي اتسجَّلت قبل تفعيل التوليد
		// التلقائي (تاخد الباركودين رقمي+حرفي أوتوماتيك عند إنشائها،
		// عبر posawesome.posawesome.api.barcode_print
		// .auto_generate_barcode_on_insert). يظهر لأي صنف محفوظ فعليًا
		// بلا متغيّرات — حتى لو عنده باركود يدوي بالفعل، الزر بيضيف أي
		// من الباركودين الاثنين الناقص بجانبه.
		if (!frm.is_new() && !frm.doc.has_variants) {
			frm.add_custom_button(__('توليد باركود'), function () {
				frappe.call({
					method: 'posawesome.posawesome.api.barcode_print.generate_barcode_for_existing_item',
					args: { item_code: frm.doc.name },
					freeze: true,
					freeze_message: __('جارٍ توليد الباركود...'),
					callback: function (r) {
						if (r.message && r.message.barcodes && r.message.barcodes.length) {
							frappe.show_alert({
								message: __('تم توليد الباركود: {0}', [r.message.barcodes.join(' ، ')]),
								indicator: 'green',
							});
							frm.reload_doc();
						}
					},
				});
			});
		}
	},
});
