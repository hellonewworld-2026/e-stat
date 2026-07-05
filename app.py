import streamlit as st
import pandas as pd
import plotly.express as px
import requests

# ==========================================
# ページ設定
# ==========================================
st.set_page_config(page_title="e-Stat 汎用BIダッシュボード", layout="wide", page_icon="🌐")

APP_ID = st.secrets.get("ESTAT_APP_ID", "")

# ==========================================
# API取得＆検索処理
# ==========================================
@st.cache_data(ttl=3600)
def search_estat_id(keyword):
    """キーワードから統計表IDを検索する"""
    if not APP_ID: return []
    url = "http://api.e-stat.go.jp/rest/3.0/app/json/getStatsList"
    params = {"appId": APP_ID, "searchWord": keyword, "limit": 30}
    try:
        response = requests.get(url, params=params).json()
        datalist = response.get('GET_STATS_LIST', {}).get('DATALIST_INF', {}).get('TABLE_INF', [])
        if isinstance(datalist, dict): datalist = [datalist]
        return datalist
    except Exception:
        return []

# ⚠️ キャッシュによる古いデータの残留を防ぐため、あえて cache_data を外して常に最新を取得・翻訳させます
def fetch_and_format_estat(stats_data_id):
    """データを取得し、確実に人間が読める形にパースする"""
    if not APP_ID: return None, "APIキーが設定されていません。"
    url = "http://api.e-stat.go.jp/rest/3.0/app/json/getStatsData"
    params = {"appId": APP_ID, "statsDataId": stats_data_id, "metaGetFlg": "Y"}
    try:
        response = requests.get(url, params=params).json()
        if response['GET_STATS_DATA']['RESULT']['STATUS'] != 0:
            return None, response['GET_STATS_DATA']['RESULT']['ERROR_MSG']

        # e-Stat特有の「要素が1つだと辞書になる」問題を回避
        class_obj_raw = response['GET_STATS_DATA']['STATISTICAL_DATA']['CLASS_INF']['CLASS_OBJ']
        class_obj = [class_obj_raw] if isinstance(class_obj_raw, dict) else class_obj_raw
        
        meta_dict = {}
        for obj in class_obj:
            cat_id = obj.get('@id')
            meta_dict[cat_id] = {'name': obj.get('@name', cat_id), 'codes': {}}
            classes = obj.get('CLASS', [])
            if isinstance(classes, dict): classes = [classes]
            for cls in classes:
                meta_dict[cat_id]['codes'][cls.get('@code')] = cls.get('@name', cls.get('@code'))

        values_raw = response['GET_STATS_DATA']['STATISTICAL_DATA']['DATA_INF']['VALUE']
        values = [values_raw] if isinstance(values_raw, dict) else values_raw
        
        parsed_data = []
        for val in values:
            row = {'値': val.get('$', '')}
            for key, code in val.items():
                if key.startswith('@') and key not in ['@unit', '@tab']:
                    cat_id = key[1:]
                    if cat_id in meta_dict:
                        col_name = meta_dict[cat_id]['name']
                        val_name = meta_dict[cat_id]['codes'].get(code, code)
                        row[col_name] = val_name
            parsed_data.append(row)
        return pd.DataFrame(parsed_data), "Success"
    except Exception as e:
        return None, f"エラー: {str(e)}"

# ==========================================
# 初期ベースデータ（日本全国の都道府県・政令市リスト）
# ==========================================
def load_base_data():
    areas = [
        "北海道", "青森県", "岩手県", "宮城県", "秋田県", "山形県", "福島県",
        "茨城県", "栃木県", "群馬県", "埼玉県", "千葉県", "東京都", "神奈川県",
        "新潟県", "富山県", "石川県", "福井県", "山梨県", "長野県", "岐阜県",
        "静岡県", "愛知県", "三重県", "滋賀県", "京都府", "大阪府", "兵庫県",
        "奈良県", "和歌山県", "鳥取県", "島根県", "岡山県", "広島県", "山口県",
        "徳島県", "香川県", "愛媛県", "高知県", "福岡県", "佐賀県", "長崎県", 
        "熊本県", "大分県", "宮崎県", "鹿児島県", "沖縄県",
        "札幌市", "仙台市", "さいたま市", "千葉市", "横浜市", "川崎市", "相模原市",
        "新潟市", "静岡市", "浜松市", "名古屋市", "京都市", "大阪市", "堺市",
        "神戸市", "岡山市", "広島市", "北九州市", "福岡市", "熊本市"
    ]
    return pd.DataFrame({'地域名': areas})

