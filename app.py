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

st.set_page_config(page_title="பூமி நகர்த்தி கண்காணிப்பு", page_icon="🚜", layout="wide")
st.title("🚜 VPP எர்த்மூவர் வணிக மேலாண்மை")

# Sidebar navigation
menu = st.sidebar.selectbox("📂 பிரிவு தேர்வு செய்யவும்", ["புதிய இயந்திரம்", "நாள் வேலை விவரம்", "செலவு சேர்க்க", "அறிக்கை டாஷ்போர்ட்"])

# ------------------------------------------------
# ADD MACHINE
# ------------------------------------------------
if menu == "புதிய இயந்திரம்":
    st.subheader("➕ புதிய இயந்திரம் சேர்க்க")
    machine_id = st.text_input("இயந்திர ID (உதா: JCB001)")
    name = st.text_input("இயந்திர பெயர்")
    type_ = st.selectbox("இயந்திர வகை", ["JCB", "டிராக்டர்"])
    purchase_date = st.date_input("வாங்கிய தேதி")

    if st.button("சேமிக்க"):
        conn = get_conn()
        try:
            conn.execute("INSERT INTO machines VALUES (?, ?, ?, ?)", (machine_id, name, type_, purchase_date))
            conn.commit()
            st.success(f"✅ '{name}' இயந்திரம் வெற்றிகரமாக சேர்க்கப்பட்டது!")
        except sqlite3.IntegrityError:
            st.error("⚠️ இந்த இயந்திர ID ஏற்கனவே உள்ளது.")
        conn.close()

