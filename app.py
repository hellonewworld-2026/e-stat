import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ==========================================
# ページ設定
# ==========================================
st.set_page_config(page_title="減塩推進・健康寿命ダッシュボード", layout="wide", page_icon="🧂")

# ==========================================
# データ準備 (第1弾用デモデータ)
# ※将来的には e-Stat API から自動取得したデータに差し替えます
# ==========================================
@st.cache_data
def load_demo_data():
    data = {
        '地域名': ['札幌市', '仙台市', 'さいたま市', '千葉市', '横浜市', '川崎市', '名古屋市', '京都市', '大阪市', '堺市', '神戸市', '広島市', '福岡市', '北九州市'],
        '平均食塩摂取量_g': [10.5, 10.8, 9.6, 9.7, 9.3, 9.4, 9.8, 9.2, 9.7, 9.9, 9.4, 10.1, 9.6, 10.3],
        '健康寿命_年': [71.5, 71.2, 72.5, 72.4, 73.1, 72.8, 72.0, 73.2, 72.2, 71.8, 72.9, 71.6, 72.4, 71.4],
        '循環器疾患死亡率_10万対': [85.2, 88.1, 68.5, 69.2, 62.5, 64.1, 73.2, 61.8, 74.5, 76.0, 63.2, 81.0, 69.1, 84.5],
        '年間医療介護費_億円': [450, 380, 410, 390, 850, 420, 780, 460, 920, 280, 440, 390, 520, 350]
    }
    return pd.DataFrame(data)

df = load_demo_data()

# ==========================================
# アプリのUIとメイン処理
# ==========================================
st.title("🧂 減塩推進による健康寿命延伸ダッシュボード")
st.markdown("市民の「食塩摂取量」と「循環器疾患リスク」「健康寿命」の相関を可視化し、政策効果をシミュレーションします。")

# タブで画面を分割
tab1, tab2, tab3 = st.tabs(["📊 現状分析 (マクロ)", "🎯 減塩政策シミュレーター", "📋 データテーブル"])

# ------------------------------------------
# タブ1: 現状分析
# ------------------------------------------
with tab1:
    st.subheader("地域別の食塩摂取量と健康寿命の相関")
    st.markdown("塩分摂取量が多い都市ほど、健康寿命が短く、循環器疾患による死亡率（円の大きさ）が高い傾向が見られます。")
    
    # Plotlyによるバブルチャート
    fig_scatter = px.scatter(
        df, 
        x="平均食塩摂取量_g", 
        y="健康寿命_年", 
        text="地域名", 
        size="循環器疾患死亡率_10万対", 
        color="循環器疾患死亡率_10万対",
        color_continuous_scale=px.colors.sequential.OrRd,
        labels={"平均食塩摂取量_g": "1日あたり平均食塩摂取量 (g)", "健康寿命_年": "健康寿命 (年)"},
        height=600
    )
    fig_scatter.update_traces(textposition='top center', marker=dict(opacity=0.8, line=dict(width=1, color='DarkSlateGrey')))
    
    # 国の目標値（成人男性7.5g未満など）の参照線を引く
    fig_scatter.add_vline(x=7.5, line_dash="dash", line_color="green", annotation_text="国の目標値(男性 7.5g)", annotation_position="top left")
    
    st.plotly_chart(fig_scatter, use_container_width=True)

# ------------------------------------------
# タブ2: シミュレーター
# ------------------------------------------
with tab2:
    st.subheader("行政介入による減塩効果シミュレーション")
    
    # 分析対象の都市を選択
    selected_city = st.selectbox("シミュレーション対象の都市を選択", df['地域名'])
    city_data = df[df['地域名'] == selected_city].iloc[0]
    current_salt = city_data['平均食塩摂取量_g']
    
    st.markdown(f"**【{selected_city}の現状】** 平均食塩摂取量: `{current_salt}g` / 健康寿命: `{city_data['健康寿命_年']}年`")
    
    # スライダーで目標値を設定
    target_salt = st.slider(
        "🎯 政策による目標摂取量 (g/日)", 
        min_value=5.0, 
        max_value=float(current_salt), 
        value=float(current_salt), 
        step=0.1,
        help="市民への減塩啓発や給食の改善などにより、摂取量をどこまで減らせるかを設定します。"
    )
    
    # 削減量
    reduction = current_salt - target_salt
    
    # === 統計モデル（仮）に基づく効果算出 ===
    # ※塩分1g低下につき、健康寿命0.6年延伸、循環器リスク8%低下、医療費4%削減と仮定
    gained_life = round(reduction * 0.6, 2)
    reduced_risk = round(reduction * 8, 1)
    saved_cost = round(city_data['年間医療介護費_億円'] * (reduction * 0.04), 0)
    
    st.write("### 期待される政策効果（推計）")
    
    if reduction > 0:
        col1, col2, col3 = st.columns(3)
        col1.metric("🌱 健康寿命の延伸", f"+ {gained_life} 年", f"予測: {round(city_data['健康寿命_年'] + gained_life, 2)}年")
        col2.metric("❤️ 循環器疾患死亡リスクの低下", f"- {reduced_risk} %", delta_color="inverse")
        col3.metric("💰 年間医療・介護費の削減", f"- {int(saved_cost)} 億円", delta_color="inverse")
        
        # 削減効果を棒グラフで比較
        fig_bar = go.Figure(data=[
            go.Bar(name='介入前 (現状)', x=['健康寿命(年)', '年間医療費(億円)'], y=[city_data['健康寿命_年'], city_data['年間医療介護費_億円']], marker_color='#EF553B'),
            go.Bar(name='介入後 (目標達成時)', x=['健康寿命(年)', '年間医療費(億円)'], y=[city_data['健康寿命_年'] + gained_life, city_data['年間医療介護費_億円'] - saved_cost], marker_color='#00CC96')
        ])
        fig_bar.update_layout(barmode='group', title="現状と介入後の比較", height=400)
        st.plotly_chart(fig_bar, use_container_width=True)
        
    else:
        st.info("👈 スライダーを左に動かして、減塩目標を設定してください。")

# ------------------------------------------
# タブ3: データテーブル
# ------------------------------------------
with tab3:
    st.subheader("基礎データ")
    st.dataframe(df.style.background_gradient(cmap='Reds', subset=['平均食塩摂取量_g', '循環器疾患死亡率_10万対']), use_container_width=True)
    
    # CSVダウンロード
    csv = df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
    st.download_button("📥 基礎データをCSVでダウンロード", data=csv, file_name="salt_reduction_data.csv", mime="text/csv")