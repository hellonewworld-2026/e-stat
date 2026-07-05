import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests

# ==========================================
# ページ設定
# ==========================================
st.set_page_config(page_title="e-Stat データ結合・分析ダッシュボード", layout="wide", page_icon="📈")

APP_ID = st.secrets.get("ESTAT_APP_ID", "")

# ==========================================
# API取得処理
# ==========================================
@st.cache_data(ttl=3600)
def fetch_and_format_estat(stats_data_id):
    if not APP_ID: return None, "APIキーが設定されていません。"
    url = "http://api.e-stat.go.jp/rest/3.0/app/json/getStatsData"
    params = {"appId": APP_ID, "statsDataId": stats_data_id, "metaGetFlg": "Y"}
    try:
        response = requests.get(url, params=params).json()
        if response['GET_STATS_DATA']['RESULT']['STATUS'] != 0:
            return None, response['GET_STATS_DATA']['RESULT']['ERROR_MSG']

        class_obj = response['GET_STATS_DATA']['STATISTICAL_DATA']['CLASS_INF']['CLASS_OBJ']
        meta_dict = {}
        for obj in class_obj:
            cat_id = obj['@id']
            meta_dict[cat_id] = {'name': obj.get('@name', cat_id), 'codes': {}}
            classes = obj.get('CLASS', [])
            if isinstance(classes, dict): classes = [classes]
            for cls in classes:
                meta_dict[cat_id]['codes'][cls['@code']] = cls['@name']

        values = response['GET_STATS_DATA']['STATISTICAL_DATA']['DATA_INF']['VALUE']
        parsed_data = []
        for val in values:
            row = {'値': val.get('$', '')}
            for key, code in val.items():
                if key.startswith('@') and key not in ['@unit', '@tab']:
                    cat_id = key[1:]
                    if cat_id in meta_dict:
                        row[meta_dict[cat_id]['name']] = meta_dict[cat_id]['codes'].get(code, code)
            parsed_data.append(row)
        return pd.DataFrame(parsed_data), "Success"
    except Exception as e:
        return None, f"エラー: {str(e)}"

# ==========================================
# データ準備 (ベースデータ)
# ==========================================
def load_demo_data():
    return pd.DataFrame({
        '地域名': ['札幌市', '仙台市', 'さいたま市', '千葉市', '横浜市', '川崎市', '名古屋市', '京都市', '大阪市', '堺市', '神戸市', '広島市', '福岡市', '北九州市'],
        '平均食塩摂取量_g': [10.5, 10.8, 9.6, 9.7, 9.3, 9.4, 9.8, 9.2, 9.7, 9.9, 9.4, 10.1, 9.6, 10.3],
        '健康寿命_年': [71.5, 71.2, 72.5, 72.4, 73.1, 72.8, 72.0, 73.2, 72.2, 71.8, 72.9, 71.6, 72.4, 71.4],
        '循環器疾患死亡率_10万対': [85.2, 88.1, 68.5, 69.2, 62.5, 64.1, 73.2, 61.8, 74.5, 76.0, 63.2, 81.0, 69.1, 84.5],
        '年間医療介護費_億円': [450, 380, 410, 390, 850, 420, 780, 460, 920, 280, 440, 390, 520, 350]
    })

def load_age_demo_data():
    return pd.DataFrame({
        '年齢階級': ['1-6歳', '7-14歳', '15-19歳', '20-29歳', '30-39歳', '40-49歳', '50-59歳', '60-69歳', '70歳以上'],
        '目標値_男': [4.0, 5.5, 7.0, 7.5, 7.5, 7.5, 7.5, 7.5, 7.5],
        '目標値_女': [4.0, 5.5, 6.5, 6.5, 6.5, 6.5, 6.5, 6.5, 6.5],
        '実績値_男': [4.8, 8.2, 10.5, 10.8, 10.9, 11.2, 11.5, 11.0, 10.5],
        '実績値_女': [4.5, 7.5, 8.8, 8.9, 9.2, 9.4, 9.8, 9.6, 9.0]
    })

# Session Stateによるデータの永続化
if "main_df" not in st.session_state:
    st.session_state["main_df"] = load_demo_data()

df_age = load_age_demo_data()

