from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from auth import login_form, logout
from database import (
    init_db, get_users, get_user_by_rfid, add_usage_log, get_usage_logs,
    get_active_rates, replace_rates, add_user, update_user, delete_user,
    save_bill, get_bills, get_user_by_id
)
from utils import (
    calculate_bill, daily_usage_dataframe, monthly_usage_dataframe,
    detect_abnormal_usage, predict_next_7_days, generate_recommendations,
    dataframe_to_csv_bytes, create_bill_pdf, serialize_breakdown,
    deserialize_breakdown
)


st.set_page_config(
    page_title="Smart Water Monitoring & Billing System",
    page_icon="💧",
    layout="wide"
)


def apply_theme():
    dark_mode = st.session_state.get("dark_mode", False)
    if dark_mode:
        st.markdown("""
        <style>
            .stApp { background-color: #0e1117; color: #fafafa; }
            .block-container {
                padding-top: 3rem;
                padding-bottom: 1rem;
                    }
            [data-testid="stSidebar"] { background-color: #111827; }
            .metric-card {
                padding: 1rem; border-radius: 16px; background: #1f2937; color: white; 
                box-shadow: 0 4px 18px rgba(0,0,0,0.2); margin-bottom: 1rem;
            }
        </style>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <style>
            .block-container { padding-top: 1rem; }
            .metric-card {
                padding: 1rem; border-radius: 16px; background: #f8fafc; color: #111827; 
                box-shadow: 0 4px 18px rgba(0,0,0,0.08); margin-bottom: 1rem;
            }
        </style>
        """, unsafe_allow_html=True)


def init_session():
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False
    if "current_user" not in st.session_state:
        st.session_state["current_user"] = None
    if "dark_mode" not in st.session_state:
        st.session_state["dark_mode"] = False


def sidebar():
    with st.sidebar:
        st.title("💧 Smart Water App")
        st.caption("RFID-based Water Monitoring & Billing")

        st.toggle("Dark Mode", key="dark_mode")
        apply_theme()

        if st.session_state["logged_in"]:
            user = st.session_state["current_user"]
            st.success(f"Logged in as {user['name']} ({user['role'].title()})")
            if st.button("Logout"):
                logout()
                st.rerun()

            pages = ["Home", "User Dashboard", "Billing", "Analytics"]
            if user["role"] == "admin":
                pages.insert(3, "Admin Panel")
            return st.radio("Navigate", pages, index=0)

        st.info("Demo credentials:\n- Admin: admin / admin123\n- User: shreya / user123")
        return None


def show_home():
    st.title("RFID-Based Smart Water Supply Monitoring & Billing System")
    st.write(
        "A production-style Streamlit application that simulates an IoT-enabled water distribution network. "
        "Users authenticate via RFID, consume water, track usage, detect anomalies, and receive slab-based dynamic billing."
    )

    c1, c2, c3, c4 = st.columns(4)
    all_logs = get_usage_logs()
    all_users = get_users()
    total_usage = round(sum(log["usage_liters"] for log in all_logs), 2)
    active_users = len([u for u in all_users if u["role"] == "user"])
    total_records = len(all_logs)
    avg_usage = round(total_usage / active_users, 2) if active_users else 0

    c1.metric("Total Usage Logged", f"{total_usage} L")
    c2.metric("Registered Users", active_users)
    c3.metric("Usage Records", total_records)
    c4.metric("Avg Usage / User", f"{avg_usage} L")

    st.markdown("### System Highlights")
    st.markdown("""
    - RFID authentication simulation with profile lookup  
    - Daily, weekly, and monthly water usage tracking  
    - Smart slab billing with downloadable PDF and CSV bills  
    - Admin controls for users, RFID assignment, and rates  
    - Alerts for overconsumption and abnormal usage  
    - Simple machine learning forecast for the next 7 days  
    - Future-ready for QR and IoT device integration
    """)

    st.markdown("### Future IoT Integration Scope")
    st.info(
        "In a real deployment, this app can connect to flow sensors, smart valves, LoRa/Wi-Fi gateways, "
        "and cloud APIs for live telemetry, automated shutoff, remote maintenance, and smart city dashboards."
    )


