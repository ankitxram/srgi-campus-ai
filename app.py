import base64
import csv
import html
import io
import json
import heapq
import re
import time
from datetime import datetime
from pathlib import Path
from urllib.request import urlopen

import pandas as pd
import streamlit as st

from utils.ai_search import CampusAI

try:
    from zoneinfo import ZoneInfo
except ImportError:  # very old Python
    ZoneInfo = None

try:
    import college_config as cfg

    COLLEGE_LAT = float(cfg.COLLEGE_LATITUDE)
    COLLEGE_LON = float(cfg.COLLEGE_LONGITUDE)
except Exception:
    COLLEGE_LAT, COLLEGE_LON = None, None

# --------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="SRGI Campus AI",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

USER_NAME = "Abhijeet"

# --------------------------------------------------
# DESIGN (same look as the SRGI Campus AI dashboard artifact)
# --------------------------------------------------

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

:root {
    --bg:#020D25; --sb:#03112B; --card:#071B40; --sf:#0B2452;
    --b1:#1677FF; --b2:#2998FF; --cy:#47D9FF;
    --tx:#F4F7FF; --mu:#A8BAD8; --bd:rgba(150,190,255,.16);
}

/* ================= BASE ================= */

.stApp { background: var(--bg); color: var(--tx); }
.stApp, .stApp p, .stApp label, .stApp button, .stApp input, .stApp a, .stApp li,
.stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5 {
    font-family: Inter, Manrope, "Segoe UI", system-ui, sans-serif;
}
.stApp p { color: var(--tx); }
h1, h2, h3, h4 { color: #fff !important; }

/* The top header bar is invisible but still catches clicks, so let clicks pass through it.
   Only the button that re-opens a closed sidebar stays clickable. */
header[data-testid="stHeader"] { background: transparent; pointer-events: none; }
header[data-testid="stHeader"] [data-testid="stExpandSidebarButton"],
header[data-testid="stHeader"] [data-testid="stSidebarCollapsedControl"],
header[data-testid="stHeader"] [data-testid="collapsedControl"],
[data-testid="collapsedControl"] { pointer-events: auto; }
/* hide Deploy / menu, but NOT the whole toolbar (it can hold the "open sidebar" button) */
[data-testid="stToolbarActions"], [data-testid="stAppDeployButton"], [data-testid="stMainMenu"],
[data-testid="stDecoration"], #MainMenu, footer { display: none !important; }
/* on a computer screen the sidebar always stays open, so it can never get lost */
@media (min-width: 900px) {
    [data-testid="stSidebarCollapseButton"] { display: none !important; }
}

.block-container, [data-testid="stMainBlockContainer"] {
    max-width: 100% !important;
    padding: 3.4rem 28px 2rem 28px !important;
}
/* the Home page runs edge to edge (hero touches the sidebar) */
.block-container:has(.st-key-page_home),
[data-testid="stMainBlockContainer"]:has(.st-key-page_home) {
    padding: 0 !important;
}
/* hide the empty element that only carries this <style> */
[data-testid="stElementContainer"]:has(> [data-testid="stMarkdown"] style) { display: none; }

hr { border-color: var(--bd) !important; }

/* ================= SIDEBAR ================= */

section[data-testid="stSidebar"] {
    background: var(--sb);
    border-right: 1px solid var(--bd);
}
section[data-testid="stSidebar"][aria-expanded="true"] {
    width: 250px !important;
    min-width: 250px !important;
}
section[data-testid="stSidebar"] [data-testid="stSidebarContent"] { padding: 0 12px; }

.logo {
    display: flex; gap: 10px; align-items: center;
    padding: 4px 0 14px 0; border-bottom: 1px solid var(--bd); margin-bottom: 14px;
}
.logo i {
    width: 38px; height: 38px; flex: 0 0 38px; border-radius: 50%;
    background: linear-gradient(135deg, var(--b1), var(--cy));
    display: grid; place-items: center; font-style: normal; font-size: 18px;
}
.logo b { display: block; font-size: 17px; color: #fff; }
.logo small { color: var(--mu); font-size: 11px; line-height: 1.35; display: block; }

section[data-testid="stSidebar"] div[role="radiogroup"] { gap: 2px; }
section[data-testid="stSidebar"] div[role="radiogroup"] label {
    width: 100%; min-height: 42px; padding: 8px 12px; border-radius: 10px;
    background: transparent; border: 0; cursor: pointer; transition: .2s;
}
section[data-testid="stSidebar"] div[role="radiogroup"] label > div:first-child:not(:has(p)) { display: none; }
section[data-testid="stSidebar"] div[role="radiogroup"] label p {
    color: var(--mu) !important; font-size: 14px !important; font-weight: 500 !important; margin: 0 !important;
}
section[data-testid="stSidebar"] div[role="radiogroup"] label:hover { background: rgba(41,152,255,.10); }
section[data-testid="stSidebar"] div[role="radiogroup"] label:hover p { color: var(--tx) !important; }
section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) {
    background: linear-gradient(90deg, var(--b1), var(--b2));
    box-shadow: 0 0 18px rgba(22,119,255,.4);
}
section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) p { color: #fff !important; font-weight: 600 !important; }

.quote {
    margin-top: 28px; border: 1px solid var(--bd); border-radius: 14px; padding: 14px;
    background: linear-gradient(180deg, var(--card), var(--sb)); font-size: 12px; color: var(--mu);
}
.quote em { color: var(--tx); display: block; margin-bottom: 6px; font-style: italic; }
.quote svg { display: block; width: 100%; opacity: .35; margin-top: 8px; }

/* ================= HERO (Home) ================= */

.st-key-hero {
    position: relative; padding: 20px 28px 28px; min-height: 380px;
    border-bottom: 1px solid var(--bd);
}
.st-key-home_main { gap: 0 !important; }
.st-key-home_body { padding: 0 28px; gap: .9rem; }

.hero-h2 { margin: 14px 0 2px; font-size: 18px; font-weight: 600; color: #fff; }
.hero-sub { color: var(--mu); margin: 0 0 14px; }
.hero-h1 { font-size: clamp(32px, 4.5vw, 52px); line-height: 1.08; margin: 0 0 12px; font-weight: 800; color: #fff; }
.hero-h1 span { color: var(--b2); }
.hero-desc { max-width: 480px; color: var(--mu); margin-bottom: 20px; }
.hand {
    position: absolute; right: 34px; bottom: 70px; text-align: left; pointer-events: none;
    font: italic 700 30px/1.15 "Segoe Script", "Brush Script MT", cursive;
    color: var(--cy); text-shadow: 0 0 14px rgba(71,217,255,.5);
}

/* top bar: bell + profile */
.st-key-topbar { align-items: center; }
.st-key-bell_new, .st-key-bell_seen { position: relative; width: 38px; }
.st-key-bell_new::after {
    content: ""; position: absolute; top: 6px; right: 6px; width: 8px; height: 8px;
    border-radius: 50%; background: #ff5a6e; pointer-events: none; z-index: 3;
}
.st-key-bell_new button, .st-key-bell_seen button {
    width: 38px; height: 38px; min-height: 38px; padding: 0; border-radius: 50%;
    background: var(--sf); border: 1px solid var(--bd); color: #fff;
}
.st-key-profile button {
    background: none; border: 0; box-shadow: none; color: #fff; font-weight: 600; padding: 0 4px;
}
.st-key-profile button:hover { background: rgba(255,255,255,.06); border: 0; }
[data-testid="stPopoverBody"] { background: var(--sf) !important; border: 1px solid var(--bd) !important; }

/* search pill */
.st-key-herosearch { max-width: 620px; }
.st-key-herosearch [data-testid="stForm"] {
    background: rgba(7,27,64,.92); border: 1px solid var(--bd); border-radius: 999px; padding: 6px 6px 6px 14px;
}
.st-key-herosearch div[data-baseweb="input"],
.st-key-herosearch div[data-baseweb="base-input"] { background: transparent !important; border: 0 !important; }
.st-key-herosearch input { color: var(--tx) !important; padding: 10px 6px !important; }
.st-key-herosearch [data-testid="stFormSubmitButton"] button {
    background: linear-gradient(90deg, var(--b1), var(--b2)); border: 0; border-radius: 999px;
    padding: 10px 20px; font-weight: 600; color: #fff; width: 100%;
}

/* ================= SECTION HEADERS ================= */

.sh { display: flex; align-items: center; gap: 10px; margin: 22px 0 4px 0; }
.sh h3 { margin: 0; font-size: 18px; font-weight: 700; padding: 0; }
.sh small { color: var(--mu); display: block; font-size: 13px; }
.sh > span { font-size: 20px; }

.st-key-viewall { margin-top: 22px; }
.st-key-viewall button {
    background: none; border: 1px solid var(--bd); border-radius: 999px; padding: 6px 14px;
    color: var(--tx); box-shadow: none; float: right;
}
.st-key-viewall button:hover { background: rgba(41,152,255,.12); transform: none; box-shadow: none; }

/* ================= CLICKABLE CARDS (overlay button) ================= */

[class*="st-key-card_"] { position: relative; }
[class*="st-key-card_"] [data-testid="stElementContainer"]:has(button) {
    position: absolute; inset: 0; z-index: 5; margin: 0; width: 100% !important; height: 100% !important;
}
[class*="st-key-card_"] div.stButton { width: 100%; height: 100%; }
[class*="st-key-card_"] div.stButton > button {
    width: 100%; height: 100%; opacity: 0; cursor: pointer; padding: 0; border: 0;
}
[class*="st-key-card_"]:has(button:focus-visible) { outline: 2px solid var(--cy); outline-offset: 2px; border-radius: 16px; }

.aud, .feat { text-align: left; transition: .2s; border: 1px solid; border-radius: 16px; padding: 18px; }
[class*="st-key-card_"]:hover .aud,
[class*="st-key-card_"]:hover .feat,
[class*="st-key-card_"]:hover .ev { transform: translateY(-3px); box-shadow: 0 0 22px var(--gl); }

.aud { min-height: 210px; display: flex; flex-direction: column; }
.aud .bg { width: 44px; height: 44px; border-radius: 50%; display: grid; place-items: center; font-size: 20px; margin-bottom: 12px; }
.aud h4 { margin: 0 0 6px; font-size: 19px; color: #fff; }
.aud p { color: var(--mu); margin: 0 0 auto; }
.aud .go { margin-top: 14px; font-weight: 600; color: #fff; }
.stu { --gl:#3b6bff88; background: linear-gradient(135deg,#1b3d99,#2a2a8a 70%,#071B40); border-color:#3b6bff; }
.stu .bg { background:#1677FF; }
.par { --gl:#10b98188; background: linear-gradient(135deg,#0b6b57,#0b4f55 70%,#071B40); border-color:#10b981; }
.par .bg { background:#10b981; }
.vis { --gl:#ff6b5a88; background: linear-gradient(135deg,#a3412f,#8a2f59 70%,#071B40); border-color:#ff6b5a; }
.vis .bg { background:#ff6b5a; }

.feat { min-height: 150px; position: relative; }
.feat h4 { margin: 10px 0 4px; font-size: 17px; color: #fff; }
.feat p { color: var(--mu); margin: 0; padding-right: 36px; font-size: 13px; }
.feat .bg { width: 40px; height: 40px; border-radius: 50%; display: grid; place-items: center; }
.feat .ar { position: absolute; right: 14px; bottom: 14px; width: 32px; height: 32px; border-radius: 50%; display: grid; place-items: center; color: #fff; }
.f1 { --gl:#2998ff88; background: linear-gradient(135deg,#0f3d8f,#071B40); border-color:#2998ff; }
.f1 .bg, .f1 .ar { background:#1677FF; }
.f2 { --gl:#14b8a688; background: linear-gradient(135deg,#0b5d57,#071B40); border-color:#14b8a6; }
.f2 .bg, .f2 .ar { background:#14b8a6; }
.f3 { --gl:#8b5cf688; background: linear-gradient(135deg,#4a2a99,#071B40); border-color:#8b5cf6; }
.f3 .bg, .f3 .ar { background:#8b5cf6; }
.f4 { --gl:#ff6b5a88; background: linear-gradient(135deg,#a3412f,#071B40); border-color:#ff6b5a; }
.f4 .bg, .f4 .ar { background:#ff6b5a; }

/* event cards */
.ev {
    --gl: rgba(41,152,255,.35);
    display: flex; gap: 12px; align-items: center; text-align: left; transition: .2s;
    background: var(--card); border: 1px solid var(--bd); border-radius: 14px; padding: 14px;
}
.date {
    min-width: 50px; text-align: center; background: var(--sf); border-radius: 10px;
    padding: 6px; font-size: 11px; color: var(--cy); font-weight: 600;
}
.date b { display: block; font-size: 20px; color: var(--tx); }
.date.big { min-width: 64px; padding: 10px 8px; }
.date.big b { font-size: 26px; }
.ev-info { min-width: 0; flex: 1; }
.ev-info b { color: #fff; font-size: 15px; display: block; margin-bottom: 2px; }
.ev-info small { color: var(--mu); display: block; font-size: 12px; }
.tag {
    display: inline-block; font-size: 10px; padding: 2px 8px; border-radius: 99px;
    background: rgba(41,152,255,.18); color: var(--cy); margin: 0 4px 4px 0;
}
.ev .ar { margin-left: auto; background: var(--b1); width: 28px; height: 28px; border-radius: 50%; display: grid; place-items: center; flex: none; color: #fff; }

/* ================= RIGHT PANEL ================= */

.st-key-right_panel { padding: 96px 20px 0 0; gap: 14px; }
.panel {
    background: var(--card); border: 1px solid var(--bd); border-radius: 14px; padding: 14px;
}
.panel h5 { margin: 0 0 8px; font-size: 14px; color: #fff; display: flex; align-items: center; gap: 6px; }

.st-key-ql_card {
    background: var(--card); border: 1px solid var(--bd); border-radius: 14px; padding: 14px; gap: 2px;
}
.st-key-ql_card button, .st-key-ql_card [data-testid="stDownloadButton"] button {
    width: 100%; background: none; border: 0; box-shadow: none; color: var(--tx);
    justify-content: space-between; padding: 9px 6px; border-radius: 8px; font-weight: 500;
}
.st-key-ql_card button::after { content: "›"; color: var(--mu); margin-left: auto; padding-left: 8px; }
.st-key-ql_card button:hover { background: rgba(41,152,255,.12); transform: none; box-shadow: none; color: #fff; }

.wx { background: linear-gradient(180deg, rgba(7,27,64,.7), rgba(7,27,64,.95)), linear-gradient(120deg,#16406e,#2a6b4a); }
.wx .t { font-size: 34px; font-weight: 700; color: #fff; line-height: 1.1; }
.wx .c { color: var(--tx); }
.wx small { color: var(--mu); }
.demo { font-size: 10px; color: #ffb86b; border: 1px solid #ffb86b66; border-radius: 99px; padding: 1px 8px; margin-left: auto; font-weight: 400; }
.live { font-size: 10px; color: #6ee7b7; border: 1px solid #6ee7b766; border-radius: 99px; padding: 1px 8px; margin-left: auto; font-weight: 400; }

.an { display: flex; gap: 8px; align-items: flex-start; border-bottom: 1px solid var(--bd); padding: 8px 0; }
.an:last-of-type { border: 0; }
.an i { width: 8px; height: 8px; border-radius: 50%; margin-top: 5px; flex: none; }
.an span { color: var(--tx); font-size: 13px; }
.an small { color: var(--mu); display: block; }

.foot {
    margin: 30px 28px 0; padding: 14px 0 24px; border-top: 1px solid var(--bd);
    color: var(--mu); font-size: 12px; text-align: center; position: relative;
}

/* ================= INNER PAGES ================= */

.page-hero {
    display: flex; align-items: center; gap: 18px; padding: 22px 26px; margin-bottom: 20px;
    background: var(--card); border: 1px solid var(--bd); border-left: 5px solid var(--b2); border-radius: 14px;
}
.page-hero.purple { border-left-color: #8b5cf6; }
.page-hero.green  { border-left-color: #14b8a6; }
.page-hero.orange { border-left-color: #ff6b5a; }
.page-icon {
    width: 56px; height: 56px; flex: 0 0 56px; display: flex; align-items: center; justify-content: center;
    font-size: 28px; border-radius: 50%; background: linear-gradient(135deg, var(--b1), var(--cy));
}
.page-text { min-width: 0; }
.page-title { color: #fff; font-size: 26px; font-weight: 800; line-height: 1.2; }
.page-subtitle { color: var(--mu); font-size: 15px; line-height: 1.5; margin-top: 4px; max-width: 760px; }
.chip-row { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 12px; }
.chip {
    display: inline-block; padding: 4px 12px; border-radius: 20px; background: rgba(41,152,255,.14);
    border: 1px solid var(--bd); color: var(--cy); font-size: 12px; font-weight: 600;
}

.hero-card {
    background: linear-gradient(135deg, var(--card), #0b2b59); border: 1px solid var(--bd);
    border-radius: 16px; padding: 28px 32px; margin: 12px 0 20px;
}
.hero-greeting { color: var(--mu); font-size: 16px; font-weight: 600; margin-bottom: 8px; }
.hero-title { color: #fff; font-size: 34px; font-weight: 800; line-height: 1.2; margin-bottom: 10px; }
.hero-title span { color: var(--b2); }
.hero-description { color: var(--mu); font-size: 16px; line-height: 1.6; max-width: 700px; }

.section-title { color: #fff; font-size: 22px; font-weight: 700; margin-top: 10px; }
.section-subtitle { color: var(--mu); font-size: 14px; margin-bottom: 14px; }

.answer-card, .notfound-card {
    padding: 24px 26px; margin: 14px 0 6px 0; border-radius: 16px; background: var(--card);
    border: 1px solid var(--bd); border-left: 5px solid var(--b1);
}
.notfound-card { border-left-color: #f0a030; }
.answer-label { color: var(--cy); font-size: 12px; font-weight: 700; letter-spacing: 1.6px; }
.notfound-card .answer-label { color: #f0b860; }
.answer-text { color: var(--tx); font-size: 17px; line-height: 1.7; margin: 10px 0 16px 0; }
.answer-meta { margin-bottom: 14px; }
.meter-text { color: var(--mu); font-size: 12px; margin-bottom: 6px; }
.meter-bar { height: 8px; border-radius: 8px; background: var(--sf); overflow: hidden; }
.meter-fill { height: 100%; border-radius: 8px; background: linear-gradient(90deg, var(--b1), #14b8a6); }
.matched { margin-top: 16px; padding: 10px 14px; border-radius: 10px; background: rgba(255,255,255,.04); color: var(--mu); font-size: 13px; }

.result-count { color: var(--cy); font-size: 14px; font-weight: 600; margin: 14px 0 8px 0; }
.loc-card {
    padding: 22px 24px; margin-bottom: 14px; border-radius: 16px; background: var(--card);
    border: 1px solid var(--bd); border-left: 5px solid #14b8a6;
}
.loc-name { color: #fff; font-size: 22px; font-weight: 800; margin-bottom: 12px; }
.crumbs { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; margin-bottom: 14px; }
.crumb { padding: 6px 12px; border-radius: 10px; background: var(--sf); border: 1px solid var(--bd); color: var(--tx); font-size: 13px; font-weight: 600; }
.crumb-arrow { color: var(--mu); font-size: 14px; }
.loc-desc { color: var(--mu); font-size: 14px; line-height: 1.6; }

.route-summary {
    padding: 12px 18px; margin: 12px 0 14px 0; border-radius: 12px; background: rgba(20,184,166,.12);
    border: 1px solid rgba(20,184,166,.45); color: #bff5e6; font-size: 14px; font-weight: 600;
}
.route-timeline { padding: 6px 4px 6px 6px; }
.route-start, .route-end {
    display: inline-block; padding: 8px 16px; border-radius: 12px; background: var(--sf);
    border: 1px solid var(--bd); color: #fff; font-size: 14px; font-weight: 700;
}
.route-end { background: linear-gradient(90deg, var(--b1), var(--b2)); border-color: var(--b2); }
.route-step { display: flex; gap: 14px; margin-left: 16px; padding: 4px 0 18px 20px; border-left: 2px dashed rgba(150,190,255,.35); }
.route-dot {
    width: 30px; height: 30px; flex: 0 0 30px; margin-left: -37px; display: flex; align-items: center;
    justify-content: center; border-radius: 50%; background: var(--b1); border: 2px solid var(--cy);
    color: #fff; font-size: 13px; font-weight: 700;
}
.route-place { color: #fff; font-size: 15px; font-weight: 700; }
.route-how { color: var(--mu); font-size: 13px; margin-top: 3px; }

.event-full {
    padding: 20px 22px; margin-top: 14px; border-radius: 16px; background: var(--card);
    border: 1px solid var(--bd); border-left: 5px solid #ff6b5a;
}
.event-full-top { display: flex; align-items: center; gap: 18px; }
.event-name { color: #fff; font-size: 20px; font-weight: 700; margin-bottom: 6px; }
.event-full-desc { color: var(--mu); font-size: 14px; line-height: 1.6; margin-top: 14px; }

/* ================= GENERAL WIDGETS ================= */

.stButton > button, div[data-testid="stFormSubmitButton"] > button {
    background: linear-gradient(90deg, var(--b1), var(--b2)); color: #fff; border: 0;
    border-radius: 999px; padding: .55rem 1.2rem; font-weight: 600; transition: .2s ease;
}
.stButton > button:hover, div[data-testid="stFormSubmitButton"] > button:hover {
    transform: translateY(-2px); box-shadow: 0 8px 25px rgba(22,119,255,.35); color: #fff;
}
div[data-baseweb="input"], div[data-baseweb="select"] > div {
    background: var(--sf); border: 1px solid var(--bd); border-radius: 10px;
}
div[data-baseweb="input"] input { color: var(--tx); }
div[data-testid="stForm"], div[data-testid="stVerticalBlockBorderWrapper"]:has(> div > [data-testid="stVerticalBlock"] .stSelectbox) {
    border-color: var(--bd);
}
div[data-baseweb="tab-list"] { gap: 8px; border-bottom: 1px solid var(--bd); }
button[data-baseweb="tab"] { background: transparent; color: var(--mu); font-weight: 600; padding: 10px 16px; }
button[data-baseweb="tab"][aria-selected="true"] { color: var(--cy); }
div[data-baseweb="tab-highlight"] { background-color: var(--cy); }
div[data-testid="stExpander"] { background: var(--card); border: 1px solid var(--bd); border-radius: 14px; }
div[data-testid="stExpander"]:hover { border-color: var(--b2); }
div[data-testid="stAlert"] { border-radius: 12px; }
::-webkit-scrollbar { width: 8px; }
::-webkit-scrollbar-track { background: var(--bg); }
::-webkit-scrollbar-thumb { background: #294b7c; border-radius: 10px; }

@media (max-width: 900px) {
    .hand { display: none; }
    .st-key-right_panel { padding: 0 16px 16px; }
    .st-key-home_body { padding: 0 16px; }
    .st-key-hero { padding: 56px 16px 24px; }
}
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# --------------------------------------------------
# FILES
# --------------------------------------------------

BASE_DIR = Path(__file__).parent
IMAGE_DIR = BASE_DIR / "images"

FAQ_FILE = BASE_DIR / "data" / "campus_faq.csv"
EVENT_FILE = BASE_DIR / "data" / "events.csv"
LOCATION_FILE = BASE_DIR / "data" / "locations.csv"
PATH_FILE = BASE_DIR / "data" / "paths.csv"
ANNOUNCEMENT_FILE = BASE_DIR / "data" / "announcements.csv"   # optional: title,date,color
BROCHURE_FILE = BASE_DIR / "data" / "brochure.pdf"            # optional: enables Download Brochure

# ---- "Organise Event" form (Events page) ----
# False -> submitted events go to data/event_requests.csv and wait for you to approve them
#          (copy the good rows into data/events.csv).
# True  -> submitted events are added straight to data/events.csv and show up immediately.
AUTO_PUBLISH_EVENTS = False
EVENT_REQUEST_FILE = BASE_DIR / "data" / "event_requests.csv"
EVENT_COLUMNS = ["date", "event", "venue", "time", "branch", "organizer", "description", "registration", "banner"]
REQUEST_COLUMNS = EVENT_COLUMNS + ["contact", "submitted_at"]

# ---- Tutorial video (Home page; the section is hidden until you set one) ----
VIDEO_FILE = BASE_DIR / "videos" / "tutorial.mp4"
TUTORIAL_VIDEO_URL = ""   # example: "https://www.youtube.com/watch?v=XXXXXXXXXXX"


def stamp(path):
    """Last-modified time of a file. Passing it to a cached loader makes the app
    re-read the CSV automatically whenever you save a change to it."""
    try:
        return path.stat().st_mtime
    except OSError:
        return 0


@st.cache_data
def load_faq(file_stamp):
    return pd.read_csv(FAQ_FILE, dtype=str)


@st.cache_data
def load_events(file_stamp):
    df = pd.read_csv(EVENT_FILE, dtype=str)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])
    return df.sort_values("date").reset_index(drop=True)


@st.cache_data
def load_locations(file_stamp):
    df = pd.read_csv(LOCATION_FILE, dtype=str)
    return df[df["name"].fillna("").str.strip().str.lower() != "place_a"].reset_index(drop=True)


@st.cache_data
def load_paths(file_stamp):
    if not PATH_FILE.is_file():
        return pd.DataFrame(columns=["place_a", "place_b", "how_to_walk", "minutes"])
    df = pd.read_csv(PATH_FILE, dtype=str)
    return df[df["place_a"].fillna("").str.strip().str.lower() != "place_a"].reset_index(drop=True)


@st.cache_data
def load_announcements_file(modified_time):
    return pd.read_csv(ANNOUNCEMENT_FILE)


def find_poster():
    """images/college_poster.jpg (or .jpeg, .png, .webp) is the Home hero photo."""
    return next(IMAGE_DIR.glob("college_poster.*"), None)


@st.cache_data
def load_poster_data_uri(path_text, modified_time):
    """Shrink the hero photo and return it as a data URI for the CSS background."""
    path = Path(path_text)
    try:
        from PIL import Image

        image = Image.open(path).convert("RGB")
        image.thumbnail((1600, 1600))
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=80)
        data = buffer.getvalue()
    except Exception:
        data = path.read_bytes()
    return "data:image/jpeg;base64," + base64.b64encode(data).decode()


@st.cache_resource
def get_ai(_faq_df, file_stamp):
    return CampusAI(_faq_df)


_missing = [p.name for p in (FAQ_FILE, EVENT_FILE, LOCATION_FILE) if not p.is_file()]
if _missing:
    st.error("Missing data file(s) in the data/ folder: " + ", ".join(_missing))
    st.stop()

faq_df = load_faq(stamp(FAQ_FILE))
events_df = load_events(stamp(EVENT_FILE))
locations_df = load_locations(stamp(LOCATION_FILE))
paths_df = load_paths(stamp(PATH_FILE))
ai_assistant = get_ai(faq_df, stamp(FAQ_FILE))


def get_now():
    try:
        return datetime.now(ZoneInfo("Asia/Kolkata"))
    except Exception:
        return datetime.now()


now = get_now()
today = pd.Timestamp(now.date())
upcoming_events = events_df[events_df["date"] >= today].sort_values("date")

# --------------------------------------------------
# HELPERS
# --------------------------------------------------


def esc(value):
    """HTML-escape any value (NaN -> empty string). '$' is escaped so Streamlit ignores it as math."""
    if pd.isna(value):
        return ""
    return html.escape(str(value)).replace("$", "&#36;")


def clean_text(value):
    return "" if pd.isna(value) else str(value).strip()


def greeting():
    if now.hour < 12:
        return "Good Morning"
    if now.hour < 17:
        return "Good Afternoon"
    return "Good Evening"


P_HOME = "🏠 Home"
P_AI = "🤖 AI Assistant"
P_NAV = "🗺️ Campus Navigation"
P_EVENTS = "📅 Events"
P_ADM = "📝 Admissions"
P_COURSES = "📚 Courses"
P_FAC = "🏛️ Facilities"
P_CONTACT = "📞 Contacts"
PAGES = [P_HOME, P_AI, P_NAV, P_EVENTS, P_ADM, P_COURSES, P_FAC, P_CONTACT]

st.session_state.setdefault("nav", P_HOME)
st.session_state.setdefault("role", None)
st.session_state.setdefault("view", None)          # "role" = a role page is open
st.session_state.setdefault("event_open", None)    # index of the event shown in detail
st.session_state.setdefault("notif_seen", False)


# ---- callbacks (they run before the page redraws, so they can change the page safely) ----

def go_to(page_name):
    st.session_state.nav = page_name
    st.session_state.view = None
    st.session_state.event_open = None


def leave_role_page():
    st.session_state.view = None
    st.session_state.event_open = None


def set_role(role_name):
    st.session_state.role = role_name
    st.session_state.view = "role" if role_name else None


def open_event(index):
    st.session_state.nav = P_EVENTS
    st.session_state.view = None
    st.session_state.event_open = index


def close_event():
    st.session_state.event_open = None


def mark_notifications_seen():
    st.session_state.notif_seen = True


def submit_hero():
    question = st.session_state.get("hero_q", "").strip()
    if not question:
        st.session_state.hero_warn = True
        return
    st.session_state.ai_question = question
    st.session_state.ai_run = True
    st.session_state.nav = P_AI
    st.session_state.view = None
    st.session_state.event_open = None


def no_brochure():
    st.toast("No brochure file yet. Put your PDF at data/brochure.pdf to enable this download.", icon="📄")


def overlay_card(key, card_html, on_click, args=()):
    """A card that is fully clickable. An invisible button is stretched over it."""
    with st.container(key=f"card_{key}"):
        st.markdown(card_html, unsafe_allow_html=True)
        st.button("Open", key=f"btn_{key}", on_click=on_click, args=args)


# ---- events ----

def event_card_html(event):
    month = event["date"].strftime("%b").upper()
    day = event["date"].strftime("%d")
    items = [b.strip() for b in clean_text(event.get("branch", "")).split(";") if b.strip()] or ["All Branches"]
    tags = items[:2] + ([f"+{len(items) - 2}"] if len(items) > 2 else [])
    tag_html = "".join(f'<span class="tag">{esc(t)}</span>' for t in tags)
    time_text = clean_text(event.get("time", "")) or "Time to be announced"
    return (
        f'<div class="ev"><div class="date">{month}<b>{day}</b></div>'
        f'<div class="ev-info"><b>{esc(event["event"])}</b><div>{tag_html}</div>'
        f"<small>🕒 {esc(time_text)}</small><small>📍 {esc(event['venue'])}</small></div>"
        f'<span class="ar">→</span></div>'
    )


def render_event_grid(events, prefix):
    rows = list(events.iterrows())
    for start in range(0, len(rows), 3):
        for column, (idx, event) in zip(st.columns(3), rows[start:start + 3]):
            with column:
                overlay_card(f"ev_{prefix}_{idx}", event_card_html(event), open_event, (int(idx),))


def show_registration_button(event):
    link = event.get("registration", "")
    if isinstance(link, str) and link.strip().lower().startswith(("http://", "https://")):
        st.link_button("🎫 Register Now", link.strip())


BRANCHES = ["CSE", "CSE (AI and ML)", "CSE (Data Science)", "IT", "ECE", "Mechanical", "Civil"]


def event_matches_branch(event, branch):
    if branch == "All Branches":
        return True
    cell = clean_text(event.get("branch", ""))
    if not cell:
        return True
    items = [item.strip().lower() for item in cell.split(";")]
    return "all branches" in items or branch.lower() in items


def render_event_full(event):
    banner = clean_text(event.get("banner", ""))
    if banner and (IMAGE_DIR / banner).is_file():
        st.image(str(IMAGE_DIR / banner))

    chips = [f"📍 {clean_text(event.get('venue', ''))}"]
    for icon, column in [("🕐", "time"), ("🎓", "branch"), ("👥", "organizer")]:
        value = clean_text(event.get(column, ""))
        if value:
            chips.append(f"{icon} {value}")
    chip_html = "".join(f'<span class="chip">{esc(c)}</span>' for c in chips)

    st.markdown(
        f'<div class="event-full"><div class="event-full-top">'
        f'<div class="date big">{event["date"].strftime("%b").upper()}<b>{event["date"].strftime("%d")}</b></div>'
        f'<div><div class="event-name">{esc(event["event"])}</div><div class="chip-row">{chip_html}</div></div></div>'
        f'<div class="event-full-desc">{esc(event.get("description", ""))}</div></div>',
        unsafe_allow_html=True,
    )
    show_registration_button(event)


# ---- FAQ pages ----

def faq_by_category(categories):
    wanted = [c.lower() for c in categories]
    return faq_df[faq_df["category"].fillna("").str.lower().isin(wanted)]


def page_header(icon, title, subtitle, color="blue", chips=None):
    chip_html = "".join(f'<span class="chip">{esc(c)}</span>' for c in (chips or []))
    st.markdown(
        f'<div class="page-hero {color}"><div class="page-icon">{icon}</div><div class="page-text">'
        f'<div class="page-title">{esc(title)}</div><div class="page-subtitle">{esc(subtitle)}</div>'
        f'<div class="chip-row">{chip_html}</div></div></div>',
        unsafe_allow_html=True,
    )


def render_faq_page(icon, title, subtitle, color, categories, show_department=False):
    rows = faq_by_category(categories)
    page_header(icon, title, subtitle, color, [f"{len(rows)} questions", "Answers from the SRGI FAQ"])

    if rows.empty:
        st.info("📭 No information added yet.")
        return

    for _, row in rows.iterrows():
        with st.expander(f"❓ {row['question']}"):
            st.write(row["answer"])
            if show_department:
                st.caption(f"Department: {row['contact_or_department']}")


# ---- AI ----

AI_SAMPLE_QUESTIONS = [
    "What is the minimum attendance required?",
    "What is the hostel fee?",
    "Who is the Principal?",
    "What scholarships are available?",
]


def ask_sample(question_text):
    st.session_state.ai_question = question_text
    st.session_state.ai_run = True


# ---- locations / routes ----

def set_place_query(place_name):
    st.session_state.loc_query = place_name


STOP_WORDS = {
    "where", "is", "the", "a", "an", "please", "show", "me", "find", "can",
    "i", "go", "to", "need", "want", "take", "get", "location", "of", "my",
    "tell", "how", "do", "does", "are", "in", "at", "which",
}


def extract_search_words(text):
    text = re.sub(r"[?!,.:;]", " ", text.lower())
    block_letters = re.findall(r"\b([a-z])\s+block\b", text)   # keep the "a" in "A Block"
    words = [w for w in text.split() if w not in STOP_WORDS or (len(w) == 1 and w in block_letters)]
    return [w[:-1] if len(w) > 3 and w.endswith("s") else w for w in words]


def search_locations(query):
    words = extract_search_words(query)
    if not words:
        return locations_df.iloc[0:0]

    searchable = (
        locations_df["name"].fillna("").astype(str) + " "
        + locations_df["block"].fillna("").astype(str) + " "
        + locations_df["floor"].fillna("").astype(str) + " "
        + locations_df["room"].fillna("").astype(str) + " "
        + locations_df["description"].fillna("").astype(str)
    ).str.lower().str.replace(r"[?!,.:;]", " ", regex=True)

    patterns = [re.compile(r"\b" + re.escape(w) + (r"\b" if len(w) <= 2 else "")) for w in words]
    scores = searchable.apply(lambda text: sum(bool(p.search(text)) for p in patterns))
    names = locations_df["name"].fillna("").astype(str).str.lower()
    scores = scores + names.apply(lambda text: sum(bool(p.search(text)) for p in patterns))

    best = scores.max()
    if best == 0:
        return locations_df.iloc[0:0]
    return locations_df[scores == best]


def norm_name(value):
    """Compare place names ignoring capital letters and extra spaces."""
    return " ".join(str(value).split()).casefold()


def build_graph():
    """Returns (graph, names). graph[a][b] = {"how", "minutes", "reverse"}; keys are normalised names.
    A row works in both directions. If you also add the opposite row (B -> A), its own text is used."""
    names = {}
    for place in locations_df["name"].dropna().astype(str):
        names[norm_name(place)] = " ".join(place.split())

    explicit = {}
    for _, row in paths_df.dropna(subset=["place_a", "place_b"]).iterrows():
        a, b = str(row["place_a"]), str(row["place_b"])
        key_a, key_b = norm_name(a), norm_name(b)
        if key_a == key_b:
            continue
        names.setdefault(key_a, " ".join(a.split()))
        names.setdefault(key_b, " ".join(b.split()))
        how = row.get("how_to_walk", "")
        how = "" if pd.isna(how) else str(how).strip()
        minutes = pd.to_numeric(row.get("minutes"), errors="coerce")
        minutes = 0 if pd.isna(minutes) else float(minutes)
        explicit[(key_a, key_b)] = {"how": how, "minutes": minutes, "reverse": False}

    graph = {}
    for (a, b), info in explicit.items():
        graph.setdefault(a, {})[b] = info
    for (a, b), info in explicit.items():
        if (b, a) not in explicit:
            graph.setdefault(b, {})[a] = {**info, "reverse": True}
    return graph, names


def find_route(graph, start, end):
    """Quickest route by walking minutes (a link without minutes counts as 1)."""
    if start not in graph or end not in graph:
        return None
    best = {start: 0.0}
    heap = [(0.0, 0, [start])]
    counter = 1
    while heap:
        cost, _, route = heapq.heappop(heap)
        last = route[-1]
        if last == end:
            return route
        if cost > best.get(last, float("inf")):
            continue
        for neighbour, info in graph[last].items():
            new_cost = cost + (info["minutes"] or 1)
            if new_cost < best.get(neighbour, float("inf")):
                best[neighbour] = new_cost
                heapq.heappush(heap, (new_cost, counter, route + [neighbour]))
                counter += 1
    return None


# ---- announcements + weather (right panel) ----

DOT_COLORS = ["#ff5ca8", "#8b5cf6", "#2998ff", "#10b981"]


def get_announcements():
    """data/announcements.csv (title,date,color) if you add it, otherwise the next events."""
    items = []
    if ANNOUNCEMENT_FILE.is_file():
        try:
            df = load_announcements_file(ANNOUNCEMENT_FILE.stat().st_mtime)
            for i, row in df.iterrows():
                color = clean_text(row.get("color", "")) or DOT_COLORS[i % len(DOT_COLORS)]
                items.append({"title": clean_text(row.get("title", "")), "sub": clean_text(row.get("date", "")), "color": color})
        except Exception:
            items = []
    if not items:
        for i, (_, ev) in enumerate(upcoming_events.head(4).iterrows()):
            items.append({
                "title": clean_text(ev["event"]),
                "sub": f'{ev["date"].strftime("%b %d, %Y")} · {clean_text(ev["venue"])}',
                "color": DOT_COLORS[i % len(DOT_COLORS)],
            })
    return items


def _download_weather(lat, lon):
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}&current=temperature_2m,weather_code,is_day&timezone=auto"
    )
    with urlopen(url, timeout=4) as response:
        current = json.load(response)["current"]
    return {"temp": round(current["temperature_2m"]), "code": int(current["weather_code"]), "day": int(current.get("is_day", 1))}


@st.cache_data(ttl=900, show_spinner=False)
def fetch_weather(lat, lon):
    return _download_weather(lat, lon)   # errors are not cached, so it retries next time


def get_weather():
    if COLLEGE_LAT is None:
        return None
    if time.time() - st.session_state.get("wx_failed_at", 0) < 60:
        return None
    try:
        return fetch_weather(COLLEGE_LAT, COLLEGE_LON)
    except Exception:
        st.session_state.wx_failed_at = time.time()
        return None


def weather_text(code, is_day):
    if code == 0:
        return ("☀️", "Clear Sky") if is_day else ("🌙", "Clear Night")
    if code in (1, 2):
        return "⛅", "Partly Cloudy"
    if code == 3:
        return "☁️", "Overcast"
    if code in (45, 48):
        return "🌫️", "Fog"
    if 51 <= code <= 57:
        return "🌦️", "Drizzle"
    if 61 <= code <= 67 or 80 <= code <= 82:
        return "🌧️", "Rain"
    if 71 <= code <= 77 or code in (85, 86):
        return "🌨️", "Snow"
    if code >= 95:
        return "⛈️", "Thunderstorm"
    return "🌡️", "Weather"


def weather_card_html():
    data = get_weather()
    if data:
        icon, label = weather_text(data["code"], data["day"])
        return (
            f'<div class="panel wx"><h5>Campus Weather <span class="live">Live</span></h5>'
            f'<div style="display:flex;align-items:center;gap:10px"><span style="font-size:36px">{icon}</span>'
            f'<div><div class="t">{data["temp"]}°C</div><div class="c">{label}</div></div></div>'
            f"<small>📍 SRGI Campus · Open-Meteo</small></div>"
        )
    return (
        '<div class="panel wx"><h5>Campus Weather <span class="demo">Unavailable</span></h5>'
        '<div style="display:flex;align-items:center;gap:10px"><span style="font-size:36px">🌡️</span>'
        '<div><div class="c">Weather could not be loaded right now.</div></div></div>'
        "<small>📍 SRGI Campus · needs internet</small></div>"
    )


# --------------------------------------------------
# SIDEBAR / NAVIGATION
# --------------------------------------------------

ROLE_INFO = {
    "Student": {
        "icon": "🎓",
        "message": "Welcome to SRGI! Find your courses, events, rules and campus places here.",
        "pages": [P_AI, P_NAV, P_EVENTS, P_COURSES],
        "questions": [
            "What is the minimum attendance required?",
            "What subjects are taught in AIML first year?",
        ],
    },
    "Parent": {
        "icon": "👨‍👩‍👧",
        "message": "Welcome! Here you can see admission details, courses, facilities and contacts.",
        "pages": [P_ADM, P_COURSES, P_FAC, P_CONTACT],
        "questions": [
            "What is the hostel fee?",
            "What scholarships are available?",
        ],
    },
    "Visitor": {
        "icon": "📍",
        "message": "Welcome to SRGI! Explore the campus, find places and see upcoming events.",
        "pages": [P_NAV, P_FAC, P_EVENTS],
        "questions": [
            "Where is the canteen?",
            "How do I reach the college by public transport?",
        ],
    },
}

PAGE_DESC = {
    P_AI: "Ask any question about the college.",
    P_NAV: "Find places and walking routes.",
    P_EVENTS: "Search events by branch, name or date.",
    P_ADM: "Admission details, fees and contacts.",
    P_COURSES: "Course information.",
    P_FAC: "Library, canteen, labs and more.",
    P_CONTACT: "Important contact details.",
}
PAGE_ICON = {p: p.split(" ")[0] for p in PAGES}

st.sidebar.markdown(
    '<div class="logo"><i>🎓</i><div><b>SRGI</b><small>Campus AI<br>Your Campus Companion</small></div></div>',
    unsafe_allow_html=True,
)
st.sidebar.radio(
    "Choose a feature",
    PAGES,
    key="nav",
    on_change=leave_role_page,
    label_visibility="collapsed",
)
st.sidebar.markdown(
    '<div class="quote"><em>“Your questions today, a better campus tomorrow.”</em>— SRGI Campus AI'
    '<svg viewBox="0 0 160 50" fill="none" stroke="#47D9FF"><path d="M5 48V25h150v23M20 25l60-18 60 18'
    'M40 48V32M70 48V32M100 48V32M130 48V32M80 7V2"/></svg></div>',
    unsafe_allow_html=True,
)

option = st.session_state.nav

# --- hero photo + profile avatar letter (generated from your files / USER_NAME) ---
_poster = find_poster()
if _poster:
    _uri = load_poster_data_uri(str(_poster), _poster.stat().st_mtime)
    _hero_bg = (
        ".st-key-hero{background:linear-gradient(180deg,rgba(2,13,37,.45),rgba(2,13,37,.96)),"
        "linear-gradient(90deg,rgba(2,13,37,.80),rgba(2,13,37,.10)),"
        f"url('{_uri}') center/cover no-repeat;}}"
    )
else:
    _hero_bg = (
        ".st-key-hero{background:linear-gradient(180deg,rgba(2,13,37,.35),rgba(2,13,37,.95)),"
        "radial-gradient(ellipse at 55% 75%,#c8742a 0,#7a3a3a 12%,#1c2d63 38%,#0a1a45 70%);}"
    )
_initial = html.escape((USER_NAME[:1] or "U").upper())
st.markdown(
    f"<style>{_hero_bg}"
    ".st-key-profile button::before{content:\"" + _initial + "\";display:inline-grid;place-items:center;"
    "width:34px;height:34px;margin-right:8px;border-radius:50%;font-weight:700;color:#fff;"
    "background:linear-gradient(135deg,#ff8a5c,#ff5ca8);}</style>",
    unsafe_allow_html=True,
)

# --------------------------------------------------
# HOME
# --------------------------------------------------


def render_hero():
    with st.container(key="hero"):
        with st.container(key="topbar"):
            _, col_bell, col_profile = st.columns([10, 1, 2.6])

            with col_bell:
                with st.container(key="bell_seen" if st.session_state.notif_seen else "bell_new"):
                    with st.popover("🔔"):
                        st.markdown("**Notifications**")
                        news = get_announcements()[:2]
                        if news and not st.session_state.notif_seen:
                            for item in news:
                                st.write(f"• {item['title']}")
                            st.button("Mark all read", key="mark_read", on_click=mark_notifications_seen)
                        else:
                            st.caption("You're all caught up.")

            with col_profile:
                with st.container(key="profile"):
                    with st.popover(f"{USER_NAME}"):
                        st.markdown(f"**{esc(USER_NAME)}**")
                        st.caption("Change the name with USER_NAME in app.py")
                        st.button("🎓 My student view", key="pf_student", on_click=set_role, args=("Student",))
                        st.button("📞 Help & contacts", key="pf_help", on_click=go_to, args=(P_CONTACT,))

        st.markdown(
            f'<div class="hero-h2">👋 {greeting()}, {esc(USER_NAME)}</div>'
            '<p class="hero-sub">Welcome to SRGI Campus AI</p>'
            '<div class="hero-h1">Your Campus<br><span>Information, Simplified.</span></div>'
            '<div class="hero-desc">Get quick answers, find locations, explore events, and access everything '
            "you need — all in one place.</div>"
            '<div class="hand">Explore<br>Learn<br>Grow'
            '<svg width="120" height="12" viewBox="0 0 120 12" fill="none" stroke="#47D9FF" stroke-width="2">'
            '<path d="M2 8Q60-4 118 6"/></svg></div>',
            unsafe_allow_html=True,
        )

        with st.container(key="herosearch"):
            with st.form("hero_form", clear_on_submit=False):
                col_input, col_button = st.columns([5, 1.3])
                col_input.text_input(
                    "Ask a question",
                    key="hero_q",
                    placeholder="🔍  Ask me anything about SRGI...",
                    label_visibility="collapsed",
                )
                col_button.form_submit_button("Ask AI ✈", on_click=submit_hero)
            if st.session_state.pop("hero_warn", False):
                st.warning("Please type a question first.")


def section_header(icon, title, subtitle):
    st.markdown(
        f'<div class="sh"><span>{icon}</span><div><h3>{title}</h3><small>{subtitle}</small></div></div>',
        unsafe_allow_html=True,
    )


def render_right_panel():
    with st.container(key="right_panel"):
        with st.container(key="ql_card"):
            st.markdown('<div class="panel" style="border:0;padding:0;background:none"><h5>⚡ Quick Links</h5></div>', unsafe_allow_html=True)
            st.button("📍 View Campus Map", key="ql_map", on_click=go_to, args=(P_NAV,))
            st.button("📅 Upcoming Events", key="ql_events", on_click=go_to, args=(P_EVENTS,))
            st.button("🧾 Fee Structure", key="ql_fees", on_click=go_to, args=(P_ADM,))
            if BROCHURE_FILE.is_file():
                st.download_button(
                    "🏢 Download Brochure", BROCHURE_FILE.read_bytes(),
                    file_name="SRGI_brochure.pdf", mime="application/pdf", key="ql_brochure",
                )
            else:
                st.button("🏢 Download Brochure", key="ql_brochure", on_click=no_brochure)
            st.button("📞 Contact Us", key="ql_contact", on_click=go_to, args=(P_CONTACT,))

        st.markdown(weather_card_html(), unsafe_allow_html=True)

        items = get_announcements()
        if items:
            rows = "".join(
                f'<div class="an"><i style="background:{esc(a["color"])}"></i>'
                f'<span>{esc(a["title"])}<small>{esc(a["sub"])}</small></span></div>'
                for a in items[:4]
            )
        else:
            rows = '<div class="an"><span>No announcements yet.</span></div>'
        st.markdown(f'<div class="panel"><h5>📣 Announcements</h5>{rows}</div>', unsafe_allow_html=True)


def render_home():
    with st.container(key="page_home"):
        col_main, col_right = st.columns([3.3, 1], gap="small")

        with col_main:
            with st.container(key="home_main"):
                render_hero()

                with st.container(key="home_body"):
                    section_header("👥", "How can we help you today?", "Choose what you are looking for")
                    audiences = [
                        ("stu", "🎓", "Student", "First-year assistance, courses, events and campus information."),
                        ("par", "👨‍👩‍👧", "Parent", "Important information about admissions, courses and facilities."),
                        ("vis", "📍", "Visitor", "Explore SRGI campus, facilities, events and locations."),
                    ]
                    for column, (css, icon, title, desc) in zip(st.columns(3), audiences):
                        with column:
                            overlay_card(
                                f"aud_{title.lower()}",
                                f'<div class="aud {css}"><div class="bg">{icon}</div><h4>{title}</h4>'
                                f'<p>{desc}</p><span class="go">Continue as {title} →</span></div>',
                                set_role, (title,),
                            )

                    section_header("🧠", "Campus AI Core", "Three powerful features working together")
                    core = [
                        ("f1", "🤖", "AI Search", "Ask questions about SRGI using TF-IDF + Cosine Similarity.", P_AI),
                        ("f2", "🗺️", "Navigation", "Find classrooms, labs, library and other campus locations.", P_NAV),
                        ("f3", "📅", "Events", "Discover campus events by branch, date and type.", P_EVENTS),
                    ]
                    for column, (css, icon, title, desc, target) in zip(st.columns(3), core):
                        with column:
                            overlay_card(
                                f"core_{title.lower().replace(' ', '_')}",
                                f'<div class="feat {css}"><div class="bg">{icon}</div><h4>{title}</h4>'
                                f'<p>{desc}</p><span class="ar">→</span></div>',
                                go_to, (target,),
                            )

                    head, button = st.columns([4, 1.4])
                    with head:
                        section_header("🗓️", "Upcoming Events", "See what’s happening on campus")
                    with button:
                        with st.container(key="viewall"):
                            st.button("View All Events →", key="viewall_btn", on_click=go_to, args=(P_EVENTS,))

                    home_events = upcoming_events.head(3)
                    if home_events.empty:
                        st.info("📭 No upcoming events.")
                    else:
                        render_event_grid(home_events, "home")

                    if VIDEO_FILE.is_file() or TUTORIAL_VIDEO_URL.strip():
                        section_header("🎬", "How to use SRGI Campus AI", "Watch this short tutorial")
                        if VIDEO_FILE.is_file():
                            st.video(str(VIDEO_FILE))
                        else:
                            st.video(TUTORIAL_VIDEO_URL.strip())

                st.markdown(
                    '<div class="foot">SRGI Campus AI &nbsp;|&nbsp; Smart Campus ✦ Better Tomorrow'
                    '<svg style="position:absolute;right:0;bottom:0" width="120" height="40" fill="none" stroke-width="1.5">'
                    '<path d="M0 40Q60 0 120 30" stroke="#2998FF"/><path d="M20 40Q70 8 120 38" stroke="#8b5cf6"/></svg></div>',
                    unsafe_allow_html=True,
                )

        with col_right:
            render_right_panel()


# --------------------------------------------------
# ROLE PAGE (after Student / Parent / Visitor is chosen)
# --------------------------------------------------


def render_role_page():
    role = st.session_state.role
    info = ROLE_INFO[role]

    st.button("← Back to Home", key="back_home", on_click=go_to, args=(P_HOME,))

    st.markdown(
        f'<div class="hero-card"><div class="hero-greeting">{info["icon"]} {esc(role)} Dashboard</div>'
        f'<div class="hero-title">Welcome, <span>{esc(role)}</span>!</div>'
        f'<div class="hero-description">{esc(info["message"])}</div></div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="section-title">👉 Recommended for you</div>'
        '<div class="section-subtitle">Open the pages that matter most to you</div>',
        unsafe_allow_html=True,
    )
    for number, (column, page) in enumerate(zip(st.columns(len(info["pages"])), info["pages"])):
        with column:
            overlay_card(
                f"role_{number}",
                f'<div class="feat f{number % 4 + 1}"><div class="bg">{PAGE_ICON[page]}</div>'
                f'<h4>{esc(page.split(" ", 1)[1])}</h4><p>{esc(PAGE_DESC.get(page, ""))}</p><span class="ar">→</span></div>',
                go_to, (page,),
            )

    st.markdown(
        '<div class="section-title">💡 Try asking the AI</div>'
        '<div class="section-subtitle">Open the AI Assistant and type one of these</div>',
        unsafe_allow_html=True,
    )
    for q in info["questions"]:
        st.write(f"• {q}")

    st.divider()
    st.markdown('<div class="section-title">📅 Upcoming Events</div>', unsafe_allow_html=True)
    role_events = upcoming_events.head(3)
    if role_events.empty:
        st.info("📭 No upcoming events.")
    else:
        render_event_grid(role_events, "role")

    st.divider()
    st.button("🔄 Change role", key="change_role", on_click=set_role, args=(None,))


# --------------------------------------------------
# PAGES
# --------------------------------------------------

def render_ai_page():
    page_header(
        "🤖", "AI Campus Assistant",
        "Ask me anything about the college, courses, admissions, fees, hostel, placements, exams and more.",
        "blue", ["TF-IDF", "Cosine Similarity", f"{len(faq_df)} FAQs"],
    )

    st.session_state.setdefault("ai_question", "")
    st.session_state.setdefault("ai_run", False)

    st.markdown(
        '<div class="section-title">💡 Try one of these</div>'
        '<div class="section-subtitle">Tap a question, or type your own below</div>',
        unsafe_allow_html=True,
    )
    for number, (column, sample) in enumerate(zip(st.columns(len(AI_SAMPLE_QUESTIONS)), AI_SAMPLE_QUESTIONS)):
        column.button(sample, key=f"sample_q_{number}", on_click=ask_sample, args=(sample,))

    with st.form("ai_form", clear_on_submit=False):
        question = st.text_input(
            "💬 Ask your question",
            key="ai_question",
            placeholder="Example: What is the minimum attendance required?",
        )
        submitted = st.form_submit_button("🔍 Ask AI")

    run_now = submitted or st.session_state.ai_run
    st.session_state.ai_run = False

    if not run_now:
        return
    if not question.strip():
        st.warning("Please enter a question.")
        return

    result = ai_assistant.ask(question)

    if result.get("found"):
        score = float(result.get("score", 0))
        percent = max(0, min(100, round(score * 100)))
        level = "High" if score >= 0.6 else "Medium" if score >= 0.35 else "Low"
        answer_html = esc(result.get("answer", "")).replace("\n", "<br>")
        department = esc(result.get("department", "")) or "N/A"
        matched = esc(result.get("question", ""))
        related = result.get("suggestions") or []
        related_html = ""
        if related:
            related_html = '<div class="matched">💡 Related: ' + " &nbsp;•&nbsp; ".join(esc(q) for q in related) + "</div>"

        st.markdown(
            f'<div class="answer-card"><div class="answer-label">🤖 ANSWER</div>'
            f'<div class="answer-text">{answer_html}</div>'
            f'<div class="answer-meta"><span class="chip">🏛️ Department: {department}</span></div>'
            f'<div class="meter-text">AI matching confidence: {score:.2f} ({level})</div>'
            f'<div class="meter-bar"><div class="meter-fill" style="width:{percent}%"></div></div>'
            f'<div class="matched">🔎 Matched FAQ: {matched}</div>{related_html}</div>',
            unsafe_allow_html=True,
        )
    else:
        suggestions = result.get("suggestions") or []
        hint = (
            "Did you mean: " + " &nbsp;•&nbsp; ".join(esc(q) for q in suggestions)
            if suggestions
            else "Try keywords such as fees, admission, hostel, AIML, attendance, placement, library."
        )
        st.markdown(
            f'<div class="notfound-card"><div class="answer-label">😕 NO RELIABLE ANSWER</div>'
            f'<div class="answer-text">{esc(result.get("answer", "Sorry, I could not find an answer."))}</div>'
            f'<div class="matched">💡 {hint}</div></div>',
            unsafe_allow_html=True,
        )


def render_navigation_page():
    link_count = len(paths_df.dropna(subset=["place_a", "place_b"]))
    page_header(
        "🗺️", "Campus Navigation",
        "Ask where a classroom, laboratory, library, canteen or other campus location is.",
        "green", [f"{len(locations_df)} places", f"{link_count} walking links"],
    )

    st.session_state.setdefault("loc_query", "")

    st.markdown(
        '<div class="section-title">🔍 Where do you want to go?</div>'
        '<div class="section-subtitle">Type a place, or tap a popular one</div>',
        unsafe_allow_html=True,
    )

    all_places = locations_df["name"].astype(str).tolist()
    popular = [p for p in ["Library", "Canteen", "Computer Lab", "Main Gate"] if p in all_places]
    if popular:
        for number, (column, place) in enumerate(zip(st.columns(len(popular)), popular)):
            column.button(place, key=f"place_{number}", on_click=set_place_query, args=(place,))

    search_location = st.text_input(
        "🔍 Ask where you want to go",
        key="loc_query",
        placeholder="Example: Where is the computer lab?",
        label_visibility="collapsed",
    )

    if search_location.strip():
        results = search_locations(search_location)

        if results.empty:
            st.markdown(
                '<div class="notfound-card"><div class="answer-label">😕 LOCATION NOT FOUND</div>'
                '<div class="answer-text">I couldn\'t find that location. Try asking something like:</div>'
                '<div class="matched">• Where is the computer lab?<br>• Where is the library?<br>'
                "• Where is C-101?<br>• Show me the canteen.</div></div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(f'<div class="result-count">📍 Found {len(results)} location(s)</div>', unsafe_allow_html=True)

            for _, location in results.iterrows():
                crumbs = []
                for icon, label, column in [("🏢", "", "block"), ("⬇️", "", "floor"), ("🚪", "Room ", "room")]:
                    value = location.get(column, "")
                    if pd.notna(value) and str(value).strip():
                        crumbs.append(f'<span class="crumb">{icon} {label}{esc(str(value).strip())}</span>')
                crumb_html = '<span class="crumb-arrow">→</span>'.join(crumbs)
                description = clean_text(location.get("description", ""))

                col_info, col_image = st.columns([3, 2])

                with col_info:
                    st.markdown(
                        f'<div class="loc-card"><div class="loc-name">📍 {esc(location["name"])}</div>'
                        f'<div class="crumbs">{crumb_html}</div><div class="loc-desc">{esc(description)}</div></div>',
                        unsafe_allow_html=True,
                    )

                with col_image:
                    image_name = clean_text(location.get("image", ""))
                    image_path = IMAGE_DIR / image_name if image_name else None
                    if image_path is not None and image_path.is_file():
                        st.image(str(image_path), caption=location["name"])
                    else:
                        st.info("🖼️ Image not available yet.")
                        if image_name:
                            st.caption(f"Expected image: {image_name}")

    st.divider()
    st.markdown(
        '<div class="section-title">🧭 Find a Route (From → To)</div>'
        '<div class="section-subtitle">Choose where you are and where you want to go</div>',
        unsafe_allow_html=True,
    )

    graph, names = build_graph()

    if not graph:
        st.info("No verified campus paths yet. Add real walking links to data/paths.csv to turn on routes.")
        return

    known = {norm_name(p) for p in locations_df["name"].dropna().astype(str)}
    unknown = [names[key] for key in graph if key not in known]
    if unknown:
        st.warning(
            "These names in paths.csv do not match any name in locations.csv (check spelling): "
            + ", ".join(sorted(unknown))
        )

    place_names = locations_df["name"].astype(str).tolist()

    with st.container(border=True):
        col_from, col_to = st.columns(2)
        start = col_from.selectbox("📍 From", place_names, key="route_from")
        end = col_to.selectbox("🏁 To", place_names, index=min(1, len(place_names) - 1), key="route_to")
        show_route = st.button("🧭 Show route", key="route_button")

    if not show_route:
        return
    if start == end:
        st.info("You are already there!")
        return

    key_start, key_end = norm_name(start), norm_name(end)
    route = find_route(graph, key_start, key_end)
    if route is None:
        lonely = [name for name, key in ((start, key_start), (end, key_end)) if key not in graph]
        if lonely:
            st.warning(
                "No walking link in data/paths.csv mentions: " + ", ".join(lonely)
                + ". Add a row that connects it to another place."
            )
        else:
            st.warning(
                f"No path from {start} to {end} yet. The places are in paths.csv but are not connected "
                "to each other through any chain of links. Add the missing link."
            )
        return

    total_minutes = 0
    steps_html = [f'<div class="route-start">🟢 Start: {esc(names[route[0]])}</div>']
    for i in range(len(route) - 1):
        step = graph[route[i]][route[i + 1]]
        total_minutes += step["minutes"]
        detail = esc(("↩ Reverse of: " if step.get("reverse") and step["how"] else "") + step["how"])
        if step["minutes"]:
            detail += f' · ⏱️ about {step["minutes"]:g} min'
        detail_html = f'<div class="route-how">{detail}</div>' if detail.strip() else ""
        steps_html.append(
            f'<div class="route-step"><div class="route-dot">{i + 1}</div>'
            f'<div class="route-body"><div class="route-place">{esc(names[route[i]])} → {esc(names[route[i + 1]])}</div>'
            f"{detail_html}</div></div>"
        )
    steps_html.append(f'<div class="route-end">🏁 Destination: {esc(names[route[-1]])}</div>')

    time_text = f" · about {total_minutes:g} minutes" if total_minutes else ""
    st.markdown(
        f'<div class="route-summary">✅ Route found · {len(route) - 1} step(s){time_text}</div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="route-timeline">' + "".join(steps_html) + "</div>", unsafe_allow_html=True)


def safe_cell(value):
    """Stop spreadsheet formulas: a cell starting with = + - @ gets a leading apostrophe."""
    text = str(value).strip().replace("\r", " ").replace("\n", " ")
    return "'" + text if text[:1] in ("=", "+", "-", "@") else text


def append_csv_row(path, columns, row):
    """Add one row at the end of a CSV file (creates the file with a header if needed)."""
    needs_header = not path.is_file() or path.stat().st_size == 0
    needs_newline = False
    if not needs_header:
        with open(path, "rb") as f:
            f.seek(-1, 2)
            needs_newline = f.read(1) not in (b"\n", b"\r")
    with open(path, "a", newline="", encoding="utf-8") as f:
        if needs_newline:
            f.write("\n")
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        if needs_header:
            writer.writeheader()
        writer.writerow(row)


def render_organise_form():
    st.markdown(
        '<div class="section-title">📝 Organise an Event</div>'
        '<div class="section-subtitle">Planning a workshop, contest or fest? Fill in the details below.</div>',
        unsafe_allow_html=True,
    )

    message = st.session_state.pop("organise_msg", None)
    if message:
        st.success(message)

    with st.form("organise_form", clear_on_submit=True):
        col_a, col_b = st.columns(2)
        name = col_a.text_input("🎯 Event name *", placeholder="Example: AI Workshop")
        date = col_b.date_input("📅 Date *", min_value=today.date())

        col_c, col_d = st.columns(2)
        venue = col_c.text_input("📍 Venue *", placeholder="Example: Seminar Hall")
        time_text = col_d.text_input("🕐 Time", placeholder="Example: 10:00 AM - 12:00 PM")

        branches = st.multiselect("🎓 Open to which branches?", ["All Branches"] + BRANCHES, default=["All Branches"])

        col_e, col_f = st.columns(2)
        organizer = col_e.text_input("👥 Organiser (club / department / your name) *")
        contact = col_f.text_input("📞 Contact (email or phone) *")

        description = st.text_area("📄 What is the event about? *", placeholder="Two or three lines are enough.")
        registration = st.text_input("🎫 Registration link (optional)", placeholder="https://...")

        submitted = st.form_submit_button("📨 Submit event")

    if not submitted:
        note = (
            "Your event is added to the calendar straight away."
            if AUTO_PUBLISH_EVENTS
            else "Submitted events are reviewed by the college before they appear in the calendar."
        )
        st.caption(f"ℹ️ {note}  Fields marked * are required.")
        return

    problems = []
    if not name.strip():
        problems.append("event name")
    if not venue.strip():
        problems.append("venue")
    if not organizer.strip():
        problems.append("organiser")
    if not contact.strip():
        problems.append("contact")
    if not description.strip():
        problems.append("description")
    if problems:
        st.error("Please fill in: " + ", ".join(problems) + ".")
        return
    if registration.strip() and not registration.strip().lower().startswith(("http://", "https://")):
        st.error("The registration link must start with http:// or https://")
        return

    row = {
        "date": date.strftime("%Y-%m-%d"),
        "event": safe_cell(name),
        "venue": safe_cell(venue),
        "time": safe_cell(time_text),
        "branch": "; ".join(branches) if branches else "All Branches",
        "organizer": safe_cell(organizer),
        "description": safe_cell(description),
        "registration": registration.strip(),
        "banner": "",
        "contact": safe_cell(contact),
        "submitted_at": now.strftime("%Y-%m-%d %H:%M"),
    }

    try:
        if AUTO_PUBLISH_EVENTS:
            append_csv_row(EVENT_FILE, EVENT_COLUMNS, row)
            st.cache_data.clear()
            st.session_state.organise_msg = f"✅ “{name.strip()}” was added to the events calendar."
        else:
            append_csv_row(EVENT_REQUEST_FILE, REQUEST_COLUMNS, row)
            st.session_state.organise_msg = f"✅ Thank you! “{name.strip()}” was submitted for approval."
    except OSError as error:
        st.error(f"Could not save the event: {error}")
        return
    st.rerun()


def render_events_page():
    opened = st.session_state.event_open
    if opened is not None and opened in events_df.index:
        st.button("← Back to events", key="ev_back", on_click=close_event)
        render_event_full(events_df.loc[opened])
        return

    page_header(
        "📅", "Campus Events",
        "Workshops, festivals and competitions. Find them by branch, name or date.",
        "orange", [f"{len(upcoming_events)} upcoming", f"{len(events_df)} in total"],
    )

    tab_all, tab_organise = st.tabs(["📋 All Events", "📝 Organise Event"])
    with tab_organise:
        render_organise_form()
    with tab_all:
        render_event_lists()


def render_event_lists():
    st.markdown(
        '<div class="section-title">🔔 Upcoming Events</div>'
        '<div class="section-subtitle">Tap an event to see its details</div>',
        unsafe_allow_html=True,
    )
    if upcoming_events.empty:
        st.info("📭 No upcoming events.")
    else:
        render_event_grid(upcoming_events, "page")

    st.divider()
    st.markdown(
        '<div class="section-title">🔎 Find Events</div>'
        '<div class="section-subtitle">Use one filter or combine them</div>',
        unsafe_allow_html=True,
    )

    with st.container(border=True):
        col_branch, col_name = st.columns(2)
        branch_choice = col_branch.selectbox("🎓 Branch", ["All Branches"] + BRANCHES)
        name_text = col_name.text_input("🔎 Event name", placeholder="Example: Coding Competition")
        use_date = st.checkbox("📅 Filter by date")
        selected_date = st.date_input("Select event date") if use_date else None

    branch_mask = pd.Series(
        [event_matches_branch(row, branch_choice) for _, row in events_df.iterrows()],
        index=events_df.index,
        dtype=bool,
    )
    filtered = events_df[branch_mask]

    if name_text.strip():
        filtered = filtered[
            filtered["event"].astype(str).str.lower().str.contains(name_text.lower().strip(), regex=False, na=False)
        ]
    if use_date:
        filtered = filtered[filtered["date"].dt.date == selected_date]

    if filtered.empty:
        st.warning("❌ No events match your filters.")
    else:
        st.markdown(f'<div class="result-count">🎉 Found {len(filtered)} event(s)</div>', unsafe_allow_html=True)
        for _, event in filtered.iterrows():
            render_event_full(event)


# --------------------------------------------------
# ROUTER
# --------------------------------------------------

if st.session_state.view == "role" and st.session_state.role:
    render_role_page()
elif option == P_HOME:
    render_home()
elif option == P_AI:
    render_ai_page()
elif option == P_NAV:
    render_navigation_page()
elif option == P_EVENTS:
    render_events_page()
elif option == P_ADM:
    render_faq_page(
        "📝", "Admissions", "About SRGI and applying: eligibility, documents, fees and dates.",
        "blue", ("general", "admissions", "fees"), show_department=True,
    )
elif option == P_COURSES:
    render_faq_page(
        "📚", "Courses", "Programs, subjects, faculty, exams and placements.",
        "purple", ("courses", "faculty", "exams", "placements"),
    )
elif option == P_FAC:
    render_faq_page(
        "🏛️", "Campus Facilities", "Library, labs, canteen, hostel, clubs and other campus facilities.",
        "green", ("facilities", "library", "food", "hostel", "transport", "health and safety", "clubs and events"),
    )
elif option == P_CONTACT:
    render_faq_page(
        "📞", "Important Contacts", "Who to contact, and how, for different needs.",
        "orange", ("contacts",), show_department=True,
    )