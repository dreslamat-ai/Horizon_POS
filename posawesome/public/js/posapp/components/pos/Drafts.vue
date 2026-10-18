<template>
  <v-row justify="center">
    <v-dialog v-model="draftsDialog" max-width="900px">
      <v-card class="drafts-card" rounded="lg">
        <v-card-title class="drafts-title">
          {{ __('إختار الفاتورة المعلقة') }}
        </v-card-title>
        <v-card-text class="pa-0">
          <v-container>
            <v-row no-gutters>
              <v-col cols="12" class="pa-1">
                <v-data-table
                  :headers="headers"
                  :items="dialog_data"
                  item-key="name"
                  class="elevation-0 drafts-table"
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
        <v-card-actions class="drafts-actions">
          <v-spacer></v-spacer>
          <v-btn variant="outlined" color="grey-darken-1" @click="close_dialog"
            >إغلاق</v-btn
          >
          <v-btn
            color="#1D2D44"
            variant="flat"
            dark
            class="drafts-choose-btn"
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
.drafts-card {
  overflow: hidden;
}
.drafts-title {
  background: #1d2d44;
  color: #f7f3ea;
  font-weight: 700;
  padding: 18px 20px;
  font-size: 1.1rem;
}
.drafts-table :deep(thead tr) {
  background-color: #f7f3ea;
}
.drafts-table :deep(thead th) {
  color: #1d2d44 !important;
  font-weight: 700 !important;
}
.drafts-table :deep(tr.selected-draft-row) {
  background-color: rgba(29, 45, 68, 0.12);
  box-shadow: inset 3px 0 0 #1d2d44;
}
.drafts-table :deep(tbody tr) {
  cursor: pointer;
}
.drafts-table :deep(tbody tr:hover) {
  background-color: rgba(29, 45, 68, 0.06);
}
.drafts-hint {
  margin: 10px 12px 0;
  color: #6b7280;
  font-size: 0.85rem;
}
.drafts-actions {
  padding: 12px 16px 16px;
}
.drafts-choose-btn {
  min-width: 110px;
}
</style>