def show_user_dashboard():
    st.title("User Dashboard")

    current_user = st.session_state["current_user"]
    all_rfids = [u["rfid_id"] for u in get_users() if u["role"] == "user"]
    input_mode = st.radio("RFID Scan Input Mode", ["Dropdown", "Manual Entry"], horizontal=True)

    if input_mode == "Dropdown":
        selected_rfid = st.selectbox("Select RFID", options=all_rfids, index=0 if current_user["rfid_id"] in all_rfids else None)
    else:
        selected_rfid = st.text_input("Enter RFID ID", value=current_user["rfid_id"])

    if selected_rfid:
        user = get_user_by_rfid(selected_rfid.strip())
        if user:
            st.success("RFID authenticated successfully.")
            c1, c2, c3 = st.columns(3)
            c1.info(f"**Name:** {user['name']}")
            c2.info(f"**Household:** {user['household']}")
            c3.info(f"**Connection ID:** {user['connection_id']}")

            with st.form("usage_form"):
                usage = st.number_input("Enter water usage (liters)", min_value=0.0, step=1.0)
                source = st.selectbox("Source", ["RFID Valve", "QR Access", "Manual Meter Entry"])
                submit_usage = st.form_submit_button("Log Water Usage")

            if submit_usage:
                add_usage_log(user["id"], usage, source=source)
                st.success(f"{usage} liters logged for {user['name']}.")
                st.rerun()

            logs = get_usage_logs(user_id=user["id"], start_date=(datetime.now() - timedelta(days=90)).date().isoformat())
            daily_df = daily_usage_dataframe(logs)
            monthly_df = monthly_usage_dataframe(logs)

            col1, col2, col3 = st.columns(3)
            month_key = datetime.now().strftime("%Y-%m")
            current_month_usage = monthly_df[monthly_df["month"] == month_key]["usage_liters"].sum() if not monthly_df.empty else 0
            col1.metric("Last 90 Days Usage", f"{round(daily_df['usage_liters'].sum(), 2) if not daily_df.empty else 0} L")
            col2.metric("Current Month Usage", f"{round(current_month_usage, 2)} L")
            col3.metric("Threshold", f"{user['threshold_liters']} L")

            if current_month_usage > user["threshold_liters"]:
                st.warning("Threshold exceeded. Simulated SMS/Email alert would be triggered here.")

            abnormal = detect_abnormal_usage(daily_df)
            if abnormal["is_abnormal"]:
                st.error("Leak Detection Alert: " + abnormal["message"])
            else:
                st.success(abnormal["message"])

            if not daily_df.empty:
                fig = px.line(daily_df, x="date", y="usage_liters", title="Daily Water Consumption Trend", markers=True)
                st.plotly_chart(fig, use_container_width=True)

            forecast_df = predict_next_7_days(daily_df)
            if not forecast_df.empty:
                forecast_fig = px.bar(forecast_df, x="date", y="predicted_usage_liters", title="Predicted Water Usage for Next 7 Days")
                st.plotly_chart(forecast_fig, use_container_width=True)

                recs = generate_recommendations(current_month_usage, forecast_df["predicted_usage_liters"].mean(), user["threshold_liters"])
                st.markdown("### Water-Saving Recommendations")
                for rec in recs:
                    st.write(f"- {rec}")

            if logs:
                st.markdown("### Recent Usage Logs")
                st.dataframe(pd.DataFrame(logs).head(20), use_container_width=True)
        else:
            st.error("RFID not found. Please check the RFID ID or ask admin to assign it.")


def show_billing():
    st.title("Billing")

    current_user = st.session_state["current_user"]
    users = [u for u in get_users() if u["role"] == "user"]

    if current_user["role"] == "admin":
        selected_user_name = st.selectbox("Select user", options=[u["name"] for u in users])
        selected_user = next(u for u in users if u["name"] == selected_user_name)
    else:
        selected_user = current_user

    period = st.selectbox(
        "Billing Period (Month)",
        options=sorted(list(set([
            datetime.fromisoformat(log["logged_at"]).strftime("%Y-%m")
            for log in get_usage_logs(user_id=selected_user["id"])
        ])), reverse=True)
    )

    period_logs = [
        log for log in get_usage_logs(user_id=selected_user["id"])
        if datetime.fromisoformat(log["logged_at"]).strftime("%Y-%m") == period
    ]

    total_liters = round(sum(log["usage_liters"] for log in period_logs), 2)
    total_amount, breakdown = calculate_bill(total_liters)

    c1, c2 = st.columns(2)
    c1.metric("Total Water Used", f"{total_liters} L")
    c2.metric("Bill Amount", f"₹{total_amount}")

    st.markdown("### Bill Breakdown")
    breakdown_df = pd.DataFrame(breakdown)
    st.dataframe(breakdown_df, use_container_width=True)

    if st.button("Generate / Save Bill"):
        bill_id = save_bill(selected_user["id"], period, total_liters, total_amount, serialize_breakdown(breakdown))
        st.success(f"Bill saved successfully. Bill ID: {bill_id}")

    csv_df = pd.DataFrame(period_logs) if period_logs else pd.DataFrame(columns=["logged_at", "usage_liters", "source"])
    st.download_button(
        label="Download Usage CSV",
        data=dataframe_to_csv_bytes(csv_df),
        file_name=f"{selected_user['connection_id']}_{period}_usage.csv",
        mime="text/csv"
    )

    pdf_bytes = create_bill_pdf(selected_user, period, total_liters, breakdown, total_amount)
    st.download_button(
        label="Download Bill PDF",
        data=pdf_bytes,
        file_name=f"{selected_user['connection_id']}_{period}_bill.pdf",
        mime="application/pdf"
    )

    st.markdown("### Saved Bills")
    bills = get_bills(user_id=None if current_user["role"] == "admin" else current_user["id"])
    if bills:
        bill_view = []
        for bill in bills:
            if current_user["role"] != "admin" and bill["user_id"] != current_user["id"]:
                continue
            bill_view.append({
                "Name": bill["name"],
                "Connection ID": bill["connection_id"],
                "Period": bill["period_month"],
                "Liters": bill["total_liters"],
                "Amount (₹)": bill["total_amount"],
                "Generated At": bill["generated_at"],
            })
        if bill_view:
            st.dataframe(pd.DataFrame(bill_view), use_container_width=True)


