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
from datetime import date, datetime

# --------------------------------------------------------------------------
# 기본 설정
# --------------------------------------------------------------------------
st.set_page_config(page_title="온라인팀", page_icon="🌐", layout="wide")

APP_VERSION = "v4"
COPYRIGHT_OWNER = "CHEA JIHYE"

DATA_PATH = os.path.join(os.path.dirname(__file__), "online_team_data.json")

DEFAULT_DATA = {
    "members": [
        {"name": "김담이", "color": "#3B82F6", "position": "사원"},
        {"name": "천지현", "color": "#F5B301", "position": "과장"},
        {"name": "채지혜", "color": "#EC4899", "position": "대리"},
    ],
    "calendars": [],
    "schedules": [],
    "event_posts": [],
    "admin_posts": [],
    "vote_templates": [],
}

STATUS_LIST = ["제안", "진행", "미선정", "종료"]
CATEGORY_LIST = ["개인", "공동"]
ADMIN_STATUS_LIST = ["등록", "취합", "공지", "완료"]
STATUS_ICONS = {
    "등록": "📝", "완료": "✅", "취합": "🗂️", "공지": "📢",
    "제안": "💡", "진행": "🔄", "미선정": "🚫", "종료": "🏁",
}

# 자주 쓰이는 색상 12개 (이름, 헥스코드)
PRESET_COLORS = [
    ("빨강", "#EF4444"), ("주황", "#F97316"), ("노랑", "#EAB308"),
    ("연두", "#84CC16"), ("초록", "#22C55E"), ("청록", "#14B8A6"),
    ("하늘", "#0EA5E9"), ("파랑", "#3B82F6"), ("남색", "#6366F1"),
    ("보라", "#8B5CF6"), ("분홍", "#EC4899"), ("갈색", "#92400E"),
]

# 구성원 추가 시 드롭다운에 노출되는 직책/직위 목록
POSITION_OPTIONS = [
    "상무", "차장", "과장", "사원", "이사", "부장",
    "부장/팀장", "대리", "부장/수석팀장", "과장/파트장",
    "차장/팀장", "대리/파트장",
]

# 구성원 불러오기 정렬 기준(직위 서열, 높은 순) - 일반적인 직급 체계 기준 임의 배치
POSITION_ORDER = [
    "상무", "이사", "부장/수석팀장", "부장/팀장", "부장",
    "차장/팀장", "차장", "과장/파트장", "과장",
    "대리/파트장", "대리", "사원",
]
POSITION_RANK = {p: i for i, p in enumerate(POSITION_ORDER)}


def sorted_member_names_by_position(data):
    """직위(서열) 기준 정렬 후, 같은 직위 내에서는 이름 가나다순."""
    return [
        m["name"] for m in sorted(
            data["members"],
            key=lambda m: (POSITION_RANK.get(m.get("position", "사원"), 999), m["name"]),
        )
    ]


def sorted_member_display_by_position(data):
    """직위(서열) 기준 정렬 후 '이름 직책' 형태로 반환 (투표 선택지 자동 채우기용)."""
    ordered = sorted(
        data["members"],
        key=lambda m: (POSITION_RANK.get(m.get("position", "사원"), 999), m["name"]),
    )
    return [f"{m['name']} {m.get('position', '사원')}" for m in ordered]


def is_lead_position(position):
    return ("팀장" in position) or ("파트장" in position)


def sorted_members_for_display(data):
    """구성원 관리 목록: 팀장/파트장 등 추가 직위가 붙은 구성원을 상단으로,
    각 그룹 내에서는 이름 가나다순."""
    leads = sorted(
        [m for m in data["members"] if is_lead_position(m.get("position", ""))],
        key=lambda m: m["name"],
    )
    others = sorted(
        [m for m in data["members"] if not is_lead_position(m.get("position", ""))],
        key=lambda m: m["name"],
    )
    return leads + others


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
    # 마이그레이션: 기존 데이터에 없는 필드 보정
    for m in data["members"]:
        m.setdefault("position", "사원")
    for p in data["admin_posts"]:
        p.setdefault("status", "등록")
        if p["status"] in ("★완료★", "진행"):
            p["status"] = "완료" if p["status"] == "★완료★" else "등록"
        p.setdefault("files", [])
        p.setdefault("images", [])
    for p in data["event_posts"]:
        p.setdefault("files", [])
        p.setdefault("images", [])
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


def member_names(data):
    return [m["name"] for m in data["members"]]


def owner_names_combined(data):
    """일정 담당자 선택 목록: 구성원 이름 + 기타 캘린더 이름."""
    return member_names(data) + [c["name"] for c in data.get("calendars", [])]