if "main_df" not in st.session_state:
    st.session_state["main_df"] = load_base_data()

# ==========================================
# サイドバー: 検索 ＆ 拡張エンジン
# ==========================================
with st.sidebar:
    st.header("🔍 1. 統計表IDを探す")
    
    search_kw = st.text_input("キーワード検索", placeholder="例: 医療施設調査 病床")
    if st.button("IDを検索", use_container_width=True):
        if search_kw:
            with st.spinner("検索中..."):
                results = search_estat_id(search_kw)
                if results:
                    st.session_state["search_results"] = results
                else:
                    st.warning("見つかりませんでした。")
    
    selected_id = ""
    if "search_results" in st.session_state:
        opts = {}
        for r in st.session_state["search_results"]:
            title = r.get('STAT_NAME', {}).get('$', '') + " - " + r.get('TITLE', {}).get('$', '')
            opts[f"[{r['@id']}] {title}"] = r['@id']
        
        selected_opt = st.selectbox("検索結果から選択:", list(opts.keys()))
        selected_id = opts[selected_opt]
    
    st.divider()

    st.header("⚙️ 2. データを取得・合体")
    target_stats_id = st.text_input("取得する統計表ID", value=selected_id, placeholder="10桁の数字を入力") 
    
    if st.button("🔄 e-Statから最新データを取得", type="primary", use_container_width=True):
        if target_stats_id:
            with st.spinner("APIからデータを翻訳中..."):
                fetched_df, msg = fetch_and_format_estat(target_stats_id)
                if fetched_df is not None:
                    st.session_state["api_data"] = fetched_df
                    st.success("✅ データ翻訳成功！下にスクロールしてください。")
                else:
                    st.error(f"❌ エラー: {msg}")
                
    if "api_data" in st.session_state:
        api_df = st.session_state["api_data"]
        
        st.markdown("#### 🔗 3. データの絞り込みと結合")
        st.caption("e-Statのデータは様々な条件が混ざっています。必要な条件（総数など）に絞り込んでから結合してください。")
        
        # 絞り込み（フィルター）UIの自動生成
        cat_cols = [col for col in api_df.columns if col != '値' and not any(x in col for x in ['地域', '都道府県', '市区町村'])]
        filter_dict = {}
        for col in cat_cols:
            unique_vals = api_df[col].unique().tolist()
            default_idx = 0
            # 「総数」や「計」がつけば自動的にデフォルト選択する
            for i, v in enumerate(unique_vals):
                if "総数" in str(v) or "計" in str(v):
                    default_idx = i
                    break
            filter_dict[col] = st.selectbox(f"[{col}] の条件:", unique_vals, index=default_idx)
        
        # フィルター実行
        filtered_df = api_df.copy()
        for col, val in filter_dict.items():
            filtered_df = filtered_df[filtered_df[col] == val]
            
        st.info(f"💡 絞り込み後: 残り {len(filtered_df)} 件のデータ")
        
        # 結合設定
        guess_area = next((col for col in filtered_df.columns if any(x in col for x in ["地域", "都道府県", "市区町村"])), filtered_df.columns[0])
        col_area = st.selectbox("A.「地域名」の列:", filtered_df.columns, index=list(filtered_df.columns).index(guess_area))
        
        new_name = st.text_input("B. グラフ上での表示名:", value="新規追加データ")
        
        if st.button("✨ ダッシュボードに結合する", use_container_width=True):
            try:
                temp_df = filtered_df[[col_area, '値']].copy()
                temp_df.columns = ['地域名', new_name]
                
                # 空白行や重複を排除
                temp_df = temp_df.dropna(subset=['地域名'])
                temp_df = temp_df.drop_duplicates(subset=['地域名'])
                
                temp_df[new_name] = temp_df[new_name].astype(str).str.replace(',', '').replace(['-', '***', 'X', 'x'], pd.NA)
                temp_df[new_name] = pd.to_numeric(temp_df[new_name], errors='coerce')
                
                if new_name in st.session_state["main_df"].columns:
                    st.session_state["main_df"] = st.session_state["main_df"].drop(columns=[new_name])
                
                st.session_state["main_df"] = pd.merge(st.session_state["main_df"], temp_df, on='地域名', how='left')
                st.success(f"「{new_name}」を追加しました！")
            except Exception as e:
                st.error(f"結合エラーが発生しました: {e}")
                    
        if st.button("🗑️ ベースデータを初期化", use_container_width=True):
            st.session_state["main_df"] = load_base_data()
            st.rerun()