# ------------------------------------------------
# ADD DAILY USAGE
# ------------------------------------------------
elif menu == "நாள் வேலை விவரம்":
    st.subheader("🕒 நாள் வேலை தரவு சேர்க்க")
    conn = get_conn()
    machines = pd.read_sql("SELECT machine_id, machine_name FROM machines", conn)
    if machines.empty:
        st.warning("⚠️ முதலில் ஒரு இயந்திரம் சேர்க்கவும்.")
    else:
        machine = st.selectbox("இயந்திரத்தைத் தேர்வு செய்யவும்", machines["machine_id"] + " - " + machines["machine_name"])
        machine_id = machine.split(" - ")[0]
        work_date = st.date_input("தேதி", date.today())
        hours = st.number_input("பணி நேரம் (மணி)", min_value=0.0)
        rate = st.number_input("மணி ஒன்றுக்கான கட்டணம்", min_value=0.0)
        operator = st.text_input("ஓட்டுநர் பெயர்")
        income = hours * rate

        if st.button("சேமிக்க"):
            conn.execute("""
                INSERT INTO daily_usage (date, machine_id, hours_worked, rate_per_hour, operator, income)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (work_date, machine_id, hours, rate, operator, income))
            conn.commit()
            st.success("✅ நாள் வேலை வெற்றிகரமாக சேர்க்கப்பட்டது!")
    conn.close()

# ------------------------------------------------
# ADD EXPENSE
# ------------------------------------------------
elif menu == "செலவு சேர்க்க":
    st.subheader("💰 செலவு விவரங்கள்")
    conn = get_conn()
    machines = pd.read_sql("SELECT machine_id, machine_name FROM machines", conn)
    if machines.empty:
        st.warning("⚠️ முதலில் ஒரு இயந்திரம் சேர்க்கவும்.")
    else:
        machine = st.selectbox("இயந்திரத்தைத் தேர்வு செய்யவும்", machines["machine_id"] + " - " + machines["machine_name"])
        machine_id = machine.split(" - ")[0]
        exp_date = st.date_input("தேதி", date.today())
        exp_type = st.selectbox("செலவு வகை", ["எரிபொருள்", "பராமரிப்பு", "ஓட்டுநர் கூலி", "மற்றவை"])
        amount = st.number_input("மொத்த தொகை", min_value=0.0)
        remarks = st.text_input("குறிப்புகள்")

        if st.button("சேமிக்க"):
            conn.execute("""
                INSERT INTO expenses (date, machine_id, expense_type, amount, remarks)
                VALUES (?, ?, ?, ?, ?)
            """, (exp_date, machine_id, exp_type, amount, remarks))
            conn.commit()
            st.success("✅ செலவு விவரம் வெற்றிகரமாக சேமிக்கப்பட்டது!")
    conn.close()

# ------------------------------------------------
# REPORTS DASHBOARD
# ------------------------------------------------
elif menu == "அறிக்கை டாஷ்போர்ட்":
    st.subheader("📊 அறிக்கை டாஷ்போர்ட்")
    conn = get_conn()

    daily = pd.read_sql("SELECT * FROM daily_usage", conn)
    expenses = pd.read_sql("SELECT * FROM expenses", conn)
    conn.close()

    if daily.empty and expenses.empty:
        st.info("ℹ️ தரவு இல்லை. முதலில் வேலை அல்லது செலவு சேர்க்கவும்.")
    else:
        # Convert to datetime
        if not daily.empty:
            daily["date"] = pd.to_datetime(daily["date"])
        if not expenses.empty:
            expenses["date"] = pd.to_datetime(expenses["date"])

        # Combine data
        income_df = daily.groupby("date")["income"].sum().reset_index()
        expense_df = expenses.groupby("date")["amount"].sum().reset_index()
        combined = pd.merge(income_df, expense_df, on="date", how="outer").fillna(0)
        combined["profit"] = combined["income"] - combined["amount"]

        # Weekly & Monthly aggregation
        combined["week"] = combined["date"].dt.to_period("W").apply(lambda r: r.start_time)
        combined["month"] = combined["date"].dt.to_period("M").apply(lambda r: r.start_time)

        weekly = combined.groupby("week")[["income", "amount", "profit"]].sum().reset_index()
        monthly = combined.groupby("month")[["income", "amount", "profit"]].sum().reset_index()

        latest_week = weekly.iloc[-1] if not weekly.empty else {"income": 0, "amount": 0, "profit": 0}
        latest_month = monthly.iloc[-1] if not monthly.empty else {"income": 0, "amount": 0, "profit": 0}

        # ---- Highlighted Profit/Loss Cards ----
        st.markdown("## 💹 வார & மாத இலாப / நட்ட அறிக்கை")

        def profit_card(title, value):
            color = "#16a34a" if value >= 0 else "#dc2626"
            emoji = "🟢" if value >= 0 else "🔴"
            return f"""
            <div style="background-color:{color}20;padding:20px;border-radius:15px;
                        border-left:8px solid {color};margin-bottom:15px;
                        box-shadow:2px 2px 10px #ddd;">
                <h3>{emoji} {title}</h3>
                <h2 style="color:{color};">₹{value:,.2f}</h2>
            </div>
            """

        colA, colB = st.columns(2)
        with colA:
            st.markdown(profit_card("வார இலாபம் / நட்டம்", latest_week["profit"]), unsafe_allow_html=True)
        with colB:
            st.markdown(profit_card("மாத இலாபம் / நட்டம்", latest_month["profit"]), unsafe_allow_html=True)

        st.divider()

        # KPI Metrics
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("📅 வார வருமானம்", f"₹{latest_week['income']:,.2f}")
        c2.metric("💸 வார செலவு", f"₹{latest_week['amount']:,.2f}")
        c3.metric("🗓️ மாத வருமானம்", f"₹{latest_month['income']:,.2f}")
        c4.metric("💰 மாத செலவு", f"₹{latest_month['amount']:,.2f}")

        st.divider()

        # Line Chart
        st.subheader("📅 வருமானம் vs செலவு - காலத்தின் அடிப்படையில்")
        line_fig = px.line(combined, x="date", y=["income", "amount"], labels={"value": "₹ தொகை", "variable": "வகை"}, title="வருமானம் மற்றும் செலவு ஒப்பீடு")
        st.plotly_chart(line_fig, use_container_width=True)

        # Weekly and Monthly Profit Trend
        st.subheader("📆 வார & மாத இலாப போக்கு")
        week_fig = px.bar(weekly, x="week", y="profit", color="profit", text_auto=".2s", title="வார இலாப / நட்ட போக்கு")
        month_fig = px.bar(monthly, x="month", y="profit", color="profit", text_auto=".2s", title="மாத இலாப / நட்ட போக்கு")

        st.plotly_chart(week_fig, use_container_width=True)
        st.plotly_chart(month_fig, use_container_width=True)

        # Comparison Summary
        st.subheader("📈 ஒப்பீட்டு சுருக்கம்")
        if len(weekly) >= 2:
            current_week, prev_week = weekly.iloc[-1]["profit"], weekly.iloc[-2]["profit"]
            week_change = current_week - prev_week
            week_percent = (week_change / prev_week * 100) if prev_week != 0 else 0
        else:
            week_change, week_percent = 0, 0

        if len(monthly) >= 2:
            current_month, prev_month = monthly.iloc[-1]["profit"], monthly.iloc[-2]["profit"]
            month_change = current_month - prev_month
            month_percent = (month_change / prev_month * 100) if prev_month != 0 else 0
        else:
            month_change, month_percent = 0, 0

        c1, c2 = st.columns(2)
        c1.metric("📅 வார இலாப மாற்றம்", f"₹{week_change:,.2f}", f"{week_percent:+.2f}% முந்தைய வாரத்துடன் ஒப்பிடும் போது")
        c2.metric("🗓️ மாத இலாப மாற்றம்", f"₹{month_change:,.2f}", f"{month_percent:+.2f}% முந்தைய மாதத்துடன் ஒப்பிடும் போது")

        st.divider()

        # Machine-wise Charts
        st.subheader("🚜 இயந்திர வாரியாக வருமானம் மற்றும் செலவு")
        if not daily.empty:
            income_chart = px.bar(daily.groupby("machine_id")["income"].sum().reset_index(), x="machine_id", y="income", color="machine_id", text_auto=".2s", title="இயந்திர வாரியாக வருமானம்")
            st.plotly_chart(income_chart, use_container_width=True)
        if not expenses.empty:
            expense_chart = px.bar(expenses.groupby("machine_id")["amount"].sum().reset_index(), x="machine_id", y="amount", color="machine_id", text_auto=".2s", title="இயந்திர வாரியாக செலவு")
            st.plotly_chart(expense_chart, use_container_width=True)

        # Raw Data
        with st.expander("📄 மூல தரவு பார்க்க"):
            st.write("### நாள் வேலை தரவு")
            st.dataframe(daily)
            st.write("### செலவு தரவு")
            st.dataframe(expenses)

        st.caption("📘 குறிப்பு: பக்கப்பட்டியைப் பயன்படுத்தி புதிய தரவைச் சேர்க்கலாம் அல்லது டாஷ்போர்ட்டை புதுப்பிக்கலாம்.")