def owner_color(name, data):
    for m in data["members"]:
        if m["name"] == name:
            return m["color"]
    for c in data.get("calendars", []):
        if c["name"] == name:
            return c["color"]
    return "#999999"


def vote_all_voted(post, data):
    """게시글의 투표에 전체 구성원이 모두 참여했는지 여부."""
    if not post.get("vote"):
        return False
    members = set(member_names(data))
    if not members:
        return False
    voted = set()
    for o in post["vote"]["options"]:
        voted.update(o["voters"])
    return members.issubset(voted)


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
        st.image(base64.b64decode(att["data"]), width="stretch")
    else:
        st.download_button(
            f"📎 {att['name']}",
            data=base64.b64decode(att["data"]),
            file_name=att["name"],
            key=f"{key_prefix}_{att['name']}_{uuid.uuid4().hex[:6]}",
        )


def go_to(page_name, **filters):
    """대시보드 등에서 다른 게시판/필터로 즉시 이동 (다음 실행 시 반영)."""
    st.session_state["_pending_nav"] = {"page": page_name, "filters": filters}
    st.rerun()


def dash_metric(label, count, page_name, **filters):
    st.caption(label)
    if st.button(str(count), key=f"dashbtn_{label}_{page_name}_{filters}", width="stretch"):
        go_to(page_name, **filters)


# --------------------------------------------------------------------------
# 사이드바
# --------------------------------------------------------------------------
data = get_data()

# 위젯이 그려지기 전에 처리해야 하는 초기화 플래그
if st.session_state.pop("_reset_vote_options", False):
    st.session_state["vote_options_text"] = ""

st.session_state.setdefault("page_radio", "대시보드")

# 대시보드 등에서 예약된 페이지/필터 이동 요청을 위젯 생성 전에 반영
_pending_nav = st.session_state.pop("_pending_nav", None)
if _pending_nav:
    st.session_state["page_radio"] = _pending_nav["page"]
    for k, v in _pending_nav["filters"].items():
        st.session_state[k] = v

