// Copyright (c) 20201 Youssef Restom and contributors
// For license information, please see license.txt

frappe.ui.form.on('POS Profile', {
	setup: function (frm) {
		frm.set_query("posa_cash_mode_of_payment", function (doc) {
			return {
				filters: { 'type': 'Cash' }
			};
		});
	},
	refresh: function (frm) {
		frm.add_custom_button(__('طباعة باركود الأصناف'), function () {
			posa_show_barcode_print_dialog(frm);
		}, __('أدوات'));
	},
});

// اتصال QZ Tray بنفس منطق Payments.vue بالضبط — شهادة وتوقيع من
// السيرفر (posawesome.posawesome.api.qz_signing)، مش من عرض جهة
// الكاشير نفسها.
function posa_connect_qz() {
	if (typeof qz === 'undefined') {
		frappe.msgprint(__('QZ Tray غير مثبّت على هذا الجهاز — لا يمكن الطباعة'));
		return Promise.reject();
	}
	if (qz.websocket.isActive()) {
		return Promise.resolve();
	}
	qz.security.setCertificatePromise(function (resolve, reject) {
		frappe.call({
			method: 'posawesome.posawesome.api.qz_signing.get_qz_certificate',
			callback: function (r) { resolve(r.message); },
			error: reject,
		});
	});
	qz.security.setSignatureAlgorithm('SHA512');
	qz.security.setSignaturePromise(function (to_sign) {
		return function (resolve, reject) {
			frappe.call({
				method: 'posawesome.posawesome.api.qz_signing.sign_qz_request',
				args: { to_sign: to_sign },
				callback: function (r) { resolve(r.message); },
				error: reject,
			});
		};
	});
	return qz.websocket.connect();
}

const POSA_MANUAL_ENTRY = '__manual__';

