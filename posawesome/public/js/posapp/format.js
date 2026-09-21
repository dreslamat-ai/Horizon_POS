export default {
    data () {
        return {
            float_precision: 2,
            currency_precision: 2
        };
    },
    methods: {
        flt (value, precision, number_format, rounding_method) {
            if (!precision && precision != 0) {
                precision = this.currency_precision || 2;
            }
            if (!rounding_method) {
                rounding_method = "Banker's Rounding (legacy)";
            }
            return flt(value, precision, number_format, rounding_method);
        },
        formtCurrency (value, precision) {
            const format = get_number_format(this.pos_profile?.currency);
            value = format_number(
                value,
                format,
                precision || this.currency_precision || 2
            );
            return value;
        },
        formtFloat (value, precision) {
            const format = get_number_format(this.pos_profile.currency);
            value = format_number(value, format, precision || this.float_precision || 2);
            return value;
        },
        setFormatedCurrency (el, field_name, precision, no_negative = false, $event) {
            let value = 0;
            try {
                // make sure it is a number and positive
                let _value = parseFloat($event);
                if (!isNaN(_value)) {
                    value = _value;
                }
                if (no_negative && value < 0) {
                    value = value * -1;
                }
                value = this.formtCurrency($event, precision);
            } catch (e) {
                console.error(e);
                value = 0;
            }
            // check if el is an object
            if (typeof el === "object") {
                el[field_name] = value;
            }
            else {
                this[field_name] = value;
            }


            return value;
        },
        setFormatedFloat (el, field_name, precision, no_negative = false, $event) {
            let value = 0;
            try {
                // make sure it is a number and positive
                value = parseFloat($event);
                if (isNaN(value)) {
                    value = 0;
                } else if (no_negative && value < 0) {
                    value = value * -1;
                }
                value = this.formtFloat($event, precision);
            } catch (e) {
                console.error(e);
                value = 0;
            }
            // check if el is an object
            if (typeof el === "object") {
                el[field_name] = value;
            }
            else {
                this[field_name] = value;
            }
            return value;
        },
        currencySymbol (currency) {
            return get_currency_symbol(currency);
        },
        isNumber (value) {
            // العطل الأصلي: الصيغة كانت أوروبية (نقطة لفصل الآلاف، فاصلة
            // للكسر العشري) — بينما formtCurrency/formtFloat هنا يخرجان
            // دائمًا بصيغة إنجليزية (فاصلة للآلاف، نقطة للكسر: "300.00"،
            // "1,258.60"). فكانت كل قيمة عشرية صحيحة تُرفَض "invalid
            // number" — لم يظهر العطل قبل الآن لأن حقول الدفع كانت ترجع
            // صفرًا قبل ظهور أي قيمة عشرية أصلًا (انظر on_payment_amount_change
            // أعلاه). اكتُشف بلقطة حقيقية بعد إصلاح ذاك العطل مباشرة.
            const pattern = /^-?\d{1,3}(,\d{3})*(\.\d+)?$/;
            return pattern.test(value) || "invalid number";

        }
    },
    mounted () {
        this.float_precision =
            frappe.defaults.get_default('float_precision') || 2;
        this.currency_precision =
            frappe.defaults.get_default('currency_precision') || 2;
    }
};