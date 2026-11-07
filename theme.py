"""Visual design system: CSS and small HTML components for Streamlit."""

import html

import project_info as info
import streamlit as st

PALETTES = {
    "Midnight Indigo": ["#243B7A", "#6675E8", "#91A3F4", "#B9C9FA"],
    "Ocean Blue": ["#1D4ED8", "#0EA5E9", "#60A5FA", "#A7C9E8"],
    "Emerald": ["#047857", "#10B981", "#6EE7B7", "#B7E4C7"],
    "Royal Purple": ["#6D28D9", "#8B5CF6", "#A78BFA", "#C4B5FD"],
    "Sunset": ["#EA580C", "#F59E0B", "#FBBF24", "#FDE68A"],
    "Midnight": ["#14213D", "#1D4ED8", "#457B9D", "#A8DADC"],
    "Teal": ["#0F766E", "#14B8A6", "#5EEAD4", "#99F6E4"],
    "Ruby": ["#BE123C", "#F43F5E", "#FB7185", "#FDA4AF"],
    "Forest": ["#14532D", "#16A34A", "#4ADE80", "#BBF7D0"],
    "Graphite": ["#1E293B", "#475569", "#94A3B8", "#CBD5E1"],
}

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, .stApp, .stApp p, .stApp label, .stApp li, .stApp button,
.stApp input, .stApp textarea, .stApp h1, .stApp h2, .stApp h3, .stApp h4 {
    font-family: 'Inter', system-ui, -apple-system, sans-serif;
}
#MainMenu, footer { visibility: hidden; }
header[data-testid="stHeader"] { background: transparent; }
.stApp { background: #F5F7FB; }
.block-container { padding: 1.6rem 2.2rem 4rem; max-width: 1320px; }

section[data-testid="stSidebar"] {
    background: #FFFFFF; border-right: 1px solid #E5EAF2;
}
.dp-brand { display: flex; align-items: center; gap: 11px; margin-bottom: 2px; }
.dp-logo {
    width: 38px; height: 38px; border-radius: 11px; color: #fff; font-size: 20px;
    display: grid; place-items: center;
    background: linear-gradient(135deg, var(--accent), var(--accent2));
    box-shadow: 0 6px 16px var(--accent-soft);
}
.dp-brand-name { font-size: 19px; font-weight: 800; letter-spacing: -0.02em; color: #0F172A; }
.dp-brand-tag { color: #64748B; font-size: 12px; margin: 2px 0 14px; }
.dp-step {
    font-size: 11px; font-weight: 700; letter-spacing: 0.08em; color: #64748B;
    text-transform: uppercase; margin: 18px 0 6px;
}

.dp-hero {
    position: relative; overflow: hidden; color: #fff;
    padding: 34px 38px; border-radius: 22px; margin-bottom: 22px;
    background: linear-gradient(120deg, var(--accent), var(--accent2));
    box-shadow: 0 18px 40px -18px var(--accent);
}
.dp-hero::after {
    content: ""; position: absolute; right: -70px; top: -90px;
    width: 300px; height: 300px; border-radius: 50%;
    background: rgba(255,255,255,0.13);
}
.dp-hero-title { font-size: 33px; font-weight: 800; letter-spacing: -0.03em; line-height: 1.15; }
.dp-hero-sub { font-size: 15px; opacity: 0.92; margin: 8px 0 16px; max-width: 640px; }
.dp-chip {
    display: inline-block; padding: 4px 13px; border-radius: 999px; margin: 0 6px 6px 0;
    background: rgba(255,255,255,0.2); font-size: 12px; font-weight: 600;
}
.dp-chip-soft { background: var(--accent-soft); color: var(--accent); }

.dp-section { font-size: 19px; font-weight: 700; color: #0F172A; margin: 30px 0 2px; letter-spacing: -0.01em; }
.dp-section-sub { color: #64748B; font-size: 13px; margin-bottom: 14px; }

.dp-kpi {
    position: relative; background: #fff; border: 1px solid #E5EAF2; border-radius: 16px;
    padding: 18px 20px 18px 24px; margin-bottom: 14px; min-height: 100px;
    box-shadow: 0 1px 2px rgba(15,23,42,0.04); overflow-wrap: anywhere;
    transition: transform .15s ease, box-shadow .15s ease;
}
.dp-kpi:hover { transform: translateY(-2px); box-shadow: 0 10px 24px -12px rgba(15,23,42,0.25); }
.dp-kpi::before {
    content: ""; position: absolute; left: 0; top: 16px; bottom: 16px; width: 4px;
    border-radius: 0 4px 4px 0; background: var(--accent);
}
.dp-kpi-label { font-size: 12px; font-weight: 600; color: #64748B; }
.dp-kpi-value { font-size: 26px; font-weight: 800; color: #0F172A; margin-top: 10px; letter-spacing: -0.02em; }

.dp-card {
    background: #fff; border: 1px solid #E5EAF2; border-radius: 16px;
    padding: 18px 22px; margin-bottom: 14px; box-shadow: 0 1px 2px rgba(15,23,42,0.04);
}
.dp-card-title { font-size: 11px; font-weight: 700; letter-spacing: 0.08em; color: #64748B; text-transform: uppercase; }
.dp-domain { font-size: 20px; font-weight: 700; color: #0F172A; margin: 6px 0 10px; }

.dp-insight { display: flex; gap: 16px; align-items: flex-start; }
.dp-num {
    flex: 0 0 30px; height: 30px; border-radius: 50%; display: grid; place-items: center;
    background: var(--accent-soft); color: var(--accent); font-weight: 700; font-size: 13px;
}
.dp-finding { font-weight: 600; color: #0F172A; line-height: 1.5; }
.dp-action { color: #475569; font-size: 14px; margin-top: 4px; line-height: 1.5; }

.dp-features { display: grid; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr)); gap: 16px; margin: 6px 0 18px; }
.dp-feature { background: #fff; border: 1px solid #E5EAF2; border-radius: 18px; padding: 22px; }
.dp-feature-icon {
    width: 44px; height: 44px; border-radius: 12px; display: grid; place-items: center;
    font-size: 22px; background: var(--accent-soft); margin-bottom: 14px;
}
.dp-feature-title { font-weight: 700; color: #0F172A; margin-bottom: 6px; }
.dp-feature-text { color: #64748B; font-size: 14px; line-height: 1.55; }

.stTabs [data-baseweb="tab-list"] { gap: 8px; border-bottom: none; }
.stTabs [data-baseweb="tab"] {
    background: #fff; border: 1px solid #E5EAF2; border-radius: 12px;
    padding: 9px 20px; height: auto; font-weight: 600;
}
.stTabs [data-baseweb="tab"] p { color: #475569; font-weight: 600; }
.stTabs [aria-selected="true"] { background: var(--accent); border-color: var(--accent); }
.stTabs [aria-selected="true"] p { color: #fff; }
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] { display: none; }

[data-testid="stMetric"] {
    background: #fff; border: 1px solid #E5EAF2; border-radius: 16px; padding: 16px 20px;
}
[data-testid="stVerticalBlockBorderWrapper"] { border-radius: 16px; background: #fff; }
.stButton > button, .stDownloadButton > button { border-radius: 11px; font-weight: 600; }
.stButton > button[kind="primary"], .stDownloadButton > button[kind="primary"] {
    background: var(--accent); border: none; color: #fff;
}
[data-testid="stExpander"] { border-radius: 14px; background: #fff; }

/* Enterprise workspace styling */
:root {
    --navy: #111B36;
    --ink: #17213B;
    --muted: #71809D;
    --line: #E4E9F3;
    --surface: #FFFFFF;
}
.stApp {
    background:
        radial-gradient(ellipse at 86% 0%, rgba(102,117,232,.08), transparent 34rem),
        #F5F7FC;
    color: var(--ink);
}
.block-container {
    max-width: 1440px;
    padding: 2rem clamp(1rem, 3vw, 3rem) 2rem;
}
h1, h2, h3, h4 { color: var(--navy); letter-spacing: -.025em; }
p, li, label { line-height: 1.55; }
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #111B36 0%, #17264A 100%);
    border-right: 1px solid rgba(255,255,255,.08);
}
section[data-testid="stSidebar"] > div { padding: 1.1rem .85rem 1.5rem; }
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
section[data-testid="stSidebar"] [data-testid="stCaptionContainer"],
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {
    color: #D7DFF1;
}
section[data-testid="stSidebar"] [data-testid="stRadio"] label {
    border: 1px solid transparent;
    border-radius: 10px;
    padding: .48rem .6rem;
    margin: .12rem 0;
    transition: background-color .12s ease, border-color .12s ease;
}
section[data-testid="stSidebar"] [data-testid="stRadio"] label:hover {
    background: rgba(255,255,255,.07);
}
section[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) {
    background: rgba(123,143,255,.18);
    border-color: rgba(166,180,255,.22);
}
section[data-testid="stSidebar"] [data-testid="stRadio"] label p {
    color: #F7F8FC;
    font-weight: 600;
}
section[data-testid="stSidebar"] [data-testid="stExpander"] {
    background: rgba(255,255,255,.055);
    border: 1px solid rgba(255,255,255,.1);
}
section[data-testid="stSidebar"] [data-testid="stExpander"] summary {
    color: #F7F8FC;
}
.dp-brand {
    gap: 12px;
    padding: 8px 4px 12px;
}
.dp-logo {
    width: 42px;
    height: 42px;
    border: 1px solid rgba(255,255,255,.28);
    border-radius: 13px;
    background: linear-gradient(145deg, #7888F4, #5368D7 58%, #344B9C);
    box-shadow: 0 8px 22px rgba(5,12,35,.28);
    font-size: 19px;
    font-weight: 800;
}
.dp-brand-name {
    color: #FFFFFF;
    font-size: 18px;
    letter-spacing: -.035em;
}
.dp-brand-tag {
    color: #AEBBDD;
    font-size: 11px;
    margin: -5px 0 14px 58px;
}
.dp-step {
    color: #9EACD0;
    margin: 14px 0 7px;
}
.dp-hero {
    padding: clamp(24px, 4vw, 42px);
    border: 1px solid rgba(255,255,255,.28);
    border-radius: 22px;
    background: linear-gradient(118deg, #17264B 0%, #293B78 52%, #5365C8 100%);
    box-shadow: 0 18px 42px -26px rgba(25,41,98,.68);
}
.dp-hero-title { font-size: clamp(27px, 3vw, 36px); }
.dp-hero-sub { color: #E0E6F7; max-width: 760px; }
.dp-chip {
    border: 1px solid rgba(255,255,255,.15);
    background: rgba(255,255,255,.12);
}
.dp-section {
    margin: 12px 0 4px;
    font-size: 21px;
    letter-spacing: -.035em;
}
.dp-section-sub { color: var(--muted); margin-bottom: 16px; }
.dp-kpi, .dp-card, .dp-feature, [data-testid="stMetric"] {
    border-color: var(--line);
    box-shadow: 0 4px 16px rgba(26,42,82,.035);
}
.dp-kpi { min-height: 110px; }
.dp-kpi-value { color: var(--navy); }
.dp-feature {
    border-radius: 16px;
    padding: 24px;
}
.dp-feature-icon {
    color: var(--accent);
    border: 1px solid var(--accent-soft);
}
div[data-testid="stFileUploader"] {
    padding: 14px 18px;
    background: #FFFFFF;
    border: 1px dashed #B7C2DA;
    border-radius: 15px;
}
.stButton > button, .stDownloadButton > button {
    min-height: 42px;
    border: 1px solid #DCE3F0;
    border-radius: 10px;
    font-weight: 650;
}
.stButton > button[kind="primary"], .stDownloadButton > button[kind="primary"] {
    background: linear-gradient(110deg, var(--accent), var(--accent2));
    box-shadow: 0 6px 16px var(--accent-soft);
}
input, textarea, [data-baseweb="select"] > div {
    border-radius: 9px !important;
}
.dp-welcome {
    margin: 20px 0;
    padding: clamp(24px, 4vw, 42px);
    text-align: center;
    background: linear-gradient(180deg, #FFFFFF, #FAFBFE);
    border: 1px solid var(--line);
    border-radius: 20px;
    box-shadow: 0 12px 36px rgba(26,42,82,.045);
}
.dp-welcome-mark {
    display: inline-grid;
    place-items: center;
    width: 64px;
    height: 64px;
    margin-bottom: 12px;
    border-radius: 19px;
    color: #FFFFFF;
    font-size: 28px;
    font-weight: 800;
    background: linear-gradient(145deg, #7888F4, #344B9C);
}
.dp-welcome-title {
    color: var(--navy);
    font-size: clamp(23px, 3vw, 31px);
    font-weight: 750;
    letter-spacing: -.04em;
}
.dp-welcome-copy {
    max-width: 650px;
    margin: 8px auto 0;
    color: var(--muted);
}
.dp-footer {
    margin-top: 40px;
    padding: 22px 10px 8px;
    border-top: 1px solid var(--line);
    color: #8290AA;
    text-align: center;
    font-size: 12px;
    line-height: 1.8;
}
.dp-footer b { color: #35456E; }
@media (max-width: 700px) {
    .block-container { padding: 1.1rem 1rem 1.7rem; }
    .dp-hero { border-radius: 17px; }
    .dp-features { grid-template-columns: 1fr; }
}
"""


def inject_css(colors):
    st.markdown(
        f"<style>{CSS}:root{{--accent:{colors[0]};--accent2:{colors[1]};"
        f"--accent-soft:{colors[0]}1F;}}</style>",
        unsafe_allow_html=True,
    )


def esc(value):
    return html.escape(str(value))


def brand():
    st.markdown(
        '<div class="dp-brand"><div class="dp-logo">D</div>'
        '<div class="dp-brand-name">DataPilot AI</div></div>'
        '<div class="dp-brand-tag">Your Autonomous AI Business Analyst</div>',
        unsafe_allow_html=True,
    )


def step(label):
    st.markdown(f'<div class="dp-step">{esc(label)}</div>', unsafe_allow_html=True)


def hero(title, subtitle, chips=()):
    chip_html = "".join(f'<span class="dp-chip">{esc(c)}</span>' for c in chips)
    st.markdown(
        f'<div class="dp-hero"><div class="dp-hero-title">{esc(title)}</div>'
        f'<div class="dp-hero-sub">{esc(subtitle)}</div>{chip_html}</div>',
        unsafe_allow_html=True,
    )


def section(title, sub=""):
    sub_html = f'<div class="dp-section-sub">{esc(sub)}</div>' if sub else ""
    st.markdown(
        f'<div class="dp-section">{esc(title)}</div>{sub_html}',
        unsafe_allow_html=True,
    )


def kpi_card(label, value):
    return (
        f'<div class="dp-kpi"><div class="dp-kpi-label">{esc(label)}</div>'
        f'<div class="dp-kpi-value">{esc(value)}</div></div>'
    )


def chips_html(items):
    return "".join(f'<span class="dp-chip dp-chip-soft">{esc(i)}</span>' for i in items)


def insight_card(number, finding, action):
    return (
        '<div class="dp-card"><div class="dp-insight">'
        f'<div class="dp-num">{number}</div><div>'
        f'<div class="dp-finding">{esc(finding)}</div>'
        f'<div class="dp-action">→ {esc(action)}</div>'
        '</div></div></div>'
    )


def feature_grid(features):
    cards = "".join(
        f'<div class="dp-feature"><div class="dp-feature-icon">{icon}</div>'
        f'<div class="dp-feature-title">{esc(title)}</div>'
        f'<div class="dp-feature-text">{esc(text)}</div></div>'
        for icon, title, text in features
    )
    st.markdown(f'<div class="dp-features">{cards}</div>', unsafe_allow_html=True)


def footer():
    st.markdown(
        '<div class="dp-footer"><b>DataPilot AI</b> | Autonomous Business Intelligence'
        f'<br>{esc(info.CREDIT_LINE)} · {esc(info.AUTHOR_QUALIFICATION)}'
        f'<br>{esc(info.AUTHOR_EMAIL)} · {esc(info.AUTHOR_PHONE)}</div>',
        unsafe_allow_html=True,
    )


def credits():
    section("Credits & contact", "Project author and professional background.")
    with st.container(border=True):
        st.markdown(f"**{info.AUTHOR_NAME}**")
        st.caption(info.AUTHOR_QUALIFICATION)
        st.markdown(f"Email: [{info.AUTHOR_EMAIL}](mailto:{info.AUTHOR_EMAIL})")
        st.markdown(f"Mobile: [{info.AUTHOR_PHONE}](tel:{info.AUTHOR_PHONE_LINK})")
