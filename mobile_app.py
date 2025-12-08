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
    page_title="İş Takip Raporu",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Tasarım İmzası
st.markdown("""
    <style>
    @keyframes gentle-pulse-glow {
        0% { transform: scale(1); text-shadow: 0 0 2px rgba(255, 75, 75, 0.3); opacity: 0.9; }
        50% { transform: scale(1.05); text-shadow: 0 0 15px rgba(255, 90, 90, 0.8), 0 0 30px rgba(255, 145, 77, 0.6); opacity: 1; }
        100% { transform: scale(1); text-shadow: 0 0 2px rgba(255, 75, 75, 0.3); opacity: 0.9; }
    }
    .fixed-design-credit {
        position: fixed; top: 12px; left: 20px;
        font-family: 'Brush Script MT', 'Comic Sans MS', cursive;
        font-size: 26px;
        background: linear-gradient(to right, #FF4B4B, #FF914D, #FF4B4B);
        background-size: 200% auto;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: bold;
        z-index: 1000001 !important;
        pointer-events: none;
        white-space: nowrap;
        animation: gentle-pulse-glow 3s ease-in-out infinite;
    }
    .stButton button {
        width: 100%;
    }
    </style>
    <div class="fixed-design-credit">Design by Oktay</div>
    """, unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. VERİTABANI FONKSİYONLARI
# ---------------------------------------------------------
@st.cache_resource
def get_connection():
    return pymysql.connect(
        host=st.secrets["db"]["host"],
        user=st.secrets["db"]["user"],
        password=st.secrets["db"]["password"],
        database=st.secrets["db"]["database"],
        port=st.secrets["db"]["port"],
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )

# Veri OKUMA Fonksiyonu
def run_query(query, params=None):
    conn = get_connection()
    try:
        conn.ping(reconnect=True)
        with conn.cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchall()
    except Exception as e:
        st.error(f"Sorgu Hatası: {e}")
        return []

# Veri GÜNCELLEME Fonksiyonu (YENİ EKLENDİ)
def run_update(query, params=None):
    conn = get_connection()
    try:
        conn.ping(reconnect=True)
        with conn.cursor() as cursor:
            cursor.execute(query, params)
            conn.commit() # Değişikliği veritabanına kaydet
            return True
    except Exception as e:
        st.error(f"Güncelleme Hatası: {e}")
        return False

# ---------------------------------------------------------
# 3. VERİLERİ ÇEKME
# ---------------------------------------------------------

# --- KPI / ÖZET ---
st.title("🏢 Merkez Genel Durum Raporu 📢")

# Danimarka Saati
denmark_zone = pytz.timezone('Europe/Copenhagen')
dk_saat = datetime.now(denmark_zone).strftime('%d-%m-%Y %H:%M:%S')

col_h1, col_h2 = st.columns([3, 1])
with col_h1:
    st.caption(f"📅 Rapor Saati (DK): {dk_saat}")
with col_h2:
    if st.button("🔄 Yenile"):
        st.cache_data.clear()
        st.rerun()

# 1. Personel
df_personel = pd.DataFrame(run_query("SELECT kullanici_adi, check_in FROM zaman_kayitlari WHERE check_out IS NULL"))
if not df_personel.empty and 'check_in' in df_personel.columns:
    df_personel['check_in'] = pd.to_datetime(df_personel['check_in'], errors='coerce') + timedelta(hours=1)

# 2. Görevler
df_gorevler = pd.DataFrame(run_query("SELECT gorev_adi, atanan_kisi, durum, baslama_tarihi FROM gorevler WHERE durum NOT IN ('Tamamlandı', 'Tamamlandi')"))

# 3. Arızalar (ID EKLENDİ - GÜNCELLEME İÇİN GEREKLİ)
# Not: id sütununu da çekiyoruz
ariza_data = run_query("""
    SELECT id, ariza_baslik, aciklama, durum, gonderen_kullanici_adi, bildirim_tarihi 
    FROM ariza_bildirimleri 
    WHERE durum NOT IN ('Cozuldu', 'Çözüldü', 'İptal')
    ORDER BY bildirim_tarihi DESC
""")
df_arizalar = pd.DataFrame(ariza_data)

# 4. İzinler
df_izinler = pd.DataFrame(run_query("SELECT kullanici_adi, baslangic_tarihi, talep_gun_sayisi FROM tatil_talepleri WHERE onay_durumu = 'Beklemede'"))

# KPI
c1, c2, c3, c4 = st.columns(4)
c1.metric("👥 Personel", len(df_personel))
c2.metric("📋 Görev", len(df_gorevler))
c3.metric("⚠️ Arıza", len(df_arizalar), delta_color="inverse")
c4.metric("✈️ İzin", len(df_izinler))

st.markdown("---")

# ---------------------------------------------------------
# 4. DETAYLI SEKMELER
# ---------------------------------------------------------

tab_personel, tab_gorev, tab_ariza, tab_izin = st.tabs(["👷‍♂️ Personel", "📝 Görevler", "🛠️ Arıza İşlemleri", "✈️ İzinler"])

with tab_personel:
    if not df_personel.empty:
        st.dataframe(df_personel, use_container_width=True, hide_index=True)
    else:
        st.info("İçeride kimse yok.")

with tab_gorev:
    if not df_gorevler.empty:
        st.dataframe(df_gorevler, use_container_width=True, hide_index=True)
    else:
        st.success("Tüm görevler tamam.")

# --- DÜZENLENEN BÖLÜM: ARIZA GÜNCELLEME ---
with tab_ariza:
    st.subheader("🛠️ Arıza Listesi ve Durum Güncelleme")
    
    if not df_arizalar.empty:
        # Dataframe yerine liste şeklinde gösteriyoruz ki buton ekleyebilelim
        for index, row in df_arizalar.iterrows():
            # Her arıza için bir kutucuk (Expander)
            with st.expander(f"⚠️ {row['ariza_baslik']} - {row['gonderen_kullanici_adi']}"):
                
                col_detay, col_islem = st.columns([2, 1])
                
                with col_detay:
                    st.write(f"**Açıklama:** {row.get('aciklama', 'Yok')}")
                    st.write(f"**Tarih:** {row['bildirim_tarihi']}")
                    st.write(f"**Mevcut Durum:** `{row['durum']}`")
                
                with col_islem:
                    st.write("##### Durumu Güncelle")
                    # Seçim Kutusu (ID'ye göre benzersiz key veriyoruz)
                    yeni_durum = st.selectbox(
                        "Yeni Durum Seçiniz:",
                        ["Beklemede", "İşlemde", "Parça Bekleniyor", "Cozuldu", "İptal"],
                        key=f"select_{row['id']}",
                        index=0
                    )
                    
                    # Güncelle Butonu
                    if st.button(f"Kaydet #{row['id']}", type="primary", key=f"btn_{row['id']}"):
                        # SQL UPDATE KOMUTU
                        sql = "UPDATE ariza_bildirimleri SET durum = %s WHERE id = %s"
                        basari = run_update(sql, (yeni_durum, row['id']))
                        
                        if basari:
                            st.success(f"Arıza #{row['id']} durumu '{yeni_durum}' olarak güncellendi!")
                            time.sleep(1) # Kullanıcı mesajı görsün diye beklet
                            st.rerun()    # Sayfayı yenile
                        else:
                            st.error("Güncelleme başarısız oldu.")
    else:
        st.success("🎉 Harika! Şu an aktif bir arıza yok.")

with tab_izin:
    if not df_izinler.empty:
        st.dataframe(df_izinler, use_container_width=True, hide_index=True)
    else:
        st.info("Talep yok.")
