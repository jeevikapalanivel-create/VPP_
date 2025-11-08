import streamlit as st
import sqlite3
import pandas as pd
from datetime import date
import plotly.express as px

# ------------------------------------------------
# Database connection
# ------------------------------------------------
def get_conn():
    return sqlite3.connect("earthmover.db")

st.set_page_config(page_title="எர்த்மூவர் மேலாண்மை", page_icon="🚜", layout="wide")
st.title("🚜 எர்த்மூவர் வணிக மேலாண்மை")

# Sidebar navigation
menu = st.sidebar.selectbox("📂 பகுதி தேர்வு", ["இயந்திரம் சேர்க்க", "தினசரி வேலை பதிவு", "செலவு பதிவு", "அறிக்கைகள் பலகை"])

# ------------------------------------------------
# ADD MACHINE
# ------------------------------------------------
if menu == "இயந்திரம் சேர்க்க":
    st.subheader("➕ புதிய இயந்திரம் சேர்க்க")
    machine_id = st.text_input("இயந்திரம் ID (உதா: JCB001)")
    name = st.text_input("இயந்திரத்தின் பெயர்")
    type_ = st.selectbox("இயந்திர வகை", ["JCB", "டிராக்டர்"])
    purchase_date = st.date_input("வாங்கிய தேதி")

    if st.button("சேமிக்கவும்"):
        conn = get_conn()
        try:
            conn.execute("INSERT INTO machines VALUES (?, ?, ?, ?)", (machine_id, name, type_, purchase_date))
            conn.commit()
            st.success(f"✅ '{name}' வெற்றிகரமாக சேர்க்கப்பட்டது!")
        except sqlite3.IntegrityError:
            st.error("⚠️ இந்த ID ஏற்கனவே உள்ளது.")
        conn.close()

