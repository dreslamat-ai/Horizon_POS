<template>
  <v-row justify="center">
    <v-dialog v-model="closingDialog" max-width="900px">
      <v-card>
        <v-card-title>
          <span class="headline primary--text">{{
            __('إغلاق الوردية')
          }}</span>
        </v-card-title>
        <v-card-text class="pa-0">
          <v-container>
            <v-row>
              <v-col cols="12" class="pa-1">
                <v-data-table
                  :headers="headers"
                  :items="dialog_data.payment_reconciliation"
                  item-key="mode_of_payment"
                  class="elevation-1"
                  :items-per-page="itemsPerPage"
                  hide-default-footer
                >
                  <template v-slot:item.closing_amount="{ item }">
                    <v-text-field
                      v-model="item.closing_amount"
                      :rules="[max25chars]"
                      :label="frappe._('تعديل')"
                      density="compact"
                      single-line
                      type="number"
                      hide-details
                    ></v-text-field>
                  </template>
                  <template v-slot:item.difference="{ item }">
                    {{ currencySymbol(pos_profile.currency) }}
                    {{
                      (item.difference = formtCurrency(
                        item.expected_amount - item.closing_amount
                      ))
                    }}</template
                  >
                  <template v-slot:item.opening_amount="{ item }">
                    {{ currencySymbol(pos_profile.currency) }}
                    {{ formtCurrency(item.opening_amount) }}</template
                  >
                  <template v-slot:item.expected_amount="{ item }">
                    {{ currencySymbol(pos_profile.currency) }}
                    {{ formtCurrency(item.expected_amount) }}</template
                  >
                </v-data-table>
              </v-col>
            </v-row>
          </v-container>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="#DC2626" variant="flat" dark @click="close_dialog">{{
            __('إغلاق')
          }}</v-btn>
          <v-btn color="#16A34A" variant="flat" dark @click="submit_dialog">{{
            __('تسجيل')
          }}</v-btn>
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
    closingDialog: false,
    itemsPerPage: 20,
    dialog_data: { payment_reconciliation: [] },
    pos_profile: '',
    // Vuetify3: `title` بدل `text` (الصيغة القديمة كانت بتعطّل عناوين
    // الأعمدة صامتًا بلا أي خطأ ظاهر).
    headers: [
      {
        title: __('طريقة السداد'),
        value: 'mode_of_payment',
        align: 'start',
        sortable: true,
      },
      {
        title: __('القيمة الإفتتاحية'),
        align: 'end',
        sortable: true,
        value: 'opening_amount',
      },
      {
        title: __('القيمة الختامية'),
        value: 'closing_amount',
        align: 'end',
        sortable: true,
      },
    ],
    max25chars: (v) => v.length <= 20 || 'القيمة طويلة جدا!', // TODO : should validate as number
    pagination: {},
  }),
  watch: {},

  methods: {
    close_dialog() {
      this.closingDialog = false;
    },
    submit_dialog() {
      evntBus.$emit('submit_closing_pos', this.dialog_data);
      this.closingDialog = false;
    },
  },

  created: function () {
    evntBus.$on('open_ClosingDialog', (data) => {
      this.closingDialog = true;
      this.dialog_data = data;
    });
    evntBus.$on('register_pos_profile', (data) => {
      this.pos_profile = data.pos_profile;
      if (!this.pos_profile.hide_expected_amount) {
        this.headers.push({
          title: __('المبلغ المتوقع'),
          value: 'expected_amount',
          align: 'end',
          sortable: false,
        });
        this.headers.push({
          title: __('الفرق'),
          value: 'difference',
          align: 'end',
          sortable: false,
        });
      }
    });
  },
};
</script>
