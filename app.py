import streamlit as st
import json
import re
import os
from supabase import create_client, Client

# --- ページ設定 ---
st.set_page_config(
    page_title="AI実装検定A級 CBT対策アプリ", 
    layout="centered", 
    initial_sidebar_state="collapsed"
)

# --- Supabase 接続設定 ---
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

@st.cache_resource
def init_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_supabase()

# --- データ読み込み ---
@st.cache_data
def load_data():
    questions_file = "questions.json"
    if os.path.exists(questions_file):
        with open(questions_file, "r", encoding="utf-8") as f:
            data_str = f.read()
            clean_str = re.sub(r'\]+\]', '', data_str)
            return json.loads(clean_str)
    return {}

data = load_data()
if not data:
    st.error("questions.json が見つかりません。")
    st.stop()

categories = list(data.keys())

# --- クラウド同期関数 ---
def load_user_marks(user_id: str):
    if not user_id:
        return set()
    res = supabase.table("user_progress").select("marks").eq("user_id", user_id).execute()
    if res.data:
        return set(res.data[0].get("marks", []))
    else:
        # 新規ユーザー作成
        supabase.table("user_progress").insert({"user_id": user_id, "marks": []}).execute()
        return set()

def save_user_marks(user_id: str, marks_set: set):
    if not user_id:
        return
    supabase.table("user_progress").upsert({
        "user_id": user_id,
        "marks": list(marks_set)
    }).execute()

# --- URLパラメータ同期関数（デグレ修正箇所） ---
def sync_params():
    st.query_params["user"] = st.session_state.user_id
    st.query_params["category"] = st.session_state.category
    st.query_params["mode"] = st.session_state.mode
    st.query_params["q"] = str(st.session_state.q_index)

# --- セッション初期化 ---
params = st.query_params

if "user_id" not in st.session_state:
    st.session_state.user_id = params.get("user", "user1")

if "review_marks" not in st.session_state:
    st.session_state.review_marks = load_user_marks(st.session_state.user_id)

if "category" not in st.session_state:
    st.session_state.category = params.get("category", categories[0]) if params.get("category") in categories else categories[0]

if "mode" not in st.session_state:
    st.session_state.mode = params.get("mode", "すべての問題")

if "q_index" not in st.session_state:
    try:
        st.session_state.q_index = int(params.get("q", 0))
    except ValueError:
        st.session_state.q_index = 0

# 起動時に現在の状態をURLに反映
sync_params()

# --- コールバック ---
def on_user_change():
    st.session_state.user_id = st.session_state.user_id_input
    st.session_state.review_marks = load_user_marks(st.session_state.user_id)
    st.session_state.q_index = 0
    sync_params()

def on_category_change():
    st.session_state.q_index = 0
    sync_params()

def on_mode_change():
    st.session_state.q_index = 0
    sync_params()

def go_prev():
    if st.session_state.q_index > 0:
        st.session_state.q_index -= 1
        sync_params()

def go_next(total_q):
    if st.session_state.q_index < total_q - 1:
        st.session_state.q_index += 1
        sync_params()

def toggle_review(q_id):
    if q_id in st.session_state.review_marks:
        st.session_state.review_marks.remove(q_id)
    else:
        st.session_state.review_marks.add(q_id)
    # クラウドに即時保存
    save_user_marks(st.session_state.user_id, st.session_state.review_marks)

# --- サイドバー ---
st.sidebar.title("設定 & 同期")
st.sidebar.text_input("ユーザーID (同期キー):", value=st.session_state.user_id, key="user_id_input", on_change=on_user_change)
st.sidebar.caption("※iPadとiPhoneで同じIDを入力すると進捗が自動同期されます。")

st.sidebar.markdown("---")
st.sidebar.title("学習モード")
st.sidebar.radio(
    "表示モード", 
    ["すべての問題", "チェックした問題のみ（復習）"], 
    key="mode", 
    on_change=on_mode_change
)

# --- UI構築 ---
if st.session_state.mode == "チェックした問題のみ（復習）":
    st.title("🔁 復習モード実行中")
else:
    st.title("AI実装検定A級 対策アプリ")

selected_category = st.selectbox("分野を選択してください", categories, key="category", on_change=on_category_change)

all_questions = data[selected_category]
if st.session_state.mode == "チェックした問題のみ（復習）":
    questions = [q for q in all_questions if q["id"] in st.session_state.review_marks]
else:
    questions = all_questions

total_q = len(questions)

if total_q == 0:
    st.warning("表示する問題がありません。")
else:
    if st.session_state.q_index >= total_q:
        st.session_state.q_index = total_q - 1

    current_q = questions[st.session_state.q_index]
    q_id = current_q["id"]

    progress_val = (st.session_state.q_index + 1) / total_q
    st.progress(progress_val)

    col_header1, col_header2 = st.columns([3, 1])
    with col_header1:
        st.caption(f"問題 {st.session_state.q_index + 1} / {total_q}")
    with col_header2:
        is_checked = q_id in st.session_state.review_marks
        st.checkbox("📌 復習リストに追加", value=is_checked, key=f"check_{q_id}", on_change=toggle_review, args=(q_id,))

    q_text = current_q.get("question", "")
    st.info(q_text)

    if "image_path" in current_q and current_q["image_path"]:
        if os.path.exists(current_q["image_path"]):
            st.image(current_q["image_path"], use_container_width=True)

    if "code_snippet" in current_q and current_q["code_snippet"]:
        st.code(current_q["code_snippet"], language="python")

    q_type = current_q.get("type", "text")
    input_key = f"ans_{q_id}"
    
    if q_type == "multiple_choice":
        options = current_q.get("options", [])
        selected_ans = st.radio("選択肢:", options, key=input_key, index=None)
        if selected_ans is not None:
            if selected_ans == current_q.get("answer", ""):
                st.success("正解！ 🎉")
            else:
                st.error("不正解...")

    elif q_type == "fill_in_blank":
        user_ans = st.text_input("空欄に当てはまるコードを入力:", key=input_key)
        if user_ans:
            if user_ans.strip() == current_q.get("answer", ""):
                st.success("正解！ 🎉")
            else:
                st.error("不正解...")

    with st.expander("💡 解答と解説を表示する"):
        st.write(f"**【正解】**\n\n{current_q.get('answer', '')}")
        if "explanation" in current_q:
            st.write("---")
            st.write(f"**【解説】**\n\n{current_q['explanation']}")

    st.write("---")

    col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 1])
    with col_btn1:
        st.button("◀ 前の問題へ", on_click=go_prev, disabled=(st.session_state.q_index == 0), use_container_width=True)
    with col_btn3:
        st.button("次の問題へ ▶", on_click=go_next, args=(total_q,), disabled=(st.session_state.q_index == total_q - 1), use_container_width=True)
