# -*- coding: utf-8 -*-
"""
온라인팀 관리 홈페이지
- 대시보드 / 일정 관리 / 온라인팀(행사) / 온라인팀(관리) / 구성원 관리
데이터는 로컬 JSON 파일(online_team_data.json)에 저장되어 여러 사용자가
같은 서버에서 접속했을 때도 데이터가 공유됩니다.
"""

import streamlit as st
import json
import os
import uuid
import base64
import calendar as cal
from datetime import date, datetime, timedelta

# --------------------------------------------------------------------------
# 기본 설정
# --------------------------------------------------------------------------
st.set_page_config(page_title="온라인팀", page_icon="🌐", layout="wide")

DATA_PATH = os.path.join(os.path.dirname(__file__), "online_team_data.json")

DEFAULT_DATA = {
    "members": [
        {"name": "김담이", "color": "#3B82F6"},
        {"name": "천지현", "color": "#F5B301"},
        {"name": "채지혜", "color": "#EC4899"},
    ],
    "schedules": [],
    "event_posts": [],
    "admin_posts": [],
    "vote_templates": [],
}

STATUS_LIST = ["제안", "진행", "미선정", "종료"]
CATEGORY_LIST = ["개인", "공동"]


def load_data():
    if not os.path.exists(DATA_PATH):
        save_data(DEFAULT_DATA)
        return json.loads(json.dumps(DEFAULT_DATA))
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            data = json.loads(json.dumps(DEFAULT_DATA))
    for k, v in DEFAULT_DATA.items():
        data.setdefault(k, v if not isinstance(v, list) else [])
    return data


def save_data(data):
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_data():
    if "data" not in st.session_state:
        st.session_state.data = load_data()
    return st.session_state.data


def persist():
    save_data(st.session_state.data)


def new_id():
    return uuid.uuid4().hex[:10]


def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def member_color(name, data):
    for m in data["members"]:
        if m["name"] == name:
            return m["color"]
    return "#999999"


def member_names(data):
    return [m["name"] for m in data["members"]]


def file_to_b64(uploaded_file):
    if uploaded_file is None:
        return None
    raw = uploaded_file.getvalue()
    return {
        "name": uploaded_file.name,
        "type": uploaded_file.type,
        "data": base64.b64encode(raw).decode("utf-8"),
    }


def render_attachment(att, key_prefix=""):
    if att is None:
        return
    if att.get("type", "").startswith("image/"):
        st.image(base64.b64decode(att["data"]), caption=att["name"], width=280)
    else:
        st.download_button(
            f"📎 {att['name']}",
            data=base64.b64decode(att["data"]),
            file_name=att["name"],
            key=f"{key_prefix}_{att['name']}_{uuid.uuid4().hex[:6]}",
        )


# --------------------------------------------------------------------------
# 사이드바
# --------------------------------------------------------------------------
data = get_data()

with st.sidebar:
    st.markdown("## 🌐 온라인팀")
    st.markdown("#### 메뉴")
    page = st.radio(
        "메뉴",
        ["대시보드", "일정 관리", "온라인팀(행사)", "온라인팀(관리)", "구성원 관리"],
        label_visibility="collapsed",
    )
    st.markdown("---")
    st.markdown("##### 현재 사용자")
    names = member_names(data)
    if names:
        current_user = st.selectbox("현재 사용자", names, label_visibility="collapsed")
    else:
        current_user = None
        st.info("구성원 관리에서 먼저 구성원을 추가해주세요.")

# --------------------------------------------------------------------------
# 공통: 일정 등록/조회 팝업 (st.dialog)
# --------------------------------------------------------------------------
if "sched_dialog_open" not in st.session_state:
    st.session_state.sched_dialog_open = False
if "sched_dialog_date" not in st.session_state:
    st.session_state.sched_dialog_date = None
if "sched_dialog_edit_id" not in st.session_state:
    st.session_state.sched_dialog_edit_id = None


def open_new_schedule_dialog(d):
    st.session_state.sched_dialog_open = True
    st.session_state.sched_dialog_date = d
    st.session_state.sched_dialog_edit_id = None


def open_view_schedule_dialog(sched_id):
    st.session_state.sched_dialog_open = True
    st.session_state.sched_dialog_edit_id = sched_id
    st.session_state.sched_dialog_date = None


