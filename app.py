import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ==========================================
# ページ設定
# ==========================================
st.set_page_config(page_title="減塩推進・健康寿命ダッシュボード", layout="wide", page_icon="🧂")

# ==========================================
# データ準備 (デモデータ)
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

@st.cache_data
def load_age_demo_data():
    """第2弾追加: 年齢階級別のデモデータ"""
    data = {
        '年齢階級': ['1-6歳', '7-14歳', '15-19歳', '20-29歳', '30-39歳', '40-49歳', '50-59歳', '60-69歳', '70歳以上'],
        '目標値_男': [4.0, 5.5, 7.0, 7.5, 7.5, 7.5, 7.5, 7.5, 7.5],
        '目標値_女': [4.0, 5.5, 6.5, 6.5, 6.5, 6.5, 6.5, 6.5, 6.5],
        '実績値_男': [4.8, 8.2, 10.5, 10.8, 10.9, 11.2, 11.5, 11.0, 10.5],
        '実績値_女': [4.5, 7.5, 8.8, 8.9, 9.2, 9.4, 9.8, 9.6, 9.0]
    }
    return pd.DataFrame(data)

df = load_demo_data()
df_age = load_age_demo_data()

# ==========================================
# アプリのUIとメイン処理
# ==========================================
st.title("🧂 減塩推進による健康寿命延伸ダッシュボード")
st.markdown("市民の「食塩摂取量」と「循環器疾患リスク」「健康寿命」の相関を可視化し、政策効果をシミュレーションします。")

# タブで画面を分割（第2弾でタブを1つ追加！）
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 現状分析 (マクロ)", 
    "🎯 減塩政策シミュレーター", 
    "👶 年齢別・ライフコース分析", 
    "📋 データテーブル"
])

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
    
    col_left, col_right = st.columns([1, 2])
    
    with col_left:
        # 分析対象の都市を選択
        selected_city = st.selectbox("シミュレーション対象の都市を選択", df['地域名'])
        city_data = df[df['地域名'] == selected_city].iloc[0]
        current_salt = city_data['平均食塩摂取量_g']
        
        st.markdown(f"**【{selected_city}の現状】**")
        st.write(f"- 平均食塩摂取量: `{current_salt} g`")
        st.write(f"- 健康寿命: `{city_data['健康寿命_年']} 年`")
        
        # スライダーで目標値を設定
        st.write("")
        target_salt = st.slider(
            "🎯 政策による目標摂取量 (g/日)", 
            min_value=5.0, 
            max_value=float(current_salt), 
            value=float(current_salt), 
            step=0.1,
            help="市民への減塩啓発や給食の改善などにより、摂取量をどこまで減らせるかを設定します。"
        )
    
    with col_right:
        # 削減量
        reduction = current_salt - target_salt
        
        # === 統計モデル（仮）に基づく効果算出 ===
        gained_life = round(reduction * 0.6, 2)
        reduced_risk = round(reduction * 8, 1)
        saved_cost = round(city_data['年間医療介護費_億円'] * (reduction * 0.04), 0)
        
        st.write("### 期待される政策効果（推計）")
        
        if reduction > 0:
            c1, c2, c3 = st.columns(3)
            c1.metric("🌱 健康寿命の延伸", f"+ {gained_life} 年")
            c2.metric("❤️ 循環器死亡リスク低下", f"- {reduced_risk} %", delta_color="inverse")
            c3.metric("💰 年間医療費の削減", f"- {int(saved_cost)} 億円", delta_color="inverse")
            
            # 削減効果を棒グラフで比較
            fig_bar = go.Figure(data=[
                go.Bar(name='介入前 (現状)', x=['健康寿命(年)', '年間医療費(億円)'], y=[city_data['健康寿命_年'], city_data['年間医療介護費_億円']], marker_color='#EF553B'),
                go.Bar(name='介入後 (目標達成時)', x=['健康寿命(年)', '年間医療費(億円)'], y=[city_data['健康寿命_年'] + gained_life, city_data['年間医療介護費_億円'] - saved_cost], marker_color='#00CC96')
            ])
            fig_bar.update_layout(barmode='group', height=350, margin=dict(t=30, b=0))
            st.plotly_chart(fig_bar, use_container_width=True)
            
        else:
            st.info("👈 左側のスライダーを動かして、減塩目標を設定してください。")

# ------------------------------------------
# タブ3: 年齢別・ライフコース分析 (★第2弾 新規追加部分)
# ------------------------------------------
with tab3:
    st.subheader("年齢階級別の食塩摂取状況（隠れた危機の可視化）")
    st.markdown("大人になってからの生活習慣改善は困難です。**小児・思春期（7〜19歳）からすでに目標値を大きく超過している現状**を把握し、学校給食や食育での早期介入の必要性を示します。")
    
    # 性別切り替えラジオボタン
    gender = st.radio("表示する性別を選択:", ["男性", "女性"], horizontal=True)
    
    # 選択した性別に応じてデータを切り替え
    if gender == "男性":
        y_actual = "実績値_男"
        y_target = "目標値_男"
        bar_color = "#3498db" # 青系
    else:
        y_actual = "実績値_女"
        y_target = "目標値_女"
        bar_color = "#e74c3c" # 赤系
        
    fig_age = go.Figure()
    
    # 1. 実際の摂取量 (棒グラフ)
    fig_age.add_trace(go.Bar(
        x=df_age['年齢階級'], 
        y=df_age[y_actual], 
        name=f'実際の平均摂取量',
        marker_color=bar_color,
        opacity=0.8,
        text=df_age[y_actual],
        textposition='auto'
    ))
    
    # 2. 目標値 (折れ線グラフ)
    fig_age.add_trace(go.Scatter(
        x=df_age['年齢階級'], 
        y=df_age[y_target], 
        mode='lines+markers+text',
        name='目標値 (推奨上限)',
        line=dict(color='green', width=3, dash='dash'),
        marker=dict(size=10, color='green'),
        text=df_age[y_target],
        textposition='top center'
    ))
    
    fig_age.update_layout(
        title=f"【{gender}】 年齢階級別の目標値と実績値のギャップ",
        xaxis_title="年齢階級",
        yaxis_title="1日あたり食塩摂取量 (g)",
        hovermode="x unified",
        height=500
    )
    
    st.plotly_chart(fig_age, use_container_width=True)
    
    # ハイライトメッセージ
    st.error(f"💡 **分析のポイント:** グラフを見ると、{gender}ともに**「7-14歳（小中学生）」の段階で目標値を大きく超過**し始めており、ここが将来の循環器疾患リスクを生み出す起点（ボトルネック）であることがわかります。")

# ------------------------------------------
# タブ4: データテーブル
# ------------------------------------------
with tab4:
    st.subheader("基礎データ")
    
    st.dataframe(
        df,
        use_container_width=True,
        column_config={
            "平均食塩摂取量_g": st.column_config.ProgressColumn(
                "平均食塩摂取量_g",
                format="%.1f",
                min_value=5.0,
                max_value=12.0,
            ),
            "循環器疾患死亡率_10万対": st.column_config.ProgressColumn(
                "循環器疾患死亡率_10万対",
                format="%.1f",
                min_value=0.0,
                max_value=100.0,
            )
        }
    )
    
    csv = df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
    st.download_button("📥 基礎データをCSVでダウンロード", data=csv, file_name="salt_reduction_data.csv", mime="text/csv")