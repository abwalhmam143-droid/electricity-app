import sqlite3
import urllib.parse
import streamlit as st

# 1. تهيئة قاعدة البيانات وإنشاء الجداول المحدثة
conn = sqlite3.connect("electricity_mobile.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute(
    """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL
)
"""
)

cursor.execute(
    """
CREATE TABLE IF NOT EXISTS subscribers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    name TEXT NOT NULL,
    phone TEXT NOT NULL,
    category TEXT NOT NULL,
    ct_ratio REAL DEFAULT 1.0,
    FOREIGN KEY(user_id) REFERENCES users(id)
)
"""
)

cursor.execute(
    """
CREATE TABLE IF NOT EXISTS bills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sub_id INTEGER,
    prev_reading REAL,
    curr_reading REAL,
    consumption REAL,
    base_amount REAL,
    meter_fee REAL,
    vat_amount REAL,
    total_amount REAL,
    issue_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(sub_id) REFERENCES subscribers(id)
)
"""
)
conn.commit()

st.set_page_config(page_title="برنامج فواتير الكهرباء", layout="centered")

# 2. إدارة الجلسة وتسجيل الدخول
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "username" not in st.session_state:
    st.session_state.username = None

# إذا لم يكن المستخدم مسجلاً للدخول
if st.session_state.user_id is None:
    st.title("⚡ برنامج فواتير الكهرباء")
    auth_mode = st.radio(
        "اختر العملية:",
        ["تسجيل الدخول", "إنشاء حساب جديد"],
        horizontal=True,
    )

    username_input = st.text_input("اسم المستخدم:")
    password_input = st.text_input("كلمة المرور:", type="password")

    if auth_mode == "تسجيل الدخول":
        if st.button("دخول", use_container_width=True):
            if username_input and password_input:
                cursor.execute(
                    "SELECT id, username FROM users WHERE username = ? AND password = ?",
                    (username_input, password_input),
                )
                user = cursor.fetchone()
                if user:
                    st.session_state.user_id = user[0]
                    st.session_state.username = user[1]
                    st.success(f"مرحباً بك {user[1]}!")
                    st.rerun()
                else:
                    st.error("اسم المستخدم أو كلمة المرور غير صحيحة")
            else:
                st.warning("يرجى إدخال اسم المستخدم وكلمة المرور")

    elif auth_mode == "إنشاء حساب جديد":
        if st.button("إنشاء الحساب", use_container_width=True):
            if username_input and password_input:
                try:
                    cursor.execute(
                        "INSERT INTO users (username, password) VALUES (?, ?)",
                        (username_input, password_input),
                    )
                    conn.commit()
                    st.success(
                        "تم إنشاء الحساب بنجاح! يمكنك الآن تسجيل الدخول."
                    )
                except sqlite3.IntegrityError:
                    st.error(
                        "اسم المستخدم هذا مستخدم بالفعل، اختر اسماً آخر."
                    )
            else:
                st.warning("يرجى تعبئة جميع الحقول")

