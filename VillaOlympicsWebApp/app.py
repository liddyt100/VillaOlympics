import base64
import io
import os
import mimetypes
from pathlib import Path

import pandas as pd
import streamlit as st
from streamlit.components.v1 import html as st_html

# -----------------------------
# Config
# -----------------------------
st.set_page_config(page_title="Villa Olympics", layout="wide")

FINISH_LINE = 100  # points needed to "finish"
CSV_PATH_DEFAULT = "players.csv"

# -----------------------------
# Helpers
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

def file_to_data_uri(file_bytes: bytes, mime: str) -> str:
    b64 = base64.b64encode(file_bytes).decode("utf-8")
    return f"data:{mime};base64,{b64}"

def local_path_to_data_uri(path_str: str) -> str:
    """Embed a local image file as a data: URI (works on Streamlit Cloud too)."""
    p = Path(path_str)
    if not p.exists() or not p.is_file():
        return ""
    mime, _ = mimetypes.guess_type(str(p))
    mime = mime or "image/png"
    with open(p, "rb") as f:
        return file_to_data_uri(f.read(), mime)

def path_or_upload_to_url(path_str: str, upload) -> str:
    """
    Return a browser-usable image URL/URI with this precedence:
      1) uploaded image -> data: URI
      2) existing usable string starting with data:/http(s) -> pass-through
      3) local file path -> embed as data: URI
      4) otherwise -> ""
    """
    # 1) uploaded image
    if upload is not None:
        bytes_ = upload.read()
        name = (upload.name or "").lower()
        mime = "image/png"
        if name.endswith(".jpg") or name.endswith(".jpeg"):
            mime = "image/jpeg"
        return file_to_data_uri(bytes_, mime)

    # 2) existing URL/URI
    s = (path_str or "").strip()
    if not s:
        return ""
    if s.startswith(("data:", "http://", "https://")):
        return s

    # 3) local path -> embed
    return local_path_to_data_uri(s)

