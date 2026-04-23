"""
main.py
-------
Streamlit Agility Sprint Dashboard.

All data is fetched directly from Agility VersionOne using the same
AgilityClient used by the original FastAPI backend.

Run with:
    streamlit run main.py
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import logging
import sys
import time
from datetime import date

import datetime as _dt
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# Force UTF-8 output on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from agility_client import AgilityClient
from auth_browser import browser_login, load_saved_session, clear_session, manual_cookie_login
from config import TEAM_ROOM_OID, AGILITY_BASE_URL, ART_TEAM_MAP
from models import TeamModel

logging.basicConfig(level=logging.WARNING)

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="FedEx Agility Dashboard",
    page_icon="📦",
    layout="wide",
)

# ── FedEx + Accenture light theme CSS ─────────────────────────────────────────
st.markdown("""
<style>
  /* Hide Streamlit default chrome */
  #MainMenu { visibility: hidden; }
  footer    { visibility: hidden; }
  header    { visibility: hidden; }

  /* FedEx + Accenture Header Banner */
  .fedex-header {
    background: linear-gradient(135deg, #4D148C 0%, #FF6200 100%);
    padding: 20px 40px;
    margin: -5rem -5rem 1rem -5rem;
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    border-bottom: 4px solid #FF6200;
    position: relative;
  }
  .fedex-header-content {
    display: flex;
    align-items: center;
    justify-content: center;
    max-width: 1400px;
    margin: 0 auto;
    position: relative;
    min-height: 44px;
  }
  .fedex-title {
    color: #FFFFFF !important;
    font-size: 32px;
    font-weight: 700;
    margin: 0;
    text-align: center;
    letter-spacing: 0.5px;
    text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
  }
  
  /* Sign Out Button inside Header */
  .signout-btn {
    position: absolute;
    right: 0;
    top: 50%;
    transform: translateY(-50%);
    background: rgba(255,255,255,0.95);
    color: #4D148C !important;
    text-decoration: none !important;
    font-size: 19px;
    font-weight: 600;
    padding: 8px 20px;
    border-radius: 8px;
    border: 2px solid rgba(255,255,255,0.8);
    cursor: pointer;
    
    white-space: nowrap;
  }
  .signout-btn:hover {
    background: #FFFFFF;
    border-color: #FFFFFF;
    box-shadow: 0 4px 12px rgba(0,0,0,0.25);
    text-decoration: none;
    color: #4D148C !important;
  }

  /* Light background */
  .stApp { background-color: #F8F8F8; color: #333333; }

  /* Metric cards with purple accent */
  [data-testid="stMetric"] {
    background: linear-gradient(135deg, #FFFFFF 0%, #FAFAFA 100%);
    border: 2px solid #E8E8E8;
    border-radius: 12px;
    padding: 18px 22px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06);
  }
  [data-testid="stMetricLabel"] { 
    color: #663399 !important; 
    font-size: 13px; 
    text-transform: uppercase; 
    letter-spacing: .08em;
    font-weight: 600;
  }
  [data-testid="stMetricValue"] { 
    color: #333333 !important;
    font-weight: 700;
  }

  /* Divider */
  hr { border-color: #E8E8E8; margin: 2rem 0; }

  /* Tab labels with purple theme and animations */
  .stTabs [data-baseweb="tab-list"] {
    gap: 8px;
    background-color: transparent;
  }
  .stTabs [data-baseweb="tab"] { 
    background: linear-gradient(135deg, #FFFFFF 0%, #F8F8F8 100%);
    border: 2px solid #E8E8E8;
    border-radius: 10px;
    color: #666666;
    font-weight: 500;
    padding: 10px 20px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.04);
  }
  .stTabs [data-baseweb="tab"]:hover { 
    background: linear-gradient(135deg, #FFFFFF 0%, #F0E6FF 100%);
    border-color: #663399;
  }
  .stTabs [aria-selected="true"] { 
    background: linear-gradient(135deg, #663399 0%, #552288 100%) !important;
    color: #FFFFFF !important;
    border-color: #663399 !important;
    font-weight: 600;
    box-shadow: 0 4px 12px rgba(102,51,153,0.3) !important;
  }

  /* Inputs with cleaner style and animations */
  .stTextInput input, .stDateInput input {
    background: #FFFFFF !important;
    border: 2px solid #E8E8E8 !important;
    color: #333333 !important;
    border-radius: 10px !important;
    padding: 10px 14px !important;
    font-size: 15px !important;
    line-height: 1.5 !important;
    min-height: 44px !important;
  }
  .stTextInput input:hover, .stDateInput input:hover {
    border-color: #B39DDB !important;
  }
  .stTextInput input:focus, .stDateInput input:focus {
    border-color: #663399 !important;
    box-shadow: 0 0 0 3px rgba(102,51,153,0.1) !important;
    outline: none !important;
  }

  /* Selectbox/Dropdown styling with modern design */
  .stSelectbox [data-baseweb="select"] {
    background: #FFFFFF !important;
    border: 2px solid #E8E8E8 !important;
    border-radius: 10px !important;
    box-shadow: 0 2px 4px rgba(0,0,0,0.04) !important;
    min-height: 44px !important;
  }
  .stSelectbox [data-baseweb="select"]:hover {
    border-color: #B39DDB !important;
  }
  .stSelectbox [data-baseweb="select"]:focus-within {
    border-color: #663399 !important;
    box-shadow: 0 0 0 3px rgba(102,51,153,0.15) !important;
  }
  .stSelectbox [data-baseweb="select"] > div {
    padding: 10px 14px !important;
    font-size: 15px !important;
    color: #333333 !important;
    line-height: 1.5 !important;
    display: flex !important;
    align-items: center !important;
  }
  /* Fix for selected value display - target Streamlit's dynamic classes */
  .stSelectbox div[data-baseweb="select"] div[class*="st-"],
  .stSelectbox div[data-baseweb="select"] span,
  .stSelectbox div[data-baseweb="select"] input {
    color: #333333 !important;
    opacity: 1 !important;
    font-size: 15px !important;
    line-height: 1.5 !important;
  }
  /* Fix .st-ar class that's hiding dropdown values */
  .st-ar {
    color: #333333 !important;
    overflow: visible !important;
    text-overflow: clip !important;
    white-space: normal !important;
    font-size: 15px !important;
  }
  .stSelectbox .st-ar {
    color: #333333 !important;
    overflow: visible !important;
    font-size: 15px !important;
    display: flex !important;
    align-items: center !important;
  }
  /* Dropdown menu */
  [data-baseweb="popover"] {
    border-radius: 10px !important;
    box-shadow: 0 8px 24px rgba(0,0,0,0.15) !important;
    border: 1px solid #E8E8E8 !important;
  }
  [role="option"] {
    padding: 12px 16px !important;
    font-size: 15px !important;
    line-height: 1.5 !important;
  }
  [role="option"]:hover {
    background: linear-gradient(90deg, #F0E6FF 0%, #FAFAFA 100%) !important;
    color: #663399 !important;
  }
  [aria-selected="true"][role="option"] {
    background: linear-gradient(90deg, #663399 0%, #552288 100%) !important;
    color: #FFFFFF !important;
    font-weight: 600 !important;
  }

  /* Multiselect styling */
  .stMultiSelect [data-baseweb="select"] {
    background: #FFFFFF !important;
    border: 2px solid #E8E8E8 !important;
    border-radius: 10px !important;
    box-shadow: 0 2px 4px rgba(0,0,0,0.04) !important;
    min-height: 44px !important;
  }
  .stMultiSelect [data-baseweb="select"]:hover {
    border-color: #B39DDB !important;
  }
  .stMultiSelect [data-baseweb="select"]:focus-within {
    border-color: #663399 !important;
    box-shadow: 0 0 0 3px rgba(102,51,153,0.15) !important;
  }
  .stMultiSelect [data-baseweb="tag"] {
    background: linear-gradient(135deg, #663399 0%, #552288 100%) !important;
    color: #FFFFFF !important;
    border-radius: 6px !important;
    font-size: 13px !important;
    padding: 4px 10px !important;
    margin: 2px !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
    max-width: 100% !important;
  }
  .stMultiSelect [data-baseweb="tag"] span {
    color: #FFFFFF !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
  }
  /* Multiselect close button */
  .stMultiSelect [data-baseweb="tag"] svg {
    fill: #FFFFFF !important;
  }
  /* Prevent team names from breaking in dropdown */
  .stMultiSelect [role="option"] {
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
  }

  /* Primary button with purple and enhanced animations */
  .stButton > button {
    border-radius: 10px !important;
    padding: 10px 24px !important;
    font-weight: 600 !important;
    font-size: 14px !important;
    border: none !important;
  }
  .stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #663399 0%, #552288 100%) !important;
    color: #FFFFFF !important;
    box-shadow: 0 4px 12px rgba(102,51,153,0.25) !important;
  }
  .stButton > button[kind="primary"]:hover { 
    background: linear-gradient(135deg, #552288 0%, #441177 100%) !important;
    box-shadow: 0 6px 16px rgba(102,51,153,0.4) !important;
  }
  .stButton > button[kind="secondary"] {
    background: #FFFFFF !important;
    color: #663399 !important;
    border: 2px solid #663399 !important;
    box-shadow: 0 2px 6px rgba(0,0,0,0.06) !important;
  }
  .stButton > button[kind="secondary"]:hover {
    background: linear-gradient(135deg, #F0E6FF 0%, #FFFFFF 100%) !important;
    box-shadow: 0 4px 12px rgba(102,51,153,0.2) !important;
  }

  /* Dataframe header with purple theme */
  [data-testid="stDataFrame"] {
    border-radius: 10px;
    overflow: hidden;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06);
  }
  [data-testid="stDataFrame"] thead th {
    background: linear-gradient(135deg, #663399 0%, #552288 100%) !important;
    color: #FFFFFF !important;
    font-weight: 600;
    padding: 14px 16px !important;
    text-transform: uppercase;
    font-size: 12px;
    letter-spacing: 0.05em;
  }
  [data-testid="stDataFrame"] tbody tr:hover {
    background-color: rgba(102,51,153,0.05) !important;
  }
  
  /* Chart containers */
  [data-testid="stPlotlyChart"] {
    background: #FFFFFF;
    border: 1px solid #E8E8E8;
    border-radius: 12px;
    padding: 12px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06);
  }
  
  /* Info/Success/Warning boxes */
  .stAlert {
    border-radius: 10px !important;
    border-left: 4px solid #663399 !important;
  }
  
  /* Spinner */
  .stSpinner > div {
    border-top-color: #663399 !important;
  }
</style>
""", unsafe_allow_html=True)

# ── Cache TTL (seconds) ────────────────────────────────────────────────────────
_CACHE_TTL = 300

# ── Session state defaults ─────────────────────────────────────────────────────
if "cookies" not in st.session_state:
    st.session_state.cookies = load_saved_session()

for _key in ("teams_cache", "summary_cache", "counts_cache"):
    if _key not in st.session_state:
        st.session_state[_key] = {}

if "show_dashboard" not in st.session_state:
    st.session_state.show_dashboard = bool(st.session_state.cookies)


# ── Async runner ───────────────────────────────────────────────────────────────
def run_async(coro):
    """Run an async coroutine safely from a synchronous Streamlit context."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, coro).result()
    return asyncio.run(coro)


# ── Cache helpers ──────────────────────────────────────────────────────────────
def _cache_get(store_key: str, key):
    e = st.session_state[store_key].get(key)
    return e["data"] if e and time.time() - e["ts"] < _CACHE_TTL else None


def _cache_set(store_key: str, key, data) -> None:
    st.session_state[store_key][key] = {"ts": time.time(), "data": data}


# ── Async data fetchers ────────────────────────────────────────────────────────
async def _async_get_teams(cookies, team_room_oid: str):
    cached = _cache_get("teams_cache", team_room_oid)
    if cached is not None:
        return cached
    client = AgilityClient.from_cookies(cookies)
    async with client:
        teams = await client.get_teams_for_team_room(team_room_oid)
    _cache_set("teams_cache", team_room_oid, teams)
    return teams


async def _async_get_summary(cookies, team_oid: str, team_name: str, year: int | None):
    key = (team_oid, year)
    cached = _cache_get("summary_cache", key)
    if cached is not None:
        return cached
    client = AgilityClient.from_cookies(cookies)
    async with client:
        team = TeamModel(oid=team_oid, name=team_name)
        stories = await client.get_all_stories_for_team(team_oid, year=year)
        sprints = await client.get_sprints_from_stories(team_oid, stories, year=year)
        summary = await client.build_team_sprint_summary(team, sprints, stories)
    _cache_set("summary_cache", key, summary)
    return summary


async def _async_get_counts(cookies, teams: list, date_from: str = None, date_to: str = None):
    """Fetch committed/completed counts for a list of teams in parallel.
    date_from / date_to are ISO date strings (YYYY-MM-DD).  Defaults to current year.
    """
    cache_key_suffix = (date_from, date_to)
    uncached = [t for t in teams if _cache_get("counts_cache", (t.oid, cache_key_suffix)) is None]

    if uncached:
        client = AgilityClient.from_cookies(cookies)
        async with client:
            counts_list = await asyncio.gather(
                *[client.get_story_counts_for_team(t.oid, date_from=date_from, date_to=date_to)
                  for t in uncached],
                return_exceptions=True,
            )
        for team, counts in zip(uncached, counts_list):
            if not isinstance(counts, Exception):
                _cache_set("counts_cache", (team.oid, cache_key_suffix), counts)

    return {t.oid: _cache_get("counts_cache", (t.oid, cache_key_suffix)) for t in teams}


# ── UI helpers ─────────────────────────────────────────────────────────────────
def short_team_name(full_name: str) -> str:
    if not full_name:
        return full_name
    parts = full_name.split(" - ")
    return " - ".join(parts[3:]).strip() if len(parts) > 3 else parts[-1].strip()


def short_art_name(art_name: str) -> str:
    if not art_name:
        return art_name
    return art_name.split(" - ")[-1].strip()


_CHART_LAYOUT = dict(
    paper_bgcolor="#FFFFFF",
    plot_bgcolor="#FFFFFF",
    font=dict(color="#333333", family="Inter, sans-serif", size=12),
    margin=dict(l=50, r=20, t=60, b=80),
    xaxis=dict(gridcolor="#E8E8E8", tickangle=-30, showline=False),
    yaxis=dict(gridcolor="#E8E8E8", showline=False, 
               rangemode='tozero', zeroline=True, zerolinecolor="#333333", zerolinewidth=2),
    legend=dict(orientation="h", y=1.15, x=0.5, xanchor="center", bgcolor="rgba(255,255,255,0.9)",
                bordercolor="#E8E8E8", borderwidth=1, font=dict(size=11)),
    barmode="group",
)

# Title styling to be applied to all charts
_CHART_TITLE_STYLE = dict(
    font=dict(size=16, color="#663399", weight="bold"),
    x=0,
    xanchor="left",
)


# ══════════════════════════════════════════════════════════════════════════════
# LOGIN PAGE
# ══════════════════════════════════════════════════════════════════════════════
def show_login() -> None:
    import platform
    is_cloud = platform.system() == "Linux"

    _, col, _ = st.columns([1, 1.4, 1])
    with col:
        st.markdown(
            """
            <div style='text-align:center;padding:40px 0 24px;'>
              <div style='font-size:52px;'>📦</div>
              <h1 style='margin:0;font-size:26px;color:#663399;'>FedEx Agility Dashboard</h1>
              <p style='color:#666666;font-size:14px;margin-top:8px;'>
                Sign in to access the dashboard.
              </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if st.session_state.cookies:
            st.success("✅ Existing session found")
            if st.button("Go to Dashboard →", use_container_width=True, type="primary"):
                st.session_state.show_dashboard = True
                st.rerun()
            st.markdown(
                "<div style='text-align:center;color:#666666;font-size:13px;margin:12px 0;'>— or sign in again below —</div>",
                unsafe_allow_html=True,
            )

        # On Streamlit Cloud (Linux) show cookie tab first; on Windows show browser tab first
        if is_cloud:
            tab_cookie, tab_browser = st.tabs(["🔑 Paste Session Cookie (Cloud)", "🌐 Browser Login (Windows only)"])
        else:
            tab_browser, tab_cookie = st.tabs(["🌐 Browser Login (Windows)", "🔑 Paste Session Cookie (Cloud)"])

        # ── Browser login tab (Windows / local) ──────────────────────────────
        with tab_browser:
            if is_cloud:
                st.warning(
                    "Browser login is not supported on Streamlit Cloud. "
                    "Please use the **Paste Session Cookie** tab instead."
                )
            else:
                st.caption(
                    "Opens a local Edge/Chrome window. Complete the MFA push — "
                    "the window closes automatically."
                )
                username = st.text_input(
                    "USERNAME / EMPLOYEE ID",
                    placeholder="e.g. 123456 or abc.xyz@fedex.com",
                    key="browser_username",
                )
                password = st.text_input(
                    "PASSWORD",
                    type="password",
                    placeholder="Your FedEx / OKTA password",
                    key="browser_password",
                )
                if st.button("🔐  Sign in with OKTA", use_container_width=True, type="primary", key="btn_browser"):
                    if not username or not password:
                        st.error("Please enter both username and password.")
                    else:
                        with st.spinner("Opening browser for OKTA login — complete any MFA step…"):
                            try:
                                cookies = browser_login(AGILITY_BASE_URL, username, password)
                                st.session_state.cookies = cookies
                                st.session_state.show_dashboard = True
                                st.success("Login successful!")
                                st.rerun()
                            except ImportError as exc:
                                st.error(f"Missing dependency: {exc}")
                            except Exception as exc:
                                st.error(f"Login failed: {exc}")

        # ── Paste session cookie tab (Cloud / any browser) ───────────────────
        with tab_cookie:
            st.markdown(
                """
**How to copy ALL cookies in 3 steps:**

1. Open **[Agility](https://www19.v1host.com/FedEx)** in your browser and sign in with OKTA.
2. Press **F12** → **Network** tab → refresh the page → click any request to `www19.v1host.com` → **Headers** → find the **`Cookie:`** request header → copy the entire value.
3. Paste the full string below and click **Connect**.

> **Alternatively** (Application tab method): F12 → Application → Cookies → `https://www19.v1host.com` → for each of the 4 cookies (`V1.FederatedAuth.FedEx`, `V1.OidcAccessToken.FedEx`, `V1.OidcRefreshToken.FedEx`, `V1.Ticket.FedEx`) copy name=value and join with `;`
                """
            )
            cookie_string = st.text_area(
                "PASTE FULL COOKIE STRING",
                placeholder="V1.FederatedAuth.FedEx=abc123; V1.OidcAccessToken.FedEx=xyz...; V1.Ticket.FedEx=def...",
                height=120,
                key="manual_cookie_string",
            )
            if st.button("🔑  Connect", use_container_width=True, type="primary", key="btn_cookie"):
                if not cookie_string or not cookie_string.strip():
                    st.error("Please paste the cookie string from DevTools.")
                else:
                    try:
                        cookies = manual_cookie_login(cookie_string, AGILITY_BASE_URL)
                        st.session_state.cookies = cookies
                        st.session_state.show_dashboard = True
                        st.success(f"Session accepted ({len(cookies)} cookies loaded)! Loading dashboard…")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Failed to set session: {exc}")


# ══════════════════════════════════════════════════════════════════════════════
# DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
def show_dashboard() -> None:
    cookies = st.session_state.cookies
    if not cookies:
        st.error("No active session. Please log in.")
        st.session_state.show_dashboard = False
        st.rerun()
        return

    # ── Handle sign-out via query param ─────────────────────────────────────
    if st.query_params.get("signout") == "1":
        st.session_state.cookies = None
        clear_session()
        st.session_state.show_dashboard = False
        st.query_params.clear()
        st.rerun()
        return

    # ── FedEx + Accenture Header ─────────────────────────────────────────────
    st.markdown("""
    <div class="fedex-header">
        <div class="fedex-header-content">
            <h1 class="fedex-title">FedEx Agility Dashboard</h1>
            <a href="?signout=1" class="signout-btn">🔓 Sign out</a>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # ── Top filter bar ────────────────────────────────────────────────────────
    fc1, fc2, fc3, fc4, fc5 = st.columns([2.5, 2.5, 1.5, 1.5, 1])

    with fc1:
        arts = sorted(ART_TEAM_MAP.keys())
        DEFAULT_ART = "SCO - P&D - Run and Close"
        # Find default index, fallback to first ART if default not found
        if DEFAULT_ART in arts:
            default_idx = arts.index(DEFAULT_ART)
        else:
            default_idx = 0 if arts else 0
        
        selected_art = st.selectbox(
            "ART",
            arts,
            index=default_idx,
            key="art_selector",
        )

    teams: list[TeamModel] = []
    if selected_art:
        try:
            all_teams = run_async(_async_get_teams(cookies, TEAM_ROOM_OID))
            art_lower = selected_art.strip().lower()
            teams = [t for t in all_teams if t.art and t.art.lower() == art_lower]
        except Exception as exc:
            st.error(f"Failed to fetch teams: {exc}")
            return

    with fc2:
        if not teams:
            st.multiselect("Teams", ["No teams available"], disabled=True, key="team_selector_disabled")
            selected_teams: list[TeamModel] = []
        else:
            # No default selection - user must select teams
            team_indices = st.multiselect(
                "Teams (Select multiple)",
                options=range(len(teams)),
                format_func=lambda i: short_team_name(teams[i].name),
                default=[],
                key="team_selector",
            )
            selected_teams = [teams[i] for i in team_indices] if team_indices else []

    with fc3:
        date_from: date | None = st.date_input("From", value=None)
    with fc4:
        date_to: date | None = st.date_input("To", value=None)
    with fc5:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        if st.button("🔄 Refresh"):
            for k in ("teams_cache", "summary_cache", "counts_cache"):
                st.session_state[k] = {}
            st.rerun()

    st.divider()

    if not selected_teams:
        st.info("👆 Select one or more teams from the dropdown above to view sprint data and graphs.")
        return

    # ── Load team summaries and aggregate data ────────────────────────────────
    current_year = time.localtime().tm_year
    team_names_str = ", ".join([short_team_name(t.name) for t in selected_teams[:3]])
    if len(selected_teams) > 3:
        team_names_str += f" +{len(selected_teams)-3} more"
    
    with st.spinner(f"Loading sprint data for **{team_names_str}**…"):
        try:
            # Load summaries for all selected teams
            summaries = []
            for team in selected_teams:
                summary = run_async(_async_get_summary(cookies, team.oid, team.name, current_year))
                summaries.append(summary)
        except Exception as exc:
            st.error(f"Failed to load team data: {exc}")
            return

    # ── Aggregate sprints from all selected teams ─────────────────────────────
    all_sprints = []
    for summary in summaries:
        if summary.sprints:
            all_sprints.extend(summary.sprints)
    
    sprints = [s for s in all_sprints if s.total_planned > 0 or s.total_delivered > 0] if all_sprints else []
    sprints.sort(key=lambda s: (s.begin_date or ""))

    if date_from:
        sprints = [s for s in sprints if (s.begin_date or "")[:10] >= str(date_from)]
    if date_to:
        sprints = [s for s in sprints if (s.begin_date or "")[:10] <= str(date_to)]

    # ── Stat cards ────────────────────────────────────────────────────────────
    total_planned   = sum(s.total_planned   for s in sprints)
    total_delivered = sum(s.total_delivered for s in sprints)
    total_pts       = sum(s.planned_points  for s in sprints)
    total_del_pts   = sum(s.delivered_points for s in sprints)
    rate_str        = f"{total_delivered / total_planned * 100:.1f}%" if total_planned else "—"

    c1, c2, c3, c4, c5 = st.columns(5)
    if len(selected_teams) == 1:
        c1.metric("Current Team", short_team_name(selected_teams[0].name))
    else:
        c1.metric("Selected Teams", f"{len(selected_teams)} teams")
    c2.metric("Total Sprints",     len(sprints))
    c3.metric("Planned Stories",   total_planned)
    c4.metric("Delivered Stories", total_delivered)
    c5.metric("Overall Delivery",  rate_str,
              delta=f"{total_del_pts:.1f} / {total_pts:.1f} pts",
              delta_color="off")

    st.divider()

    # Initialize session state for clicked team
    if "clicked_team_for_velocity" not in st.session_state:
        st.session_state.clicked_team_for_velocity = None

    # ── Chart tabs ────────────────────────────────────────────────────────────
    team_tab_label = "👥 Team Performance"
    art_tab_label = "📊 Committed vs Completed by ART"
    if selected_teams:
        if len(selected_teams) > 1:
            team_tab_label = f"👥 Selected Teams Performance ({len(selected_teams)})"
            art_tab_label = f"📊 ART Performance (from {len(selected_teams)} teams)"
        else:
            team_tab_label = f"👥 Team Performance — {short_team_name(selected_teams[0].name)}"
            art_tab_label = f"📊 ART Performance — {short_team_name(selected_teams[0].name)}"
    
    # Conditionally show Sprint Velocity tab only if a team was clicked
    if st.session_state.clicked_team_for_velocity:
        clicked_team_name = short_team_name(st.session_state.clicked_team_for_velocity["name"])
        tab_list = [
            art_tab_label,
            team_tab_label,
            f"📈 Sprint Velocity — {clicked_team_name}",
        ]
        tab1, tab2, tab3 = st.tabs(tab_list)
    else:
        tab_list = [
            art_tab_label,
            team_tab_label,
        ]
        tabs = st.tabs(tab_list)
        tab1, tab2 = tabs[0], tabs[1]
        tab3 = None
    # Effective date bounds for the two ART charts: use UI filter if set,
    # otherwise default to the current calendar year.
    _today = date.today()
    _chart_from = str(date_from) if date_from else f"{_today.year}-01-01"
    _chart_to   = str(date_to)   if date_to   else f"{_today.year}-12-31"
    _chart_label = (
        f"{_chart_from} → {_chart_to}"
        if (date_from or date_to)
        else str(_today.year)
    )

    # ── Tab 1: ART-level performance (filtered by selected teams) ────────────
    with tab1:
        if not selected_teams:
            st.info("Select teams from the dropdown to view ART performance.")
        else:
            with st.spinner("Loading ART performance…"):
                try:
                    # Only get counts for selected teams
                    counts_map = run_async(_async_get_counts(cookies, selected_teams,
                                                              date_from=_chart_from, date_to=_chart_to))
                    art_totals: dict[str, dict] = {}
                    for t in selected_teams:
                        c = counts_map.get(t.oid)
                        if not c:
                            continue
                        entry = art_totals.setdefault(t.art, {"art": t.art, "committed": 0, "completed": 0})
                        entry["committed"] += c["committed"]
                        entry["completed"] += c["completed"]

                    art_data = sorted(art_totals.values(), key=lambda x: x["art"])
                    if art_data:
                        art_labels = [short_art_name(d["art"]) for d in art_data]
                        committed  = [d["committed"] for d in art_data]
                        completed  = [d["completed"] for d in art_data]
                        g_max      = max(max(committed), max(completed), 1)

                        annotations = [
                            dict(
                                x=art_labels[i],
                                y=max(d["committed"], d["completed"]) + g_max * 0.06,
                                text=f"<b>{d['completed'] / d['committed'] * 100:.1f}%</b>" if d["committed"] else "<b>0%</b>",
                                showarrow=False,
                                font=dict(size=12, color="#663399"),
                                bgcolor="rgba(102,51,153,0.08)",
                                bordercolor="#663399", borderwidth=1, borderpad=3,
                                xanchor="center",
                            )
                            for i, d in enumerate(art_data)
                        ]

                        fig_art = go.Figure(data=[
                            go.Bar(name="Committed", x=art_labels, y=committed,
                                   marker_color="#663399", opacity=0.95,
                                   text=committed, textposition="outside", textfont=dict(size=11, color="#333333")),
                            go.Bar(name="Completed",  x=art_labels, y=completed,
                                   marker_color="#00A86B", opacity=0.95,
                                   text=completed, textposition="outside", textfont=dict(size=11, color="#333333")),
                        ])
                        
                        # Build title based on number of teams
                        if len(selected_teams) == 1:
                            art_chart_title = f"Committed vs Completed — {short_team_name(selected_teams[0].name)} — {_chart_label}"
                        else:
                            art_chart_title = f"Committed vs Completed by ART — {len(selected_teams)} Selected Teams — {_chart_label}"
                        
                        fig_art.update_layout(
                            **_CHART_LAYOUT,
                            title=dict(text=art_chart_title, **_CHART_TITLE_STYLE),
                            xaxis_title="ART",
                            yaxis_title="Stories",
                            yaxis_range=[0, g_max * 1.25],
                            annotations=annotations,
                            height=380,
                        )
                        st.plotly_chart(fig_art, use_container_width=True)
                    else:
                        st.info("No performance data available for selected teams.")
                except Exception as exc:
                    st.error(f"Failed to load ART performance: {exc}")

    # ── Tab 2: Per-team performance within selected ART ───────────────────────
    with tab2:
        if not selected_teams:
            st.info("Select teams from the filter above.")
        else:
            with st.spinner(f"Loading team performance for {short_art_name(selected_art)}…"):
                try:
                    # Only get counts for selected teams
                    team_counts = run_async(_async_get_counts(cookies, selected_teams,
                                                               date_from=_chart_from, date_to=_chart_to))
                    t_rows = [
                        {"team": t.name, "team_obj": t,
                         "committed": team_counts[t.oid]["committed"],
                         "completed": team_counts[t.oid]["completed"]}
                        for t in selected_teams
                        if team_counts.get(t.oid)
                        and (team_counts[t.oid]["committed"] > 0 or team_counts[t.oid]["completed"] > 0)
                    ]
                    t_rows.sort(key=lambda r: r["team"])

                    if t_rows:
                        t_labels    = [short_team_name(r["team"]) for r in t_rows]
                        t_committed = [r["committed"] for r in t_rows]
                        t_completed = [r["completed"] for r in t_rows]
                        g_max       = max(max(t_committed), max(t_completed), 1)

                        # Create mapping for click handling
                        team_label_to_data = {short_team_name(r["team"]): r for r in t_rows}

                        t_annotations = [
                            dict(
                                x=t_labels[i],
                                y=max(r["committed"], r["completed"]) + g_max * 0.07,
                                text=f"<b>{r['completed'] / r['committed'] * 100:.1f}%</b>" if r["committed"] else "<b>0%</b>",
                                showarrow=False,
                                font=dict(size=11, color="#663399"),
                                bgcolor="rgba(102,51,153,0.08)",
                                bordercolor="#663399", borderwidth=1, borderpad=3,
                                xanchor="center",
                            )
                            for i, r in enumerate(t_rows)
                        ]

                        fig_teams = go.Figure(data=[
                            go.Bar(name="Committed", x=t_labels, y=t_committed,
                                   marker_color="#663399", opacity=0.95,
                                   text=t_committed, textposition="outside", textfont=dict(size=11, color="#333333"),
                                   customdata=[[r["team"]] for r in t_rows],
                                   hovertemplate='<b>%{x}</b><br>Committed: %{y}<br><extra></extra>'),
                            go.Bar(name="Completed",  x=t_labels, y=t_completed,
                                   marker_color="#00A86B", opacity=0.95,
                                   text=t_completed, textposition="outside", textfont=dict(size=11, color="#333333"),
                                   customdata=[[r["team"]] for r in t_rows],
                                   hovertemplate='<b>%{x}</b><br>Completed: %{y}<br><extra></extra>'),
                        ])
                        fig_teams.update_layout(
                            **{**_CHART_LAYOUT, "margin": dict(l=50, r=20, t=50, b=110)},
                            title=dict(text=f"Team Performance — {short_art_name(selected_art)} — {_chart_label}<br><sub style='font-size:12px;color:#666;'>Click on a team name to view Sprint Velocity</sub>", **_CHART_TITLE_STYLE),
                            xaxis_title="Team (Click to view Sprint Velocity)",
                            yaxis_title="Stories",
                            xaxis_tickangle=-35,
                            yaxis_range=[0, g_max * 1.22],
                            annotations=t_annotations,
                            height=max(420, 420 + (len(t_rows) - 10) * 14),
                        )
                        
                        # Display chart and capture click events
                        # Use dynamic key to ensure chart resets after each team click
                        chart_key = f"team_chart_{st.session_state.clicked_team_for_velocity['oid'] if st.session_state.clicked_team_for_velocity else 'none'}"
                        selected_points = st.plotly_chart(fig_teams, use_container_width=True, 
                                                         on_select="rerun", selection_mode="points", key=chart_key)
                        
                        # Handle click on team bar
                        if selected_points and selected_points.selection and selected_points.selection.points:
                            point = selected_points.selection.points[0]
                            clicked_label = point["x"] if isinstance(point, dict) else point.x
                            if clicked_label in team_label_to_data:
                                team_data = team_label_to_data[clicked_label]
                                new_team_oid = team_data["team_obj"].oid
                                # Only rerun if clicking a different team
                                current_team_oid = st.session_state.clicked_team_for_velocity["oid"] if st.session_state.clicked_team_for_velocity else None
                                if new_team_oid != current_team_oid:
                                    st.session_state.clicked_team_for_velocity = {
                                        "name": team_data["team"],
                                        "oid": new_team_oid
                                    }
                                    st.rerun()
                    else:
                        st.info("No activity data found for teams in this ART.")
                except Exception as exc:
                    st.error(f"Failed to load team performance: {exc}")

    # ── Tab 3: Sprint detail for the clicked team ────────────────────────────
    if tab3:  # Only render if tab3 exists (i.e., a team was clicked)
        with tab3:
            clicked_team_info = st.session_state.clicked_team_for_velocity
            if clicked_team_info:
                # Add close button at the top, always visible
                col1, col2 = st.columns([6, 1])
                with col2:
                    if st.button("✖ Close", key="close_velocity"):
                        st.session_state.clicked_team_for_velocity = None
                        st.rerun()
                
                # Load data for the clicked team only
                current_year = time.localtime().tm_year
                with st.spinner(f"Loading sprint data for **{short_team_name(clicked_team_info['name'])}**…"):
                    try:
                        summary = run_async(
                            _async_get_summary(cookies, clicked_team_info['oid'], clicked_team_info['name'], current_year)
                        )
                        
                        clicked_sprints = summary.sprints or []
                        active = [s for s in clicked_sprints if s.total_planned > 0 or s.total_delivered > 0]
                        clicked_sprints = active if active else clicked_sprints
                        clicked_sprints.sort(key=lambda s: (s.begin_date or ""))

                        if date_from:
                            clicked_sprints = [s for s in clicked_sprints if (s.begin_date or "")[:10] >= str(date_from)]
                        if date_to:
                            clicked_sprints = [s for s in clicked_sprints if (s.begin_date or "")[:10] <= str(date_to)]

                    except Exception as exc:
                        st.error(f"Failed to load sprint data: {exc}")
                        clicked_sprints = []

                if not clicked_sprints:
                    st.info(f"No sprint data available for {short_team_name(clicked_team_info['name'])}.")
                else:
                    labels         = [s.sprint_name for s in clicked_sprints]
                    planned_vals   = [s.total_planned   for s in clicked_sprints]
                    delivered_vals = [s.total_delivered for s in clicked_sprints]
                    p_pts          = [s.planned_points  for s in clicked_sprints]
                    d_pts          = [s.delivered_points for s in clicked_sprints]
                    rate_vals      = [
                        round(s.total_delivered / s.total_planned * 100, 1) if s.total_planned else 0
                        for s in clicked_sprints
                    ]

                    velocity_title = f"Sprint Velocity — {short_team_name(clicked_team_info['name'])}"

                    # Sprint velocity chart
                    fig_vel = go.Figure(data=[
                        go.Bar(name="Planned",   x=labels, y=planned_vals,
                               marker_color="#663399", opacity=0.95,
                               text=planned_vals, textposition="outside", textfont=dict(size=10, color="#333333")),
                        go.Bar(name="Delivered", x=labels, y=delivered_vals,
                               marker_color="#00A86B", opacity=0.95,
                               text=delivered_vals, textposition="outside", textfont=dict(size=10, color="#333333")),
                    ])
                    fig_vel.update_layout(
                        **_CHART_LAYOUT,
                        title=dict(text=velocity_title, **_CHART_TITLE_STYLE),
                        yaxis_title="Stories",
                        height=340,
                    )
                    st.plotly_chart(fig_vel, use_container_width=True)

                    # Story points + Delivery rate side by side
                    col_pts, col_rate = st.columns(2)
                    with col_pts:
                        fig_pts = go.Figure(data=[
                            go.Bar(name="Planned pts",   x=labels, y=p_pts,
                                   marker_color="#663399", opacity=0.95,
                                   text=p_pts, textposition="outside", textfont=dict(size=10, color="#333333")),
                            go.Bar(name="Delivered pts", x=labels, y=d_pts,
                                   marker_color="#00A86B", opacity=0.95,
                                   text=d_pts, textposition="outside", textfont=dict(size=10, color="#333333")),
                        ])
                        fig_pts.update_layout(
                            **{**_CHART_LAYOUT, "margin": dict(l=40, r=20, t=40, b=80)},
                            title=dict(text="Story Points", **_CHART_TITLE_STYLE),
                            yaxis_title="Points",
                            height=300,
                        )
                        st.plotly_chart(fig_pts, use_container_width=True)

                    with col_rate:
                        fig_rate = go.Figure(data=[
                            go.Scatter(
                                name="Delivery %", x=labels, y=rate_vals,
                                mode="lines+markers+text",
                                line=dict(color="#FF6B35", width=3),
                                marker=dict(color="#FF6B35", size=8),
                                text=[f"{v:.0f}%" for v in rate_vals],
                                textposition="top center",
                                textfont=dict(size=10, color="#333333"),
                                fill="tozeroy",
                                fillcolor="rgba(255,107,53,0.1)",
                            )
                        ])
                        fig_rate.update_layout(
                            **{**_CHART_LAYOUT,
                               "yaxis": dict(gridcolor="#E8E8E8", showline=False,
                                             rangemode='tozero', zeroline=True, zerolinecolor="#333333", zerolinewidth=2,
                                             ticksuffix="%", range=[0, 110]),
                               "showlegend": False,
                               "margin": dict(l=48, r=20, t=40, b=80)},
                            title=dict(text="Delivery Rate %", **_CHART_TITLE_STYLE),
                            height=300,
                        )
                        st.plotly_chart(fig_rate, use_container_width=True)

                    # Sprint details table
                    st.markdown("### Sprint Details")
                    rows = []
                    today_str = _dt.date.today().isoformat()
                    for s in clicked_sprints:
                        pct = round(s.total_delivered / s.total_planned * 100, 1) if s.total_planned else 0.0
                        sprint_ended   = bool(s.end_date   and s.end_date[:10]   < today_str)
                        sprint_started = bool(s.begin_date and s.begin_date[:10] <= today_str)
                        pull_fwd_val   = str(s.pull_forward_count)          if sprint_started and s.pull_forward_count  >= 0 else "–"
                        pull_fwd_pts   = str(round(s.pull_forward_points, 1)) if sprint_started and s.pull_forward_points >= 0 else "–"
                        carry_over_val = str(s.carry_over_count)             if sprint_started and s.carry_over_count    > 0  else "–"
                        carry_over_pts = str(round(s.carry_over_points, 1))  if sprint_started and s.carry_over_points   > 0  else "–"
                        rows.append({
                            "Sprint":          s.sprint_name,
                            "From":            (s.begin_date or "")[:10],
                            "To":              (s.end_date   or "")[:10],
                            "Planned":         s.total_planned,
                            "Delivered":       s.total_delivered,
                            "Pull Forward":    pull_fwd_val,
                            "Carry Over":      carry_over_val,
                            "Planned Pts":     round(s.planned_points,   1),
                            "Delivered Pts":   round(s.delivered_points, 1),
                            "Pull Fwd Pts":    pull_fwd_pts,
                            "Carry Over Pts":  carry_over_pts,
                            "Delivery Rate":   f"{pct:.0f}%",
                        })
                    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

                    # ── Story-level validation expander ───────────────────────────────
                    with st.expander("🔍 Validate Pull Forward / Carry Over — Story Details", expanded=False):
                        st.caption(
                            "Use this to cross-check counts against the Agility board. "
                            "Pull Forward = story created after sprint started (pulled from backlog/future mid-sprint). "
                            "Carry-over = story created before sprint start and not delivered (moved in from previous sprint)."
                        )
                        for s in clicked_sprints:
                            sprint_end   = (s.end_date   or "")[:10]
                            sprint_begin = (s.begin_date or "")[:10]
                            sprint_ended   = bool(sprint_end   and sprint_end   < today_str)
                            sprint_started = bool(sprint_begin and sprint_begin <= today_str)

                            pull_fwd_stories = [
                                st_obj for st_obj in s.stories
                                if st_obj.name.startswith("PF:")
                            ]
                            carry_stories = [
                                st_obj for st_obj in s.stories
                                if st_obj.name.startswith("CO:")
                            ]

                            has_pull  = sprint_started and len(pull_fwd_stories) > 0
                            has_carry = sprint_started and len(carry_stories)    > 0

                            if not has_pull and not has_carry:
                                continue  # skip sprints with nothing to show

                            st.markdown(f"**{s.sprint_name}** ({sprint_begin} → {sprint_end})")
                            col_p, col_c = st.columns(2)

                            with col_p:
                                if sprint_started and pull_fwd_stories:
                                    st.markdown(f"**Pull Forward: {len(pull_fwd_stories)} stories**")
                                    pf_rows = []
                                    for st_obj in pull_fwd_stories:
                                        pf_rows.append({
                                            "#":        st_obj.number or st_obj.oid,
                                            "Type":     st_obj.item_type,
                                            "Story":    st_obj.name[:60],
                                            "Status":   st_obj.status or "–",
                                            "Created":  st_obj.create_date or "–",
                                            "Closed":   st_obj.closed_date or "–",
                                            "Estimate": st_obj.estimate or 0,
                                        })
                                    st.dataframe(pd.DataFrame(pf_rows), use_container_width=True, hide_index=True)
                                else:
                                    st.markdown("_No pull-forwards_")

                            with col_c:
                                if sprint_started and carry_stories:
                                    st.markdown(f"**Carry Over: {len(carry_stories)} stories**")
                                    carry_rows = []
                                    for st_obj in carry_stories:
                                        carry_rows.append({
                                            "#":        st_obj.number or st_obj.oid,
                                            "Type":     st_obj.item_type,
                                            "Story":    st_obj.name[:60],
                                            "Status":   st_obj.status or "–",
                                            "Created":  st_obj.create_date or "–",
                                            "Closed":   st_obj.closed_date or "–",
                                            "Estimate": st_obj.estimate or 0,
                                        })
                                    st.dataframe(pd.DataFrame(carry_rows), use_container_width=True, hide_index=True)
                                else:
                                    st.markdown("_No carry-overs_")

                            st.divider()


# ── Entry point ────────────────────────────────────────────────────────────────
def main() -> None:
    if st.session_state.show_dashboard and st.session_state.cookies:
        show_dashboard()
    else:
        show_login()


main()