@st.dialog("일정")
def schedule_dialog():
    d = get_data()
    edit_id = st.session_state.sched_dialog_edit_id
    editing_existing = edit_id is not None
    sched = None
    if editing_existing:
        sched = next((s for s in d["schedules"] if s["id"] == edit_id), None)
        if sched is None:
            st.session_state.sched_dialog_open = False
            st.rerun()

    edit_mode_key = f"edit_mode_{edit_id or 'new'}"
    if editing_existing and edit_mode_key not in st.session_state:
        st.session_state[edit_mode_key] = False

    if editing_existing and not st.session_state[edit_mode_key]:
        # 조회 모드
        st.markdown(f"### {sched['title']}")
        st.write(f"**기간** : {sched['start']} ~ {sched['end']}")
        st.write(f"**담당자** : {sched['owner']}  ·  **구분** : {sched['category']}")
        if sched.get("memo"):
            st.write("**메모**")
            st.info(sched["memo"])
        c1, c2, c3 = st.columns([1, 1, 3])
        if c1.button("✏️ 수정", use_container_width=True):
            st.session_state[edit_mode_key] = True
            st.rerun()
        if c2.button("🗑️ 삭제", use_container_width=True):
            d["schedules"] = [s for s in d["schedules"] if s["id"] != edit_id]
            persist()
            st.session_state.sched_dialog_open = False
            st.rerun()
        return

    # 등록 / 수정 모드
    default_title = sched["title"] if sched else ""
    default_start = date.fromisoformat(sched["start"]) if sched else (
        st.session_state.sched_dialog_date or date.today()
    )
    default_end = date.fromisoformat(sched["end"]) if sched else default_start
    default_owner = sched["owner"] if sched else (current_user or (member_names(d)[0] if d["members"] else ""))
    default_cat = sched["category"] if sched else "개인"
    default_memo = sched["memo"] if sched else ""

    title = st.text_input("제목", value=default_title)
    period = st.date_input("기간", value=(default_start, default_end))
    owner = st.selectbox(
        "담당자", member_names(d),
        index=member_names(d).index(default_owner) if default_owner in member_names(d) else 0,
    )
    category = st.selectbox("구분", CATEGORY_LIST, index=CATEGORY_LIST.index(default_cat))
    memo = st.text_area("메모", value=default_memo, height=100)

    b1, b2 = st.columns(2)
    if b1.button("저장", type="primary", use_container_width=True):
        if isinstance(period, tuple) and len(period) == 2:
            start_d, end_d = period
        else:
            start_d = end_d = period
        if not title.strip():
            st.warning("제목을 입력해주세요.")
        else:
            if editing_existing:
                sched.update(
                    title=title.strip(),
                    start=start_d.isoformat(),
                    end=end_d.isoformat(),
                    owner=owner,
                    category=category,
                    memo=memo,
                )
            else:
                d["schedules"].append(
                    {
                        "id": new_id(),
                        "title": title.strip(),
                        "start": start_d.isoformat(),
                        "end": end_d.isoformat(),
                        "owner": owner,
                        "category": category,
                        "memo": memo,
                    }
                )
            persist()
            st.session_state.sched_dialog_open = False
            if editing_existing:
                st.session_state[edit_mode_key] = False
            st.rerun()
    if b2.button("취소", use_container_width=True):
        st.session_state.sched_dialog_open = False
        if editing_existing:
            st.session_state[edit_mode_key] = False
        st.rerun()


if st.session_state.sched_dialog_open:
    schedule_dialog()

# --------------------------------------------------------------------------
# 페이지: 대시보드
# --------------------------------------------------------------------------
if page == "대시보드":
    st.markdown("# 🌐 온라인팀")
    st.caption("일정 · 안건 · 투표를 한 곳에서 관리합니다.")

    c1, c2, c3 = st.columns(3)
    c1.metric("등록된 일정", len(data["schedules"]))
    c2.metric("진행 중 안건", len([p for p in data["event_posts"] if p["status"] == "진행"]))
    c3.metric("진행 중 투표", len([p for p in data["admin_posts"] if p.get("kind") == "vote"]))

    st.markdown("### 🗓️ 오늘 이후 일정")
    today = date.today()
    upcoming = [s for s in data["schedules"] if date.fromisoformat(s["end"]) >= today]
    upcoming.sort(key=lambda s: s["start"])
    if upcoming:
        rows = [
            {
                "제목": s["title"],
                "기간": f"{s['start']} ~ {s['end']}",
                "담당자": s["owner"],
                "구분": s["category"],
            }
            for s in upcoming
        ]
        st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
        st.info("등록된 예정 일정이 없습니다.")