def show_admin_panel():
    st.title("Admin Panel")
    st.caption("Manage users, RFID assignments, billing slabs, and system-wide usage.")

    tab1, tab2, tab3 = st.tabs(["User Management", "Billing Rates", "System Monitoring"])

    with tab1:
        users = get_users()
        st.dataframe(pd.DataFrame(users), use_container_width=True)

        st.markdown("#### Add User")
        with st.form("add_user_form"):
            c1, c2 = st.columns(2)
            name = c1.text_input("Name")
            household = c2.text_input("Household")
            c3, c4 = st.columns(2)
            connection_id = c3.text_input("Connection ID")
            rfid_id = c4.text_input("RFID ID")
            c5, c6 = st.columns(2)
            username = c5.text_input("Username")
            password = c6.text_input("Password", type="password")
            c7, c8 = st.columns(2)
            role = c7.selectbox("Role", ["user", "admin"])
            threshold_liters = c8.number_input("Threshold (L)", min_value=50.0, value=500.0, step=10.0)
            add_submit = st.form_submit_button("Add User")
        if add_submit:
            try:
                add_user(name, household, connection_id, rfid_id, role, username, password, threshold_liters)
                st.success("User added successfully.")
                st.rerun()
            except Exception as e:
                st.error(f"Could not add user: {e}")

        st.markdown("#### Edit or Delete User")
        editable_users = [u for u in users]
        selected_label = st.selectbox("Select user to edit", options=[f"{u['id']} - {u['name']}" for u in editable_users])
        selected_id = int(selected_label.split(" - ")[0])
        edit_user = next(u for u in editable_users if u["id"] == selected_id)

        with st.form("edit_user_form"):
            e1, e2 = st.columns(2)
            name_e = e1.text_input("Name", value=edit_user["name"])
            household_e = e2.text_input("Household", value=edit_user["household"])
            e3, e4 = st.columns(2)
            connection_id_e = e3.text_input("Connection ID", value=edit_user["connection_id"])
            rfid_id_e = e4.text_input("RFID ID", value=edit_user["rfid_id"])
            e5, e6 = st.columns(2)
            username_e = e5.text_input("Username", value=edit_user["username"])
            password_e = e6.text_input("Password", value=edit_user["password"])
            e7, e8 = st.columns(2)
            role_e = e7.selectbox("Role", ["user", "admin"], index=0 if edit_user["role"] == "user" else 1)
            threshold_e = e8.number_input("Threshold (L)", min_value=50.0, value=float(edit_user["threshold_liters"]), step=10.0)

            col_save, col_delete = st.columns(2)
            save_edit = col_save.form_submit_button("Save Changes")
            delete_btn = col_delete.form_submit_button("Delete User")

        if save_edit:
            try:
                update_user(selected_id, name_e, household_e, connection_id_e, rfid_id_e, role_e, username_e, password_e, threshold_e)
                if st.session_state["current_user"]["id"] == selected_id:
                    st.session_state["current_user"] = get_user_by_id(selected_id)
                st.success("User updated.")
                st.rerun()
            except Exception as e:
                st.error(f"Update failed: {e}")

        if delete_btn:
            if st.session_state["current_user"]["id"] == selected_id:
                st.error("You cannot delete the currently logged-in user.")
            else:
                try:
                    delete_user(selected_id)
                    st.success("User deleted.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Delete failed: {e}")

    with tab2:
        current_rates = get_active_rates()
        st.dataframe(pd.DataFrame(current_rates), use_container_width=True)
        st.markdown("#### Update Billing Slabs")

        with st.form("rates_form"):
            r1, r2, r3 = st.columns(3)
            slab1_end = r1.number_input("Slab 1 End", min_value=1.0, value=100.0, step=1.0)
            slab1_rate = r2.number_input("Slab 1 Rate", min_value=0.1, value=2.0, step=0.1)
            slab2_end = r3.number_input("Slab 2 End", min_value=slab1_end + 1, value=500.0, step=1.0)

            r4, r5 = st.columns(2)
            slab2_rate = r4.number_input("Slab 2 Rate", min_value=0.1, value=5.0, step=0.1)
            slab3_rate = r5.number_input("Slab 3 Rate", min_value=0.1, value=10.0, step=0.1)

            save_rates = st.form_submit_button("Save Billing Rates")

        if save_rates:
            new_rates = [
                {"slab_start": 0, "slab_end": slab1_end, "rate_per_liter": slab1_rate},
                {"slab_start": slab1_end, "slab_end": slab2_end, "rate_per_liter": slab2_rate},
                {"slab_start": slab2_end, "slab_end": None, "rate_per_liter": slab3_rate},
            ]
            replace_rates(new_rates)
            st.success("Billing rates updated successfully.")
            st.rerun()

    with tab3:
        logs = get_usage_logs(start_date=(datetime.now() - timedelta(days=30)).date().isoformat())
        logs_df = pd.DataFrame(logs)
        if not logs_df.empty:
            logs_df["logged_at"] = pd.to_datetime(logs_df["logged_at"])
            usage_by_user = logs_df.groupby("name")["usage_liters"].sum().reset_index().sort_values("usage_liters", ascending=False)

            c1, c2 = st.columns(2)
            c1.metric("Last 30 Days Total Usage", f"{round(logs_df['usage_liters'].sum(), 2)} L")
            c2.metric("Highest Usage User", usage_by_user.iloc[0]["name"] if not usage_by_user.empty else "-")

            fig = px.bar(usage_by_user, x="name", y="usage_liters", title="User-wise Water Usage (Last 30 Days)")
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(logs_df.sort_values("logged_at", ascending=False), use_container_width=True)
        else:
            st.info("No logs available yet.")