# ==========================================
# サイドバー: 拡張マッシュアップ・エンジン
# ==========================================
with st.sidebar:
    st.header("⚙️ データ合体エンジン")
    st.markdown("e-Statから取得したデータをダッシュボードに追加します。")
    
    target_stats_id = st.text_input("統計表ID (10桁)", value="0003411646") 
    
    if st.button("🔄 e-Statから取得", type="primary", use_container_width=True):
        with st.spinner("APIと通信中..."):
            fetched_df, msg = fetch_and_format_estat(target_stats_id)
            if fetched_df is not None:
                st.session_state["api_data"] = fetched_df
                st.success("✅ データ取得成功！")
            else:
                st.error(f"❌ エラー: {msg}")
                
    # 取得したデータをメインの表に合体させるUI
    if "api_data" in st.session_state:
        api_df = st.session_state["api_data"]
        
        with st.expander("1. 取得したデータの中身を確認", expanded=True):
            st.dataframe(api_df.head(5))
            
        st.markdown("#### 🔗 2. ダッシュボードへ結合 (Merge)")
        st.caption("取得したデータから必要な列を選び、メインデータに合体させます。")
        
        # 地域名と推測される列を自動選択
        guess_area = next((col for col in api_df.columns if "地域" in col or "市区町村" in col), api_df.columns[0])
        col_area = st.selectbox("A.「地域名」が含まれる列:", api_df.columns, index=list(api_df.columns).index(guess_area))
        
        # 値の列
        guess_val = "値" if "値" in api_df.columns else api_df.columns[-1]
        col_val = st.selectbox("B. 追加したい「数値」の列:", api_df.columns, index=list(api_df.columns).index(guess_val))
        
        new_name = st.text_input("C. グラフ上での表示名:", value="新規APIデータ")
        
        if st.button("✨ ダッシュボードに結合する"):
            try:
                # 必要な列だけ抽出してリネーム
                temp_df = api_df[[col_area, col_val]].copy()
                temp_df = temp_df.rename(columns={col_area: '地域名', col_val: new_name})
                
                # 重複排除と数値変換
                temp_df = temp_df.drop_duplicates(subset=['地域名'])
                temp_df[new_name] = temp_df[new_name].astype(str).str.replace(',', '') # カンマ除去
                temp_df[new_name] = pd.to_numeric(temp_df[new_name], errors='coerce')
                
                # Pandasの強力な Merge (結合) 機能
                st.session_state["main_df"] = pd.merge(st.session_state["main_df"], temp_df, on='地域名', how='left')
                
                st.success(f"「{new_name}」を追加しました！グラフを確認してください。")
            except Exception as e:
                st.error(f"結合エラーが発生しました: {e}")

# ==========================================
# アプリのメインUI (フロントエンド)
# ==========================================
st.title("📈 超・拡張型 データ分析ダッシュボード")
st.markdown("サイドバーからe-Statのデータを結合することで、分析の次元を無限に拡張できます。")

tab1, tab2, tab3, tab4 = st.tabs([
    "📊 多次元・相関分析マップ", 
    "🎯 減塩政策シミュレーター", 
    "👶 年齢別・ライフコース分析", 
    "📋 現在のデータテーブル"
])

# 現在の最新データを取得
current_df = st.session_state["main_df"]

# ------------------------------------------
# タブ1: 現状分析 (ユーザーが軸を自由に変更可能に進化！)
# ------------------------------------------
with tab1:
    st.subheader("相関分析マップ")
    st.info("💡 グラフのX軸、Y軸、円の大きさを自由に変更して、未知の相関関係を探し出せます。")
    
    # 結合されたデータの中から「数値」の列だけを抽出
    num_cols = current_df.select_dtypes(include=['float64', 'int64']).columns.tolist()
    
    col_x, col_y, col_s = st.columns(3)
    with col_x: x_axis = st.selectbox("X軸 (原因/要因):", num_cols, index=0)
    with col_y: y_axis = st.selectbox("Y軸 (結果):", num_cols, index=1 if len(num_cols)>1 else 0)
    with col_s: size_axis = st.selectbox("円の大きさ:", num_cols, index=2 if len(num_cols)>2 else 0)

    # 動的に描画される散布図
    fig_scatter = px.scatter(
        current_df, x=x_axis, y=y_axis, text="地域名", 
        size=size_axis, color=size_axis,
        color_continuous_scale=px.colors.sequential.OrRd,
        height=600
    )
    fig_scatter.update_traces(textposition='top center', marker=dict(opacity=0.8, line=dict(width=1, color='DarkSlateGrey')))
    st.plotly_chart(fig_scatter, use_container_width=True)

