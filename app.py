"""
링피플 맛집 지도 웹 애플리케이션
실행 방법: streamlit run app.py
"""

import psycopg2
import random
import pandas as pd
import streamlit as st
from datetime import datetime
import folium
from streamlit_folium import st_folium
from geopy.geocoders import ArcGIS

# ─────────────────────────────────────────────
# 0. 페이지 설정
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="링피플 맛집 지도",
    page_icon="🍽️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────
# 1. 커스텀 CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700;900&family=Gmarket+Sans&display=swap');

html, body, [class*="css"] {
    font-family: 'Noto Sans KR', sans-serif;
}

/* 헤더 */
.app-header {
    background: linear-gradient(135deg, #FF6B35 0%, #F7931E 50%, #FFD23F 100%);
    border-radius: 20px;
    padding: 2rem 2.5rem;
    margin-bottom: 1.5rem;
    box-shadow: 0 8px 32px rgba(255,107,53,0.25);
    position: relative;
    overflow: hidden;
}
.app-header::before {
    content: "🍜🍱🍣🍔☕";
    position: absolute;
    right: 2rem; top: 1rem;
    font-size: 2.5rem;
    opacity: 0.25;
    letter-spacing: 0.3rem;
}
.app-header h1 {
    color: white;
    font-size: 2.2rem;
    font-weight: 900;
    margin: 0;
    text-shadow: 0 2px 8px rgba(0,0,0,0.15);
}
.app-header p {
    color: rgba(255,255,255,0.9);
    margin: 0.3rem 0 0;
    font-size: 1rem;
}

/* 카드 */
.restaurant-card {
    background: white;
    border: 1.5px solid #f0f0f0;
    border-radius: 16px;
    padding: 1.2rem 1.5rem;
    margin-bottom: 0.8rem;
    transition: box-shadow 0.2s, transform 0.2s;
    box-shadow: 0 2px 8px rgba(0,0,0,0.05);
}
.restaurant-card:hover {
    box-shadow: 0 8px 24px rgba(255,107,53,0.12);
    transform: translateY(-2px);
}
.restaurant-name {
    font-size: 1.1rem;
    font-weight: 700;
    color: #1a1a1a;
    margin-bottom: 0.2rem;
}
.restaurant-meta {
    font-size: 0.82rem;
    color: #888;
}
.category-badge {
    display: inline-block;
    background: #FFF3EE;
    color: #FF6B35;
    border-radius: 20px;
    padding: 2px 10px;
    font-size: 0.78rem;
    font-weight: 600;
    margin-right: 6px;
}
.star-display {
    color: #FFB800;
    font-size: 1rem;
}
.no-review {
    color: #bbb;
    font-size: 0.82rem;
}

/* 리뷰 카드 */
.review-card {
    background: #FAFAFA;
    border-left: 3px solid #FF6B35;
    border-radius: 0 12px 12px 0;
    padding: 0.9rem 1.2rem;
    margin-bottom: 0.7rem;
}
.review-author {
    font-weight: 700;
    color: #333;
    font-size: 0.92rem;
}
.review-date {
    font-size: 0.78rem;
    color: #aaa;
    margin-left: 8px;
}
.review-comment {
    color: #555;
    font-size: 0.9rem;
    margin-top: 0.3rem;
    line-height: 1.5;
}

/* 룰렛 결과 박스 */
.roulette-result {
    background: linear-gradient(135deg, #FF6B35, #FFD23F);
    border-radius: 20px;
    padding: 2rem;
    text-align: center;
    color: white;
    box-shadow: 0 12px 40px rgba(255,107,53,0.3);
    animation: popIn 0.5s ease;
}
.roulette-result h2 {
    font-size: 1.8rem;
    font-weight: 900;
    margin-bottom: 0.3rem;
}
.roulette-result p {
    font-size: 1rem;
    opacity: 0.9;
    margin: 0;
}
@keyframes popIn {
    0% { transform: scale(0.8); opacity: 0; }
    100% { transform: scale(1); opacity: 1; }
}

/* 섹션 타이틀 */
.section-title {
    font-size: 1.1rem;
    font-weight: 700;
    color: #333;
    margin-bottom: 0.8rem;
    padding-bottom: 0.4rem;
    border-bottom: 2px solid #FF6B35;
    display: inline-block;
}

/* 평균 점수 뱃지 */
.avg-score {
    background: linear-gradient(90deg,#FF6B35,#F7931E);
    color: white;
    border-radius: 12px;
    padding: 3px 10px;
    font-size: 0.82rem;
    font-weight: 700;
}

/* 탭 스타일 override */
[data-testid="stTabs"] [data-baseweb="tab"] {
    font-weight: 600;
    font-size: 0.97rem;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# 2. DB 초기화 (테이블 생성)
# ─────────────────────────────────────────────
def get_conn():
    db_url = st.secrets.get("SUPABASE_DB_URL", "")
    if not db_url or "[your-password]" in db_url:
        st.error("🔑 .streamlit/secrets.toml 파일에 올바른 SUPABASE_DB_URL을 입력해 주세요.")
        st.stop()
    return psycopg2.connect(db_url)

@st.cache_resource
def init_db():
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS restaurants (
                id         SERIAL PRIMARY KEY,
                name       VARCHAR(255) NOT NULL,
                category   VARCHAR(50) NOT NULL,
                map_url    TEXT,
                author     VARCHAR(100) NOT NULL,
                created_at VARCHAR(50) NOT NULL,
                address    TEXT,
                lat        DOUBLE PRECISION,
                lng        DOUBLE PRECISION
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS reviews (
                id            SERIAL PRIMARY KEY,
                restaurant_id INTEGER NOT NULL,
                author        VARCHAR(100) NOT NULL,
                rating        INTEGER NOT NULL,
                comment       TEXT,
                created_at    VARCHAR(50) NOT NULL,
                FOREIGN KEY (restaurant_id) REFERENCES restaurants(id) ON DELETE CASCADE
            )
        """)
        conn.commit()
        conn.close()
    except Exception as e:
        st.error(f"DB 초기화 중 오류가 발생했습니다: {e}")

init_db()

# ─────────────────────────────────────────────
# 3. DB 헬퍼 함수
# ─────────────────────────────────────────────
CATEGORIES = ["한식", "중식", "일식", "양식", "카페", "분식", "기타"]

def get_lat_lng(address):
    try:
        geolocator = ArcGIS(user_agent="matzip_locator")
        location = geolocator.geocode(address, timeout=3)
        if location:
            return location.latitude, location.longitude
    except Exception as e:
        pass
    return None, None

def add_restaurant(name, category, address, lat, lng, author):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO restaurants (name, category, address, lat, lng, author, created_at) VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id",
        (name, category, address, lat, lng, author, datetime.now().strftime("%Y-%m-%d %H:%M"))
    )
    new_id = cursor.fetchone()[0]
    conn.commit()
    conn.close()
    st.cache_data.clear()  # 캐시 초기화
    return new_id

@st.cache_data(ttl=600)
def get_restaurants(category_filter="전체"):
    conn = get_conn()
    if category_filter == "전체":
        df = pd.read_sql("""
            SELECT r.*, ROUND(AVG(rv.rating)::numeric,1) as avg_rating, COUNT(rv.id) as review_count
            FROM restaurants r
            LEFT JOIN reviews rv ON r.id = rv.restaurant_id
            GROUP BY r.id
            ORDER BY r.created_at DESC
        """, conn)
    else:
        df = pd.read_sql("""
            SELECT r.*, ROUND(AVG(rv.rating)::numeric,1) as avg_rating, COUNT(rv.id) as review_count
            FROM restaurants r
            LEFT JOIN reviews rv ON r.id = rv.restaurant_id
            WHERE r.category = %s
            GROUP BY r.id
            ORDER BY r.created_at DESC
        """, conn, params=(category_filter,))
    conn.close()
    return df

def add_review(restaurant_id, author, rating, comment):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO reviews (restaurant_id, author, rating, comment, created_at) VALUES (%s,%s,%s,%s,%s)",
        (restaurant_id, author, rating, comment, datetime.now().strftime("%Y-%m-%d %H:%M"))
    )
    conn.commit()
    conn.close()
    st.cache_data.clear()  # 캐시 초기화

@st.cache_data(ttl=600)
def get_all_reviews():
    conn = get_conn()
    df = pd.read_sql(
        "SELECT * FROM reviews ORDER BY created_at DESC",
        conn
    )
    conn.close()
    return df

@st.cache_data(ttl=600)
def get_reviews(restaurant_id):
    conn = get_conn()
    df = pd.read_sql(
        "SELECT * FROM reviews WHERE restaurant_id=%s ORDER BY created_at DESC",
        conn, params=(restaurant_id,)
    )
    conn.close()
    return df

def delete_restaurant(restaurant_id):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM reviews WHERE restaurant_id=%s", (restaurant_id,))
    cursor.execute("DELETE FROM restaurants WHERE id=%s", (restaurant_id,))
    conn.commit()
    conn.close()
    st.cache_data.clear()  # 캐시 초기화

def stars(rating, max_stars=5):
    if pd.isna(rating):
        return "리뷰 없음"
    filled = int(round(rating))
    return "★" * filled + "☆" * (max_stars - filled) + f"  {rating:.1f}"

# ─────────────────────────────────────────────
# 4. 헤더
# ─────────────────────────────────────────────
st.markdown("""
<div class="app-header">
    <h1>🍽️ 사내 맛집 지도</h1>
    <p>팀원들과 함께 만들어가는 우리 오피스 주변 맛집 가이드</p>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# 5. 탭 구성
# ─────────────────────────────────────────────
tab_map, tab1, tab2, tab3 = st.tabs(["🗺️ 지도 & 등록", "📋 맛집 목록", "⭐ 리뷰 & 평점", "🎰 오늘의 점심 룰렛"])

# ═══════════════════════════════════════════════
# TAB MAP — 맛집 지도 & 등록
# ═══════════════════════════════════════════════
with tab_map:
    col_map_form, col_map_view = st.columns([1, 2.5], gap="large")
    
    with col_map_form:
        st.markdown('<div class="section-title">✏️ 맛집 빠른 등록</div>', unsafe_allow_html=True)
        with st.form("register_form_map", clear_on_submit=True):
            author_r = st.text_input("👤 작성자 이름", placeholder="비워두면 익명(링피플 XXXX)으로 등록돼요")
            rest_name = st.text_input("🍴 식당 이름 *", placeholder="예) 명동교자")
            category  = st.selectbox("📂 카테고리", CATEGORIES)
            address   = st.text_input("🗺️ 식당 주소 (필수)", placeholder="예) 서울 강남구 테헤란로 123 (도로명 주소 권장)")
            
            st.markdown("---")
            st.markdown("💬 **빠른 리뷰 등록 (선택)**")
            map_rating  = st.slider("⭐ 별점", min_value=1, max_value=5, value=4, format="%d점")
            map_comment = st.text_area("📝 리뷰 코멘트", placeholder="빈칸으로 두면 리뷰 없이 식당만 등록됩니다.", height=80)
            
            submitted = st.form_submit_button("📌 등록하기", use_container_width=True, type="primary")

            if submitted:
                if not rest_name.strip():
                    st.warning("식당 이름을 입력해 주세요.")
                elif not address.strip():
                    st.warning("식당 주소를 입력해 주세요.")
                else:
                    final_author = author_r.strip()
                    if not final_author:
                        final_author = f"링피플 {random.randint(1000, 9999)}"
                    with st.spinner("주소 좌표를 찾는 중..."):
                        lat, lng = get_lat_lng(address.strip())
                    if lat is None or lng is None:
                        st.warning("입력하신 주소의 좌표를 찾을 수 없습니다. 정확한 도로명 주소를 입력해 주세요.")
                    else:
                        new_id = add_restaurant(rest_name.strip(), category, address.strip(), lat, lng, final_author)
                        
                        if map_comment.strip():
                            add_review(new_id, final_author, map_rating, map_comment.strip())
                            st.success(f"✅ **{rest_name}** 등록 및 리뷰가 작성되었습니다! (지도에 추가됨)")
                        else:
                            st.success(f"✅ **{rest_name}** 이(가) 등록되었습니다! (지도에 추가됨)")
                        st.rerun()

    with col_map_view:
        st.markdown('<div class="section-title">🗺️ 우리 회사 주변 맛집 지도</div>', unsafe_allow_html=True)
        st.caption("핀을 클릭하면 상세 리뷰를 볼 수 있습니다. (지도: Vworld)")

        df_map = get_restaurants()
        df_all_reviews = get_all_reviews()  # N+1 쿼리 해결을 위해 모든 리뷰 한 번에 가져옴
        
        # 링티 회사 좌표 (고정값)
        COMPANY_LAT = 37.504944
        COMPANY_LNG = 127.053058
        
        if df_map.empty or df_map['lat'].dropna().empty:
            center = [COMPANY_LAT, COMPANY_LNG] # 링티 회사 기본
        else:
            # 회사 위치를 포함하여 중심점 계산하거나, 그냥 회사 중심으로 고정해도 됨
            # 여기서는 등록된 식당들의 평균 위치를 중심으로 하되, 식당이 회사 주변이므로 무방함.
            center = [df_map['lat'].mean(), df_map['lng'].mean()]
            
        m = folium.Map(
            location=center, 
            zoom_start=15
        )
        
        # 회사 마커 추가 (빨간색 집 모양)
        folium.Marker(
            [COMPANY_LAT, COMPANY_LNG],
            popup=folium.Popup("<div style='min-width: 150px;'><b>🏢 링티 (우리 회사)</b><br><span style='font-size: 12px; color: gray;'>서울특별시 강남구 선릉로90길 48</span></div>", max_width=250),
            tooltip="링티 (우리 회사)",
            icon=folium.Icon(color="red", icon="home")
        ).add_to(m)
        
        for _, row in df_map.iterrows():
            if pd.notna(row['lat']) and pd.notna(row['lng']):
                # 메모리 상에서 해당 맛집의 리뷰만 필터링하여 N+1 쿼리 방지
                reviews = df_all_reviews[df_all_reviews['restaurant_id'] == row['id']]
                avg_rating = row['avg_rating']
                avg_str = f"⭐ {avg_rating:.1f}" if pd.notna(avg_rating) else "리뷰 없음"
                
                popup_html = f'''
                <div style="min-width: 200px;">
                    <h4 style="margin-bottom: 5px; font-family: sans-serif;">{row["name"]}</h4>
                    <p style="margin: 0; color: gray; font-family: sans-serif; font-size: 13px;">{row["category"]} | {avg_str}</p>
                    <hr style="margin: 8px 0;">
                    <b style="font-size: 13px; font-family: sans-serif;">유저 리뷰 ({len(reviews)}개):</b>
                    <div style="max-height: 120px; overflow-y: auto; margin-top: 5px; font-size: 12px; color: #444; font-family: sans-serif;">
                '''
                
                if reviews.empty:
                    popup_html += "<p style='margin: 3px 0;'>아직 리뷰가 없습니다.</p>"
                else:
                    for _, rv in reviews.iterrows():
                        comment = str(rv["comment"]).replace('<', '&lt;').replace('>', '&gt;')
                        author_name = str(rv["author"]).replace('<', '&lt;').replace('>', '&gt;')
                        popup_html += f'<div style="margin-bottom: 6px; padding-bottom: 4px; border-bottom: 1px dashed #eee;"><b>{author_name}</b> ({rv["rating"]}점)<br>{comment}</div>'
                        
                popup_html += '''
                    </div>
                </div>
                '''
                
                folium.Marker(
                    [row['lat'], row['lng']],
                    popup=folium.Popup(popup_html, max_width=300),
                    tooltip=row['name'],
                    icon=folium.Icon(color="orange", icon="info-sign")
                ).add_to(m)
                
        import streamlit.components.v1 as components
        components.html(m.get_root().render(), height=600)

# ═══════════════════════════════════════════════
# TAB 1 — 맛집 목록
# ═══════════════════════════════════════════════
with tab1:
    st.markdown('<div class="section-title">📋 등록된 맛집 목록</div>', unsafe_allow_html=True)

    # 카테고리 필터
    filter_opts = ["전체"] + CATEGORIES
    cat_filter  = st.selectbox("카테고리 필터", filter_opts, label_visibility="collapsed")
    df_rest = get_restaurants(cat_filter)

    if df_rest.empty:
        st.info("아직 등록된 맛집이 없어요. 첫 번째 맛집을 등록해 보세요! 🙌")
    else:
        st.caption(f"총 **{len(df_rest)}개** 식당")
        for _, row in df_rest.iterrows():
            avg  = row["avg_rating"]
            cnt  = int(row["review_count"])
            star_str = f'<span class="star-display">{stars(avg)}</span> <span class="restaurant-meta">({cnt}개 리뷰)</span>' \
                       if cnt > 0 else '<span class="no-review">리뷰 없음</span>'
            address_str = f'&nbsp;·&nbsp;<span style="color:#888;">📍 {row["address"]}</span>' \
                          if "address" in row and pd.notna(row["address"]) else ""

            st.markdown(f"""
            <div class="restaurant-card">
                <div class="restaurant-name">
                    <span class="category-badge">{row['category']}</span>{row['name']}
                </div>
                <div class="restaurant-meta">
                    {star_str}
                    {address_str}
                </div>
                <div class="restaurant-meta" style="margin-top:4px;">
                    📝 {row['author']} · {row['created_at']}
                </div>
            </div>
            """, unsafe_allow_html=True)

            # 삭제 버튼 (expander 안으로)
            with st.expander("⚙️ 관리"):
                del_author = st.text_input("삭제하려면 본인 이름 입력", key=f"del_auth_{row['id']}", placeholder="등록자 이름과 동일하게")
                if st.button("🗑️ 이 식당 삭제", key=f"del_{row['id']}", type="secondary"):
                    if del_author.strip() == row["author"]:
                        delete_restaurant(row["id"])
                        st.success("삭제되었습니다.")
                        st.rerun()
                    else:
                        st.error("등록자 이름이 일치하지 않습니다.")

# ═══════════════════════════════════════════════
# TAB 2 — 리뷰 & 평점
# ═══════════════════════════════════════════════
with tab2:
    df_all = get_restaurants()

    if df_all.empty:
        st.info("먼저 Tab 1에서 맛집을 등록해 주세요!")
    else:
        st.markdown('<div class="section-title">🔍 식당 선택</div>', unsafe_allow_html=True)
        st.caption("아래 표에서 리뷰를 확인하거나 작성할 식당을 **클릭(선택)**하세요. (열 제목을 눌러 정렬할 수 있습니다)")
        
        # 보기 좋게 데이터프레임 가공 (id를 보존하여 정렬 후에도 올바른 식당 매핑)
        df_display = df_all[['id', 'name', 'category', 'avg_rating', 'review_count']].copy()
        df_display.columns = ['_id', '식당 이름', '카테고리', '평균 별점', '리뷰 수']
        df_display['평균 별점'] = df_display['평균 별점'].apply(lambda x: f"⭐ {x:.1f}" if pd.notna(x) else "-")
        df_display['리뷰 수'] = df_display['리뷰 수'].apply(lambda x: f"{int(x)}개")
        
        event = st.dataframe(
            df_display.drop(columns=['_id']),
            use_container_width=True,
            hide_index=True,
            selection_mode="single-row",
            on_select="rerun"
        )
        
        if not event.selection.rows:
            st.info("👆 위 표에서 식당을 하나 선택해 주세요!")
        else:
            selected_idx = event.selection.rows[0]
            selected_id  = int(df_display.iloc[selected_idx]["_id"])
            selected_row = df_all[df_all["id"] == selected_id].iloc[0]
            
            st.markdown(f"### 🍽️ {selected_row['name']}")

            # 요약 정보
            avg  = selected_row["avg_rating"]
            cnt  = int(selected_row["review_count"])
            c1, c2, c3 = st.columns(3)
            c1.metric("카테고리", selected_row["category"])
            c2.metric("평균 별점", f"{avg:.1f} / 5.0" if not pd.isna(avg) else "없음")
            c3.metric("리뷰 수", f"{cnt}개")

            if "address" in selected_row and pd.notna(selected_row["address"]):
                st.caption(f"📍 주소: {selected_row['address']}")

            st.divider()
            col_rv_form, col_rv_list = st.columns([1, 1.4], gap="large")

            # ── 리뷰 작성 ──
            with col_rv_form:
                st.markdown('<div class="section-title">✍️ 리뷰 작성</div>', unsafe_allow_html=True)
                with st.form("review_form", clear_on_submit=True):
                    rv_author  = st.text_input("👤 작성자 이름", placeholder="비워두면 익명(링피플 XXXX)으로 등록돼요")
                    rv_rating  = st.slider("⭐ 별점", min_value=1, max_value=5, value=4,
                                           format="%d점")
                    # 별점 시각화
                    st.markdown(
                        f'<div style="font-size:1.6rem;color:#FFB800;">{"★"*rv_rating}{"☆"*(5-rv_rating)}</div>',
                        unsafe_allow_html=True
                    )
                    rv_comment = st.text_area("💬 코멘트", placeholder="맛, 분위기, 가격 등 자유롭게 남겨주세요.", height=110)
                    rv_submit  = st.form_submit_button("📮 리뷰 등록", use_container_width=True, type="primary")

                    if rv_submit:
                        if not rv_comment.strip():
                            st.warning("코멘트를 입력해 주세요.")
                        else:
                            import random
                            final_author = rv_author.strip()
                            if not final_author:
                                final_author = f"링피플 {random.randint(1000, 9999)}"
                            add_review(selected_id, final_author, rv_rating, rv_comment.strip())
                            st.success("✅ 리뷰가 등록되었습니다! 감사합니다 😊")
                            st.rerun()

            # ── 리뷰 목록 ──
            with col_rv_list:
                st.markdown('<div class="section-title">💬 리뷰 목록</div>', unsafe_allow_html=True)
                df_reviews = get_reviews(selected_id)

                if df_reviews.empty:
                    st.info("아직 리뷰가 없어요. 첫 번째 리뷰를 남겨보세요!")
                else:
                    for _, rv in df_reviews.iterrows():
                        star_full  = "★" * int(rv["rating"]) + "☆" * (5 - int(rv["rating"]))
                        st.markdown(f"""
                        <div class="review-card">
                            <div>
                                <span class="review-author">👤 {rv['author']}</span>
                                <span class="review-date">{rv['created_at']}</span>
                            </div>
                            <div style="color:#FFB800;font-size:1rem;margin:3px 0;">{star_full} ({rv['rating']}점)</div>
                            <div class="review-comment">{rv['comment']}</div>
                        </div>
                        """, unsafe_allow_html=True)

# ═══════════════════════════════════════════════
# TAB 3 — 오늘의 점심 룰렛
# ═══════════════════════════════════════════════
with tab3:
    st.markdown("### 🎰 오늘 점심 뭐 먹을지 고민된다면?")
    st.caption("카테고리를 선택하고 룰렛을 돌려보세요!")

    df_roulette = get_restaurants()

    if df_roulette.empty:
        st.info("먼저 Tab 1에서 맛집을 등록해 주세요!")
    else:
        cat_options = ["전체"] + sorted(df_roulette["category"].unique().tolist())
        r_col1, r_col2 = st.columns([1, 2], gap="large")

        with r_col1:
            roulette_cat = st.radio("📂 카테고리 선택", cat_options)
            spin_btn = st.button("🎲 룰렛 돌리기!", use_container_width=True, type="primary")

        with r_col2:
            if spin_btn:
                if roulette_cat == "전체":
                    pool = df_roulette
                else:
                    pool = df_roulette[df_roulette["category"] == roulette_cat]

                if pool.empty:
                    st.warning(f"'{roulette_cat}' 카테고리에 등록된 식당이 없어요.")
                else:
                    winner = pool.sample(1).iloc[0]
                    avg    = winner["avg_rating"]
                    avg_str = f"{avg:.1f}점" if not pd.isna(avg) else "리뷰 없음"
                    addr_str = f"<div style='margin-top:0.5rem; font-size:0.9rem; opacity:0.9;'>📍 {winner['address']}</div>" \
                               if "address" in winner and pd.notna(winner['address']) else ""

                    st.markdown(f"""
                    <div class="roulette-result">
                        <div style="font-size:3rem;">🎉</div>
                        <h2>{winner['name']}</h2>
                        <p>카테고리: {winner['category']} &nbsp;|&nbsp; 평균 별점: {avg_str}</p>
                        {addr_str}
                    </div>
                    """, unsafe_allow_html=True)
                    st.balloons()
            else:
                st.markdown("""
                <div style="text-align:center;padding:3rem 1rem;color:#ccc;">
                    <div style="font-size:4rem;">🎯</div>
                    <p style="font-size:1rem;color:#aaa;">버튼을 눌러 오늘의 점심을 뽑아보세요!</p>
                </div>
                """, unsafe_allow_html=True)

        # 선택 가능한 식당 목록 미리보기
        with st.expander(f"📋 '{roulette_cat}' 후보 식당 목록 보기"):
            if roulette_cat == "전체":
                pool_view = df_roulette
            else:
                pool_view = df_roulette[df_roulette["category"] == roulette_cat]

            if pool_view.empty:
                st.write("등록된 식당이 없습니다.")
            else:
                for _, row in pool_view.iterrows():
                    avg  = row["avg_rating"]
                    s    = f"⭐ {avg:.1f}" if not pd.isna(avg) else "리뷰 없음"
                    st.write(f"• **{row['name']}** ({row['category']}) — {s}")

# ─────────────────────────────────────────────
# 푸터
# ─────────────────────────────────────────────
st.divider()
st.markdown(
    "<div style='text-align:center;color:#bbb;font-size:0.8rem;'>링피플 맛집 지도 🍴 · 팀원들과 함께 만들어가는 맛집 가이드</div>",
    unsafe_allow_html=True
)
