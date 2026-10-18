// ترحيل Vue3 (١٧ سبتمبر ٢٠٢٦): كان `new Vue()` بلا استيراد (كائن bus
// كلاسيكي Vue2 بيعتمد على المتغيّر العالمي `Vue`) — Vue3 شالت
// الـconstructor العالمي ده تمامًا. بديل بسيط بنفس واجهة $on/$off/$emit
// عشان الـ٢١ مكوّن اللي بيستخدموا evntBus مايحتاجوش أي تعديل.
const listeners = new Map();

export const evntBus = {
    $on(event, callback) {
        if (!listeners.has(event)) listeners.set(event, []);
        listeners.get(event).push(callback);
    },
    $off(event, callback) {
        if (!listeners.has(event)) return;
        if (!callback) {
            listeners.delete(event);
            return;
        }
        const cbs = listeners.get(event).filter((cb) => cb !== callback);
        listeners.set(event, cbs);
    },
    $emit(event, ...args) {
        if (!listeners.has(event)) return;
        listeners.get(event).forEach((cb) => cb(...args));
    },
};
