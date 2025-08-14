import base64
import os
import mimetypes
from pathlib import Path
from textwrap import dedent
import time


import pandas as pd
import streamlit as st

# -----------------------------
# Config
# -----------------------------
st.set_page_config(page_title="Villa Olympics", layout="wide")

FINISH_LINE = 100                 # points needed to "finish"
MIN_LANE_H = 54   # smallest lane height when you have lots of players
MAX_LANE_H = 90   # biggest lane height when you have just a few
LANE_GAP   = 10   # space between lanes (px)
AVATAR_PX = 64   # keep in sync with .avatar { width/height }


CSV_PATH_DEFAULT = "players.csv"  # editable roster
BACKGROUND_IMAGE = "https://github.com/liddyt100/VillaOlympics/blob/main/VillaOlympicsWebApp/Assets/background.jpeg?raw=true"

# Theme tweaks
TITLE_COLOUR = "#FFFFFF"
TEXT_COLOUR  = "#F5F7FA"
OVERLAY_OPACITY = 0.55  # 0..1 darkness behind content

# -----------------------------
# Data helpers
# -----------------------------
def read_players(csv_path: str) -> pd.DataFrame:
    if not os.path.exists(csv_path):
        return pd.DataFrame(columns=["name", "points", "avatar"])
    df = pd.read_csv(csv_path)
    if "points" in df:
        df["points"] = pd.to_numeric(df["points"], errors="coerce").fillna(0).astype(float)
    for col in ["name", "avatar"]:
        if col in df:
            df[col] = df[col].fillna("")
    return df

def write_players(df: pd.DataFrame, csv_path: str):
    save_cols = ["name", "points", "avatar"]
    for c in save_cols:
        if c not in df.columns:
            df[c] = ""
    df[save_cols].to_csv(csv_path, index=False)

def bump_points(player_name: str, delta: float):
    df = st.session_state.get("players", pd.DataFrame())
    if df.empty or "name" not in df.columns:
        return
    # normalize names on compare
    mask = df["name"].astype(str).str.strip() == str(player_name).strip()
    if not mask.any():
        return
    pts = pd.to_numeric(df.loc[mask, "points"], errors="coerce").fillna(0.0)
    df.loc[mask, "points"] = (pts + delta).clip(lower=0)  # no negatives
    st.session_state["players"] = df
    # freeze resorting for a short moment so buttons don't jump under the cursor
    st.session_state["sort_frozen_until"] = time.time() + 0.8  # seconds

def get_leaderboard_df():
    df = st.session_state["players"].copy()
    df["points"] = pd.to_numeric(df["points"], errors="coerce").fillna(0.0)
    df["name"] = df["name"].astype(str).str.strip()

    live_sort = st.session_state.get("live_sort", True)
    now = time.time()
    freeze_until = st.session_state.get("sort_frozen_until", 0)

    # Use a stable display order list in session_state
    display_order = st.session_state.get("display_order", list(df["name"]))

    if live_sort:
        if now < freeze_until and display_order:
            # while frozen, keep previous visual order
            df = df.set_index("name").reindex([n for n in display_order if n in df["name"].values]).reset_index()
        else:
            # resort and remember this order
            df = df.sort_values(["points", "name"], ascending=[False, True]).reset_index(drop=True)
            st.session_state["display_order"] = df["name"].tolist()
    else:
        # fixed order mode (first load uses CSV order)
        if not display_order:
            display_order = list(df["name"])
        df = df.set_index("name").reindex([n for n in display_order if n in df["name"].values]).reset_index()

    return df



# -----------------------------
# Image helpers
# -----------------------------

from textwrap import dedent  # make sure this import is at the top

def render_html(html: str):
    """Render left-aligned HTML so Streamlit doesn't treat it as a code block."""
    html = dedent(html).strip()
    html = "\n".join(line.lstrip() for line in html.splitlines())
    st.markdown(html, unsafe_allow_html=True)


def file_to_data_uri(file_bytes: bytes, mime: str) -> str:
    b64 = base64.b64encode(file_bytes).decode("utf-8")
    return f"data:{mime};base64,{b64}"

def local_path_to_data_uri(path_str: str) -> str:
    p = Path(path_str)
    if not (p.exists() and p.is_file()):
        return ""
    mime, _ = mimetypes.guess_type(str(p))
    mime = mime or "image/png"
    with open(p, "rb") as f:
        return file_to_data_uri(f.read(), mime)