function posa_show_barcode_print_dialog(frm) {
	const presets = {
		'50×30 مم (شائع للملابس)': [50, 30],
		'40×30 مم': [40, 30],
		'40×25 مم': [40, 25],
		'30×20 مم': [30, 20],
		'25×15 مم (صغير)': [25, 15],
		'مخصّص': null,
	};
	let items_list = [];
	let current_barcodes = []; // باركودات الصنف المختار حاليًا في الحقول العلوية

	function get_label_size(dialog) {
		const preset = dialog.get_value('preset');
		if (presets[preset]) return presets[preset];
		return [dialog.get_value('custom_width') || 50, dialog.get_value('custom_height') || 30];
	}

	// تحكّم صريح بطلب المالك (٢٠ سبتمبر ٢٠٢٦) — بدل حساب تلقائي ثابت
	// يفشل ينسّق مع بعض مقاسات الملصقات الحقيقية.
	function get_barcode_height_mm(dialog) {
		return dialog.get_value('barcode_height_mm') || 16;
	}

	// أسهم زيادة/تقليل مخصَّصة لكل حقل رقمي — أسهم input[type=number]
	// الافتراضية مش ظاهرة في هذا الفورم (bootstrap.css بيضيّقها بلا
	// إخفائها فعليًا لكن بلا وضوح كافٍ)، بطلب صريح من المالك.
	function add_number_stepper(dialog, fieldname, step, min_value) {
		const field = dialog.fields_dict[fieldname];
		if (!field || !field.$input) return;
		const $input = field.$input;
		$input.css({ 'padding-left': '22px' });
		const $stepper = $(
			'<div class="posa-stepper" style="position:absolute;left:1px;top:0;bottom:0;display:flex;flex-direction:column;width:20px;">' +
				'<button type="button" class="posa-step-up" style="flex:1;border:none;background:#f0f0f0;cursor:pointer;font-size:9px;line-height:1;">&#9650;</button>' +
				'<button type="button" class="posa-step-down" style="flex:1;border:none;background:#f0f0f0;cursor:pointer;font-size:9px;line-height:1;border-top:1px solid #ddd;">&#9660;</button>' +
			'</div>'
		);
		$input.parent().css('position', 'relative').append($stepper);
		function apply(delta) {
			const cur = parseFloat(dialog.get_value(fieldname)) || 0;
			let next = cur + delta;
			if (typeof min_value === 'number') next = Math.max(min_value, next);
			dialog.set_value(fieldname, next);
		}
		$stepper.find('.posa-step-up').on('click', function () { apply(step); });
		$stepper.find('.posa-step-down').on('click', function () { apply(-step); });
	}

	function refresh_barcode_choice_options(dialog) {
		const options = current_barcodes.map((b) => `${b.barcode} (${__('مسجَّل')})`);
		options.push(`${POSA_MANUAL_ENTRY} ${__('— أدخل باركود جديد يدويًا')}`);
		dialog.fields_dict.barcode_choice.df.options = options.join('\n');
		dialog.fields_dict.barcode_choice.refresh();
		dialog.set_value('barcode_choice', options[0]);
	}

	function on_item_selected(dialog) {
		const item_code = dialog.get_value('item_code');
		if (!item_code) {
			refresh_preview(dialog);
			return;
		}
		frappe.call({
			method: 'posawesome.posawesome.api.barcode_print.get_item_barcodes',
			args: { item_code },
			callback: function (r) {
				current_barcodes = r.message || [];
				refresh_barcode_choice_options(dialog);
				refresh_preview(dialog);
			},
		});
	}

	function on_barcode_choice_change(dialog) {
		const choice = (dialog.get_value('barcode_choice') || '').split(' ')[0];
		dialog.set_df_property('manual_barcode', 'hidden', choice !== POSA_MANUAL_ENTRY);
		refresh_preview(dialog);
	}

	// يرجّع Promise تتحلّ لقيمة الباركود النهائية — لو يدوي/مولَّد
	// يسجّله دائمًا على الصنف أولًا (add_item_barcode) قبل الاستخدام.
	function resolve_selected_barcode(dialog) {
		const item_code = dialog.get_value('item_code');
		const choice = (dialog.get_value('barcode_choice') || '').split(' ')[0];
		if (choice === POSA_MANUAL_ENTRY) {
			const value = (dialog.get_value('manual_barcode') || '').trim();
			if (!value) return Promise.reject(__('اكتب قيمة الباركود اليدوي'));
			return new Promise(function (resolve, reject) {
				frappe.call({
					method: 'posawesome.posawesome.api.barcode_print.add_item_barcode',
					args: { item_code, barcode_value: value },
					callback: function (r) { resolve(r.message.barcode); },
					error: reject,
				});
			});
		}
		return Promise.resolve(choice);
	}

	// قيمة الباركود للمعاينة فقط — بلا أي نداء تسجيل على الصنف، بعكس
	// resolve_selected_barcode التي تُستدعى فقط عند "أضف للقائمة".
	function get_preview_barcode_value(dialog) {
		const choice = (dialog.get_value('barcode_choice') || '').split('\u2001')[0];
		if (choice === POSA_MANUAL_ENTRY) {
			return (dialog.get_value('manual_barcode') || '').trim();
		}
		return choice;
	}

	function refresh_preview(dialog) {
		const item_code = dialog.get_value('item_code');
		const barcode_value = get_preview_barcode_value(dialog);
		if (!item_code || !barcode_value) {
			dialog.fields_dict.barcode_preview.$wrapper.html('');
			return;
		}
		const [w, h] = get_label_size(dialog);
		frappe.call({
			method: 'posawesome.posawesome.api.barcode_print.get_barcode_preview_html',
			args: {
				item_code, barcode_value, label_width_mm: w, label_height_mm: h,
				show_price: dialog.get_value('show_price') ? 1 : 0,
				show_company: dialog.get_value('show_company') ? 1 : 0,
				company_name: frm.doc.company,
				price_list: frm.doc.selling_price_list,
				barcode_height_mm: get_barcode_height_mm(dialog),
			},
			callback: function (r) {
				dialog.fields_dict.barcode_preview.$wrapper.html(r.message);
			},
		});
	}

	function render_items_preview(dialog) {
		const rows = items_list.map((r, i) =>
			`<div class="posa-barcode-row" style="display:flex;justify-content:space-between;padding:2px 0">
				<span>${frappe.utils.escape_html(r.item_code)} — ${frappe.utils.escape_html(r.barcode_value)} × ${r.qty}</span>
				<a href="#" data-idx="${i}" class="posa-remove-item">${__('حذف')}</a>
			</div>`
		).join('') || `<div class="text-muted">${__('لا توجد أصناف بعد')}</div>`;
		dialog.fields_dict.items_preview.$wrapper.html(rows);
		dialog.fields_dict.items_preview.$wrapper.find('.posa-remove-item').on('click', function (e) {
			e.preventDefault();
			items_list.splice($(this).data('idx'), 1);
			render_items_preview(dialog);
		});
	}

	const dialog = new frappe.ui.Dialog({
		title: __('طباعة باركود الأصناف'),
		size: 'large',
		fields: [
			{
				fieldtype: 'Link', fieldname: 'item_code', label: __('الصنف'), options: 'Item',
				onchange: function () { on_item_selected(dialog); },
			},
			{
				fieldtype: 'Select', fieldname: 'barcode_choice', label: __('الباركود'),
				onchange: function () { on_barcode_choice_change(dialog); },
			},
			{
				fieldtype: 'Data', fieldname: 'manual_barcode', label: __('الباركود اليدوي (رقم أو حروف)'), hidden: 1,
				onchange: function () { refresh_preview(dialog); },
			},
			{ fieldtype: 'Column Break' },
			{ fieldtype: 'Int', fieldname: 'qty', label: __('الكمية'), default: 1 },
			{
				fieldtype: 'Button', fieldname: 'add_item', label: __('+ أضف للقائمة'),
				click: function () {
					const item_code = dialog.get_value('item_code');
					const qty = dialog.get_value('qty') || 1;
					if (!item_code) {
						frappe.msgprint(__('اختر صنفًا أولًا'));
						return;
					}
					resolve_selected_barcode(dialog).then(function (barcode_value) {
						items_list.push({ item_code, qty, barcode_value });
						render_items_preview(dialog);
						dialog.set_value('item_code', '');
						dialog.set_value('manual_barcode', '');
					}).catch(function (err) {
						frappe.msgprint(typeof err === 'string' ? err : __('تعذّر تحديد الباركود'));
					});
				},
			},
			{ fieldtype: 'Section Break' },
			{ fieldtype: 'HTML', fieldname: 'items_preview' },
			{ fieldtype: 'Section Break' },
			{
				fieldtype: 'Select', fieldname: 'preset', label: __('مقاس الملصق'),
				options: Object.keys(presets).join('\n'), default: '50×30 مم (شائع للملابس)',
				onchange: function () { refresh_preview(dialog); },
			},
			{ fieldtype: 'Column Break' },
			{
				fieldtype: 'Int', fieldname: 'custom_width', label: __('العرض (مم)'), default: 50,
				depends_on: "eval:doc.preset=='مخصّص'",
				onchange: function () { refresh_preview(dialog); },
			},
			{
				fieldtype: 'Int', fieldname: 'custom_height', label: __('الارتفاع (مم)'), default: 30,
				depends_on: "eval:doc.preset=='مخصّص'",
				onchange: function () { refresh_preview(dialog); },
			},
			{
				fieldtype: 'Int', fieldname: 'barcode_height_mm', label: __('ارتفاع شريط الباركود (مم)'), default: 16,
				description: __('لتنسيق الملصق — قلّله لو الباركود بيطلع خارج حدود الملصق أو فوق النص'),
				onchange: function () { refresh_preview(dialog); },
			},
			{ fieldtype: 'Column Break' },
			{
				fieldtype: 'Check', fieldname: 'show_price', label: __('اطبع السعر على الملصق'),
				onchange: function () { refresh_preview(dialog); },
			},
			{
				fieldtype: 'Check', fieldname: 'show_company', label: __('اطبع اسم الشركة على الملصق'),
				onchange: function () { refresh_preview(dialog); },
			},
			{ fieldtype: 'Section Break' },
			{ fieldtype: 'HTML', fieldname: 'barcode_preview', label: __('معاينة الملصق') },
			{ fieldtype: 'Section Break' },
			{
				fieldtype: 'Button', fieldname: 'print_a4', label: __('طباعة A4 (صفحة عادية، بلا QZ Tray)'),
				click: function () {
					if (!items_list.length) {
						frappe.msgprint(__('أضف صنفًا واحدًا على الأقل'));
						return;
					}
					const [w, h] = get_label_size(dialog);
					frappe.call({
						method: 'posawesome.posawesome.api.barcode_print.get_barcode_a4_html',
						args: {
							items: items_list, label_width_mm: w, label_height_mm: h,
							show_price: dialog.get_value('show_price') ? 1 : 0,
							show_company: dialog.get_value('show_company') ? 1 : 0,
							company_name: frm.doc.company,
							price_list: frm.doc.selling_price_list,
							barcode_height_mm: get_barcode_height_mm(dialog),
						},
						callback: function (r) {
							const win = window.open('', '_blank');
							win.document.write(r.message);
							win.document.close();
						},
					});
				},
			},
		],
		primary_action_label: __('طباعة على طابعة الملصقات (QZ Tray)'),
		primary_action: function () {
			if (!items_list.length) {
				frappe.msgprint(__('أضف صنفًا واحدًا على الأقل'));
				return;
			}
			const printer_name = frm.doc.posa_barcode_printer_name;
			if (!printer_name) {
				frappe.msgprint(__('حدّد اسم طابعة الملصقات في هذا الفورم أولًا واحفظه'));
				return;
			}
			const [w, h] = get_label_size(dialog);
			posa_connect_qz().then(function () {
				frappe.call({
					method: 'posawesome.posawesome.api.barcode_print.get_barcode_zpl',
					args: {
						items: items_list, label_width_mm: w, label_height_mm: h,
						show_price: dialog.get_value('show_price') ? 1 : 0,
						show_company: dialog.get_value('show_company') ? 1 : 0,
						company_name: frm.doc.company,
						price_list: frm.doc.selling_price_list,
						barcode_height_mm: get_barcode_height_mm(dialog),
					},
					callback: function (r) {
						const config = qz.configs.create(printer_name);
						qz.print(config, [{ type: 'raw', format: 'plain', data: r.message.zpl }])
							.then(function () {
								frappe.show_alert({ message: __('اترسلت للطباعة'), indicator: 'green' });
								dialog.hide();
							})
							.catch(function (err) {
								frappe.msgprint(__('فشلت الطباعة: {0}', [String(err)]));
							});
					},
				});
			}).catch(function () {
				frappe.msgprint(__('تعذّر الاتصال بخدمة QZ Tray — تأكّد من تثبيتها وتشغيلها على هذا الجهاز'));
			});
		},
	});

	render_items_preview(dialog);
	dialog.show();

	add_number_stepper(dialog, 'qty', 1, 1);
	add_number_stepper(dialog, 'custom_width', 1, 10);
	add_number_stepper(dialog, 'custom_height', 1, 10);
	add_number_stepper(dialog, 'barcode_height_mm', 1, 4);
}