# بعد تسجيل الدخول بنجاح
else:
    # شريط هيدر الترحيب وتسجيل الخروج
    col_user, col_logout = st.columns([3, 1])
    with col_user:
        st.write(f"👤 مرحباً: **{st.session_state.username}**")
    with col_logout:
        if st.button("خروج"):
            st.session_state.user_id = None
            st.session_state.username = None
            st.rerun()

    st.title("⚡ تطبيق فواتير الكهرباء")

    tab1, tab2, tab3 = st.tabs(
        ["إصدار فاتورة", "إضافة مشترك", "سجل الفواتير"]
    )

    # --- تبويب إضافة مشترك ---
    with tab2:
        st.header("إضافة مشترك جديد")
        sub_name = st.text_input("اسم المشترك:")
        sub_phone = st.text_input("رقم الجوال:")
        sub_cat = st.selectbox(
            "فئة الاستهلاك:", ["سكني", "تجاري", "عداد محول (CT)"]
        )

        ct_val = 1.0
        if sub_cat == "عداد محول (CT)":
            ct_val = st.number_input(
                "معامل الضرب (CT Ratio):", min_value=1.0, value=10.0
            )

        if st.button("حفظ المشترك", use_container_width=True):
            if sub_name and sub_phone:
                cat_code = (
                    "residential"
                    if sub_cat == "سكني"
                    else ("commercial" if sub_cat == "تجاري" else "ct")
                )
                cursor.execute(
                    "INSERT INTO subscribers (user_id, name, phone, category, ct_ratio) VALUES (?, ?, ?, ?, ?)",
                    (
                        st.session_state.user_id,
                        sub_name,
                        sub_phone,
                        cat_code,
                        ct_val,
                    ),
                )
                conn.commit()
                st.success(f"تمت إضافة المشترك {sub_name} بنجاح!")
            else:
                st.warning("يرجى إدخال اسم المشترك ورقم الجوال")

    # --- تبويب إصدار فاتورة ---
    with tab1:
        st.header("إصدار فاتورة جديدة")

        # جلب مشتركي المستخدم الحالي فقط
        cursor.execute(
            "SELECT id, name, category, ct_ratio, phone FROM subscribers WHERE user_id = ?",
            (st.session_state.user_id,),
        )
        subs = cursor.fetchall()

        if not subs:
            st.info(
                "لا يوجد مشتركين في حسابك حتى الآن. يرجى إضافة مشترك من تبويب (إضافة مشترك)."
            )
        else:
            sub_options = {
                f"{s[1]} ({'سكني' if s[2]=='residential' else ('تجاري' if s[2]=='commercial' else 'CT')})": s
                for s in subs
            }
            selected_sub_name = st.selectbox(
                "اختر المشترك:", list(sub_options.keys())
            )
            selected_sub = sub_options[selected_sub_name]

            prev_read = st.number_input("القراءة السابقة:", min_value=0.0)
            curr_read = st.number_input("القراءة الحالية:", min_value=0.0)

            if st.button("حساب الفاتورة", use_container_width=True):
                if curr_read < prev_read:
                    st.error(
                        "خطأ: القراءة الحالية أقل من القراءة السابقة!"
                    )
                else:
                    raw_consumption = curr_read - prev_read
                    ct_ratio = selected_sub[3]
                    actual_consumption = raw_consumption * ct_ratio
                    cat = selected_sub[2]

                    # حساب الاستهلاك بناءً على الفئة
                    if cat == "residential":
                        if actual_consumption <= 6000:
                            base_cost = actual_consumption * 0.18
                        else:
                            base_cost = (6000 * 0.18) + (
                                (actual_consumption - 6000) * 0.30
                            )
                    else:  # commercial / ct
                        if actual_consumption <= 6000:
                            base_cost = actual_consumption * 0.20
                        else:
                            base_cost = (6000 * 0.20) + (
                                (actual_consumption - 6000) * 0.30
                            )

                    meter_fee = 15.0  # رسوم العداد الثابتة
                    subtotal = base_cost + meter_fee
                    vat = subtotal * 0.15
                    total = subtotal + vat

                    # حفظ الفاتورة
                    cursor.execute(
                        """
                    INSERT INTO bills (sub_id, prev_reading, curr_reading, consumption, base_amount, meter_fee, vat_amount, total_amount)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            selected_sub[0],
                            prev_read,
                            curr_read,
                            actual_consumption,
                            base_cost,
                            meter_fee,
                            vat,
                            total,
                        ),
                    )
                    conn.commit()

                    st.success(f"إجمالي المبلغ: {total:.2f} ريال سعودي")
                    st.write(f"- الاستهلاك: {actual_consumption:.2f} ك.و.س")
                    st.write(f"- ضريبة القيمة المضافة: {vat:.2f} ريال")

                    # تجهيز نص الواتساب
                    msg = (
                        f"فاتورة كهرباء للمشترك: {selected_sub[1]}\n"
                        f"الاستهلاك: {actual_consumption:.2f} ك.و.س\n"
                        f"رسوم العداد: {meter_fee:.2f} ريال\n"
                        f"الضريبة (15%): {vat:.2f} ريال\n"
                        f"الإجمالي المستحق: {total:.2f} ريال سعودي"
                    )
                    encoded_msg = urllib.parse.quote(msg)
                    whatsapp_url = f"https://wa.me/{selected_sub[4]}?text={encoded_msg}"

                    st.markdown(
                        f"[📱 إرسال الفاتورة عبر WhatsApp]({whatsapp_url})"
                    )

    # --- تبويب سجل الفواتير ---
    with tab3:
        st.header("سجل الفواتير المسجلة")
        cursor.execute(
            """
        SELECT s.name, b.consumption, b.total_amount, b.issue_date 
        FROM bills b 
        JOIN subscribers s ON b.sub_id = s.id 
        WHERE s.user_id = ?
        ORDER BY b.issue_date DESC
        """,
            (st.session_state.user_id,),
        )
        history = cursor.fetchall()

        if history:
            for item in history:
                st.info(
                    f"👤 **المشترك:** {item[0]} | ⚡ **الاستهلاك:** {item[1]:.2f} ك.و.س | 💵 **المبلغ:** {item[2]:.2f} ريال | 📅 {item[3]}"
                )
        else:
            st.write("لا توجد فواتير مسجلة في حسابك حتى الآن.")