# --------------------------------------------------------------------------
# 페이지: 일정 관리
# --------------------------------------------------------------------------
elif page == "일정 관리":
    st.markdown("# 🗓️ 일정 관리")
    tab1, tab2 = st.tabs(["월간 일정 보기", "일정 직접 등록"])

    with tab1:
        colA, colB, colC = st.columns([1, 1, 2])
        if "cal_year" not in st.session_state:
            st.session_state.cal_year = date.today().year
        if "cal_month" not in st.session_state:
            st.session_state.cal_month = date.today().month

        with colA:
            st.write("연도")
            y1, y2, y3 = st.columns([1, 2, 1])
            if y1.button("−", key="y_minus"):
                st.session_state.cal_year -= 1
                st.rerun()
            y2.markdown(f"<h4 style='text-align:center'>{st.session_state.cal_year}</h4>", unsafe_allow_html=True)
            if y3.button("＋", key="y_plus"):
                st.session_state.cal_year += 1
                st.rerun()
        with colB:
            st.write("월")
            m1, m2, m3 = st.columns([1, 2, 1])
            if m1.button("−", key="m_minus"):
                st.session_state.cal_month -= 1
                if st.session_state.cal_month < 1:
                    st.session_state.cal_month = 12
                    st.session_state.cal_year -= 1
                st.rerun()
            m2.markdown(f"<h4 style='text-align:center'>{st.session_state.cal_month}</h4>", unsafe_allow_html=True)
            if m3.button("＋", key="m_plus"):
                st.session_state.cal_month += 1
                if st.session_state.cal_month > 12:
                    st.session_state.cal_month = 1
                    st.session_state.cal_year += 1
                st.rerun()
        with colC:
            st.write("구성원 필터 (비워두면 전체)")
            filter_members = st.multiselect(
                "구성원 필터", member_names(data), label_visibility="collapsed"
            )

        st.caption("날짜를 클릭하면 해당 날짜를 시작일로 하는 일정 등록 팝업이 열립니다.")

        year = st.session_state.cal_year
        month = st.session_state.cal_month

        visible_schedules = [
            s for s in data["schedules"]
            if not filter_members or s["owner"] in filter_members
        ]

        calendar_obj = cal.Calendar(firstweekday=6)  # 일요일 시작
        weeks = calendar_obj.monthdatescalendar(year, month)

        weekday_labels = ["일", "월", "화", "수", "목", "금", "토"]
        header_cols = st.columns(7)
        for i, wl in enumerate(weekday_labels):
            color = "#d33" if i == 0 else ("#36c" if i == 6 else "#333")
            header_cols[i].markdown(
                f"<div style='text-align:center;font-weight:600;color:{color}'>{wl}</div>",
                unsafe_allow_html=True,
            )

        for week in weeks:
            # 날짜 버튼 줄
            day_cols = st.columns(7)
            for i, d_ in enumerate(week):
                with day_cols[i]:
                    if d_.month == month:
                        if st.button(str(d_.day), key=f"day_{d_.isoformat()}", use_container_width=True):
                            open_new_schedule_dialog(d_)
                            st.rerun()
                    else:
                        st.markdown(
                            f"<div style='color:#ccc;text-align:center'>{d_.day}</div>",
                            unsafe_allow_html=True,
                        )

            # 이 주에 걸치는 일정을 하나의 연결된 블록으로 표시
            week_start, week_end = week[0], week[-1]
            week_events = []
            for s in visible_schedules:
                s_start = date.fromisoformat(s["start"])
                s_end = date.fromisoformat(s["end"])
                if s_end < week_start or s_start > week_end:
                    continue
                col_start = max(0, (max(s_start, week_start) - week_start).days)
                col_end = min(6, (min(s_end, week_end) - week_start).days)
                week_events.append((col_start, col_end, s))

            # lane(줄) 배정 - 겹치는 일정은 다른 줄에 표시
            lanes = []  # each lane: list of (start,end)
            placed = []  # (lane_idx, col_start, col_end, s)
            for col_start, col_end, s in sorted(week_events, key=lambda x: (x[0], -(x[1] - x[0]))):
                lane_idx = None
                for li, intervals in enumerate(lanes):
                    if all(col_end < a or col_start > b for a, b in intervals):
                        lane_idx = li
                        break
                if lane_idx is None:
                    lanes.append([])
                    lane_idx = len(lanes) - 1
                lanes[lane_idx].append((col_start, col_end))
                placed.append((lane_idx, col_start, col_end, s))

            if placed:
                max_lane = max(p[0] for p in placed) + 1
                html = (
                    "<div style='display:grid;grid-template-columns:repeat(7,1fr);"
                    f"grid-auto-rows:24px;gap:3px;margin-bottom:6px'>"
                )
                for lane_idx, col_start, col_end, s in placed:
                    color = member_color(s["owner"], data)
                    html += (
                        f"<div style='grid-column:{col_start + 1} / {col_end + 2};"
                        f"grid-row:{lane_idx + 1};background:{color};color:white;"
                        "font-size:12px;padding:2px 6px;border-radius:6px;overflow:hidden;"
                        f"white-space:nowrap;text-overflow:ellipsis' title='{s['title']}'>"
                        f"{s['title']}</div>"
                    )
                html += "</div>"
                st.markdown(html, unsafe_allow_html=True)
            st.markdown(
                "<hr style='margin:2px 0;border:none;border-top:1px solid #eee'>",
                unsafe_allow_html=True,
            )

        st.markdown("#### 📋 이번 달 일정 목록 (클릭하면 상세 팝업이 열립니다)")
        month_events = [
            s for s in visible_schedules
            if date.fromisoformat(s["start"]).strftime("%Y-%m") <= f"{year}-{month:02d}" <= date.fromisoformat(s["end"]).strftime("%Y-%m")
        ]
        if month_events:
            for s in month_events:
                c1, c2 = st.columns([5, 1])
                color = member_color(s["owner"], data)
                c1.markdown(
                    f"<span style='display:inline-block;width:10px;height:10px;border-radius:50%;"
                    f"background:{color};margin-right:6px'></span>"
                    f"**{s['title']}** &nbsp;&nbsp; {s['start']} ~ {s['end']} &nbsp;·&nbsp; {s['owner']} ({s['category']})",
                    unsafe_allow_html=True,
                )
                if c2.button("상세보기", key=f"view_{s['id']}"):
                    open_view_schedule_dialog(s["id"])
                    st.rerun()
        else:
            st.caption("표시할 일정이 없습니다.")

    with tab2:
        st.markdown("#### 새 일정 직접 등록")
        title = st.text_input("제목", key="direct_title")
        period = st.date_input("기간", value=(date.today(), date.today()), key="direct_period")
        owner = st.selectbox("담당자", member_names(data), key="direct_owner") if data["members"] else None
        category = st.selectbox("구분", CATEGORY_LIST, key="direct_category")
        memo = st.text_area("메모", key="direct_memo")
        if st.button("일정 등록", type="primary"):
            if isinstance(period, tuple) and len(period) == 2:
                s_d, e_d = period
            else:
                s_d = e_d = period
            if not title.strip():
                st.warning("제목을 입력해주세요.")
            else:
                data["schedules"].append(
                    {
                        "id": new_id(),
                        "title": title.strip(),
                        "start": s_d.isoformat(),
                        "end": e_d.isoformat(),
                        "owner": owner,
                        "category": category,
                        "memo": memo,
                    }
                )
                persist()
                st.success("일정이 등록되었습니다.")
                st.rerun()

