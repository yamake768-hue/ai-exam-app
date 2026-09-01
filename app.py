import streamlit as st
import json
import re
import os
import base64

# --- ページ設定 ---
st.set_page_config(
    page_title="AI実装検定A級 CBT対策アプリ", 
    layout="centered", 
    initial_sidebar_state="collapsed"
)

# --- データ読み込み ---
@st.cache_data
def load_data():
    questions_file = "questions.json"
    if os.path.exists(questions_file):
        with open(questions_file, "r", encoding="utf-8") as f:
            data_str = f.read()
            # 引用タグ[cite: 1] などを正規表現で一括削除
            clean_str = re.sub(r'\]+\]', '', data_str)
            return json.loads(clean_str)
    return {}

data = load_data()

if not data:
    st.error("questions.json が見つかりません。")
    st.stop()

categories = list(data.keys())

# --- URLパラメータとセッション状態の同期 ---
params = st.query_params

if "category" not in st.session_state:
    st.session_state.category = params.get("category", categories[0])

if "mode" not in st.session_state:
    st.session_state.mode = params.get("mode", "すべての問題")

if "q_index" not in st.session_state:
    try:
        st.session_state.q_index = int(params.get("q", 0))
    except ValueError:
        st.session_state.q_index = 0

if "review_marks" not in st.session_state:
    marks_str = params.get("marks", "")
    st.session_state.review_marks = set(marks_str.split(",")) if marks_str else set()

# 状態変更時にURLパラメータを更新する関数
def sync_params():
    st.query_params["category"] = st.session_state.category
    st.query_params["mode"] = st.session_state.mode
    st.query_params["q"] = str(st.session_state.q_index)
    
    marks_joined = ",".join(st.session_state.review_marks)
    if marks_joined:
        st.query_params["marks"] = marks_joined
    else:
        if "marks" in st.query_params:
            del st.query_params["marks"]

# --- コールバック関数 ---
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
    sync_params()

def restore_data():
    code = st.session_state.transfer_code_input
    if code:
        try:
            decoded_bytes = base64.b64decode(code.encode('utf-8'))
            decoded_str = decoded_bytes.decode('utf-8')
            st.session_state.review_marks = set(decoded_str.split(",")) if decoded_str else set()
            sync_params()
            st.session_state.restore_msg = "復元に成功しました！"
        except Exception:
            st.session_state.restore_msg = "無効なコードです。"

# --- サイドバー ---
st.sidebar.title("学習モード設定")
st.sidebar.radio(
    "表示モード", 
    ["すべての問題", "チェックした問題のみ（復習）"], 
    key="mode", 
    on_change=on_mode_change
)

st.sidebar.markdown("---")
st.sidebar.subheader("💾 データ引き継ぎ")
with st.sidebar.expander("引き継ぎコードの発行 / 復元"):
    st.markdown("**1. コードを発行してコピー**")
    marks_joined = ",".join(st.session_state.review_marks)
    if marks_joined:
        # 復習リストのID群をBase64でエンコードして短縮
        export_code = base64.b64encode(marks_joined.encode('utf-8')).decode('utf-8')
        st.code(export_code)
        st.caption("※右上のコピーアイコンをタップしてください")
    else:
        st.info("チェックした問題がありません。")
        
    st.markdown("---")
    st.markdown("**2. コードを貼り付けて復元**")
    st.text_input("コードを入力:", key="transfer_code_input")
    st.button("復元する", on_click=restore_data)
    
    if "restore_msg" in st.session_state:
        if "成功" in st.session_state.restore_msg:
            st.success(st.session_state.restore_msg)
        else:
            st.error(st.session_state.restore_msg)

# --- UI構築 ---
if st.session_state.mode == "チェックした問題のみ（復習）":
    st.title("🔁 復習モード実行中")
    st.info("チェックを付けた問題のみを集中的に出題しています。")
else:
    st.title("AI実装検定A級 対策アプリ")

selected_category = st.selectbox(
    "分野を選択してください",
    categories,
    key="category",
    on_change=on_category_change
)

all_questions = data[selected_category]
if st.session_state.mode == "チェックした問題のみ（復習）":
    questions = [q for q in all_questions if q["id"] in st.session_state.review_marks]
else:
    questions = all_questions

total_q = len(questions)

if total_q == 0:
    if st.session_state.mode == "チェックした問題のみ（復習）":
        st.warning("この分野でチェックされた復習問題はありません。")
    else:
        st.warning("この分野で表示する問題がありません。")
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

    st.info(current_q.get("question", ""))

    if "image_path" in current_q and current_q["image_path"]:
        if os.path.exists(current_q["image_path"]):
            st.image(current_q["image_path"], use_container_width=True)
        else:
            st.warning(f"画像が見つかりません: {current_q['image_path']}")

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

    else:
        st.text_area("解答を入力:", key=input_key, height=100)

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
