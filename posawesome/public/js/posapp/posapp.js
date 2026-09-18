import { createApp } from 'vue';
import { createVuetify } from 'vuetify';
import * as components from 'vuetify/components';
import * as directives from 'vuetify/directives';
import Home from './Home.vue';

frappe.provide('frappe.PosApp');


frappe.PosApp.posapp = class {
    constructor({ parent }) {
        this.page = parent.page;
        this.make_body();

    }
    make_body () {
        // page.main هو مرجع frappe.ui.Page الفعلي (jQuery على
        // .layout-main-section في v16.31) — البحث القديم بـ
        // $(document).find('.main-section') كان بيفشل صامتًا (jQuery
        // collection فاضية → $el[0] === undefined) لأن الكلاس ده مش
        // مضمون وجوده على هذا العنصر بالذات دايمًا، والنتيجة كانت صفحة
        // POS بيضاء تمامًا (اتقاست فعليًا على sutra.horizonerp.cloud).
        this.$el = this.page.main;

        // ترحيل Vue3/Vuetify3 (١٧ سبتمبر ٢٠٢٦): esbuild-plugin-vue3
        // المشترك على البنش بيترجم كل ملفات .vue بمعيار Vue3 بغض النظر
        // عن رغبتنا — فالتركيب لازم يكون Vue3 فعليًا (createApp)، لا
        // Vue2 (new Vue). Vuetify2 (القديمة) ما كانتش هتشتغل تحت Vue3
        // إطلاقًا، فاتحدّثت لـVuetify3 كمان (راجع الذاكرة الدائمة:
        // horizon-sutra-pos-vue2-vue3-conflict).
        const isRtl = frappe.utils.is_rtl();
        const vuetify = createVuetify({
            components,
            directives,
            locale: {
                locale: isRtl ? 'ar' : 'en',
                rtl: { ar: true, en: false },
            },
            theme: {
                defaultTheme: 'light',
                themes: {
                    light: {
                        dark: false,
                        colors: {
                            // هوية Horizon المعتمدة في بروتوتايب كاشير سترة
                            // (docs/prototypes/sutra-pos-cashier.html) — كحلي
                            // أساسي بدل التركواز الافتراضي لـposawesome، وذهبي
                            // بدل البني الباهت. باقي الألوان الدلالية (success/
                            // warning/error) لم تُمس عمدًا — هي حالة لا هوية.
                            background: '#F7F3EA',
                            primary: '#1D2D44',
                            secondary: '#2B4066',
                            accent: '#C8A560',
                            success: '#66BB6A',
                            info: '#2196F3',
                            warning: '#FF9800',
                            error: '#E86674',
                            orange: '#E65100',
                            golden: '#C8A560',
                            badge: '#F5528C',
                            customPrimary: '#085294',
                        },
                    },
                    dark: {
                        dark: true,
                        colors: {
                            // قيم الوضع الداكن من نفس البروتوتايب
                            // (docs/prototypes/sutra-pos-cashier.html أسطر ٢٢-٣٢).
                            background: '#101825',
                            surface: '#182231',
                            primary: '#2B4066',
                            secondary: '#3A5480',
                            accent: '#C8A560',
                            success: '#66BB6A',
                            info: '#2196F3',
                            warning: '#FF9800',
                            error: '#E86674',
                            orange: '#E65100',
                            golden: '#C8A560',
                            badge: '#F5528C',
                            customPrimary: '#3A5480',
                        },
                    },
                },
            },
        });
        // مرجع عام يسمح لـNavbar.vue بتبديل الوضع الداكن/الفاتح دون
        // تمرير الـinstance عبر كل شجرة المكوّنات — نفس نمط
        // frappe.provide المستخدم أصلًا في هذا الملف.
        frappe.PosApp.vuetify = vuetify;

        this.vue = createApp(Home);
        this.vue.use(vuetify);
        // Vue2's template compiler كان بيسمح بالوصول التلقائي لأي
        // global (زي window.__ دالة الترجمة، وwindow._ الخاصة بـlodash)
        // من جوه أي template بلا تسجيل صريح. Vue3's compiler ما بيعملش
        // ده — لازم تسجيل صريح كـglobalProperties عشان كل مكوّنات
        // posawesome (اللي بتنادي __('...') و_.xxx من الـtemplate
        // مباشرة) تفضل شغالة من غير تعديل الـ٢١ مكوّن.
        this.vue.config.globalProperties.__ = window.__;
        this.vue.config.globalProperties._ = window._;
        this.vue.config.globalProperties.frappe = frappe;
        this.vue.mount(this.$el[0]);
    }
    setup_header () {

    }

};