# --------------------------------------------------------------------------
# 페이지: 온라인팀(행사)  (제안 / 진행 / 미선정 / 종료 게시판)
# --------------------------------------------------------------------------
elif page == "온라인팀(행사)":
    st.markdown("# 📝 온라인팀(행사)")
    st.caption("행사와 관련된 아이디어, 진행 사항, 선정 결과를 관리합니다.")

    filter_status = st.radio(
        "보기", ["전체"] + STATUS_LIST, horizontal=True, key="event_filter_status"
    )
    only_mine = st.checkbox("내가 쓴 글만 보기")

    posts = data["event_posts"]
    shown = [p for p in posts if (filter_status == "전체" or p["status"] == filter_status)]
    if only_mine:
        shown = [p for p in shown if p["author"] == current_user]
    shown.sort(key=lambda p: p["created_at"], reverse=True)

    if not shown:
        st.info("표시할 게시글이 없습니다.")

    for p in shown:
        with st.container(border=True):
            left, right = st.columns([1, 1])
            with left:
                new_status = st.selectbox(
                    "상태", STATUS_LIST, index=STATUS_LIST.index(p["status"]),
                    key=f"status_{p['id']}", label_visibility="collapsed",
                )
                if new_status != p["status"]:
                    p["status"] = new_status
                    persist()
                    st.rerun()
            with right:
                b1, b2 = st.columns(2)
                edit_key = f"editing_event_{p['id']}"
                if b1.button("수정", key=f"edit_btn_{p['id']}", use_container_width=True):
                    st.session_state[edit_key] = not st.session_state.get(edit_key, False)
                    st.rerun()
                if b2.button("삭제", key=f"del_btn_{p['id']}", use_container_width=True):
                    data["event_posts"] = [x for x in data["event_posts"] if x["id"] != p["id"]]
                    persist()
                    st.rerun()

            st.markdown(f"### {p['title']}")
            st.caption(f"작성자 {p['author']} · {p['created_at']}")

            if st.session_state.get(f"editing_event_{p['id']}"):
                new_title = st.text_input("제목 수정", value=p["title"], key=f"et_{p['id']}")
                new_content = st.text_area("내용 수정", value=p["content"], key=f"ec_{p['id']}", height=120)
                if st.button("저장", key=f"save_edit_{p['id']}"):
                    p["title"] = new_title.strip() or p["title"]
                    p["content"] = new_content
                    persist()
                    st.session_state[f"editing_event_{p['id']}"] = False
                    st.rerun()
            else:
                st.write(p["content"])
                for img in p.get("images", []):
                    render_attachment(img, key_prefix=f"img_{p['id']}")
                for f_ in p.get("files", []):
                    render_attachment(f_, key_prefix=f"file_{p['id']}")

            st.markdown("**💬 댓글**")
            for c in p.get("comments", []):
                st.markdown(f"- **{c['author']}** ({c['time']}): {c['text']}")
            new_comment = st.text_input("댓글 작성", key=f"comment_input_{p['id']}", label_visibility="collapsed", placeholder="댓글을 입력하세요")
            if st.button("댓글 등록", key=f"comment_btn_{p['id']}"):
                if new_comment.strip():
                    p.setdefault("comments", []).append(
                        {"author": current_user, "text": new_comment.strip(), "time": now_str()}
                    )
                    persist()
                    st.rerun()

    st.markdown("---")
    st.markdown("### ➕ 새 행사 게시글 작성")
    e_title = st.text_input("제목", key="new_event_title")
    e_status = st.selectbox("상태", STATUS_LIST, key="new_event_status")
    e_content = st.text_area("내용 (텍스트 입력 또는 붙여넣기)", key="new_event_content", height=140)
    e_images = st.file_uploader(
        "이미지 첨부 (드래그앤드롭 또는 클립보드 붙여넣기 지원)",
        type=["png", "jpg", "jpeg", "gif", "webp"],
        accept_multiple_files=True,
        key="new_event_images",
    )
    e_files = st.file_uploader("첨부파일", accept_multiple_files=True, key="new_event_files")

    if st.button("게시글 등록", type="primary"):
        if not e_title.strip():
            st.warning("제목을 입력해주세요.")
        else:
            data["event_posts"].append(
                {
                    "id": new_id(),
                    "title": e_title.strip(),
                    "status": e_status,
                    "content": e_content,
                    "images": [file_to_b64(f_) for f_ in (e_images or [])],
                    "files": [file_to_b64(f_) for f_ in (e_files or [])],
                    "author": current_user,
                    "created_at": now_str(),
                    "comments": [],
                }
            )
            persist()
            st.success("게시글이 등록되었습니다.")
            st.rerun()

