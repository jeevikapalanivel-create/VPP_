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

        # ---------------------------
        # KPI Metrics (Overall)
        # ---------------------------
        total_income = daily["income"].sum() if not daily.empty else 0
        total_expense = expenses["amount"].sum() if not expenses.empty else 0
        net_profit = total_income - total_expense

        col1, col2, col3 = st.columns(3)
        col1.metric("💵 Total Income", f"₹{total_income:,.2f}")
        col2.metric("💸 Total Expense", f"₹{total_expense:,.2f}")
        col3.metric("📈 Net Profit", f"₹{net_profit:,.2f}")

        st.divider()

        # ---------------------------
        # Combine for trend analysis
        # ---------------------------
        income_df = daily.groupby("date")["income"].sum().reset_index()
        expense_df = expenses.groupby("date")["amount"].sum().reset_index()
        combined = pd.merge(income_df, expense_df, on="date", how="outer").fillna(0)
        combined["profit"] = combined["income"] - combined["amount"]

        # ---------------------------
        # Line Chart: Income vs Expense over time
        # ---------------------------
        st.subheader("📅 Income vs Expense Over Time")
        line_fig = px.line(
            combined,
            x="date",
            y=["income", "amount"],
            labels={"value": "Amount (₹)", "date": "Date", "variable": "Type"},
            title="Income vs Expense Over Time"
        )
        st.plotly_chart(line_fig, use_container_width=True)

        st.divider()

        # ---------------------------
        # Weekly and Monthly Analysis
        # ---------------------------
        st.subheader("📆 Weekly & Monthly Profit and Loss")

        combined["week"] = combined["date"].dt.to_period("W").apply(lambda r: r.start_time)
        combined["month"] = combined["date"].dt.to_period("M").apply(lambda r: r.start_time)

        weekly = combined.groupby("week")[["income", "amount", "profit"]].sum().reset_index()
        monthly = combined.groupby("month")[["income", "amount", "profit"]].sum().reset_index()

        # Weekly Chart
        week_fig = px.bar(
            weekly,
            x="week",
            y="profit",
            title="Weekly Profit / Loss Trend",
            color="profit",
            text_auto=".2s"
        )
        st.plotly_chart(week_fig, use_container_width=True)

        # Monthly Chart
        month_fig = px.bar(
            monthly,
            x="month",
            y="profit",
            title="Monthly Profit / Loss Trend",
            color="profit",
            text_auto=".2s"
        )
        st.plotly_chart(month_fig, use_container_width=True)

        st.divider()

        # ---------------------------
        # Comparison Cards
        # ---------------------------
        st.subheader("📈 Comparison Summary")

        if len(weekly) >= 2:
            current_week = weekly.iloc[-1]["profit"]
            prev_week = weekly.iloc[-2]["profit"]
            week_change = current_week - prev_week
            week_percent = (week_change / prev_week * 100) if prev_week != 0 else 0
        else:
            week_change, week_percent = 0, 0

        if len(monthly) >= 2:
            current_month = monthly.iloc[-1]["profit"]
            prev_month = monthly.iloc[-2]["profit"]
            month_change = current_month - prev_month
            month_percent = (month_change / prev_month * 100) if prev_month != 0 else 0
        else:
            month_change, month_percent = 0, 0

        c1, c2 = st.columns(2)
        c1.metric(
            "📅 Week-over-Week Profit Change",
            f"₹{week_change:,.2f}",
            f"{week_percent:+.2f}% vs Last Week"
        )
        c2.metric(
            "🗓️ Month-over-Month Profit Change",
            f"₹{month_change:,.2f}",
            f"{month_percent:+.2f}% vs Last Month"
        )

        st.divider()

        # ---------------------------
        # Machine-wise Charts
        # ---------------------------
        st.subheader("🚜 Machine-wise Income and Expense")

        if not daily.empty:
            income_machine = daily.groupby("machine_id")["income"].sum().reset_index()
            income_chart = px.bar(
                income_machine,
                x="machine_id",
                y="income",
                color="machine_id",
                title="Machine-wise Income",
                text_auto=".2s"
            )
            st.plotly_chart(income_chart, use_container_width=True)

        if not expenses.empty:
            expense_machine = expenses.groupby("machine_id")["amount"].sum().reset_index()
            expense_chart = px.bar(
                expense_machine,
                x="machine_id",
                y="amount",
                color="machine_id",
                title="Machine-wise Expenses",
                text_auto=".2s"
            )
            st.plotly_chart(expense_chart, use_container_width=True)

        st.divider()

        # ---------------------------
        # Raw Data Section
        # ---------------------------
        with st.expander("📄 View Raw Data"):
            st.write("### Daily Usage Data")
            st.dataframe(daily)
            st.write("### Expense Data")
            st.dataframe(expenses)

        st.caption("📘 Tip: Use sidebar to add more data or refresh dashboard.")
