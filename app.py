import streamlit as st
import requests
import pandas as pd

# ページ設定
st.set_page_config(page_title="e-Stat データ自動収集アプリ", layout="wide")
st.title("📊 e-Stat データ自動収集・成形アプリ")

# ==========================================
# 準備: シークレットからAPP_IDを取得
# ==========================================
try:
    APP_ID = st.secrets["ESTAT_APP_ID"]
except KeyError:
    st.error("【エラー】StreamlitのSecretsに `ESTAT_APP_ID` が設定されていません。")
    st.stop()

# ==========================================
# 関数定義
# ==========================================
@st.cache_data(ttl=3600)
def search_stats_id(keyword):
    """キーワードから統計表情報を検索する"""
    url = "http://api.e-stat.go.jp/rest/3.0/app/json/getStatsList"
    params = {"appId": APP_ID, "searchWord": keyword, "limit": 30}
    response = requests.get(url, params=params).json()
    
    try:
        datalist = response['GET_STATS_LIST']['DATALIST_INF']['TABLE_INF']
        if isinstance(datalist, dict): 
            datalist = [datalist]
        return datalist
    except KeyError:
        return []

def fetch_and_format_estat(stats_data_id):
    """e-Stat APIからデータを取得し、綺麗なDataFrameに変換する"""
    url = "http://api.e-stat.go.jp/rest/3.0/app/json/getStatsData"
    params = {"appId": APP_ID, "statsDataId": stats_data_id, "metaGetFlg": "Y"}
    response = requests.get(url, params=params).json()
    
    if response['GET_STATS_DATA']['RESULT']['STATUS'] != 0:
        st.error(f"APIエラー: {response['GET_STATS_DATA']['RESULT']['ERROR_MSG']}")
        return None

    try:
        # メタデータ（コード表）の辞書化
        class_obj = response['GET_STATS_DATA']['STATISTICAL_DATA']['CLASS_INF']['CLASS_OBJ']
        meta_dict = {}
        for obj in class_obj:
            category_id = obj['@id']
            meta_dict[category_id] = {'name': obj.get('@name', category_id), 'codes': {}}
            classes = obj.get('CLASS', [])
            if isinstance(classes, dict): classes = [classes]
            for cls in classes:
                meta_dict[category_id]['codes'][cls['@code']] = cls['@name']

        # 実データの抽出とパース
        values = response['GET_STATS_DATA']['STATISTICAL_DATA']['DATA_INF']['VALUE']
        parsed_data = []
        for val in values:
            row = {'値': val.get('$', ''), '単位': val.get('@unit', '')}
            for key, code in val.items():
                if key.startswith('@') and key not in ['@unit', '@tab']:
                    cat_id = key[1:]
                    if cat_id in meta_dict:
                        col_name = meta_dict[cat_id]['name']
                        row[col_name] = meta_dict[cat_id]['codes'].get(code, code)
            parsed_data.append(row)
        return pd.DataFrame(parsed_data)
    except Exception as e:
        st.error(f"データのパース中にエラーが発生しました: {e}")
        return None

# ==========================================
# UI と アプリのメイン処理
# ==========================================

# セッションステートの初期化
if "search_results" not in st.session_state:
    st.session_state["search_results"] = []

st.markdown("### 1. キーワード検索")
col1, col2 = st.columns([3, 1])
with col1:
    keyword = st.text_input("検索キーワードを入力", placeholder="例: 医療施設調査 病床数")
with col2:
    st.write("") # 位置合わせ用
    st.write("")
    if st.button("🔍 検索する", use_container_width=True):
        if keyword:
            with st.spinner("検索中..."):
                st.session_state["search_results"] = search_stats_id(keyword)
                if not st.session_state["search_results"]:
                    st.warning("データが見つかりませんでした。別のキーワードをお試しください。")
        else:
            st.warning("キーワードを入力してください。")

st.divider()

# 検索結果がある場合のみプルダウンを表示
if st.session_state["search_results"]:
    st.markdown("### 2. 統計表の選択とダウンロード")
    
    # プルダウン用の選択肢を作成（表示用テキスト : 統計表ID）
    options = {}
    for item in st.session_state["search_results"]:
        stats_id = item['@id']
        stat_name = item.get('STAT_NAME', {}).get('$', '名称不明')
        title = item.get('TITLE', {}).get('$', 'タイトル不明')
        display_text = f"【{stats_id}】 {stat_name} - {title}"
        options[display_text] = stats_id

    selected_display = st.selectbox("取得したい統計表を選んでください:", list(options.keys()))
    selected_id = options[selected_display]

    # オプション: 政令市のみに絞るかどうかのチェックボックス
    is_seirei_only = st.checkbox("🏙️ 政令指定都市（20都市）のデータのみに絞り込む", value=True)

    if st.button("🚀 データを取得して表を作成", type="primary"):
        with st.spinner(f"データ取得・成形中... (ID: {selected_id})"):
            df = fetch_and_format_estat(selected_id)
            
            if df is not None:
                if is_seirei_only:
                    # 政令指定都市フィルタ
                    seirei_cities = ["札幌市", "仙台市", "さいたま市", "千葉市", "横浜市", "川崎市",
                                     "相模原市", "新潟市", "静岡市", "浜松市", "名古屋市", "京都市",
                                     "大阪市", "堺市", "神戸市", "岡山市", "広島市", "北九州市", "福岡市", "熊本市"]
                    area_col = next((col for col in df.columns if any(x in col for x in ["地域", "都道府県", "市区町村", "市町村"])), None)
                    if area_col:
                        pattern = '|'.join(seirei_cities)
                        df = df[df[area_col].str.contains(pattern, na=False, regex=True)]
                        st.info("政令指定都市のデータに絞り込みました。")
                    else:
                        st.warning("地域を示す列が見つからなかったため、絞り込みをスキップしました。")

                st.success("統計表の作成が完了しました！")
                
                # 表の表示
                st.dataframe(df, use_container_width=True)
                
                # CSVダウンロードボタン
                csv = df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
                st.download_button(
                    label="📥 CSVファイルをダウンロード",
                    data=csv,
                    file_name=f"estat_data_{selected_id}.csv",
                    mime="text/csv",
                )