# ------------------------------------------------
# ADD DAILY USAGE
# ------------------------------------------------
elif menu == "தினசரி வேலை பதிவு":
    st.subheader("🕒 தினசரி வேலை விவரங்கள்")
    conn = get_conn()
    machines = pd.read_sql("SELECT machine_id, machine_name FROM machines", conn)
    if machines.empty:
        st.warning("⚠️ தயவுசெய்து முதலில் ஒரு இயந்திரத்தை சேர்க்கவும்.")
    else:
        machine = st.selectbox("இயந்திரம் தேர்வு", machines["machine_id"] + " - " + machines["machine_name"])
        machine_id = machine.split(" - ")[0]
        work_date = st.date_input("தேதி", date.today())
        hours = st.number_input("வேலை நேரம் (மணிநேரம்)", min_value=0.0)
        rate = st.number_input("மணிநேரத்திற்கு விலை (₹)", min_value=0.0)
        operator = st.text_input("ஓட்டுநர் பெயர்")
        income = hours * rate

        if st.button("சேமிக்கவும்"):
            conn.execute("""
                INSERT INTO daily_usage (date, machine_id, hours_worked, rate_per_hour, operator, income)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (work_date, machine_id, hours, rate, operator, income))
            conn.commit()
            st.success("✅ தினசரி வேலை விவரங்கள் சேமிக்கப்பட்டது!")
    conn.close()

# ------------------------------------------------
# ADD EXPENSE
# ------------------------------------------------
elif menu == "செலவு பதிவு":
    st.subheader("💰 செலவு விவரங்கள்")
    conn = get_conn()
    machines = pd.read_sql("SELECT machine_id, machine_name FROM machines", conn)
    if machines.empty:
        st.warning("⚠️ முதலில் ஒரு இயந்திரத்தை சேர்க்கவும்.")
    else:
        machine = st.selectbox("இயந்திரம் தேர்வு", machines["machine_id"] + " - " + machines["machine_name"])
        machine_id = machine.split(" - ")[0]
        exp_date = st.date_input("தேதி", date.today())
        exp_type = st.selectbox("செலவு வகை", ["எரிபொருள்", "பராமரிப்பு", "ஓட்டுநர் சம்பளம்", "மற்றவை"])
        amount = st.number_input("செலவு தொகை (₹)", min_value=0.0)
        remarks = st.text_input("குறிப்புகள்")

        if st.button("சேமிக்கவும்"):
            conn.execute("""
                INSERT INTO expenses (date, machine_id, expense_type, amount, remarks)
                VALUES (?, ?, ?, ?, ?)
            """, (exp_date, machine_id, exp_type, amount, remarks))
            conn.commit()
            st.success("✅ செலவு விவரங்கள் சேமிக்கப்பட்டது!")
    conn.close()

# ------------------------------------------------
# REPORTS DASHBOARD
# ------------------------------------------------
elif menu == "அறிக்கைகள் பலகை":
    st.subheader("📊 அறிக்கைகள் மற்றும் லாப-இழப்பு விவரங்கள்")
    conn = get_conn()

    daily = pd.read_sql("SELECT * FROM daily_usage", conn)
    expenses = pd.read_sql("SELECT * FROM expenses", conn)
    conn.close()

    if daily.empty and expenses.empty:
        st.info("ℹ️ இதுவரை எந்த தகவலும் இல்லை. தயவுசெய்து வேலை மற்றும் செலவுகளை பதிவு செய்யுங்கள்.")
    else:
        col1, col2, col3 = st.columns(3)
        total_income = daily["income"].sum() if not daily.empty else 0
        total_expense = expenses["amount"].sum() if not expenses.empty else 0
        net_profit = total_income - total_expense

        col1.metric("💵 மொத்த வருமானம்", f"₹{total_income:,.2f}")
        col2.metric("💸 மொத்த செலவு", f"₹{total_expense:,.2f}")
        col3.metric("📈 மொத்த லாபம்", f"₹{net_profit:,.2f}")

        st.divider()

        # Convert date columns
        if not daily.empty:
            daily["date"] = pd.to_datetime(daily["date"])
        if not expenses.empty:
            expenses["date"] = pd.to_datetime(expenses["date"])

        # ---------------------------
        # Line Chart: Income vs Expense over time
        # ---------------------------
        st.subheader("📅 வருமானம் மற்றும் செலவு நேரத்தின் அடிப்படையில்")

        income_df = daily.groupby("date")["income"].sum().reset_index()
        expense_df = expenses.groupby("date")["amount"].sum().reset_index()
        combined = pd.merge(income_df, expense_df, on="date", how="outer").fillna(0)

        line_fig = px.line(
            combined,
            x="date",
            y=["income", "amount"],
            labels={"value": "தொகை (₹)", "date": "தேதி", "variable": "வகை"},
            title="நாள் வாரியாக வருமானம் vs செலவு"
        )
        st.plotly_chart(line_fig, use_container_width=True)

        st.divider()

        # ---------------------------
        # Bar Chart: Machine-wise Income
        # ---------------------------
        st.subheader("🚜 இயந்திர வாரியாக வருமானம் மற்றும் செலவு")
        if not daily.empty:
            income_machine = daily.groupby("machine_id")["income"].sum().reset_index()
            income_chart = px.bar(
                income_machine,
                x="machine_id",
                y="income",
                color="machine_id",
                title="இயந்திர வாரியாக வருமானம்",
                text_auto=".2s"
            )
            st.plotly_chart(income_chart, use_container_width=True)

        # ---------------------------
        # Bar Chart: Machine-wise Expense
        # ---------------------------
        if not expenses.empty:
            expense_machine = expenses.groupby("machine_id")["amount"].sum().reset_index()
            expense_chart = px.bar(
                expense_machine,
                x="machine_id",
                y="amount",
                color="machine_id",
                title="இயந்திர வாரியாக செலவு",
                text_auto=".2s"
            )
            st.plotly_chart(expense_chart, use_container_width=True)

        st.divider()

        # ---------------------------
        # Data Tables
        # ---------------------------
        with st.expander("📄 விவரமான தரவுகள் பார்க்க"):
            st.write("### தினசரி வேலை விவரங்கள்")
            st.dataframe(daily)
            st.write("### செலவு விவரங்கள்")
            st.dataframe(expenses)

        st.caption("📘 குறிப்பு: பக்கத்திலுள்ள பட்டியில் இருந்து புதிய தகவல்களை சேர்க்கலாம்.")