# --------------------------------------------------------------------------
# 페이지: 온라인팀(관리)  (일반 게시글 + 투표)
# --------------------------------------------------------------------------
elif page == "온라인팀(관리)":
    st.markdown("# ⚙️ 온라인팀(관리)")
    st.caption("공지·안건 게시글과 투표를 함께 관리합니다.")

    view_filter = st.radio("보기", ["전체", "게시글", "투표"], horizontal=True, key="admin_view_filter")

    posts = sorted(data["admin_posts"], key=lambda p: p["created_at"], reverse=True)
    if view_filter == "게시글":
        posts = [p for p in posts if p.get("kind") != "vote"]
    elif view_filter == "투표":
        posts = [p for p in posts if p.get("kind") == "vote"]

    if not posts:
        st.info("표시할 게시글이 없습니다.")

    for p in posts:
        with st.container(border=True):
            top_l, top_r = st.columns([4, 1])
            top_l.markdown(f"### {'🗳️ ' if p.get('kind') == 'vote' else ''}{p['title']}")
            with top_r:
                b1, b2 = st.columns(2)
                if b1.button("수정", key=f"aedit_{p['id']}"):
                    st.session_state[f"admin_editing_{p['id']}"] = not st.session_state.get(f"admin_editing_{p['id']}", False)
                    st.rerun()
                if b2.button("삭제", key=f"adel_{p['id']}"):
                    data["admin_posts"] = [x for x in data["admin_posts"] if x["id"] != p["id"]]
                    persist()
                    st.rerun()
            st.caption(f"작성자 {p['author']} · {p['created_at']}")

            if st.session_state.get(f"admin_editing_{p['id']}"):
                new_title = st.text_input("제목 수정", value=p["title"], key=f"at_{p['id']}")
                new_content = st.text_area("내용 수정", value=p.get("content", ""), key=f"ac_{p['id']}", height=100)
                if st.button("저장", key=f"admin_save_{p['id']}"):
                    p["title"] = new_title.strip() or p["title"]
                    p["content"] = new_content
                    persist()
                    st.session_state[f"admin_editing_{p['id']}"] = False
                    st.rerun()
            else:
                if p.get("content"):
                    st.write(p["content"])

            if p.get("kind") == "vote":
                vote = p["vote"]
                st.markdown(f"**{vote['question']}**")
                options = vote["options"]
                my_votes = [i for i, o in enumerate(options) if current_user in o["voters"]]
                total_voters = len({v for o in options for v in o["voters"]}) or 1

                if vote.get("multi"):
                    picked = st.multiselect(
                        "선택지 (복수 선택 가능)",
                        list(range(len(options))),
                        default=my_votes,
                        format_func=lambda i: options[i]["text"],
                        key=f"vote_multi_{p['id']}",
                    )
                else:
                    idx_default = my_votes[0] if my_votes else None
                    picked_single = st.radio(
                        "선택지",
                        list(range(len(options))),
                        index=idx_default,
                        format_func=lambda i: options[i]["text"],
                        key=f"vote_single_{p['id']}",
                    )
                    picked = [picked_single] if picked_single is not None else []

                if st.button("투표하기", key=f"vote_submit_{p['id']}"):
                    for o in options:
                        if current_user in o["voters"]:
                            o["voters"].remove(current_user)
                    for i in picked:
                        if current_user not in options[i]["voters"]:
                            options[i]["voters"].append(current_user)
                    persist()
                    st.rerun()

                st.markdown("**📊 현재 결과**")
                for o in options:
                    cnt = len(o["voters"])
                    pct = int(cnt / total_voters * 100) if total_voters else 0
                    st.write(f"{o['text']} — {cnt}표")
                    st.progress(min(pct, 100) / 100 if pct else 0.0)

            st.markdown("**💬 댓글**")
            for c in p.get("comments", []):
                st.markdown(f"- **{c['author']}** ({c['time']}): {c['text']}")
            new_comment = st.text_input(
                "댓글 작성", key=f"admin_comment_{p['id']}", label_visibility="collapsed", placeholder="댓글을 입력하세요"
            )
            if st.button("댓글 등록", key=f"admin_comment_btn_{p['id']}"):
                if new_comment.strip():
                    p.setdefault("comments", []).append(
                        {"author": current_user, "text": new_comment.strip(), "time": now_str()}
                    )
                    persist()
                    st.rerun()

    st.markdown("---")
    st.markdown("### ➕ 새 글 작성")
    write_type = st.radio("작성 유형", ["일반 게시글", "투표 만들기"], horizontal=True, key="admin_write_type")

    if write_type == "일반 게시글":
        a_title = st.text_input("제목", key="new_admin_title")
        a_content = st.text_area("내용", key="new_admin_content", height=140)
        if st.button("게시글 등록", type="primary", key="submit_admin_post"):
            if not a_title.strip():
                st.warning("제목을 입력해주세요.")
            else:
                data["admin_posts"].append(
                    {
                        "id": new_id(),
                        "kind": "post",
                        "title": a_title.strip(),
                        "content": a_content,
                        "author": current_user,
                        "created_at": now_str(),
                        "comments": [],
                    }
                )
                persist()
                st.success("게시글이 등록되었습니다.")
                st.rerun()

    else:
        st.markdown("#### 🗳️ 투표 만들기")
        templates = data["vote_templates"]
        template_names = ["(직접 입력)"] + [t["name"] for t in templates]
        chosen_template = st.selectbox("투표 양식 불러오기", template_names, key="vote_template_select")
        prefill_options = ""
        if chosen_template != "(직접 입력)":
            tpl = next(t for t in templates if t["name"] == chosen_template)
            prefill_options = "\n".join(tpl["options"])

        v_question = st.text_input("투표 제목 / 질문", key="new_vote_question")
        v_options_text = st.text_area(
            "선택지 (한 줄에 하나씩 입력)", value=prefill_options, key="new_vote_options", height=120
        )
        v_multi = st.checkbox("복수 선택 허용", key="new_vote_multi")

        if st.button("투표 게시글 등록", type="primary", key="submit_vote_post"):
            opts = [o.strip() for o in v_options_text.split("\n") if o.strip()]
            if not v_question.strip() or len(opts) < 2:
                st.warning("질문과 2개 이상의 선택지를 입력해주세요.")
            else:
                data["admin_posts"].append(
                    {
                        "id": new_id(),
                        "kind": "vote",
                        "title": v_question.strip(),
                        "content": "",
                        "author": current_user,
                        "created_at": now_str(),
                        "comments": [],
                        "vote": {
                            "question": v_question.strip(),
                            "multi": v_multi,
                            "options": [{"text": o, "voters": []} for o in opts],
                        },
                    }
                )
                persist()
                st.success("투표가 등록되었습니다.")
                st.rerun()

        with st.expander("📋 투표 양식(템플릿) 관리"):
            tpl_name = st.text_input("현재 선택지를 템플릿으로 저장 (템플릿 이름)", key="tpl_save_name")
            if st.button("템플릿으로 저장"):
                opts = [o.strip() for o in v_options_text.split("\n") if o.strip()]
                if not tpl_name.strip() or len(opts) < 1:
                    st.warning("템플릿 이름과 선택지를 입력해주세요.")
                else:
                    data["vote_templates"] = [t for t in data["vote_templates"] if t["name"] != tpl_name.strip()]
                    data["vote_templates"].append({"name": tpl_name.strip(), "options": opts})
                    persist()
                    st.success("템플릿이 저장되었습니다.")
                    st.rerun()

            if templates:
                st.write("저장된 템플릿")
                for t in templates:
                    tc1, tc2 = st.columns([4, 1])
                    tc1.write(f"**{t['name']}** — {', '.join(t['options'])}")
                    if tc2.button("삭제", key=f"tpl_del_{t['name']}"):
                        data["vote_templates"] = [x for x in data["vote_templates"] if x["name"] != t["name"]]
                        persist()
                        st.rerun()

