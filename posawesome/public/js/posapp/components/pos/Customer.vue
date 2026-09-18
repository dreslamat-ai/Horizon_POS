<template>
  <div class="customer-search-wrap">
    <div class="customer-row" v-show="!show_search_input" @click="open_search_input">
      <div class="customer-avatar">{{ customer_display_initial }}</div>
      <div class="customer-text">
        <div class="customer-name">{{ customer_display_name }}</div>
        <div class="customer-hint">{{ customer ? __("اضغط للتغيير") : __("اضغط لاختيار عميل مسجّل") }}</div>
      </div>
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#6B7280" stroke-width="2">
        <path d="M9 6l6 6-6 6" />
      </svg>
    </div>
    <v-autocomplete
      ref="customer_autocomplete"
      dense
      clearable
      auto-select-first
      outlined
      color="primary"
      :label="frappe._('العميل')"
      v-model="customer"
      :items="customers"
      item-title="customer_name"
      item-value="name"
      background-color="white"
      :no-data-text="__('العميل غير موجود')"
      hide-details
      :filter="customFilter"
      :disabled="readonly"
      append-icon="mdi-plus"
      @click:append="new_customer"
      prepend-inner-icon="mdi-account-edit"
      @click:prepend-inner="edit_customer"
      @update:search="onCustomerSearchUpdate"
    >
      <template v-slot:item="data">
        <template>
          <v-list-item-content>
            <v-list-item-title
              class="primary--text subtitle-1"
              v-html="data.item.customer_name"
            ></v-list-item-title>
            <v-list-item-subtitle
              v-if="data.item.customer_name != data.item.name"
              v-html="`ID: ${data.item.name}`"
            ></v-list-item-subtitle>
            <v-list-item-subtitle
              v-if="data.item.tax_id"
              v-html="`الرقم الضريبي : ${data.item.tax_id}`"
            ></v-list-item-subtitle>
            <v-list-item-subtitle
              v-if="data.item.email_id"
              v-html="`الإيميل : ${data.item.email_id}`"
            ></v-list-item-subtitle>
            <v-list-item-subtitle
              v-if="data.item.mobile_no"
              v-html="`رقم الموبايل : ${data.item.mobile_no}`"
            ></v-list-item-subtitle>
            <v-list-item-subtitle
              v-if="data.item.primary_address"
              v-html="`العنوان الرئيسي : ${data.item.primary_address}`"
            ></v-list-item-subtitle>
          </v-list-item-content>
        </template>
      </template>
    </v-autocomplete>
    <div class="mb-8">
      <UpdateCustomer></UpdateCustomer>
    </div>
  </div>
</template>

<script>
import { evntBus } from '../../bus';
import UpdateCustomer from './UpdateCustomer.vue';
export default {
  data: () => ({
    pos_profile: '',
    customers: [],
    customer: '',
    readonly: false,
    customer_info: {},
    customer_search_query: '',
    show_search_input: false,
  }),

  components: {
    UpdateCustomer,
  },

  computed: {
    customer_display_name() {
      return this.customer_info && this.customer_info.customer_name
        ? this.customer_info.customer_name
        : this.__('عميل نقدي');
    },
    customer_display_initial() {
      const name = this.customer_display_name;
      return name ? name.trim().charAt(0) : 'ع';
    },
  },

  methods: {
    open_search_input() {
      this.show_search_input = true;
      this.$nextTick(() => {
        if (this.$refs.customer_autocomplete) {
          this.$refs.customer_autocomplete.focus();
        }
      });
    },
    get_customer_names() {
      const vm = this;
      if (this.customers.length > 0) {
        return;
      }
      if (vm.pos_profile.posa_local_storage && localStorage.customer_storage) {
        vm.customers = JSON.parse(localStorage.getItem('customer_storage'));
      }
      frappe.call({
        method: 'posawesome.posawesome.api.posapp.get_customer_names',
        args: {
          pos_profile: this.pos_profile.pos_profile,
        },
        callback: function (r) {
          if (r.message) {
            vm.customers = r.message;
            console.info('loadCustomers');
            if (vm.pos_profile.posa_local_storage) {
              localStorage.setItem('customer_storage', '');
              localStorage.setItem(
                'customer_storage',
                JSON.stringify(r.message)
              );
            }
          }
        },
      });
    },
    new_customer() {
      // نص البحث اللي كتبه الكاشير قبل الضغط على "+" ممكن يكون رقم
      // موبايل مش موجود في القائمة — نمرّره كقيمة مبدئية لحقل الموبايل
      // في فورم الإنشاء بدل ما الكاشير يعيد كتابته.
      const query = (this.customer_search_query || '').trim();
      const looksLikeMobile = /^\+?\d{6,}$/.test(query);
      evntBus.$emit(
        'open_update_customer',
        looksLikeMobile ? { prefill_mobile_no: query } : null
      );
    },
    edit_customer() {
      evntBus.$emit('open_update_customer', this.customer_info);
    },
    onCustomerSearchUpdate(value) {
      // Vuetify بيصفّر قيمة البحث تلقائيًا عند فقد التركيز (blur) — وده
      // بيحصل قبل ما حدث الضغط على "+" يوصل. لو تجاهلنا القيم الفارغة هنا
      // بنحتفظ بآخر نص كتبه الكاشير فعليًا لحظة الضغط، بدل ما يتصفّر قبلها.
      if (value) {
        this.customer_search_query = value;
      }
    },
    customFilter(item, queryText, itemText) {
      const textOne = item.customer_name
        ? item.customer_name.toLowerCase()
        : '';
      const textTwo = item.tax_id ? item.tax_id.toLowerCase() : '';
      const textThree = item.email_id ? item.email_id.toLowerCase() : '';
      const textFour = item.mobile_no ? item.mobile_no.toLowerCase() : '';
      const textFifth = item.name.toLowerCase();
      const searchText = queryText.toLowerCase();

      return (
        textOne.indexOf(searchText) > -1 ||
        textTwo.indexOf(searchText) > -1 ||
        textThree.indexOf(searchText) > -1 ||
        textFour.indexOf(searchText) > -1 ||
        textFifth.indexOf(searchText) > -1
      );
    },
  },

  created: function () {
    this.$nextTick(function () {
      evntBus.$on('register_pos_profile', (pos_profile) => {
        this.pos_profile = pos_profile;
        this.get_customer_names();
      });
      evntBus.$on('payments_register_pos_profile', (pos_profile) => {
        this.pos_profile = pos_profile;
        this.get_customer_names();
      });
      evntBus.$on('set_customer', (customer) => {
        this.customer = customer;
      });
      evntBus.$on('add_customer_to_list', (customer) => {
        this.customers.push(customer);
      });
      evntBus.$on('set_customer_readonly', (value) => {
        this.readonly = value;
      });
      evntBus.$on('set_customer_info_to_edit', (data) => {
        this.customer_info = data;
      });
      evntBus.$on('fetch_customer_details', () => {
        this.get_customer_names();
      });
      evntBus.$on('posa_focus_customer_search', () => {
        this.$nextTick(() => {
          if (this.$refs.customer_autocomplete) {
            this.$refs.customer_autocomplete.focus();
          }
        });
      });
    });
  },

  watch: {
    customer() {
      evntBus.$emit('update_customer', this.customer);
      // اختيار عميل موجود فعليًا يُنهي محاولة البحث الحالية — نصفّر النص
      // المحفوظ حتى لا يظهر عالقًا في فورم إضافة عميل لاحق مختلف تمامًا.
      this.customer_search_query = '';
      this.show_search_input = false;
    },
  },
};
</script>
