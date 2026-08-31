import streamlit as st
import json
import re
import os

@st.cache_data
def load_data():
    questions_file = "questions.json"
    if os.path.exists(questions_file):
        with open(questions_file, "r", encoding="utf-8") as f:
            data_str = f.read()
            #[cite: 1] や[cite: 1, 3] などの引用表記を一括削除
            clean_str = re.sub(r'\+\]', '', data_str)
            return json.loads(clean_str)
    return {}
    
# --- ページ設定 ---
st.set_page_config(page_title="AI実装検定A級 CBT対策アプリ", layout="centered")

# --- データ読み込み ---
@st.cache_data
def load_data():
    questions_file = "questions.json"
    if os.path.exists(questions_file):
        with open(questions_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

data = load_data()

if not data:
    st.error("questions.json が見つかりません。")
    st.stop()

categories = list(data.keys())

# --- セッション状態の初期化 ---
if "category" not in st.session_state:
    st.session_state.category = categories[0]
if "q_index" not in st.session_state:
    st.session_state.q_index = 0
if "review_marks" not in st.session_state:
    st.session_state.review_marks = set() # チェックした問題IDを保存

# --- コールバック関数 ---
def on_category_change():
    st.session_state.q_index = 0

def go_prev():
    if st.session_state.q_index > 0:
        st.session_state.q_index -= 1

def go_next(total_q):
    if st.session_state.q_index < total_q - 1:
        st.session_state.q_index += 1

def toggle_review(q_id):
    if q_id in st.session_state.review_marks:
        st.session_state.review_marks.remove(q_id)
    else:
        st.session_state.review_marks.add(q_id)

# --- サイドバー (モード選択) ---
st.sidebar.title("学習モード設定")
mode = st.sidebar.radio("表示モード", ["すべての問題", "チェックした問題のみ（復習）"], on_change=on_category_change)

# --- UI構築 ---
st.title("AI実装検定A級 対策アプリ")

selected_category = st.selectbox(
    "分野を選択してください",
    categories,
    key="category",
    on_change=on_category_change
)

# モードに応じて問題をフィルタリング
all_questions = data[selected_category]
if mode == "チェックした問題のみ（復習）":
    questions = [q for q in all_questions if q["id"] in st.session_state.review_marks]
else:
    questions = all_questions

total_q = len(questions)

if total_q == 0:
    st.warning("この分野で表示する問題がありません。")
else:
    # 現在のインデックスが範囲外にならないよう調整
    if st.session_state.q_index >= total_q:
        st.session_state.q_index = total_q - 1

    current_q = questions[st.session_state.q_index]
    q_id = current_q["id"]

    # 1. ヘッダー情報と振り返りチェックボックス
    col_header1, col_header2 = st.columns([3, 1])
    with col_header1:
        st.caption(f"問題 {st.session_state.q_index + 1} / {total_q}")
    with col_header2:
        is_checked = q_id in st.session_state.review_marks
        st.checkbox("復習にチェック", value=is_checked, key=f"check_{q_id}", on_change=toggle_review, args=(q_id,))

    # 2. 問題文の表示
    st.info(current_q.get("question", ""))

    # 3. 画像がある場合の表示 (例: 画像から判断する問題)
    if "image_path" in current_q and current_q["image_path"]:
        if os.path.exists(current_q["image_path"]):
            st.image(current_q["image_path"], use_container_width=True)
        else:
            st.warning(f"画像が見つかりません: {current_q['image_path']}")

    # 4. コードがある場合の表示 (例: Python穴埋め問題)
    if "code_snippet" in current_q and current_q["code_snippet"]:
        st.code(current_q["code_snippet"], language="python")

    # 5. 解答入力 / 選択肢
    q_type = current_q.get("type", "text")
    input_key = f"ans_{q_id}"
    
    if q_type == "multiple_choice":
        options = current_q.get("options", [])
        st.radio("選択肢:", options, key=input_key, index=None)
    elif q_type == "fill_in_blank":
        st.text_input("空欄に当てはまるコードを入力:", key=input_key)
    else:
        st.text_area("解答を入力:", key=input_key, height=100)

    # 6. 解答・解説の表示
    with st.expander("💡 解答と解説を表示する"):
        st.success(f"**【正解】**\n\n{current_q.get('answer', '')}")
        if "explanation" in current_q:
            st.write(f"**【解説】**\n\n{current_q['explanation']}")

    st.write("---")

    # 7. ナビゲーションボタン
    col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 1])
    with col_btn1:
        st.button("◀ 前の問題へ", on_click=go_prev, disabled=(st.session_state.q_index == 0), use_container_width=True)
    with col_btn3:
        st.button("次の問題へ ▶", on_click=go_next, args=(total_q,), disabled=(st.session_state.q_index == total_q - 1), use_container_width=True)
