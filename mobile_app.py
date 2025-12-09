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
# 2. GÜVENLİ TASARIM VE GİZLEME KODLARI
# ---------------------------------------------------------
st.markdown("""
    <style>
    /* --- 1. GENEL TEMA (Karanlık Mod) --- */
    .stApp { background-color: #0E1117; color: #FAFAFA; }
    
    /* --- 2. GİZLENECEK ÖĞELER (GÜVENLİ YÖNTEM) --- */
    /* Sadece hedef odaklı gizleme yapıyoruz, ana sayfayı bozmuyoruz */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    [data-testid="stToolbar"] {display: none;}
    .stAppDeployButton {display: none;}
    [data-testid="stStatusWidget"] {display: none;}
    
    /* --- 3. SABİT ÜST BAR (DESIGN BY OKTAY) --- */
    .fixed-header {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 60px; /* Bar yüksekliği */
        background-color: #0E1117; /* Sayfa rengiyle aynı (Arkayı kapatır) */
        border-bottom: 2px solid #FF4B4B; /* Alt çizgi */
        z-index: 999999; /* En üst katman */
        display: flex;
        align-items: center;
        padding-left: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    
    /* Animasyonlu Yazı */
    .design-text {
        font-family: 'Brush Script MT', cursive;
        font-size: 26px;
        font-weight: bold;
        background: linear-gradient(to right, #FF4B4B, #FF914D);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        animation: pulse 3s infinite;
    }
    
    @keyframes pulse {
        0% { transform: scale(1); opacity: 0.9; }
        50% { transform: scale(1.05); opacity: 1; }
        100% { transform: scale(1); opacity: 0.9; }
    }

    /* --- 4. İÇERİK DÜZENİ --- */
    /* Sayfa içeriğini header'ın altından başlat */
    .block-container {
        padding-top: 5rem !important; 
        padding-bottom: 2rem !important;
    }
    
    /* Tablo ve Buton Stilleri */
    .stButton button { width: 100%; border-radius: 8px; font-weight: bold; }
    div[data-testid="stExpander"] { background-color: #1A1C24 !important; border: 1px solid #41444C; }
    </style>
    
    <div class="fixed-header">
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
    except Exception as e:
        st.error(f"Bağlantı Hatası: {e}")
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
# 4. SAYFA YAPISI VE OTO-YENİLEME
# ---------------------------------------------------------
# Başlık (Artık sabit barın altında kalmayacak çünkü padding verdik)
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

# ---------------------------------------------------------
# 5. VERİLERİ ÇEKME
# ---------------------------------------------------------

# 1. PERSONEL
raw_personel = run_query("SELECT * FROM zaman_kayitlari ORDER BY id DESC LIMIT 500")
df_tum = pd.DataFrame(raw_personel)
df_aktif = pd.DataFrame()

if not df_tum.empty:
    c_in = next((c for c in ['check_in', 'giris'] if c in df_tum.columns), None)
    c_out = next((c for c in ['check_out', 'cikis'] if c in df_tum.columns), None)

    if c_in:
        df_tum[c_in] = pd.to_datetime(df_tum[c_in], errors='coerce') + timedelta(hours=1)
    
    if c_out:
        temp_out = pd.to_datetime(df_tum[c_out], errors='coerce')
        df_tum[c_out] = temp_out + timedelta(hours=1)
        # Çıkış saati olmayanlar aktiftir
        df_aktif = df_tum[temp_out.isna()].copy()
    else:
        df_aktif = df_tum.copy()

# 2. Görevler
df_gorev = pd.DataFrame(run_query("SELECT * FROM gorevler WHERE durum NOT IN ('Tamamlandı', 'Tamamlandi', 'Bitti')"))

# 3. Arızalar
df_ariza = pd.DataFrame(run_query("SELECT * FROM ariza_bildirimleri WHERE durum NOT IN ('Cozuldu', 'Çözüldü', 'İptal') ORDER BY id DESC"))
if not df_ariza.empty:
    t_col = next((c for c in ['bildirim_tarihi', 'tarih'] if c in df_ariza.columns), None)
    if t_col: df_ariza[t_col] = pd.to_datetime(df_ariza[t_col], errors='coerce')

# 4. Diğer
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

# ---------------------------------------------------------
# 6. SEKMELER
# ---------------------------------------------------------

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["👷‍♂️ Personel", "📝 Görevler", "🛠️ Arızalar", "✈️ İzinler", "📅 Toplantı", "📢 Duyurular"])

# TAB 1: PERSONEL
with tab1:
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("🟢 İçeride Olanlar")
        if not df_aktif.empty:
            ad = next((c for c in ['kullanici_adi', 'ad_soyad'] if c in df_aktif.columns), df_aktif.columns[0])
            giris = next((c for c in ['check_in', 'giris'] if c in df_aktif.columns), None)
            cols = [ad]
            if giris: cols.append(giris)
            st.dataframe(df_aktif[cols], hide_index=True, use_container_width=True)
        else:
            st.info("Kimse yok.")
            
    with c2:
        st.subheader("📋 Giriş/Çıkış Logu")
        if not df_tum.empty:
            ad = next((c for c in ['kullanici_adi', 'ad_soyad'] if c in df_tum.columns), None)
            giris = next((c for c in ['check_in', 'giris'] if c in df_tum.columns), None)
            cikis = next((c for c in ['check_out', 'cikis'] if c in df_tum.columns), None)
            
            cols_log = []
            if ad: cols_log.append(ad)
            if giris: cols_log.append(giris)
            if cikis: cols_log.append(cikis)
            
            st.dataframe(
                df_tum[cols_log],
                column_config={
                    giris: st.column_config.DatetimeColumn("Giriş", format="DD/MM HH:mm"),
                    cikis: st.column_config.DatetimeColumn("Çıkış", format="DD/MM HH:mm")
                },
                hide_index=True, 
                use_container_width=True
            )

# TAB 2: GÖREVLER
with tab2:
    st.subheader("📝 Görev Yönetimi")
    if not df_gorev.empty:
        for i, row in df_gorev.iterrows():
            g_id = row.get('id')
            g_baslik = row.get('gorev_adi', 'Görev')
            g_kisi = row.get('atanan_kisi', '-')
            g_durum = row.get('durum', 'Beklemede')
            
            with st.expander(f"📌 {g_baslik} ({g_kisi})"):
                c1, c2 = st.columns([2,1])
                c1.write(f"Durum: {g_durum}")
                yeni_d = c2.selectbox("Durum:", ["Beklemede", "Devam Ediyor", "Tamamlandı"], key=f"g_{g_id if g_id else i}")
                if c2.button("Kaydet", key=f"gb_{g_id if g_id else i}"):
                    if g_id:
                        run_update("UPDATE gorevler SET durum=%s WHERE id=%s", (yeni_d, g_id))
                        st.success("Güncellendi!")
                        time.sleep(0.5)
                        st.rerun()
    else:
        st.success("Tüm görevler tamam.")

# TAB 3: ARIZALAR
with tab3:
    st.subheader("🚨 Arıza Bildirimleri")
    if not df_ariza.empty:
        for i, row in df_ariza.iterrows():
            a_id = row.get('id')
            a_baslik = row.get('ariza_baslik', 'Arıza')
            a_kisi = row.get('gonderen_kullanici_adi', '-')
            a_durum = row.get('durum', 'Beklemede')
            a_tarih = row.get('bildirim_tarihi')
            
            t_str = a_tarih.strftime('%d/%m %H:%M') if pd.notnull(a_tarih) else ""
            
            with st.expander(f"⚠️ #{a_id} {a_baslik} ({a_kisi})"):
                c1, c2 = st.columns([2,1])
                c1.write(f"**Tarih:** {t_str}")
                c1.info(f"Durum: {a_durum}")
                if row.get('aciklama'): c1.write(row['aciklama'])
                
                yeni_a = c2.selectbox("İşlem:", ["Beklemede", "İşlemde", "Parça Bekleniyor", "Cozuldu"], key=f"a_{a_id if a_id else i}")
                if c2.button("Kaydet", key=f"ab_{a_id if a_id else i}"):
                    if a_id:
                        run_update("UPDATE ariza_bildirimleri SET durum=%s WHERE id=%s", (yeni_a, a_id))
                        st.success("Güncellendi!")
                        time.sleep(0.5)
                        st.rerun()
    else:
        st.success("Arıza yok.")

# DİĞERLERİ
with tab4:
    if not df_izin.empty: st.dataframe(df_izin, use_container_width=True)
    else: st.info("İzin talebi yok.")

with tab5:
    if not df_toplanti.empty: st.dataframe(df_toplanti, use_container_width=True)
    else: st.info("Toplantı yok.")

with tab6:
    if not df_duyuru.empty:
        for i, r in df_duyuru.iterrows():
            with st.expander(f"📢 {r.get('baslik','Duyuru')}"): st.write(r.get('icerik',''))
    else: st.info("Duyuru yok.")