def normalise_remote_url(u: str) -> str:
    """Turn common share links into direct image URLs (GitHub raw, etc.)."""
    u = (u or "").strip()
    if not u:
        return u
    if "github.com" in u and "/blob/" in u:
        owner_repo, blob_path = u.split("github.com/", 1)[1].split("/blob/", 1)
        return f"https://raw.githubusercontent.com/{owner_repo}/{blob_path}"
    return u

def path_or_upload_to_url(path_str: str, upload) -> str:
    """
    Returns a browser-usable image URL/URI with this precedence:
      1) uploaded image -> data: URI
      2) existing usable string starting with data:/http(s) -> (normalised) pass-through
      3) local file path -> embed as data: URI
      4) otherwise -> ""
    """
    if upload is not None:
        bytes_ = upload.read()
        name = (upload.name or "").lower()
        mime = "image/jpeg" if name.endswith((".jpg", ".jpeg")) else "image/png"
        return file_to_data_uri(bytes_, mime)

    s = (path_str or "").strip()
    if not s:
        return ""
    if s.startswith(("data:", "http://", "https://")):
        return normalise_remote_url(s)

    return local_path_to_data_uri(s)

# -----------------------------
# Page styling
# -----------------------------

def inject_page_bg(image_url: str):
    if not image_url:
        return
    st.markdown(
        f"""
        <style>
        /* Background image */
        .stApp {{
            background-image: url('{image_url}');
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
        }}

        /* Remove Streamlit's white header/toolbar */
        header[data-testid="stHeader"] {{
            background: transparent;
            height: 0;
        }}
        header[data-testid="stHeader"] * {{ visibility: hidden; }}
        div[data-testid="stToolbar"] {{ display: none; }}

        /* Full-width content with dark glass overlay */
        [data-testid="stAppViewContainer"] .block-container {{
            max-width: 100% !important;
            padding: 0.75rem 1.25rem 1.25rem;
            background: rgba(0,0,0,{OVERLAY_OPACITY});
            border-radius: 16px;
        }}

        /* Sidebar glass + readable text */
        section[data-testid="stSidebar"] .block-container {{
            background: rgba(0,0,0,0.55);
            color: {TEXT_COLOUR};
        }}

        /* Typography */
        h1, h2, h3, h4, h5, h6 {{
            color: {TITLE_COLOUR} !important;
            text-shadow: 0 2px 8px rgba(0,0,0,0.5);
        }}
        p, li, label, span, [data-testid="stMarkdownContainer"] * {{
            color: {TEXT_COLOUR} !important;
        }}
        [data-testid="stDataFrame"] * {{
            color: {TEXT_COLOUR} !important;
        }}

        /* Leaderboard buttons – clearer +/– */
        div.stButton > button {{
            background: rgba(255,255,255,0.95);
            color: #111 !important;
            border: 2px solid rgba(255,255,255,0.95);
            border-radius: 12px;
            width: 52px;
            height: 52px;
            font-size: 1.6rem;
            font-weight: 800;
            line-height: 1;
            box-shadow: 0 4px 12px rgba(0,0,0,0.25);
        }}
        div.stButton > button:hover {{ transform: translateY(-1px); }}
        div.stButton > button:active {{ transform: translateY(0); }}
        </style>
        """,
        unsafe_allow_html=True,
    )

# -----------------------------
# Race track (responsive)
# -----------------------------

