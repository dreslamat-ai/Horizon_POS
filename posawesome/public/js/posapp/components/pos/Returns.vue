<template>
  <v-row justify="center">
    <v-dialog v-model="invoicesDialog" max-width="800px" min-width="800px">
      <v-card>
        <v-card-title>
          <span class="headline primary--text">{{
            __('إختار فاتورة المرتجع')
          }}</span>
        </v-card-title>
        <v-container>
          <v-row class="mb-4">
            <v-text-field
              color="primary"
              :label="frappe._('رقم الفاتورة')"
              background-color="white"
              hide-details
              v-model="invoice_name"
              dense
              clearable
              class="mx-4"
            ></v-text-field>
            <v-btn
              text
              class="ml-2"
              color="primary"
              dark
              @click="search_invoices"
              >{{ __('بحث') }}</v-btn
            >
          </v-row>
          <v-row>
            <v-col cols="12" class="pa-1" v-if="dialog_data.length">
              <v-data-table
                :headers="headers"
                :items="dialog_data"
                item-key="name"
                class="elevation-1"
                @click:row="select_row"
              >
                <template v-slot:item.grand_total="{ item }">
                  {{ currencySymbol(item.currency) }}
                  {{ formtCurrency(item.grand_total) }}</template
                >
              </v-data-table>
            </v-col>
          </v-row>
        </v-container>
        <v-card-actions class="mt-4">
          <v-spacer></v-spacer>
          <v-btn color="error mx-2" dark @click="close_dialog">{{ __('إغلاق') }}</v-btn>
          <v-btn
            v-if="selected.length"
            color="success"
            dark
            @click="submit_dialog"
            >{{ __('إختيار') }}</v-btn
          >
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-row>
</template>

<script>
import { evntBus } from '../../bus';
import format from '../../format';
export default {
  mixins: [format],
  data: () => ({
    invoicesDialog: false,
    singleSelect: true,
    selected: [],
    dialog_data: [],
    company: '',
    invoice_name: '',
    headers: [
      {
        title: __('العميل'),
        value: 'customer',
        align: 'start',
        sortable: true,
      },
      {
        title: __('التاريخ'),
        align: 'start',
        sortable: true,
        value: 'posting_date',
      },
      {
        title: __('الفاتورة'),
        value: 'name',
        align: 'start',
        sortable: true,
      },
      {
        title: __('الإجمالي'),
        value: 'grand_total',
        align: 'end',
        sortable: false,
      },
    ],
  }),
  watch: {},
  methods: {
    close_dialog() {
      this.invoicesDialog = false;
    },
    // Vuetify3: show-select's v-model اتغيّرت آليتها بالكامل — استُبدلت
    // باختيار مباشر عبر الضغط على الصف (نفس الوظيفة: فاتورة واحدة).
    select_row(event, { item }) {
      this.selected = [item];
    },
    search_invoices_by_enter(e) {
      if (e.keyCode === 13) {
        this.search_invoices();
      }
    },
    search_invoices() {
      const vm = this;
      frappe.call({
        method: 'posawesome.posawesome.api.posapp.search_invoices_for_return',
        args: {
          invoice_name: vm.invoice_name,
          company: vm.company,
        },
        async: false,
        callback: function (r) {
          if (r.message) {
            vm.dialog_data = r.message;
          }
        },
      });
    },
    submit_dialog() {
      if (this.selected.length > 0) {
        const return_doc = this.selected[0];
        const invoice_doc = {};
        const items = [];
        return_doc.items.forEach((item) => {
          const new_item = { ...item };
          new_item.qty = item.qty * -1;
          new_item.stock_qty = item.stock_qty * -1;
          new_item.amount = item.amount * -1;
          items.push(new_item);
        });
        invoice_doc.items = items;
        invoice_doc.is_return = 1;
        invoice_doc.return_against = return_doc.name;
        invoice_doc.customer = return_doc.customer;
        const data = { invoice_doc, return_doc };
        evntBus.$emit('load_return_invoice', data);
        this.invoicesDialog = false;
      }
    },
  },
  created: function () {
    evntBus.$on('open_returns', (data) => {
      this.invoicesDialog = true;
      this.company = data;
      this.invoice_name = '';
      this.dialog_data = [];
      this.selected = [];
    });
  },
};
</script>
