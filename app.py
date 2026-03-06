from __future__ import annotations

import streamlit as st

st.set_page_config(page_title="BUX Portfolio Dashboard", layout="wide")

pg = st.navigation(
    [
        st.Page("home_page.py", title="Home", icon=":material/home:", default=True),
        st.Page("pages/1_Overview.py", title="Overview", icon=":material/dashboard:"),
        st.Page("pages/2_Asset_Drilldown.py", title="Asset Drilldown", icon=":material/insights:"),
        st.Page("pages/3_Cashflows_And_Costs.py", title="Cashflows And Costs", icon=":material/payments:"),
        st.Page("pages/4_Forecast_And_Regression.py", title="Forecast And Regression", icon=":material/trending_up:"),
        st.Page("pages/5_Mapping_And_QA.py", title="Mapping And QA", icon=":material/verified:"),
        st.Page("pages/6_Transactions_Explorer.py", title="Transactions Explorer", icon=":material/table_view:"),
        st.Page("pages/7_Reconciliation.py", title="Reconciliation", icon=":material/balance:"),
        st.Page("pages/8_Realized_Leaderboard.py", title="Realized Leaderboard", icon=":material/leaderboard:"),
    ],
    position="sidebar",
)

pg.run()