def race_track(players_df: pd.DataFrame):
    """
    Responsive race track:
    - width: 100% (fills the page)
    - height: auto (grows to fit however many players you have)
    - lane height scales down as player count goes up, but never below MIN_LANE_H
    - avatar center is clamped so it never hangs off the left/right edges
    """
    lanes = len(players_df)

    # Scale lane height down as the roster grows (gentle slope)
    if lanes <= 6:
        lane_h = MAX_LANE_H
    else:
        lane_h = max(MIN_LANE_H, MAX_LANE_H - (lanes - 6) * 4)

    lane_divs = []
    for _, row in players_df.iterrows():
        name = str(row.get("name", "") or "")
        pts = float(row.get("points", 0) or 0)
        avatar_cell = str(row.get("avatar", "") or "")
        avatar_url = path_or_upload_to_url(avatar_cell, None)

        progress = max(0.0, min(1.0, pts / FINISH_LINE))
        # Place the *center* of the avatar from (AVATAR_PX/2) to (100% - AVATAR_PX/2)
        left_css = f"calc((100% - {AVATAR_PX}px) * {progress:.4f} + {AVATAR_PX/2}px)"

        if not avatar_url:
            avatar_url = "data:image/svg+xml;base64," + base64.b64encode(
                ('<svg xmlns="http://www.w3.org/2000/svg" width="80" height="80">'
                 '<circle cx="40" cy="40" r="40" fill="#7785FF"/></svg>').encode("utf-8")
            ).decode("utf-8")

        lane_divs.append(dedent(f"""
        <div class="lane">
          <div class="finish"></div>
          <div class="racer" style="left:{left_css}">
            <img class="avatar" src="{avatar_url}" alt="{name}"/>
            <div class="name">{name}</div>
          </div>
        </div>
        """))

    html = f"""
    <div class="track">
    {''.join(lane_divs)}
    </div>
    <style>
      .track {{
        position: relative;
        width: 100%;
        /* no fixed height: container grows with content */
        border-radius: 16px;
        padding: 16px;
        background: rgba(0,0,0,0.25);
        box-shadow: 0 8px 24px rgba(0,0,0,0.25) inset;
        overflow: hidden;
      }}
      .lane {{
        position: relative;
        height: {lane_h}px;
        margin-bottom: {LANE_GAP}px;
        border-bottom: 1px dashed rgba(255,255,255,0.45);
      }}
      .finish {{
        position: absolute;
        right: 0;
        top: 0;
        bottom: 0;
        width: 24px;
        background:
          linear-gradient(45deg, #000 25%, transparent 25%) -6px 0/12px 12px,
          linear-gradient(-45deg, #000 25%, transparent 25%) -6px 0/12px 12px,
          linear-gradient(45deg, transparent 75%, #000 75%) -6px 0/12px 12px,
          linear-gradient(-45deg, transparent 75%, #000 75%) -6px 0/12px 12px;
        background-color:#fff;
        opacity: .9;
      }}
      .racer {{
        position: absolute;
        top: 50%;
        transform: translate(-50%, -50%); /* center on computed left */
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 4px;
        transition: left 0.4s ease;
      }}
      .avatar {{
        width: {AVATAR_PX}px;
        height: {AVATAR_PX}px;
        border-radius: 50%;
        border: 3px solid #fff;
        object-fit: cover;
        box-shadow: 0 4px 10px rgba(0,0,0,0.4);
        background: #777;
      }}
      .name {{
        color: #fff;
        font-weight: 600;
        text-shadow: 0 2px 6px rgba(0,0,0,0.6);
        font-size: 0.9rem;
      }}
    </style>
    """
    render_html(html)


# -----------------------------
# Sidebar – load/save players
# -----------------------------
with st.sidebar:
    st.header("Settings")
    csv_path = st.text_input("Players CSV path", CSV_PATH_DEFAULT)

    col1, col2, col3 = st.columns([1,1,1])
    with col1:
        if st.button("Load CSV"):
            st.session_state["players"] = read_players(csv_path)
    with col2:
        if st.button("Save CSV"):
            write_players(st.session_state.get("players", pd.DataFrame()), csv_path)
            st.success(f"Saved to {csv_path}")
    with col3:
        st.download_button(
            "Download CSV",
            (st.session_state.get("players", pd.DataFrame(columns=["name","points","avatar"]))
             ).to_csv(index=False).encode("utf-8"),
            file_name="players.csv",
            mime="text/csv",
        )

# -----------------------------
# Init & background
# -----------------------------
if "players" not in st.session_state:
    st.session_state["players"] = read_players(csv_path)

bg_url = path_or_upload_to_url(BACKGROUND_IMAGE, None)
inject_page_bg(bg_url)

# -----------------------------
# Main layout
# -----------------------------
st.title("🏆 Villa Olympics")

players = st.session_state["players"].copy()

st.subheader("Race")
race_track(st.session_state["players"])

st.subheader("Leaderboard")

# toggle: turn live resorting on/off
colA, colB = st.columns([0.4, 0.6])
with colA:
    st.session_state.setdefault("live_sort", True)
    st.toggle("Live resort by points", key="live_sort", help="Turn off to keep the current order while editing")

lb = get_leaderboard_df()

for i, row in lb.iterrows():
    name = str(row.get("name", "") or "")
    pts  = float(row.get("points", 0) or 0)

    c1, c2, c3, c4, c5 = st.columns([0.6, 0.1, 0.4, 0.25, 0.25])
    c1.markdown(f"**{i+1}. {name or '—'}**")
    c2.markdown("&nbsp;")
    c3.markdown(f"{int(pts)} pts" if pts.is_integer() else f"{pts:.1f} pts")

    # stable keys based on player name (not index)
    if c4.button("−", key=f"minus_{name}"):
        bump_points(name, -1)
    if c5.button("+", key=f"plus_{name}"):
        bump_points(name, +1)


st.caption("Finish line set at 100 points. Change via FINISH_LINE in code if you like.")