# ---- add near your other constants if you want to tweak later
TITLE_COLOUR = "#FFFFFF"      # headings
TEXT_COLOUR  = "#F5F7FA"      # body text
OVERLAY_OPACITY = 0.55        # darken the glass behind content (0..1)

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

        /* Dark glass behind the content so text pops */
        .block-container {{
            background: rgba(0,0,0,{OVERLAY_OPACITY});
            border-radius: 16px;
            padding: 1.5rem;
        }}

        /* Sidebar glass + text */
        section[data-testid="stSidebar"] .block-container {{
            background: rgba(0,0,0,0.55);
            color: {TEXT_COLOUR};
        }}

        /* Headings + body text */
        h1, h2, h3, h4, h5, h6 {{
            color: {TITLE_COLOUR} !important;
            text-shadow: 0 2px 8px rgba(0,0,0,0.5);
        }}
        p, li, label, span, [data-testid="stMarkdownContainer"] * {{
            color: {TEXT_COLOUR} !important;
        }}

        /* Make data editor text readable */
        [data-testid="stDataFrame"] * {{
            color: {TEXT_COLOUR} !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def race_track(players_df: pd.DataFrame):
    """
    Render a horizontal race track with avatars positioned by points/FINISH_LINE.
    Uses CSS for layout so it's fast and simple.
    """
    height_px = 420
    lanes = len(players_df)
    lane_h = max(54, int((height_px - 40) / max(1, lanes)))

    lane_divs = []
    for _, row in players_df.iterrows():
        name = str(row.get("name", "") or "")
        pts = float(row.get("points", 0) or 0)
        # IMPORTANT: resolve avatar to data URI / URL (handles data:, http(s), or local path)
        avatar_cell = str(row.get("avatar", "") or "")
        avatar_url = path_or_upload_to_url(avatar_cell, None)

        progress = max(0.0, min(1.0, pts / FINISH_LINE))
        left_pct = int(progress * 100)

        # Fallback avatar (coloured circle) if nothing resolvable
        if not avatar_url:
            avatar_url = "data:image/svg+xml;base64," + base64.b64encode(
                ('<svg xmlns="http://www.w3.org/2000/svg" width="80" height="80">'
                 '<circle cx="40" cy="40" r="40" fill="#7785FF"/></svg>').encode("utf-8")
            ).decode("utf-8")

        lane_divs.append(f"""
        <div class="lane">
            <div class="finish"></div>
            <div class="racer" style="left:{left_pct}%">
                <img class="avatar" src="{avatar_url}" alt="{name}"/>
                <div class="name">{name}</div>
            </div>
        </div>
        """)

    html = f"""
    <div class="track">
        {''.join(lane_divs)}
    </div>
    <style>
        .track {{
            position: relative;
            width: 100%;
            height: {height_px}px;
            border-radius: 16px;
            padding: 16px;
            background: rgba(0,0,0,0.25);
            box-shadow: 0 8px 24px rgba(0,0,0,0.25) inset;
            overflow: hidden;
        }}
        .lane {{
            position: relative;
            height: {lane_h}px;
            margin-bottom: 10px;
            border-bottom: 1px dashed rgba(255,255,255,0.25);
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
            transform: translate(-50%, -50%);
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 4px;
            transition: left 0.4s ease;
        }}
        .avatar {{
            width: 64px;
            height: 64px;
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
    st_html(html, height=height_px + 120, scrolling=False)

# -----------------------------
# Sidebar – load/save & customisation
# -----------------------------
with st.sidebar:
    st.header("Settings")

    csv_path = st.text_input("Players CSV path", CSV_PATH_DEFAULT)
    bg_file = st.file_uploader("Upload background image (optional)", type=["png", "jpg", "jpeg"], key="bg_up")
    bg_path_text = st.text_input("…or background file/URL", value="assets/background.jpg")

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

# Initialise players in session
if "players" not in st.session_state:
    st.session_state["players"] = read_players(csv_path)

# Apply background (handles upload, URL, data:, or local path)
bg_url = "https://github.com/liddyt100/VillaOlympics/blob/main/VillaOlympicsWebApp/Assets/background.jpeg?raw=true"
inject_page_bg(bg_url)

# -----------------------------
# Main layout
# -----------------------------
st.title("🏆 Villa Olympics")

players = st.session_state["players"].copy()

# Avatar uploader/editor per player
with st.expander("Add / edit players"):
    st.caption("Tip: paste public URLs or data URIs for avatars, or keep local paths when you control the server.")
    if players.empty:
        players = pd.DataFrame([{"name": "", "points": 0, "avatar": ""}])

    edited = st.data_editor(
        players[["name", "points", "avatar"]],
        num_rows="dynamic",
        use_container_width=True,
        key="players_editor",
    )
    st.session_state["players"] = edited

# Race track
st.subheader("Race")
race_track(st.session_state["players"])

# Leaderboard with +/–
st.subheader("Leaderboard")
lb = st.session_state["players"].copy()
lb = lb.sort_values(["points", "name"], ascending=[False, True]).reset_index(drop=True)

for i, row in lb.iterrows():
    c1, c2, c3, c4, c5 = st.columns([0.6, 0.1, 0.4, 0.3, 0.3])
    c1.markdown(f"**{i+1}. {row['name'] or '—'}**")
    c2.markdown("&nbsp;")
    c3.markdown(
        f"{float(row['points']):.0f} pts" if float(row["points"]).is_integer()
        else f"{float(row['points']):.1f} pts"
    )
    if c4.button("−", key=f"minus_{i}"):
        name = row["name"]
        mask = st.session_state["players"]["name"] == name
        st.session_state["players"].loc[mask, "points"] = (
            st.session_state["players"].loc[mask, "points"].astype(float) - 1
        )
    if c5.button("+", key=f"plus_{i}"):
        name = row["name"]
        mask = st.session_state["players"]["name"] == name
        st.session_state["players"].loc[mask, "points"] = (
            st.session_state["players"].loc[mask, "points"].astype(float) + 1
        )

st.caption("Finish line set at 100 points. Change via `FINISH_LINE` in code if you like.")