# --------------------------------------------------------------------------
# 페이지: 구성원 관리
# --------------------------------------------------------------------------
elif page == "구성원 관리":
    st.markdown("# ⚙️ 구성원 관리")

    st.markdown("### 구성원 추가")
    c1, c2, c3 = st.columns([3, 1, 1])
    new_name = c1.text_input("이름", key="new_member_name", label_visibility="collapsed", placeholder="이름")
    new_color = c2.color_picker("개인 색상", value="#3B82F6", key="new_member_color", label_visibility="collapsed")
    if c3.button("추가", use_container_width=True):
        if not new_name.strip():
            st.warning("이름을 입력해주세요.")
        elif new_name.strip() in member_names(data):
            st.warning("이미 존재하는 구성원입니다.")
        else:
            data["members"].append({"name": new_name.strip(), "color": new_color})
            persist()
            st.success(f"{new_name.strip()}님이 추가되었습니다.")
            st.rerun()

    st.markdown("---")
    st.markdown("### 현재 구성원")
    if not data["members"]:
        st.info("등록된 구성원이 없습니다.")
    for m in data["members"]:
        c1, c2, c3 = st.columns([1, 5, 1])
        c1.markdown(
            f"<div style='width:22px;height:22px;border-radius:50%;background:{m['color']}'></div>",
            unsafe_allow_html=True,
        )
        c2.write(m["name"])
        if c3.button("삭제", key=f"member_del_{m['name']}"):
            data["members"] = [x for x in data["members"] if x["name"] != m["name"]]
            persist()
            st.success(f"{m['name']}님이 삭제되었습니다.")
            st.rerun()
