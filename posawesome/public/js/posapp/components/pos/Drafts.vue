<template>
  <v-row justify="center">
    <v-dialog v-model="draftsDialog" max-width="900px">
      <v-card>
        <v-card-title>
          <span class="headline primary--text">{{
            __('إختار الفاتورة المعلقة')
          }}</span>
        </v-card-title>
        <v-card-text class="pa-0">
          <v-container>
            <v-row no-gutters>
              <v-col cols="12" class="pa-1">
                <v-data-table
                  :headers="headers"
                  :items="dialog_data"
                  item-key="name"
                  class="elevation-1 drafts-table"
                  :row-props="row_props"
                  @click:row="select_row"
                >
                  <template v-slot:item.posting_time="{ item }">
                    {{ item.posting_time.split('.')[0] }}
                  </template>
                  <template v-slot:item.grand_total="{ item }">
                    {{ currencySymbol(item.currency) }}
                    {{ formtCurrency(item.grand_total) }}
                  </template>
                </v-data-table>
                <p class="drafts-hint" v-if="dialog_data.length > 1">
                  {{ __('اضغط على الفاتورة المطلوبة لتحديدها، ثم "إختيار"') }}
                </p>
              </v-col>
            </v-row>
          </v-container>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="grey darken-1" dark @click="close_dialog">إغلاق</v-btn>
          <v-btn
            color="primary"
            dark
            :disabled="!selected.length"
            @click="submit_dialog"
            >إختيار</v-btn
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
  // props: ["draftsDialog"],
  mixins: [format],
  data: () => ({
    draftsDialog: false,
    singleSelect: true,
    selected: [],
    dialog_data: [],
    headers: [
      {
        title: __('العميل'),
        value: 'customer_name',
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
        title: __('الوقت'),
        align: 'start',
        sortable: true,
        value: 'posting_time',
      },
      {
        title: __('الفاتورة'),
        value: 'name',
        align: 'start',
        sortable: true,
      },
      {
        title: __('القيمة'),
        value: 'grand_total',
        align: 'end',
        sortable: false,
      },
    ],
  }),
  watch: {},
  methods: {
    close_dialog() {
      this.draftsDialog = false;
    },
    // Vuetify3: show-select's v-model اتغيّرت آليتها بالكامل (بتاخد
    // مفاتيح لا كائنات كاملة) وكانت بترمي خطأ داخلي عند البناء —
    // استُبدلت باختيار مباشر عبر الضغط على الصف نفسه (نفس الوظيفة:
    // فاتورة واحدة تُختار من القائمة).
    select_row(event, { item }) {
      this.selected = [item];
    },
    // لتلوين الصف المختار بصريًا — rowProps مدعومة فعليًا في نسخة
    // Vuetify3 المثبتة هنا (VDataTableRows.js)، بلا الحاجة لـshow-select
    // المعطوبة في هذا الإصدار (راجع تعليق select_row أعلاه).
    row_props({ item }) {
      const is_selected =
        this.selected.length && this.selected[0].name === item.name;
      return { class: is_selected ? 'selected-draft-row' : '' };
    },
    submit_dialog() {
      if (this.selected.length > 0) {
        evntBus.$emit('load_invoice', this.selected[0]);
        this.draftsDialog = false;
      }
    },
  },
  created: function () {
    evntBus.$on('open_drafts', (data) => {
      this.draftsDialog = true;
      this.dialog_data = data;
      this.selected = [];
    });
  },
};
</script>

<style scoped>
.drafts-table :deep(tr.selected-draft-row) {
  background-color: rgba(29, 45, 68, 0.12);
  box-shadow: inset 3px 0 0 #1d2d44;
}
.drafts-table :deep(tbody tr) {
  cursor: pointer;
}
.drafts-hint {
  margin: 8px 12px 0;
  color: rgba(0, 0, 0, 0.6);
  font-size: 0.85rem;
}
</style>
