import streamlit as st
import pymysql
import pandas as pd
import time
from datetime import datetime, timedelta
import pytz

# ---------------------------------------------------------
# 1. AYARLAR (Merkez İkonlu 🏢)
# ---------------------------------------------------------
st.set_page_config(
    page_title="Merkez İş Takip",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ---------------------------------------------------------
# 2. CSS: SABİT BAR + GİZLEME + GÖRÜNÜM
# ---------------------------------------------------------
st.markdown("""
    <style>
    /* --- 1. DARK MODE ZORLAMA --- */
    .stApp { background-color: #0E1117 !important; color: #FAFAFA !important; }
    .streamlit-expanderHeader { background-color: #262730 !important; color: #FAFAFA !important; }
    div[data-testid="stExpander"] { border: 1px solid #41444C !important; background-color: #161920 !important; }
    [data-testid="stDataFrame"] { background-color: #262730 !important; }
    div[data-baseweb="select"] > div { background-color: #262730 !important; color: white !important; }

    /* --- 2. GİZLEME KODLARI --- */
    footer, #MainMenu .footer, .stFooter { display: none !important; }
    .stAppDeployButton { display: none !important; }
    [data-testid="stStatusWidget"] { display: none !important; }
    div[class*="viewerBadge"] { display: none !important; }

    /* --- 3. STREAMLIT MENÜSÜ (Görünür Kalsın) --- */
    header, [data-testid="stHeader"] {
        background-color: transparent !important;
        visibility: visible !important;
        z-index: 9999999 !important;
    }
    [data-testid="stToolbar"] {
        display: flex !important;
        visibility: visible !important;
        right: 1rem !important;
        top: 0.5rem !important;
        color: white !important;
    }

    /* --- 4. İÇERİK BOŞLUĞU --- */
    .block-container {
        padding-top: 5rem !important; 
        padding-bottom: 1rem !important;
    }

    /* --- 5. ÖZEL TASARIM BAR (SABİT DUVAR) --- */
    .fixed-header-container {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 60px;
        background-color: #0E1117;
        border-bottom: 2px solid #FF4B4B;
        z-index: 999990; 
        display: flex;
        align-items: center;
        padding-left: 20px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.5);
    }

    .design-text {
        font-family: 'Brush Script MT', 'Comic Sans MS', cursive;
        font-size: 26px;
        font-weight: bold;
        background: linear-gradient(to right, #FF4B4B, #FF914D, #FF4B4B);
        background-size: 200% auto; 
        -webkit-background-clip: text; 
        -webkit-text-fill-color: transparent;
        white-space: nowrap; 
        animation: gentle-pulse-glow 3s ease-in-out infinite;
    }
    
    @keyframes gentle-pulse-glow {
        0% { transform: scale(1); text-shadow: 0 0 2px rgba(255, 75, 75, 0.3); opacity: 0.9; }
        50% { transform: scale(1.05); text-shadow: 0 0 15px rgba(255, 90, 90, 0.8), 0 0 30px rgba(255, 145, 77, 0.6); opacity: 1; }
        100% { transform: scale(1); text-shadow: 0 0 2px rgba(255, 75, 75, 0.3); opacity: 0.9; }
    }
    
    .stButton button { width: 100%; border-radius: 8px; font-weight: bold; background-color: #FF4B4B; color: white; border: none; }
    </style>
    
    <div class="fixed-header-container">
        <div class="design-text">Design by Oktay</div>
    </div>
    """, unsafe_allow_html=True)

# ---------------------------------------------------------
# 3. BAĞLANTI (ANLIK)
# ---------------------------------------------------------
@st.cache_resource(ttl=0)
def get_connection():
    try:
        return pymysql.connect(
            host=st.secrets["db"]["host"],
            user=st.secrets["db"]["user"],
            password=st.secrets["db"]["password"],
            database=st.secrets["db"]["database"],
            port=st.secrets["db"]["port"],
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=True 
        )
    except Exception as e:
        return None

def run_query(query, params=None):
    conn = get_connection()
    if not conn: return []
    try:
        with conn.cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchall()
    except Exception:
        return []

def run_update(query, params=None):
    conn = get_connection()
    if not conn: return False
    try:
        with conn.cursor() as cursor:
            cursor.execute(query, params)
            conn.commit()
            return True
    except Exception as e:
        st.error(f"Hata: {e}")
        return False

# ---------------------------------------------------------
# 4. İÇERİK
# ---------------------------------------------------------
st.title("🏢 Merkez Genel Durum Raporu")

dk_saat = datetime.now(pytz.timezone('Europe/Copenhagen')).strftime('%d-%m-%Y %H:%M:%S')

col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    st.caption(f"📅 Rapor Saati (DK): {dk_saat}")
with col2:
    oto_yenile = st.checkbox("🔄 Otomatik Yenile (30sn)", value=False)
with col3:
    if st.button("🔄 Yenile", type="primary"):
        st.cache_data.clear()
        st.rerun()

if oto_yenile:
    time.sleep(30)
    st.rerun()

# --- VERİ ÇEKME ---
raw_personel = run_query("SELECT * FROM zaman_kayitlari ORDER BY id DESC LIMIT 500")
df_tum = pd.DataFrame(raw_personel)
df_aktif = pd.DataFrame()

if not df_tum.empty:
    c_in = next((c for c in ['check_in', 'giris'] if c in df_tum.columns), None)
    c_out = next((c for c in ['check_out', 'cikis'] if c in df_tum.columns), None)
    if c_in: df_tum[c_in] = pd.to_datetime(df_tum[c_in], errors='coerce') + timedelta(hours=1)
    if c_out:
        temp = pd.to_datetime(df_tum[c_out], errors='coerce')
        df_tum[c_out] = temp + timedelta(hours=1)
        df_aktif = df_tum[temp.isna()].copy()
    else:
        df_aktif = df_tum.copy()

df_gorev = pd.DataFrame(run_query("SELECT * FROM gorevler WHERE durum NOT IN ('Tamamlandı', 'Tamamlandi', 'Bitti')"))
df_ariza = pd.DataFrame(run_query("SELECT * FROM ariza_bildirimleri WHERE durum NOT IN ('Cozuldu', 'Çözüldü', 'İptal') ORDER BY id DESC"))
if not df_ariza.empty:
    t = next((c for c in ['bildirim_tarihi', 'tarih'] if c in df_ariza.columns), None)
    if t: df_ariza[t] = pd.to_datetime(df_ariza[t], errors='coerce')

df_izin = pd.DataFrame(run_query("SELECT * FROM tatil_talepleri WHERE onay_durumu = 'Beklemede'"))
df_toplanti = pd.DataFrame(run_query("SELECT * FROM rezervasyonlar WHERE baslangic_zamani >= CURDATE()"))
df_duyuru = pd.DataFrame(run_query("SELECT * FROM duyurular ORDER BY id DESC LIMIT 5"))

# KPI
k1, k2, k3, k4 = st.columns(4)
k1.metric("👥 Aktif Personel", len(df_aktif))
k2.metric("📋 Açık Görev", len(df_gorev))
k3.metric("🚨 Arızalar", len(df_ariza), delta_color="inverse")
k4.metric("✈️ İzinler", len(df_izin))

st.markdown("---")

# SEKMELER
t1, t2, t3, t4, t5, t6 = st.tabs(["👷‍♂️ Personel", "📝 Görevler", "🛠️ Arızalar", "✈️ İzinler", "📅 Toplantı", "📢 Duyurular"])

with t1:
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("🟢 İçeride")
        if not df_aktif.empty:
            ad = next((c for c in ['kullanici_adi', 'ad_soyad'] if c in df_aktif.columns), df_aktif.columns[0])
            gr = next((c for c in ['check_in', 'giris'] if c in df_aktif.columns), None)
            cols = [ad]; 
            if gr: cols.append(gr)
            st.dataframe(df_aktif[cols], hide_index=True, use_container_width=True)
        else: st.info("Kimse yok.")
    with c2:
        st.subheader("📋 Log")
        if not df_tum.empty:
            ad = next((c for c in ['kullanici_adi', 'ad_soyad'] if c in df_tum.columns), None)
            gr = next((c for c in ['check_in', 'giris'] if c in df_tum.columns), None)
            ck = next((c for c in ['check_out', 'cikis'] if c in df_tum.columns), None)
            cols = []
            if ad: cols.append(ad)
            if gr: cols.append(gr)
            if ck: cols.append(ck)
            st.dataframe(df_tum[cols], hide_index=True, use_container_width=True, 
                         column_config={gr: st.column_config.DatetimeColumn("Giriş", format="HH:mm"), 
                                        ck: st.column_config.DatetimeColumn("Çıkış", format="HH:mm")})

# --- GÖREVLER (AÇIKLAMA EKLENDİ) ---
with t2:
    if not df_gorev.empty:
        for i, r in df_gorev.iterrows():
            gid = r.get('id')
            gad = r.get('gorev_adi','G')
            gk = r.get('atanan_kisi','-')
            gd = r.get('durum','')
            
            # Açıklamayı bul (Farklı isimler olabilir diye kontrol ediyoruz)
            g_aciklama = r.get('aciklama', r.get('gorev_aciklamasi', r.get('detay', '')))
            
            with st.expander(f"📌 {gad} ({gk})"):
                # EĞER AÇIKLAMA VARSA GÖSTER
                if g_aciklama:
                    st.info(f"📄 **Açıklama:** {g_aciklama}")
                
                c1, c2 = st.columns([2,1])
                c1.write(f"**Mevcut Durum:** {gd}")
                
                nd = c2.selectbox("Yeni Durum:", ["Beklemede", "Devam Ediyor", "Tamamlandı"], key=f"g{gid if gid else i}")
                
                if c2.button("Kaydet", key=f"gb{gid if gid else i}"):
                    run_update("UPDATE gorevler SET durum=%s WHERE id=%s", (nd, gid))
                    st.success("Güncellendi!")
                    time.sleep(0.5)
                    st.rerun()
    else: st.success("Görev yok.")

with t3:
    if not df_ariza.empty:
        for i, r in df_ariza.iterrows():
            aid = r.get('id'); ab = r.get('ariza_baslik','A'); ak = r.get('gonderen_kullanici_adi','-'); ad = r.get('durum','')
            with st.expander(f"⚠️ #{aid} {ab} ({ak})"):
                c1, c2 = st.columns([2,1])
                c1.info(f"Durum: {ad}")
                if r.get('aciklama'): c1.write(f"**Detay:** {r['aciklama']}")
                na = c2.selectbox("İşlem:", ["Beklemede", "İşlemde", "Parça Bekleniyor", "Cozuldu"], key=f"a{aid if aid else i}")
                if c2.button("Kaydet", key=f"ab{aid if aid else i}"):
                    run_update("UPDATE ariza_bildirimleri SET durum=%s WHERE id=%s", (na, aid))
                    st.success("Ok"); time.sleep(0.5); st.rerun()
    else: st.success("Arıza yok.")

with t4:
    if not df_izin.empty: st.dataframe(df_izin, use_container_width=True)
    else: st.info("İzin yok.")
with t5:
    if not df_toplanti.empty: st.dataframe(df_toplanti, use_container_width=True)
    else: st.info("Toplantı yok.")
with t6:
    if not df_duyuru.empty:
        for i, r in df_duyuru.iterrows():
            with st.expander(f"📢 {r.get('baslik','Duyuru')}"): st.write(r.get('icerik',''))
    else: st.info("Duyuru yok.")