def show_analytics():
    st.title("Analytics")

    logs = get_usage_logs(start_date=(datetime.now() - timedelta(days=120)).date().isoformat())
    if not logs:
        st.info("No usage data available.")
        return

    df = pd.DataFrame(logs)
    df["logged_at"] = pd.to_datetime(df["logged_at"])
    df["date"] = df["logged_at"].dt.date
    df["month"] = df["logged_at"].dt.to_period("M").astype(str)

    daily_overall = df.groupby("date")["usage_liters"].sum().reset_index()
    monthly_overall = df.groupby("month")["usage_liters"].sum().reset_index()
    user_usage = df.groupby("name")["usage_liters"].sum().reset_index().sort_values("usage_liters", ascending=False)

    c1, c2, c3 = st.columns(3)
    c1.metric("120-Day Total Usage", f"{round(df['usage_liters'].sum(),2)} L")
    c2.metric("Avg Daily Usage", f"{round(daily_overall['usage_liters'].mean(),2)} L")
    c3.metric("Top Consumer", user_usage.iloc[0]['name'])

    line_fig = px.line(daily_overall, x="date", y="usage_liters", title="Daily Consumption Trend", markers=True)
    st.plotly_chart(line_fig, use_container_width=True)

    bar_fig = px.bar(monthly_overall, x="month", y="usage_liters", title="Monthly Consumption Trend")
    st.plotly_chart(bar_fig, use_container_width=True)

    pie_fig = px.pie(user_usage, names="name", values="usage_liters", title="Consumption Share by User")
    st.plotly_chart(pie_fig, use_container_width=True)

    st.markdown("### Highest Usage Users")
    st.dataframe(user_usage, use_container_width=True)

    st.markdown("### Water Conservation Insights")
    avg_user_usage = user_usage["usage_liters"].mean()
    low_users = user_usage[user_usage["usage_liters"] < avg_user_usage]["name"].tolist()
    high_users = user_usage[user_usage["usage_liters"] > avg_user_usage]["name"].tolist()

    st.write(f"- Users above average consumption: {', '.join(high_users) if high_users else 'None'}")
    st.write(f"- Users below average consumption: {', '.join(low_users) if low_users else 'None'}")
    st.write("- Encourage staggered usage, leak audits, and smart storage tank monitoring.")
    st.write("- Peak use analysis can later be integrated with IoT time-series sensors for distribution optimization.")

    report_csv = dataframe_to_csv_bytes(user_usage)
    st.download_button("Export Analytics Report CSV", data=report_csv, file_name="analytics_report.csv", mime="text/csv")


def main():
    init_db()
    init_session()
    page = sidebar()

    if not st.session_state["logged_in"]:
        login_form()
        return

    if page == "Home":
        show_home()
    elif page == "User Dashboard":
        show_user_dashboard()
    elif page == "Billing":
        show_billing()
    elif page == "Admin Panel":
        show_admin_panel()
    elif page == "Analytics":
        show_analytics()


if __name__ == "__main__":
    main()
