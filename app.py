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

st.set_page_config(page_title="Earthmover Tracker", page_icon="🚜", layout="wide")
st.title("🚜 Earthmover Operations Tracker")

# Sidebar navigation
menu = st.sidebar.selectbox("📂 Choose Section", ["Add Machine", "Add Daily Usage", "Add Expense", "Reports Dashboard"])

# ------------------------------------------------
# ADD MACHINE
# ------------------------------------------------
if menu == "Add Machine":
    st.subheader("➕ Add Machine")
    machine_id = st.text_input("Machine ID (e.g., JCB001)")
    name = st.text_input("Machine Name")
    type_ = st.selectbox("Type", ["JCB", "Tractor"])
    purchase_date = st.date_input("Purchase Date")

    if st.button("Save Machine"):
        conn = get_conn()
        try:
            conn.execute("INSERT INTO machines VALUES (?, ?, ?, ?)", (machine_id, name, type_, purchase_date))
            conn.commit()
            st.success(f"✅ Machine '{name}' added successfully!")
        except sqlite3.IntegrityError:
            st.error("⚠️ Machine ID already exists.")
        conn.close()

# ------------------------------------------------
# ADD DAILY USAGE
# ------------------------------------------------
elif menu == "Add Daily Usage":
    st.subheader("🕒 Add Daily Work Data")
    conn = get_conn()
    machines = pd.read_sql("SELECT machine_id, machine_name FROM machines", conn)
    if machines.empty:
        st.warning("⚠️ Please add a machine first.")
    else:
        machine = st.selectbox("Select Machine", machines["machine_id"] + " - " + machines["machine_name"])
        machine_id = machine.split(" - ")[0]
        work_date = st.date_input("Date", date.today())
        hours = st.number_input("Hours Worked", min_value=0.0)
        rate = st.number_input("Rate per Hour", min_value=0.0)
        operator = st.text_input("Operator Name")
        income = hours * rate

        if st.button("Save Usage"):
            conn.execute("""
                INSERT INTO daily_usage (date, machine_id, hours_worked, rate_per_hour, operator, income)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (work_date, machine_id, hours, rate, operator, income))
            conn.commit()
            st.success("✅ Daily usage saved successfully!")
    conn.close()

# ------------------------------------------------
# ADD EXPENSE
# ------------------------------------------------
elif menu == "Add Expense":
    st.subheader("💰 Add Expense")
    conn = get_conn()
    machines = pd.read_sql("SELECT machine_id, machine_name FROM machines", conn)
    if machines.empty:
        st.warning("⚠️ Please add a machine first.")
    else:
        machine = st.selectbox("Select Machine", machines["machine_id"] + " - " + machines["machine_name"])
        machine_id = machine.split(" - ")[0]
        exp_date = st.date_input("Date", date.today())
        exp_type = st.selectbox("Expense Type", ["Fuel", "Maintenance", "Operator Pay", "Other"])
        amount = st.number_input("Amount", min_value=0.0)
        remarks = st.text_input("Remarks")

        if st.button("Save Expense"):
            conn.execute("""
                INSERT INTO expenses (date, machine_id, expense_type, amount, remarks)
                VALUES (?, ?, ?, ?, ?)
            """, (exp_date, machine_id, exp_type, amount, remarks))
            conn.commit()
            st.success("✅ Expense saved successfully!")
    conn.close()

# ------------------------------------------------
# REPORTS DASHBOARD
# ------------------------------------------------
elif menu == "Reports Dashboard":
    st.subheader("📊 Reports Dashboard")
    conn = get_conn()

    daily = pd.read_sql("SELECT * FROM daily_usage", conn)
    expenses = pd.read_sql("SELECT * FROM expenses", conn)
    conn.close()

    if daily.empty and expenses.empty:
        st.info("ℹ️ No data available yet. Add usage and expenses to see reports.")
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

        # ---- New Highlighted Profit/Loss Cards ----
        st.markdown("## 💹 Weekly & Monthly Profit / Loss Summary")

        def profit_card(title, value):
            color = "#16a34a" if value >= 0 else "#dc2626"  # green for profit, red for loss
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
            st.markdown(profit_card("Weekly Profit / Loss", latest_week["profit"]), unsafe_allow_html=True)
        with colB:
            st.markdown(profit_card("Monthly Profit / Loss", latest_month["profit"]), unsafe_allow_html=True)

        st.divider()

        # KPI Metrics
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("📅 Weekly Income", f"₹{latest_week['income']:,.2f}")
        c2.metric("💸 Weekly Expense", f"₹{latest_week['amount']:,.2f}")
        c3.metric("🗓️ Monthly Income", f"₹{latest_month['income']:,.2f}")
        c4.metric("💰 Monthly Expense", f"₹{latest_month['amount']:,.2f}")

        st.divider()

        # Line Chart
        st.subheader("📅 Income vs Expense Over Time")
        line_fig = px.line(combined, x="date", y=["income", "amount"], labels={"value": "₹ Amount", "variable": "Type"}, title="Income vs Expense Over Time")
        st.plotly_chart(line_fig, use_container_width=True)

        # Weekly and Monthly Profit Trend
        st.subheader("📆 Weekly & Monthly Profit Trends")
        week_fig = px.bar(weekly, x="week", y="profit", color="profit", text_auto=".2s", title="Weekly Profit / Loss Trend")
        month_fig = px.bar(monthly, x="month", y="profit", color="profit", text_auto=".2s", title="Monthly Profit / Loss Trend")

        st.plotly_chart(week_fig, use_container_width=True)
        st.plotly_chart(month_fig, use_container_width=True)

        # Comparison Summary
        st.subheader("📈 Comparison Summary")
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
        c1.metric("📅 Week-over-Week Profit Change", f"₹{week_change:,.2f}", f"{week_percent:+.2f}% vs Last Week")
        c2.metric("🗓️ Month-over-Month Profit Change", f"₹{month_change:,.2f}", f"{month_percent:+.2f}% vs Last Month")

        st.divider()

        # Machine-wise Charts
        st.subheader("🚜 Machine-wise Income and Expense")
        if not daily.empty:
            income_chart = px.bar(daily.groupby("machine_id")["income"].sum().reset_index(), x="machine_id", y="income", color="machine_id", text_auto=".2s", title="Machine-wise Income")
            st.plotly_chart(income_chart, use_container_width=True)
        if not expenses.empty:
            expense_chart = px.bar(expenses.groupby("machine_id")["amount"].sum().reset_index(), x="machine_id", y="amount", color="machine_id", text_auto=".2s", title="Machine-wise Expenses")
            st.plotly_chart(expense_chart, use_container_width=True)

        # Raw Data
        with st.expander("📄 View Raw Data"):
            st.write("### Daily Usage Data")
            st.dataframe(daily)
            st.write("### Expense Data")
            st.dataframe(expenses)

        st.caption("📘 Tip: Use sidebar to add more data or refresh dashboard.")
