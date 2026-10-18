{% include "posawesome/posawesome/api/pos_profile.js" %}

frappe.pages['print_barcode'].on_page_load = function (wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __('طباعة الباركود'),
		single_column: true,
	});

	page.main.html(`<div class="text-muted" style="padding:20px">${__('جارٍ التحميل...')}</div>`);

	// أفضل POS Profile متاح — سترة عندها واحد بس فعليًا. لو المستقبل
	// فيه أكتر من واحد (فروع متعددة)، أول واحد كافٍ كافتراض لحد ما
	// يُطلَب صريحًا اختيار صريح بين الفروع.
	frappe.call({
		method: 'frappe.client.get_list',
		args: { doctype: 'POS Profile', limit_page_length: 1 },
		callback: function (r) {
			if (!r.message || !r.message.length) {
				page.main.html(`<div class="text-muted" style="padding:20px">${__('لا يوجد ملف تعريف نقطة بيع مسجَّل على هذا الموقع')}</div>`);
				return;
			}
			frappe.call({
				method: 'frappe.client.get',
				args: { doctype: 'POS Profile', name: r.message[0].name },
				callback: function (r2) {
					page.main.html('');
					var fake_frm = { doc: r2.message };
					posa_show_barcode_print_dialog(fake_frm);
				},
			});
		},
	});
};
