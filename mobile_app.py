import streamlit as st
import pymysql
import pandas as pd
import time
from datetime import datetime, timedelta
import pytz

# ---------------------------------------------------------
# 1. AYARLAR
# ---------------------------------------------------------
st.set_page_config(
    page_title="Merkez İş Takip",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ---------------------------------------------------------
# 2. CSS TASARIM
# ---------------------------------------------------------
st.markdown("""
    <style>
    /* Dark Mode Ayarları */
    .stApp { background-color: #0E1117 !important; color: #FAFAFA !important; }
    .streamlit-expanderHeader { background-color: #262730 !important; color: #FAFAFA !important; }
    div[data-testid="stExpander"] { border: 1px solid #41444C !important; background-color: #161920 !important; }
    [data-testid="stDataFrame"] { background-color: #262730 !important; }
    
    /* Gizleme Kodları */
    footer, #MainMenu .footer { display: none !important; }
    .stAppDeployButton { display: none !important; }
    
    /* Üst Bar Ayarları */
    .block-container { padding-top: 5rem !important; padding-bottom: 1rem !important; }
    
    /* Özel Header (Design by Oktay) */
    .fixed-header-container {
        position: fixed; top: 0; left: 0; width: 100%; height: 60px;
        background-color: #0E1117; border-bottom: 2px solid #FF4B4B;
        z-index: 999990; display: flex; align-items: center; padding-left: 20px;
    }
    .design-text {
        font-family: cursive; font-size: 26px; font-weight: bold;
        background: linear-gradient(to right, #FF4B4B, #FF914D);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    }
    
    /* Sağ Panel Başlıkları */
    .sag-panel-baslik {
        color: #FF914D; font-weight: bold; font-size: 1.1em;
        border-bottom: 1px solid #444; margin-top: 15px; margin-bottom: 10px;
    }
    </style>
    <div class="fixed-header-container">
        <div class="design-text">Design by Oktay</div>
    </div>
    """, unsafe_allow_html=True)

# ---------------------------------------------------------
# 3. VERİTABANI BAĞLANTISI
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
    except: return None

def run_query(query, params=None):
    conn = get_connection()
    if not conn: return []
    with conn.cursor() as cursor:
        cursor.execute(query, params)
        return cursor.fetchall()

def run_update(query, params=None):
    conn = get_connection()
    if not conn: return False
    try:
        with conn.cursor() as cursor:
            cursor.execute(query, params)
            conn.commit()
            return True
    except: return False

# ---------------------------------------------------------
# 4. ÜST MENÜ & BUTONLAR
# ---------------------------------------------------------
st.title("🏢 Merkez Genel Durum")
dk_saat = datetime.now(pytz.timezone('Europe/Copenhagen')).strftime('%d-%m-%Y %H:%M:%S')

c1, c2, c3 = st.columns([2, 1, 1])
c1.caption(f"📅 Saat: {dk_saat}")
oto_yenile = c2.checkbox("🔄 Oto Yenile", value=False)
if c3.button("🔄 Yenile", type="primary"):
    st.cache_data.clear()
    st.rerun()

if oto_yenile:
    time.sleep(30)
    st.rerun()

# ---------------------------------------------------------
# 5. VERİ ÇEKME İŞLEMLERİ
# ---------------------------------------------------------
# Log için veri
raw_personel = run_query("SELECT * FROM zaman_kayitlari ORDER BY id DESC LIMIT 2000")
df_tum = pd.DataFrame(raw_personel)
df_aktif = pd.DataFrame()

# Tarih düzenleme ve Aktif Personel
if not df_tum.empty:
    c_in = next((c for c in ['check_in', 'giris'] if c in df_tum.columns), None)
    c_out = next((c for c in ['check_out', 'cikis'] if c in df_tum.columns), None)
    
    if c_in: df_tum[c_in] = pd.to_datetime(df_tum[c_in], errors='coerce') + timedelta(hours=1)
    if c_out:
        temp = pd.to_datetime(df_tum[c_out], errors='coerce')
        df_tum[c_out] = temp + timedelta(hours=1)
        df_aktif = df_tum[temp.isna()].copy() # Çıkış yapmayanlar
    else:
        df_aktif = df_tum.copy()

# Diğer Veriler
df_gorev = pd.DataFrame(run_query("SELECT * FROM gorevler WHERE durum NOT IN ('Tamamlandı', 'Tamamlandi', 'Bitti')"))
df_ariza = pd.DataFrame(run_query("SELECT * FROM ariza_bildirimleri WHERE durum NOT IN ('Cozuldu', 'Çözüldü', 'İptal') ORDER BY id DESC"))
df_izin = pd.DataFrame(run_query("SELECT * FROM tatil_talepleri WHERE onay_durumu = 'Beklemede'"))
df_toplanti = pd.DataFrame(run_query("SELECT * FROM rezervasyonlar WHERE baslangic_zamani >= CURDATE() ORDER BY baslangic_zamani ASC LIMIT 5"))
df_duyuru = pd.DataFrame(run_query("SELECT * FROM duyurular ORDER BY id DESC LIMIT 5"))

# ---------------------------------------------------------
# 6. EKRAN DÜZENİ (3 SOL - 1 SAĞ)
# ---------------------------------------------------------
# Sayfayı en tepeden bölüyoruz. Sol taraf ana işlem, sağ taraf bilgi paneli.
col_sol, col_sag = st.columns([3, 1])

# --- SOL TARAF (ANA PANEL) ---
with col_sol:
    # KPI Kartları (Burada duruyor)
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("👥 Aktif", len(df_aktif))
    k2.metric("📋 Görev", len(df_gorev))
    k3.metric("🚨 Arıza", len(df_ariza), delta_color="inverse")
    k4.metric("✈️ İzin", len(df_izin))
    
    st.divider()
    
    # SEKMELER
    tab1, tab2, tab3, tab4 = st.tabs(["👷‍♂️ Personel & Log", "📝 Görevler", "🛠️ Arızalar", "✈️ İzinler"])
    
    # 1. PERSONEL & LOG (1 HAFTALIK FİLTRE)
    with tab1:
        st.info("📊 Son 1 haftalık giriş/çıkış kayıtları aşağıdadır.")
        if not df_tum.empty and c_in:
            # Sadece son 7 günü filtrele
            bir_hafta_once = datetime.now() - timedelta(days=7)
            df_log = df_tum[df_tum[c_in] > bir_hafta_once].copy()
            
            ad = next((c for c in ['kullanici_adi', 'ad_soyad'] if c in df_tum.columns), None)
            cols = [ad, c_in, c_out] if c_out else [ad, c_in]
            
            st.dataframe(
                df_log[[c for c in cols if c]], 
                hide_index=True, 
                use_container_width=True,
                column_config={
                    c_in: st.column_config.DatetimeColumn("Giriş", format="DD.MM HH:mm"),
                    c_out: st.column_config.DatetimeColumn("Çıkış", format="DD.MM HH:mm")
                }
            )
        else:
            st.warning("Kayıt yok.")

    # 2. GÖREVLER
    with tab2:
        if not df_gorev.empty:
            for i, r in df_gorev.iterrows():
                with st.expander(f"📌 {r.get('gorev_adi','-')} ({r.get('atanan_kisi','-')})"):
                    st.write(f"Durum: {r.get('durum','')}")
                    if r.get('aciklama'): st.info(r['aciklama'])
                    c_a, c_b = st.columns([2,1])
                    yeni_durum = c_b.selectbox("Durum:", ["Devam Ediyor", "Tamamlandı"], key=f"g{r['id']}")
                    if c_b.button("Kaydet", key=f"gb{r['id']}"):
                        run_update("UPDATE gorevler SET durum=%s WHERE id=%s", (yeni_durum, r['id']))
                        st.success("Güncellendi"); time.sleep(0.5); st.rerun()
        else: st.success("Açık görev yok.")

    # 3. ARIZALAR (DETAYLI İŞLEM)
    with tab3:
        if not df_ariza.empty:
            for i, r in df_ariza.iterrows():
                with st.expander(f"⚠️ {r.get('ariza_baslik','-')} - {r.get('gonderen_kullanici_adi','-')}"):
                    st.write(r.get('aciklama',''))
                    c_a, c_b = st.columns([2,1])
                    islem = c_b.selectbox("İşlem:", ["İşlemde", "Cozuldu"], key=f"a{r['id']}")
                    if c_b.button("Güncelle", key=f"ab{r['id']}"):
                        run_update("UPDATE ariza_bildirimleri SET durum=%s WHERE id=%s", (islem, r['id']))
                        st.success("Güncellendi"); time.sleep(0.5); st.rerun()
        else: st.success("Arıza yok.")

    # 4. İZİNLER
    with tab4:
        st.dataframe(df_izin, use_container_width=True)


# --- SAĞ TARAF (BİLGİ AKIŞ PANELİ) ---
with col_sag:
    # 1. AKTİF PERSONEL
    st.markdown('<div class="sag-panel-baslik">👥 İçerdekiler</div>', unsafe_allow_html=True)
    if not df_aktif.empty:
        ad_col = next((c for c in ['kullanici_adi', 'ad_soyad'] if c in df_aktif.columns), df_aktif.columns[0])
        st.dataframe(df_aktif[[ad_col]], hide_index=True, use_container_width=True)
    else:
        st.info("Kimse yok.")
        
    # 2. ARIZALAR (LİSTE)
    st.markdown('<div class="sag-panel-baslik">🚨 Arızalar</div>', unsafe_allow_html=True)
    if not df_ariza.empty:
        for i, r in df_ariza.iterrows():
            st.error(f"🔧 {r.get('ariza_baslik')}")
    else:
        st.success("Temiz")

    # 3. TOPLANTILAR
    st.markdown('<div class="sag-panel-baslik">📅 Toplantılar</div>', unsafe_allow_html=True)
    if not df_toplanti.empty:
        for i, r in df_toplanti.iterrows():
            zaman = r.get('baslangic_zamani')
            konu = r.get('toplanti_konusu', 'Toplantı')
            st.warning(f"🕒 {zaman}\n📌 {konu}")
    else:
        st.caption("Planlı toplantı yok.")

    # 4. DUYURULAR
    st.markdown('<div class="sag-panel-baslik">📢 Duyurular</div>', unsafe_allow_html=True)
    if not df_duyuru.empty:
        for i, r in df_duyuru.iterrows():
            with st.expander(f"🔹 {r.get('baslik','Duyuru')}"):
                st.write(r.get('icerik',''))
    else:
        st.caption("Duyuru yok.")
