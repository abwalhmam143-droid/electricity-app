import streamlit as st
import sqlite3
import urllib.parse

# إعداد قاعدة البيانات
def init_db():
    conn = sqlite3.connect('electricity_mobile.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS subscribers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT, phone TEXT, category TEXT, ct_ratio REAL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subscriber_id INTEGER, total_kwh REAL, amount_due REAL, issue_date TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

st.set_page_config(page_title="حساب الكهرباء", page_icon="⚡")

# العنوان وبيانات الفني
st.title("⚡ نظام فواتير الكهرباء")
st.info("👨‍🔧 إشراف: فني كهربائي | 📞 0539093825")

tab1, tab2, tab3 = st.tabs(["إصدار فاتورة", "إضافة مشترك", "سجل الفواتير"])

# Tab 1: إصدار فاتورة
with tab1:
    conn = sqlite3.connect('electricity_mobile.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, name, phone, category, ct_ratio FROM subscribers')
    subscribers = cursor.fetchall()
    conn.close()

    if subscribers:
        sub_dict = {f"{s[1]} ({'سكني' if s[3]=='residential' else 'تجاري'})": s for s in subscribers}
        selected_sub_name = st.selectbox("اختر المشترك:", list(sub_dict.keys()))
        sub_data = sub_dict[selected_sub_name]

        prev_read = st.number_input("القراءة السابقة:", min_value=0.0)
        curr_read = st.number_input("القراءة الحالية:", min_value=0.0)

        if st.button("حساب الفاتورة", type="primary"):
            if curr_read >= prev_read:
                raw = curr_read - prev_read
                total_kwh = raw * sub_data[4]
                rate1 = 0.18 if sub_data[3] == 'residential' else 0.20
                
                cost = total_kwh * rate1 if total_kwh <= 6000 else (6000 * rate1) + ((total_kwh - 6000) * 0.30)
                subtotal = cost + 15.0
                vat = subtotal * 0.15
                total = subtotal + vat

                st.success(f"إجمالي المبلغ: {total:,.2f} ريال سعودي")
                st.write(f"- الاستهلاك: {total_kwh:,.2f} ك.و.س")
                st.write(f"- ضريبة القيمة المضافة: {vat:,.2f} ريال")

                # رابط الواتساب
                msg = f"مرحباً {sub_data[1]} 👋\nفاتورة الكهرباء المستحقة: {total:,.2f} ريال سعودي.\nالاستهلاك: {total_kwh:,.2f} ك.و.س.\n------------------\n👨‍🔧 الفني الكهربائي | 📞 0539093825"
                wa_url = f"https://wa.me/{sub_data[2]}?text={urllib.parse.quote(msg)}"
                
                st.markdown(f'[{":📲 إرسال الفاتورة عبر WhatsApp"}]({wa_url})')
            else:
                st.error("القراءة الحالية يجب أن تكون أكبر من السابقة.")
    else:
        st.warning("يرجى إضافة مشترك أولاً من تبويب 'إضافة مشترك'.")

# Tab 2: إضافة مشترك
with tab2:
    name = st.text_input("اسم المشترك:")
    phone = st.text_input("رقم الجوال (مثال: 966500000000):", value="9665")
    category = st.selectbox("الفئة:", ["سكني", "تجاري"])
    ct_ratio = st.number_input("معامل CT:", value=1.0)

    if st.button("حفظ المشترك"):
        if name and phone:
            cat_code = "residential" if category == "سكني" else "commercial"
            conn = sqlite3.connect('electricity_mobile.db')
            cursor = conn.cursor()
            cursor.execute('INSERT INTO subscribers (name, phone, category, ct_ratio) VALUES (?, ?, ?, ?)', (name, phone, cat_code, ct_ratio))
            conn.commit()
            conn.close()
            st.success(f"تم حفظ المشترك {name} بنجاح!")

# Tab 3: السجل
with tab3:
    conn = sqlite3.connect('electricity_mobile.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, name, phone, category FROM subscribers')
    rows = cursor.fetchall()
    conn.close()
    st.dataframe(rows, column_config={"0": "الرقم", "1": "الاسم", "2": "الجوال", "3": "الفئة"})