# ==========================================
# アプリのメインUI (フロントエンド)
# ==========================================
st.title("🌐 e-Stat 汎用データ分析・BIダッシュボード")
st.markdown("サイドバーでe-Stat内を検索し、データを次々と結合していくことで、あなただけの分析ダッシュボードを作ることができます。")

tab1, tab2, tab3 = st.tabs([
    "📊 多次元・相関分析マップ", 
    "📈 ランキング・比較グラフ", 
    "📋 結合済みデータテーブル"
])

current_df = st.session_state["main_df"]
num_cols = current_df.select_dtypes(include=['float64', 'int64']).columns.tolist()

with tab1:
    st.subheader("相関分析マップ (散布図)")
    if len(num_cols) < 2:
        st.info("👈 サイドバーから、比較したい「数値データ」を2つ以上結合してください。")
    else:
        col_x, col_y, col_s = st.columns(3)
        with col_x: x_axis = st.selectbox("X軸 (原因/要因):", num_cols, index=0)
        with col_y: y_axis = st.selectbox("Y軸 (結果):", num_cols, index=1)
        with col_s: size_axis = st.selectbox("円の大きさ (オプション):", ["なし"] + num_cols, index=0)

        plot_df = current_df.dropna(subset=[x_axis, y_axis])
        
        if size_axis == "なし":
            fig_scatter = px.scatter(plot_df, x=x_axis, y=y_axis, text="地域名", height=600)
        else:
            plot_df = plot_df.dropna(subset=[size_axis])
            plot_df['size_abs'] = plot_df[size_axis].fillna(0).abs() 
            fig_scatter = px.scatter(plot_df, x=x_axis, y=y_axis, text="地域名", size='size_abs', color=size_axis, color_continuous_scale="Viridis", height=600)
            
        fig_scatter.update_traces(textposition='top center', marker=dict(opacity=0.8, line=dict(width=1, color='DarkSlateGrey')))
        st.plotly_chart(fig_scatter, use_container_width=True)

with tab2:
    st.subheader("ランキング比較 (棒グラフ)")
    if len(num_cols) == 0:
        st.info("👈 サイドバーから、比較したい「数値データ」を結合してください。")
    else:
        c1, c2, c3 = st.columns(3)
        with c1: bar_col = st.selectbox("比較する指標:", num_cols)
        with c2: sort_order = st.radio("並び順:", ["大きい順", "小さい順"], horizontal=True)
        with c3: top_n = st.slider("表示件数:", 5, len(current_df), 20)
        
        plot_bar_df = current_df.dropna(subset=[bar_col])
        if sort_order == "大きい順":
            plot_bar_df = plot_bar_df.sort_values(bar_col, ascending=False).head(top_n)
        else:
            plot_bar_df = plot_bar_df.sort_values(bar_col, ascending=True).head(top_n)
            
        fig_bar = px.bar(plot_bar_df, x="地域名", y=bar_col, color=bar_col, color_continuous_scale="Blues", height=500)
        st.plotly_chart(fig_bar, use_container_width=True)

with tab3:
    st.subheader("結合済みデータテーブル")
    if len(num_cols) == 0:
        st.write("現在、地域名のリストのみ保持しています。サイドバーからデータを結合してください。")
        st.dataframe(current_df, use_container_width=True)
    else:
        st.markdown("結合されたデータセットです。列名をクリックするとソートできます。")
        st.dataframe(current_df, use_container_width=True)
        csv = current_df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
        st.download_button("📥 この結合済み表をCSVでダウンロード", data=csv, file_name="estat_custom_dataset.csv", mime="text/csv")