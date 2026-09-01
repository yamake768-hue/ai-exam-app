import streamlit as st
import json
import re
import os

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
            #[cite: 1] などの引用タグを正規表現で一括削除
            clean_str = re.sub(r'\]+\]', '', data_str)
            return json.loads(clean_str)
    return {}

data = load_data()

if not data:
    st.error("questions.json が見つかりません。")
    st.stop()

categories = list(data.keys())

# --- URLパラメータとセッション状態の同期 ---
# URLから状態を取得（リロード対策）
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


# --- サイドバー (モード選択) ---
st.sidebar.title("学習モード設定")
st.sidebar.radio(
    "表示モード", 
    ["すべての問題", "チェックした問題のみ（復習）"], 
    key="mode", 
    on_change=on_mode_change
)

# --- UI構築 ---
# モードに応じてタイトルを変更
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

# モードに応じて問題をフィルタリング
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
    # 現在のインデックスが範囲外にならないよう調整（リロード時のフェイルセーフ）
    if st.session_state.q_index >= total_q:
        st.session_state.q_index = total_q - 1

    current_q = questions[st.session_state.q_index]
    q_id = current_q["id"]

    # 1. 進捗プログレスバー
    progress_val = (st.session_state.q_index + 1) / total_q
    st.progress(progress_val)

    # 2. ヘッダー情報と振り返りチェックボックス
    col_header1, col_header2 = st.columns([3, 1])
    with col_header1:
        st.caption(f"問題 {st.session_state.q_index + 1} / {total_q}")
    with col_header2:
        is_checked = q_id in st.session_state.review_marks
        st.checkbox("📌 復習リストに追加", value=is_checked, key=f"check_{q_id}", on_change=toggle_review, args=(q_id,))

    # 3. 問題文の表示
    st.info(current_q.get("question", ""))

    # 4. 画像がある場合の表示
    if "image_path" in current_q and current_q["image_path"]:
        if os.path.exists(current_q["image_path"]):
            st.image(current_q["image_path"], use_container_width=True)
        else:
            st.warning(f"画像が見つかりません: {current_q['image_path']}")

    # 5. コードがある場合の表示
    if "code_snippet" in current_q and current_q["code_snippet"]:
        st.code(current_q["code_snippet"], language="python")

    # 6. 解答入力 / 選択肢 (即時フィードバック付き)
    q_type = current_q.get("type", "text")
    input_key = f"ans_{q_id}"
    
    if q_type == "multiple_choice":
        options = current_q.get("options", [])
        # ラジオボタンの選択
        selected_ans = st.radio("選択肢:", options, key=input_key, index=None)
        
        # 選択した瞬間に正誤判定
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

    # 7. 解答・解説の表示アコーディオン
    with st.expander("💡 解答と解説を表示する"):
        st.write(f"**【正解】**\n\n{current_q.get('answer', '')}")
        if "explanation" in current_q:
            st.write("---")
            st.write(f"**【解説】**\n\n{current_q['explanation']}")

    st.write("---")

    # 8. ナビゲーションボタン
    col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 1])
    with col_btn1:
        st.button("◀ 前の問題へ", on_click=go_prev, disabled=(st.session_state.q_index == 0), use_container_width=True)
    with col_btn3:
        st.button("次の問題へ ▶", on_click=go_next, args=(total_q,), disabled=(st.session_state.q_index == total_q - 1), use_container_width=True)
