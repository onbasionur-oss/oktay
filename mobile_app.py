import streamlit as st
import pymysql
import pandas as pd
import time
from datetime import datetime, timedelta
import pytz

# ---------------------------------------------------------
# 1. AYARLAR VE GÜVENLİ BAĞLANTI
# ---------------------------------------------------------
st.set_page_config(
    page_title="İş Takip Raporu",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- TASARIM İMZASI ---
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
    </style>
    <div class="fixed-design-credit">Design by Oktay</div>
    """, unsafe_allow_html=True)

# ---------------------------------------------------------
# VERİTABANI BAĞLANTISI
# ---------------------------------------------------------
@st.cache_resource
def get_connection():
    """Veritabanı bağlantısını önbelleğe alır."""
    try:
        return pymysql.connect(
            host=st.secrets["db"]["host"],
            user=st.secrets["db"]["user"],
            password=st.secrets["db"]["password"],
            database=st.secrets["db"]["database"],
            port=st.secrets["db"]["port"],
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
    except Exception as e:
        st.error(f"⚠️ Veritabanı bağlantı hatası: {e}")
        return None

def run_query(query, params=None):
    """Sorguyu çalıştırır ve sonucu döndürür."""
    conn = get_connection()
    if conn is None:
        return []
    
    try:
        conn.ping(reconnect=True)
        with conn.cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchall()
    except Exception as e:
        # Hata detayını ekranda gösterelim ki sorunu anlayabilelim
        st.error(f"Sorgu Hatası: {e} \n\nSorgu: {query}")
        return []

# ---------------------------------------------------------
# 2. ÜST PANEL VE VERİ HAZIRLIĞI
# ---------------------------------------------------------

st.title("🏢 Merkez Genel Durum Raporu 📢")

# --- Danimarka Saati ---
denmark_zone = pytz.timezone('Europe/Copenhagen')
dk_saat = datetime.now(denmark_zone).strftime('%d-%m-%Y %H:%M:%S')

col_header_1, col_header_2 = st.columns([3, 1])
with col_header_1:
    st.caption(f"📅 Rapor Saati (DK): {dk_saat}")
with col_header_2:
    if st.button("🔄 Verileri Canlı Yenile", type="primary", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# --- VERİLERİ ÇEKME VE İŞLEME ---

# 1. Personel
personel_data = run_query("SELECT kullanici_adi, check_in FROM zaman_kayitlari WHERE check_out IS NULL")
df_personel = pd.DataFrame(personel_data)
if not df_personel.empty and 'check_in' in df_personel.columns:
    df_personel['check_in'] = pd.to_datetime(df_personel['check_in'], errors='coerce') + timedelta(hours=1)

# 2. Görevler (Tamamlanmayanlar)
gorev_data = run_query("SELECT gorev_adi, atanan_kisi, durum, baslama_tarihi FROM gorevler WHERE durum NOT IN ('Tamamlandı', 'Tamamlandi') ORDER BY baslama_tarihi ASC")
df_gorevler = pd.DataFrame(gorev_data)

# 3. Arızalar (Çözülmeyenler - Kapsamı genişlettik)
# NOT: SQL'de 'Cozuldu' ve 'Çözüldü' kontrolü eklendi.
ariza_data = run_query("""
    SELECT ariza_baslik, durum, gonderen_kullanici_adi, bildirim_tarihi 
    FROM ariza_bildirimleri 
    WHERE durum NOT IN ('Cozuldu', 'Çözüldü', 'İptal')
""")
df_arizalar = pd.DataFrame(ariza_data)
# Tarih formatını garantiye alalım
if not df_arizalar.empty and 'bildirim_tarihi' in df_arizalar.columns:
    df_arizalar['bildirim_tarihi'] = pd.to_datetime(df_arizalar['bildirim_tarihi'], errors='coerce')

# 4. İzinler
izin_data = run_query("SELECT kullanici_adi, baslangic_tarihi, bitis_tarihi, talep_gun_sayisi FROM tatil_talepleri WHERE onay_durumu = 'Beklemede'")
df_izinler = pd.DataFrame(izin_data)

# 5. Toplantılar
toplanti_data = run_query("SELECT salon_adi, baslangic_zamani, konu, rezerve_eden_adi FROM rezervasyonlar WHERE baslangic_zamani >= CURDATE() ORDER BY baslangic_zamani")
df_toplanti = pd.DataFrame(toplanti_data)

# 6. Duyurular
duyuru_data = run_query("SELECT baslik, icerik, olusturma_tarihi FROM duyurular ORDER BY id DESC LIMIT 5")
df_duyuru = pd.DataFrame(duyuru_data)
if not df_duyuru.empty and 'olusturma_tarihi' in df_duyuru.columns:
    df_duyuru['olusturma_tarihi'] = pd.to_datetime(df_duyuru['olusturma_tarihi'], errors='coerce')


# --- KPI KARTLARI ---
kpi1, kpi2, kpi3, kpi4 = st.columns(4)
kpi1.metric("👥 Aktif Personel", len(df_personel))
kpi2.metric("📋 Açık Görev", len(df_gorevler))
kpi3.metric("⚠️ Aktif Arıza", len(df_arizalar), delta_color="inverse")
kpi4.metric("✈️ Bekleyen İzin", len(df_izinler))

st.markdown("---")

# ---------------------------------------------------------
# 3. DETAYLI SEKMELER
# ---------------------------------------------------------

tab_personel, tab_gorev, tab_ariza, tab_izin, tab_toplanti, tab_duyuru = st.tabs([
    "👷‍♂️ Personel", "📝 Görevler", "🛠️ Arızalar", "✈️ İzinler", "📅 Toplantı", "📢 Duyurular"
])

# --- TAB 1: PERSONEL ---
with tab_personel:
    st.subheader("Şu An İçeride Olanlar")
    if not df_personel.empty:
        st.dataframe(
            df_personel, 
            column_config={
                "kullanici_adi": "Personel Adı",
                "check_in": st.column_config.DatetimeColumn("Giriş Saati", format="D MMM, HH:mm")
            },
            use_container_width=True, hide_index=True
        )
    else:
        st.info("Şu an içeride aktif çalışan görünmüyor.")

# --- TAB 2: GÖREVLER ---
with tab_gorev:
    st.subheader("Devam Eden Görevler")
    if not df_gorevler.empty:
        st.dataframe(
            df_gorevler,
            column_config={
                "gorev_adi": "Görev",
                "atanan_kisi": "Sorumlu",
                "durum": "Durum",
                "baslama_tarihi": st.column_config.DateColumn("Başlama", format="DD-MM-YYYY")
            },
            use_container_width=True, hide_index=True
        )
    else:
        st.success("Tüm görevler tamamlanmış.")

# --- TAB 3: ARIZALAR (Sorunlu Bölge) ---
with tab_ariza:
    st.subheader("Aktif Arıza Bildirimleri")
    
    if not df_arizalar.empty:
        # Eğer veri geldiyse göster
        st.dataframe(
            df_arizalar,
            column_config={
                "ariza_baslik": "Arıza Konusu",
                "durum": "Durum",
                "gonderen_kullanici_adi": "Bildiren",
                "bildirim_tarihi": st.column_config.DatetimeColumn("Bildirim Zamanı", format="D/M HH:mm")
            },
            use_container_width=True,
            hide_index=True
        )
    else:
        # Veri yoksa nedenini anlamak için basit bir mesaj
        st.success("Sistemde çözülmemiş arıza yok.")
        
        # DEBUG: Eğer gerçekten arıza olduğunu düşünüyorsanız bunu açın
        with st.expander("Veri Görünmüyor mu? (Debug Bilgisi)"):
            st.write("Veritabanından dönen ham veri sayısı:", len(ariza_data))
            st.write("Sorgu:", "SELECT ... FROM ariza_bildirimleri WHERE durum NOT IN ('Cozuldu', 'Çözüldü', 'İptal')")
            if len(ariza_data) == 0:
                st.warning("Veritabanı sorgusu 0 kayıt döndürdü. 'durum' sütununun değerlerini kontrol edin.")

# --- TAB 4: İZİNLER ---
with tab_izin:
    st.subheader("Onay Bekleyen İzinler")
    if not df_izinler.empty:
        st.dataframe(
            df_izinler,
            column_config={
                "kullanici_adi": "Personel",
                "baslangic_tarihi": st.column_config.DateColumn("Başlangıç", format="DD-MM-YYYY"),
                "bitis_tarihi": st.column_config.DateColumn("Bitiş", format="DD-MM-YYYY"),
                "talep_gun_sayisi": "Gün"
            },
            use_container_width=True, hide_index=True
        )
    else:
        st.info("Bekleyen izin talebi yok.")

# --- TAB 5: TOPLANTILAR ---
with tab_toplanti:
    st.subheader("Rezervasyonlar")
    if not df_toplanti.empty:
        st.dataframe(
            df_toplanti,
            column_config={
                "salon_adi": "Salon",
                "konu": "Konu",
                "rezerve_eden_adi": "Rezerve Eden",
                "baslangic_zamani": st.column_config.DatetimeColumn("Tarih/Saat", format="D MMM, HH:mm")
            },
            use_container_width=True, hide_index=True
        )
    else:
        st.info("Planlanmış toplantı yok.")

# --- TAB 6: DUYURULAR ---
with tab_duyuru:
    st.subheader("Duyurular")
    if not df_duyuru.empty:
        for index, row in df_duyuru.iterrows():
            tarih_str = row['olusturma_tarihi'].strftime('%d-%m-%Y') if pd.notnull(row['olusturma_tarihi']) else "-"
            with st.expander(f"📢 {row['baslik']} ({tarih_str})"):
                st.write(row['icerik'])
    else:
        st.info("Duyuru yok.")

# ---------------------------------------------------------
# YÖNETİCİ & DEBUG PANELİ (SADECE SORUN ÇÖZMEK İÇİN)
# ---------------------------------------------------------
with st.expander("🛠️ Yönetici & Hata Kontrolü (Ham Veriler)"):
    st.warning("Burada veritabanından çekilen işlenmemiş verileri görebilirsiniz. Sütun isimlerini kontrol etmek için kullanın.")
    
    st.markdown("**Arızalar Tablosundan İlk 5 Kayıt (Filtresiz):**")
    # Filtresiz ham sorgu - sorunun nerede olduğunu anlamak için
    raw_ariza = run_query("SELECT * FROM ariza_bildirimleri LIMIT 5")
    if raw_ariza:
        st.write(pd.DataFrame(raw_ariza))
    else:
        st.error("ariza_bildirimleri tablosundan hiç veri çekilemedi. Tablo adı yanlış olabilir mi?")