# ------------------------------------------
# タブ2: シミュレーター (変更なし)
# ------------------------------------------
with tab2:
    st.subheader("行政介入による減塩効果シミュレーション")
    col_left, col_right = st.columns([1, 2])
    
    with col_left:
        selected_city = st.selectbox("対象都市を選択", current_df['地域名'])
        city_data = current_df[current_df['地域名'] == selected_city].iloc[0]
        current_salt = city_data.get('平均食塩摂取量_g', 10.0)
        st.markdown(f"**【{selected_city}の現状】**\n- 平均食塩摂取量: `{current_salt} g`\n- 健康寿命: `{city_data.get('健康寿命_年', 72.0)} 年`")
        
        target_salt = st.slider("🎯 政策による目標摂取量 (g/日)", min_value=5.0, max_value=float(current_salt), value=float(current_salt), step=0.1)
    
    with col_right:
        reduction = current_salt - target_salt
        gained_life = round(reduction * 0.6, 2)
        reduced_risk = round(reduction * 8, 1)
        saved_cost = round(city_data.get('年間医療介護費_億円', 500) * (reduction * 0.04), 0)
        
        st.write("### 期待される政策効果（推計）")
        if reduction > 0:
            c1, c2, c3 = st.columns(3)
            c1.metric("🌱 健康寿命の延伸", f"+ {gained_life} 年")
            c2.metric("❤️ 循環器死亡リスク低下", f"- {reduced_risk} %", delta_color="inverse")
            c3.metric("💰 年間医療費の削減", f"- {int(saved_cost)} 億円", delta_color="inverse")
            
            fig_bar = go.Figure(data=[
                go.Bar(name='介入前 (現状)', x=['健康寿命(年)', '年間医療費(億円)'], y=[city_data.get('健康寿命_年', 72), city_data.get('年間医療介護費_億円', 500)], marker_color='#EF553B'),
                go.Bar(name='介入後 (目標達成時)', x=['健康寿命(年)', '年間医療費(億円)'], y=[city_data.get('健康寿命_年', 72) + gained_life, city_data.get('年間医療介護費_億円', 500) - saved_cost], marker_color='#00CC96')
            ])
            fig_bar.update_layout(barmode='group', height=350, margin=dict(t=30, b=0))
            st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("👈 左側のスライダーを動かして目標を設定してください。")

# ------------------------------------------
# タブ3: 年齢別・ライフコース分析 (変更なし)
# ------------------------------------------
with tab3:
    st.subheader("年齢階級別の食塩摂取状況（隠れた危機の可視化）")
    gender = st.radio("表示する性別を選択:", ["男性", "女性"], horizontal=True)
    y_actual, y_target, bar_color = ("実績値_男", "目標値_男", "#3498db") if gender == "男性" else ("実績値_女", "目標値_女", "#e74c3c")
    fig_age = go.Figure()
    fig_age.add_trace(go.Bar(x=df_age['年齢階級'], y=df_age[y_actual], name='実際の平均摂取量', marker_color=bar_color, opacity=0.8, text=df_age[y_actual], textposition='auto'))
    fig_age.add_trace(go.Scatter(x=df_age['年齢階級'], y=df_age[y_target], mode='lines+markers+text', name='目標値 (推奨上限)', line=dict(color='green', width=3, dash='dash'), marker=dict(size=10, color='green'), text=df_age[y_target], textposition='top center'))
    fig_age.update_layout(title=f"【{gender}】 年齢階級別の目標値と実績値のギャップ", xaxis_title="年齢階級", yaxis_title="1日あたり食塩摂取量 (g)", hovermode="x unified", height=500)
    st.plotly_chart(fig_age, use_container_width=True)

# ------------------------------------------
# タブ4: データテーブル
# ------------------------------------------
with tab4:
    st.subheader("現在のベースデータ（結合結果）")
    st.markdown("サイドバーでデータを結合すると、ここの列がどんどん増えていきます。")
    
    col_config = {}
    if "平均食塩摂取量_g" in current_df.columns:
        col_config["平均食塩摂取量_g"] = st.column_config.ProgressColumn("平均食塩摂取量_g", format="%.1f", min_value=5.0, max_value=12.0)
    if "循環器疾患死亡率_10万対" in current_df.columns:
        col_config["循環器疾患死亡率_10万対"] = st.column_config.ProgressColumn("循環器疾患死亡率_10万対", format="%.1f", min_value=0.0, max_value=100.0)
        
    st.dataframe(current_df, use_container_width=True, column_config=col_config)
    csv = current_df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
    st.download_button("📥 この表をCSVでダウンロード", data=csv, file_name="merged_analysis_data.csv", mime="text/csv")