with st.sidebar:
    st.markdown("## 🌐 온라인팀")
    st.markdown("#### 메뉴")
    page = st.radio(
        "메뉴",
        ["대시보드", "일정 관리", "온라인팀(행사)", "온라인팀(관리)", "구성원 관리"],
        label_visibility="collapsed",
        key="page_radio",
    )
    st.markdown("---")
    st.markdown("##### 현재 사용자")
    names = member_names(data)
    if names:
        current_user = st.selectbox("현재 사용자", names, label_visibility="collapsed", key="current_user_select")
    else:
        current_user = None
        st.info("구성원 관리에서 먼저 구성원을 추가해주세요.")

    if current_user:
        pending = [
            p for p in data["admin_posts"]
            if p.get("vote") and current_user not in {v for o in p["vote"]["options"] for v in o["voters"]}
        ]
        if pending:
            st.markdown("---")
            st.markdown("##### ⚠️ 확인이 필요한 게시글")
            for p in pending[:6]:
                if st.button(f"🗳️ {p['title']}", key=f"pending_jump_{p['id']}", width="stretch"):
                    go_to("온라인팀(관리)", admin_view_filter="전체", admin_quick_filter="없음")

    st.markdown("---")
    st.caption(f"© {date.today().year} {COPYRIGHT_OWNER}")
    st.caption(f"수정 버전: {APP_VERSION}")

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
        if c1.button("✏️ 수정", width="stretch"):
            st.session_state[edit_mode_key] = True
            st.rerun()
        if c2.button("🗑️ 삭제", width="stretch"):
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
    owner_options = owner_names_combined(d)
    default_owner = sched["owner"] if sched else (current_user or (owner_options[0] if owner_options else ""))
    default_cat = sched["category"] if sched else "개인"
    default_memo = sched["memo"] if sched else ""

    title = st.text_input("제목", value=default_title)
    dcol1, dcol2 = st.columns(2)
    start_d = dcol1.date_input("시작일", value=default_start)
    end_d = dcol2.date_input("종료일", value=max(default_end, start_d), min_value=start_d)
    owner = st.selectbox(
        "담당자 / 캘린더", owner_options,
        index=owner_options.index(default_owner) if default_owner in owner_options else 0,
    )
    category = st.selectbox("구분", CATEGORY_LIST, index=CATEGORY_LIST.index(default_cat))
    memo = st.text_area("메모", value=default_memo, height=100)

    b1, b2 = st.columns(2)
    if b1.button("저장", type="primary", width="stretch"):
        if not title.strip():
            st.warning("제목을 입력해주세요.")
        else:
            if editing_existing:
                sched.update(
                    title=title.strip(), start=start_d.isoformat(), end=end_d.isoformat(),
                    owner=owner, category=category, memo=memo,
                )
            else:
                d["schedules"].append(
                    {
                        "id": new_id(), "title": title.strip(),
                        "start": start_d.isoformat(), "end": end_d.isoformat(),
                        "owner": owner, "category": category, "memo": memo,
                    }
                )
            persist()
            st.session_state.sched_dialog_open = False
            if editing_existing:
                st.session_state[edit_mode_key] = False
            st.rerun()
    if b2.button("취소", width="stretch"):
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

    dc1, dc2 = st.columns(2)
    with dc1:
        dash_metric("🗓️ 등록된 일정", len(data["schedules"]), "일정 관리")
    with dc2:
        dash_metric(
            "📢 등록된 공지", len([p for p in data["admin_posts"] if p.get("status") == "공지"]),
            "온라인팀(관리)", admin_view_filter="공지", admin_quick_filter="없음",
        )

    st.markdown("#### 📌 온라인팀(행사)")
    ec1, ec2, ec3 = st.columns(3)
    with ec1:
        dash_metric(
            "💡 제안 중 행사", len([p for p in data["event_posts"] if p["status"] == "제안"]),
            "온라인팀(행사)", event_filter_status="제안",
        )
    with ec2:
        dash_metric(
            "🔄 진행 중 행사", len([p for p in data["event_posts"] if p["status"] == "진행"]),
            "온라인팀(행사)", event_filter_status="진행",
        )
    with ec3:
        dash_metric(
            "🏁 종료된 행사", len([p for p in data["event_posts"] if p["status"] == "종료"]),
            "온라인팀(행사)", event_filter_status="종료",
        )

    st.markdown("#### ⚙️ 온라인팀(관리)")
    ac1, ac2, ac3 = st.columns(3)
    with ac1:
        dash_metric(
            "📝 등록", len([p for p in data["admin_posts"] if p.get("status", "등록") == "등록"]),
            "온라인팀(관리)", admin_view_filter="등록", admin_quick_filter="없음",
        )
    with ac2:
        dash_metric(
            "✅ 체크완료", len([p for p in data["admin_posts"] if vote_all_voted(p, data)]),
            "온라인팀(관리)", admin_view_filter="전체", admin_quick_filter="체크완료",
        )
    with ac3:
        dash_metric(
            "⏳ 완료 처리 필요",
            len([p for p in data["admin_posts"] if vote_all_voted(p, data) and p.get("status") != "완료"]),
            "온라인팀(관리)", admin_view_filter="전체", admin_quick_filter="완료처리필요",
        )

    st.markdown("### 🗓️ 오늘 이후 일정")
    my_only_dash = st.checkbox("내 일정만 보기", key="dash_my_only")
    today = date.today()
    upcoming = [s for s in data["schedules"] if date.fromisoformat(s["end"]) >= today]
    if my_only_dash and current_user:
        upcoming = [s for s in upcoming if s["owner"] == current_user]
    upcoming.sort(key=lambda s: s["start"])
    if upcoming:
        rows = [
            {"제목": s["title"], "기간": f"{s['start']} ~ {s['end']}", "담당자": s["owner"], "구분": s["category"]}
            for s in upcoming
        ]
        st.dataframe(rows, width="stretch", hide_index=True)
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
                "구성원 필터", owner_names_combined(data), label_visibility="collapsed"
            )

        my_only_sched = st.checkbox("내 일정만 보기", key="sched_my_only")

        st.caption("날짜를 클릭하면 해당 날짜를 시작일로 하는 일정 등록 팝업이 열립니다.")

        year = st.session_state.cal_year
        month = st.session_state.cal_month

        visible_schedules = [
            s for s in data["schedules"]
            if not filter_members or s["owner"] in filter_members
        ]
        if my_only_sched and current_user:
            visible_schedules = [s for s in visible_schedules if s["owner"] == current_user]

        calendar_obj = cal.Calendar(firstweekday=6)  # 일요일 시작
        weeks = calendar_obj.monthdatescalendar(year, month)

        # 날짜 버튼을 작고 좌측 상단에 배치하기 위한 스코프 CSS
        st.markdown(
            """
            <style>
            .st-key-cal_grid button {
                height: 22px !important;
                min-height: 22px !important;
                padding: 0px 6px !important;
                font-size: 12px !important;
                line-height: 1 !important;
                justify-content: flex-start !important;
                text-align: left !important;
                color: #333 !important;
                background: transparent !important;
                border: none !important;
            }
            .st-key-cal_grid button:hover {
                color: #fff !important;
                background: #3B82F6 !important;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )

        with st.container(key="cal_grid"):
            weekday_labels = ["일", "월", "화", "수", "목", "금", "토"]
            header_cols = st.columns(7)
            for i, wl in enumerate(weekday_labels):
                color = "#d33" if i == 0 else ("#36c" if i == 6 else "#333")
                header_cols[i].markdown(
                    f"<div style='text-align:center;font-weight:600;color:{color}'>{wl}</div>",
                    unsafe_allow_html=True,
                )

            for week in weeks:
                # 날짜 버튼 줄 (작고 좌측 상단 정렬)
                day_cols = st.columns(7)
                for i, d_ in enumerate(week):
                    with day_cols[i]:
                        if d_.month == month:
                            if st.button(str(d_.day), key=f"day_{d_.isoformat()}"):
                                open_new_schedule_dialog(d_)
                                st.rerun()
                        else:
                            st.markdown(
                                f"<div style='color:#ccc;font-size:12px;padding:2px 6px'>{d_.day}</div>",
                                unsafe_allow_html=True,
                            )

                # 이 주에 걸치는 일정을 하나의 연결된 블록으로 표시 (넓은 영역)
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

                lanes = []
                placed = []
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
                    html = (
                        "<div style='display:grid;grid-template-columns:repeat(7,1fr);"
                        "grid-auto-rows:32px;gap:4px;margin-bottom:8px'>"
                    )
                    for lane_idx, col_start, col_end, s in placed:
                        color = owner_color(s["owner"], data)
                        html += (
                            f"<div style='grid-column:{col_start + 1} / {col_end + 2};"
                            f"grid-row:{lane_idx + 1};background:{color};color:white;"
                            "font-size:13px;padding:5px 8px;border-radius:6px;overflow:hidden;"
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
                color = owner_color(s["owner"], data)
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
        dcol1, dcol2 = st.columns(2)
        s_d = dcol1.date_input("시작일", value=date.today(), key="direct_start")
        e_d = dcol2.date_input("종료일", value=date.today(), key="direct_end", min_value=s_d)
        owner_opts = owner_names_combined(data)
        owner = st.selectbox("담당자 / 캘린더", owner_opts, key="direct_owner") if owner_opts else None
        category = st.selectbox("구분", CATEGORY_LIST, key="direct_category")
        memo = st.text_area("메모", key="direct_memo")
        if st.button("일정 등록", type="primary"):
            if not title.strip():
                st.warning("제목을 입력해주세요.")
            else:
                data["schedules"].append(
                    {
                        "id": new_id(), "title": title.strip(),
                        "start": s_d.isoformat(), "end": e_d.isoformat(),
                        "owner": owner, "category": category, "memo": memo,
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
        "보기", ["전체"] + STATUS_LIST, horizontal=True, key="event_filter_status",
        format_func=lambda s: s if s == "전체" else f"{STATUS_ICONS.get(s, '')} {s}",
    )
    only_mine = st.checkbox("내가 쓴 글만 보기")

    # 새 게시글 작성 버튼: '제안' 필터에서만 노출
    if filter_status == "제안":
        if st.button("➕ 새 행사 게시글 작성", key="toggle_new_event_form"):
            st.session_state["show_new_event_form"] = not st.session_state.get("show_new_event_form", False)

        if st.session_state.get("show_new_event_form"):
            with st.container(border=True):
                st.markdown("#### ➕ 새 행사 게시글 작성 (상태: 💡 제안)")
                e_title = st.text_input("제목", key="new_event_title")
                e_content = st.text_area(
                    "내용 (텍스트 입력 또는 붙여넣기)", key="new_event_content", height=140
                )
                e_files = st.file_uploader(
                    "첨부파일 (이미지 포함, 드래그앤드롭 지원)",
                    accept_multiple_files=True, key="new_event_files",
                )
                if st.button("게시글 등록", type="primary", key="submit_event_post"):
                    if not e_title.strip():
                        st.warning("제목을 입력해주세요.")
                    else:
                        data["event_posts"].append(
                            {
                                "id": new_id(), "title": e_title.strip(), "status": "제안",
                                "content": e_content,
                                "images": [],
                                "files": [file_to_b64(f_) for f_ in (e_files or [])],
                                "author": current_user, "created_at": now_str(), "comments": [],
                            }
                        )
                        persist()
                        st.session_state["show_new_event_form"] = False
                        st.success("게시글이 등록되었습니다.")
                        st.rerun()
    else:
        st.caption("새 게시글 작성은 '제안' 탭에서만 가능합니다.")

    st.markdown("---")

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
                    format_func=lambda s: f"{STATUS_ICONS.get(s, '')} {s}",
                    key=f"status_{p['id']}", label_visibility="collapsed",
                )
                if new_status != p["status"]:
                    p["status"] = new_status
                    persist()
                    st.rerun()
            with right:
                b1, b2 = st.columns(2)
                edit_key = f"editing_event_{p['id']}"
                if b1.button("수정", key=f"edit_btn_{p['id']}", width="stretch"):
                    st.session_state[edit_key] = not st.session_state.get(edit_key, False)
                    st.rerun()
                if b2.button("삭제", key=f"del_btn_{p['id']}", width="stretch"):
                    data["event_posts"] = [x for x in data["event_posts"] if x["id"] != p["id"]]
                    persist()
                    st.rerun()

            st.markdown(f"### {p['title']}")
            st.caption(f"작성자 {p['author']} · {p['created_at']}")

            existing_atts = p.get("files", []) + p.get("images", [])

            if st.session_state.get(f"editing_event_{p['id']}"):
                new_title = st.text_input("제목 수정", value=p["title"], key=f"et_{p['id']}")
                new_content = st.text_area("내용 수정", value=p["content"], key=f"ec_{p['id']}", height=120)
                st.write("기존 첨부파일 (삭제할 항목 체크)")
                keep_flags = []
                for idx, att in enumerate(existing_atts):
                    cA, cB = st.columns([4, 1])
                    cA.write(f"📎 {att['name']}")
                    remove = cB.checkbox("삭제", key=f"ev_delatt_{p['id']}_{idx}")
                    keep_flags.append(not remove)
                add_files = st.file_uploader(
                    "첨부파일 추가", accept_multiple_files=True, key=f"ev_addfiles_{p['id']}"
                )
                if st.button("저장", key=f"save_edit_{p['id']}"):
                    kept = [att for keep, att in zip(keep_flags, existing_atts) if keep]
                    added = [file_to_b64(f_) for f_ in (add_files or [])]
                    p["title"] = new_title.strip() or p["title"]
                    p["content"] = new_content
                    p["files"] = kept + added
                    p["images"] = []
                    persist()
                    st.session_state[f"editing_event_{p['id']}"] = False
                    st.rerun()
            else:
                st.write(p["content"])
                for att in existing_atts:
                    render_attachment(att, key_prefix=f"ev_{p['id']}")

            st.markdown("**💬 댓글**")
            for c in p.get("comments", []):
                st.markdown(f"- **{c['author']}** ({c['time']}): {c['text']}")
            new_comment = st.text_input(
                "댓글 작성", key=f"comment_input_{p['id']}", label_visibility="collapsed", placeholder="댓글을 입력하세요"
            )
            if st.button("댓글 등록", key=f"comment_btn_{p['id']}"):
                if new_comment.strip():
                    p.setdefault("comments", []).append(
                        {"author": current_user, "text": new_comment.strip(), "time": now_str()}
                    )
                    persist()
                    st.rerun()

# --------------------------------------------------------------------------
# 페이지: 온라인팀(관리)  (일반 게시글 + 투표)
# --------------------------------------------------------------------------
elif page == "온라인팀(관리)":
    st.markdown("# ⚙️ 온라인팀(관리)")
    st.caption("공지·안건 게시글과 투표를 함께 관리합니다.")

    view_filter = st.radio(
        "보기", ["전체"] + ADMIN_STATUS_LIST, horizontal=True, key="admin_view_filter",
        format_func=lambda s: s if s == "전체" else f"{STATUS_ICONS.get(s, '')} {s}",
    )
    quick_filter = st.selectbox(
        "빠른 필터", ["없음", "체크완료", "완료처리필요"], key="admin_quick_filter",
    )

    if st.button("➕ 새 글 작성", key="toggle_new_admin_form"):
        st.session_state["show_new_admin_form"] = not st.session_state.get("show_new_admin_form", False)

    if st.session_state.get("show_new_admin_form"):
        with st.container(border=True):
            st.markdown("#### ➕ 새 글 작성")
            a_title = st.text_input("제목", key="new_admin_title")
            a_status = st.selectbox(
                "상태", ADMIN_STATUS_LIST, key="new_admin_status",
                format_func=lambda s: f"{STATUS_ICONS.get(s, '')} {s}",
            )
            a_content = st.text_area("내용 (텍스트 입력 또는 붙여넣기)", key="new_admin_content", height=140)
            a_files = st.file_uploader(
                "첨부파일 (이미지 포함, 드래그앤드롭 지원)",
                accept_multiple_files=True, key="new_admin_files",
            )

            add_vote = st.checkbox("🗳️ 이 게시글에 투표 추가하기", key="new_admin_add_vote")

            v_multi = False
            if add_vote:
                st.markdown("##### 투표 설정")
                st.caption("투표 문항은 위의 '제목'이 그대로 사용됩니다. 선택지를 아래에 입력해주세요.")

                templates = data["vote_templates"]
                template_names = ["(직접 입력)"] + [t["name"] for t in templates]
                tcol1, tcol2, tcol3 = st.columns([2, 1, 1])
                chosen_template = tcol1.selectbox("투표 양식 불러오기", template_names, key="vote_template_select")
                if tcol2.button("양식 불러오기", width="stretch"):
                    if chosen_template != "(직접 입력)":
                        tpl = next(t for t in templates if t["name"] == chosen_template)
                        st.session_state["vote_options_text"] = "\n".join(tpl["options"])
                        st.rerun()
                if tcol3.button("👥 구성원 불러오기", width="stretch"):
                    st.session_state["vote_options_text"] = "\n".join(sorted_member_display_by_position(data))
                    st.rerun()

                st.session_state.setdefault("vote_options_text", "")
                v_options_text = st.text_area(
                    "선택지 (한 줄에 하나씩 입력)", key="vote_options_text", height=120
                )
                v_multi = st.checkbox("복수 선택 허용", key="new_vote_multi")

                with st.expander("📋 현재 선택지를 투표 양식(템플릿)으로 저장"):
                    tpl_name = st.text_input("템플릿 이름", key="tpl_save_name")
                    if st.button("템플릿으로 저장"):
                        opts = [o.strip() for o in st.session_state["vote_options_text"].split("\n") if o.strip()]
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

            if st.button("게시글 등록", type="primary", key="submit_admin_post"):
                if not a_title.strip():
                    st.warning("제목을 입력해주세요.")
                else:
                    vote_field = None
                    if add_vote:
                        opts = [o.strip() for o in st.session_state.get("vote_options_text", "").split("\n") if o.strip()]
                        if len(opts) < 2:
                            st.warning("투표 선택지를 2개 이상 입력해주세요.")
                            st.stop()
                        vote_field = {
                            "question": a_title.strip(), "multi": v_multi,
                            "options": [{"text": o, "voters": []} for o in opts],
                        }
                    new_post = {
                        "id": new_id(), "title": a_title.strip(), "content": a_content,
                        "status": a_status, "author": current_user, "created_at": now_str(),
                        "comments": [],
                        "images": [],
                        "files": [file_to_b64(f_) for f_ in (a_files or [])],
                    }
                    if vote_field:
                        new_post["vote"] = vote_field
                    data["admin_posts"].append(new_post)
                    persist()
                    st.session_state["_reset_vote_options"] = True
                    st.session_state["show_new_admin_form"] = False
                    st.success("게시글이 등록되었습니다.")
                    st.rerun()

    st.markdown("---")

    posts = sorted(data["admin_posts"], key=lambda p: p["created_at"], reverse=True)
    if view_filter != "전체":
        posts = [p for p in posts if p.get("status", "등록") == view_filter]
    if quick_filter == "체크완료":
        posts = [p for p in posts if vote_all_voted(p, data)]
    elif quick_filter == "완료처리필요":
        posts = [p for p in posts if vote_all_voted(p, data) and p.get("status") != "완료"]

    if not posts:
        st.info("표시할 게시글이 없습니다.")

    for p in posts:
        with st.container(border=True):
            top_l, top_r = st.columns([1, 1])
            with top_l:
                cur_status = p.get("status", "등록")
                new_status = st.selectbox(
                    "상태", ADMIN_STATUS_LIST, index=ADMIN_STATUS_LIST.index(cur_status),
                    format_func=lambda s: f"{STATUS_ICONS.get(s, '')} {s}",
                    key=f"admin_status_{p['id']}", label_visibility="collapsed",
                )
                if new_status != cur_status:
                    p["status"] = new_status
                    persist()
                    st.rerun()
            with top_r:
                b1, b2 = st.columns(2)
                if b1.button("수정", key=f"aedit_{p['id']}", width="stretch"):
                    st.session_state[f"admin_editing_{p['id']}"] = not st.session_state.get(f"admin_editing_{p['id']}", False)
                    st.rerun()
                if b2.button("삭제", key=f"adel_{p['id']}", width="stretch"):
                    data["admin_posts"] = [x for x in data["admin_posts"] if x["id"] != p["id"]]
                    persist()
                    st.rerun()

            title_prefix = "🗳️ " if p.get("vote") else ""
            if vote_all_voted(p, data):
                title_prefix += "✅ "
            st.markdown(f"### {title_prefix}{p['title']}")
            st.caption(f"작성자 {p['author']} · {p['created_at']}")

            existing_atts = p.get("files", []) + p.get("images", [])

            if st.session_state.get(f"admin_editing_{p['id']}"):
                new_title = st.text_input("제목 수정", value=p["title"], key=f"at_{p['id']}")
                new_content = st.text_area("내용 수정", value=p.get("content", ""), key=f"ac_{p['id']}", height=100)

                st.write("기존 첨부파일 (삭제할 항목 체크)")
                keep_flags = []
                for idx, att in enumerate(existing_atts):
                    cA, cB = st.columns([4, 1])
                    cA.write(f"📎 {att['name']}")
                    remove = cB.checkbox("삭제", key=f"ad_delatt_{p['id']}_{idx}")
                    keep_flags.append(not remove)
                add_files = st.file_uploader(
                    "첨부파일 추가", accept_multiple_files=True, key=f"ad_addfiles_{p['id']}"
                )

                new_vote_options_text = None
                new_vote_multi = None
                if p.get("vote"):
                    st.write("투표 선택지 수정 (한 줄에 하나씩, 기존 투표 결과는 텍스트가 같으면 유지됩니다)")
                    existing_opts_text = "\n".join(o["text"] for o in p["vote"]["options"])
                    new_vote_options_text = st.text_area(
                        "선택지", value=existing_opts_text, key=f"editvote_{p['id']}", height=100
                    )
                    new_vote_multi = st.checkbox(
                        "복수 선택 허용", value=p["vote"].get("multi", False), key=f"editvotemulti_{p['id']}"
                    )

                if st.button("저장", key=f"admin_save_{p['id']}"):
                    kept = [att for keep, att in zip(keep_flags, existing_atts) if keep]
                    added = [file_to_b64(f_) for f_ in (add_files or [])]
                    p["title"] = new_title.strip() or p["title"]
                    p["content"] = new_content
                    p["files"] = kept + added
                    p["images"] = []
                    if p.get("vote") and new_vote_options_text is not None:
                        old_by_text = {o["text"]: o["voters"] for o in p["vote"]["options"]}
                        new_lines = [l.strip() for l in new_vote_options_text.split("\n") if l.strip()]
                        p["vote"]["options"] = [
                            {"text": t, "voters": old_by_text.get(t, [])} for t in new_lines
                        ]
                        p["vote"]["multi"] = new_vote_multi
                        p["vote"]["question"] = p["title"]
                    persist()
                    st.session_state[f"admin_editing_{p['id']}"] = False
                    st.rerun()
            else:
                if p.get("content"):
                    st.write(p["content"])
                for att in existing_atts:
                    render_attachment(att, key_prefix=f"admin_{p['id']}")

            if p.get("vote"):
                vote = p["vote"]
                st.markdown(f"**🗳️ {vote['question']}**")
                options = vote["options"]
                my_votes = [i for i, o in enumerate(options) if current_user in o["voters"]]

                if vote.get("multi"):
                    picked = st.multiselect(
                        "선택지 (복수 선택 가능)", list(range(len(options))), default=my_votes,
                        format_func=lambda i: options[i]["text"], key=f"vote_multi_{p['id']}",
                    )
                else:
                    idx_default = my_votes[0] if my_votes else None
                    picked_single = st.radio(
                        "선택지", list(range(len(options))), index=idx_default,
                        format_func=lambda i: options[i]["text"], key=f"vote_single_{p['id']}",
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

                st.markdown("**👥 투표 완료자**")
                result_html = "<div style='margin-bottom:6px;font-size:13px'>"
                for o in options:
                    voters_str = ", ".join(o["voters"]) if o["voters"] else "-"
                    result_html += (
                        f"<div style='margin-bottom:2px'><b>{o['text']}</b> "
                        f"({len(o['voters'])}명): {voters_str}</div>"
                    )
                result_html += "</div>"
                st.markdown(result_html, unsafe_allow_html=True)

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

# --------------------------------------------------------------------------
# 페이지: 구성원 관리
# --------------------------------------------------------------------------
elif page == "구성원 관리":
    st.markdown("# ⚙️ 구성원 관리")

    st.markdown("### 구성원 추가")
    new_name = st.text_input("이름", key="new_member_name", placeholder="이름")
    new_position = st.selectbox("직책/직위", POSITION_OPTIONS, key="new_member_position")

    used_colors = {m["color"] for m in data["members"]} | {c["color"] for c in data.get("calendars", [])}
    available_presets = [c for c in PRESET_COLORS if c[1] not in used_colors]

    if "member_color_choice" not in st.session_state:
        st.session_state.member_color_choice = available_presets[0][1] if available_presets else "custom"

    st.markdown("**개인 색상 선택** (이미 다른 구성원/캘린더가 사용 중인 색상은 표시되지 않습니다)")
    swatch_cols = st.columns(6)
    for i, (cname, hexcode) in enumerate(available_presets):
        with swatch_cols[i % 6]:
            selected = st.session_state.member_color_choice == hexcode
            border = "3px solid #111827" if selected else "1px solid #ddd"
            st.markdown(
                f"<div style='width:100%;height:34px;border-radius:8px;background:{hexcode};"
                f"border:{border};margin-bottom:2px'></div>",
                unsafe_allow_html=True,
            )
            if st.button(cname, key=f"swatch_{hexcode}", width="stretch"):
                st.session_state.member_color_choice = hexcode
                st.rerun()

    other_selected = st.session_state.member_color_choice == "custom"
    other_col = swatch_cols[len(available_presets) % 6] if len(available_presets) % 6 != 0 else st.columns(6)[0]
    with other_col:
        border = "3px solid #111827" if other_selected else "1px dashed #999"
        st.markdown(
            f"<div style='width:100%;height:34px;border-radius:8px;"
            "background:repeating-linear-gradient(45deg,#eee,#eee 4px,#fff 4px,#fff 8px);"
            f"border:{border};margin-bottom:2px'></div>",
            unsafe_allow_html=True,
        )
        if st.button("기타", key="swatch_custom", width="stretch"):
            st.session_state.member_color_choice = "custom"
            st.rerun()

    final_color = st.session_state.member_color_choice
    if final_color == "custom":
        final_color = st.color_picker("기타 색상 직접 선택", value="#999999", key="member_custom_color")

    if st.button("추가", type="primary"):
        if not new_name.strip():
            st.warning("이름을 입력해주세요.")
        elif new_name.strip() in member_names(data):
            st.warning("이미 존재하는 구성원입니다.")
        elif final_color in used_colors:
            st.warning("이미 사용 중인 색상입니다. 다른 색상을 선택해주세요.")
        else:
            data["members"].append(
                {"name": new_name.strip(), "color": final_color, "position": new_position}
            )
            persist()
            del st.session_state["member_color_choice"]
            st.success(f"{new_name.strip()}님이 추가되었습니다.")
            st.rerun()

    st.markdown("---")
    st.markdown("### 현재 구성원")
    st.caption("직책에 '팀장'·'파트장'이 포함된 구성원은 목록 상단에 가나다순으로 표시됩니다.")
    if not data["members"]:
        st.info("등록된 구성원이 없습니다.")
    for m in sorted_members_for_display(data):
        c1, c2, c3, c4 = st.columns([1, 3, 2, 1])
        c1.markdown(
            f"<div style='width:22px;height:22px;border-radius:50%;background:{m['color']}'></div>",
            unsafe_allow_html=True,
        )
        c2.write(m["name"])
        c3.caption(m.get("position", "사원"))
        if c4.button("삭제", key=f"member_del_{m['name']}"):
            data["members"] = [x for x in data["members"] if x["name"] != m["name"]]
            persist()
            st.success(f"{m['name']}님이 삭제되었습니다.")
            st.rerun()

    st.markdown("---")
    st.markdown("### 🗓️ 기타 캘린더")
    st.caption("구성원 개인 일정 외에, 공용/기타 목적의 캘린더를 추가로 만들 수 있습니다. "
               "추가 → 이름 수정 → 색상 지정 순서로 설정해주세요.")
    if st.button("+ 캘린더 추가"):
        used = {m["color"] for m in data["members"]} | {c["color"] for c in data.get("calendars", [])}
        avail = [hexcode for _, hexcode in PRESET_COLORS if hexcode not in used]
        new_color = avail[0] if avail else "#999999"
        idx = len(data.get("calendars", [])) + 1
        data.setdefault("calendars", []).append(
            {"id": new_id(), "name": f"새 캘린더 {idx}", "color": new_color}
        )
        persist()
        st.rerun()

    for c in data.get("calendars", []):
        cc1, cc2, cc3 = st.columns([3, 2, 1])
        with cc1:
            new_cal_name = st.text_input(
                "이름", value=c["name"], key=f"cal_name_{c['id']}", label_visibility="collapsed"
            )
        with cc2:
            new_cal_color = st.color_picker(
                "색상", value=c["color"], key=f"cal_color_{c['id']}", label_visibility="collapsed"
            )
        if new_cal_name != c["name"] or new_cal_color != c["color"]:
            c["name"] = new_cal_name
            c["color"] = new_cal_color
            persist()
        if cc3.button("삭제", key=f"cal_del_{c['id']}"):
            data["calendars"] = [x for x in data["calendars"] if x["id"] != c["id"]]
            persist()
            st.rerun()
