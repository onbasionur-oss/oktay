import streamlit as st
import pymysql
import pandas as pd
import time
from datetime import datetime, timedelta # EKLENDI
import pytz # EKLENDI

# ---------------------------------------------------------
# 1. AYARLAR VE GÜVENLİ BAĞLANTI
# ---------------------------------------------------------
st.set_page_config(
    page_title="İş Takip Raporu", 
    page_icon="🏢", 
    layout="wide", # Geniş görünüm (Tablolar için daha iyi)
    initial_sidebar_state="collapsed"
)

# Önbellekli Bağlantı Fonksiyonu
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

def run_query(query):
    try:
        conn = get_connection()
        conn.ping(reconnect=True)
        with conn.cursor() as cursor:
            cursor.execute(query)
            return cursor.fetchall()
    except Exception as e:
        st.error(f"Veri çekme hatası: {e}")
        return []

# ---------------------------------------------------------
# 2. ÜST PANEL VE ÖZET (KPI)
# ---------------------------------------------------------

st.title("🏢 DiT   Durum Raporu")

# --- BURASI DÜZELTİLDİ: Danimarka Saati ---
denmark_zone = pytz.timezone('Europe/Copenhagen')
dk_saat = datetime.now(denmark_zone).strftime('%d-%m-%Y %H:%M:%S')
st.caption(f"📅 Rapor Saati (DK): {dk_saat}")
# ------------------------------------------

if st.button("🔄 Verileri Canlı Yenile", type="primary"):
    st.cache_data.clear()
    st.rerun()

# --- VERİLERİ ÇEKİYORUZ ---
# 1. Personel
df_personel = pd.DataFrame(run_query("SELECT kullanici_adi, check_in FROM zaman_kayitlari WHERE check_out IS NULL"))

# --- EKLENEN KISIM: Tablodaki saati 1 saat ileri al (Danimarka ayarı) ---
if not df_personel.empty and 'check_in' in df_personel.columns:
    # Veritabanından gelen saati datetime formatına çevirip 1 saat ekliyoruz
    df_personel['check_in'] = pd.to_datetime(df_personel['check_in']) + timedelta(hours=1)
# ------------------------------------------------------------------------

# 2. Görevler
df_gorevler = pd.DataFrame(run_query("SELECT gorev_adi, atanan_kisi, durum, baslama_tarihi FROM gorevler WHERE durum != 'Tamamlandı' ORDER BY baslama_tarihi ASC"))
# 3. Arızalar
df_arizalar = pd.DataFrame(run_query("SELECT ariza_baslik, durum, gonderen_kullanici_adi, bildirim_tarihi FROM ariza_bildirimleri WHERE durum != 'Cozuldu'"))
# 4. İzinler (Bekleyenler)
df_izinler = pd.DataFrame(run_query("SELECT kullanici_adi, baslangic_tarihi, bitis_tarihi, talep_gun_sayisi FROM tatil_talepleri WHERE onay_durumu = 'Beklemede'"))
# 5. Toplantılar (Bugün ve Sonrası)
df_toplanti = pd.DataFrame(run_query("SELECT salon_adi, baslangic_zamani, konu, rezerve_eden_adi FROM rezervasyonlar WHERE baslangic_zamani >= CURDATE() ORDER BY baslangic_zamani"))
# 6. Duyurular
df_duyuru = pd.DataFrame(run_query("SELECT baslik, icerik, olusturma_tarihi FROM duyurular ORDER BY id DESC LIMIT 5"))

# --- ÖZET KUTUCUKLARI (METRICS) ---
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(label="👥 Aktif Personel", value=len(df_personel))
with col2:
    st.metric(label="📋 Açık Görev", value=len(df_gorevler))
with col3:
    st.metric(label="⚠️ Aktif Arıza", value=len(df_arizalar), delta_color="inverse")
with col4:
    st.metric(label="✈️ Bekleyen İzin", value=len(df_izinler))

st.markdown("---")

# ---------------------------------------------------------
# 3. DETAYLI SEKMELER (TÜM BÖLÜMLER)
# ---------------------------------------------------------

tab_personel, tab_gorev, tab_ariza, tab_izin, tab_toplanti, tab_duyuru = st.tabs([
    "👷‍♂️ Personel", "📝 Görevler", "🛠️ Arızalar", "✈️ İzinler", "📅 Toplantı", "📢 Duyurular"
])

# --- TAB 1: PERSONEL DURUMU ---
with tab_personel:
    st.subheader("Şu An İçeride Olanlar")
    if not df_personel.empty:
        # Tarih formatını düzeltelim
        st.dataframe(
            df_personel, 
            column_config={
                "kullanici_adi": "Personel Adı",
                "check_in": st.column_config.DatetimeColumn("Giriş Saati", format="D MMM, HH:mm")
            },
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("Şu an içeride aktif çalışan görünmüyor.")

# --- TAB 2: GÖREVLER ---
with tab_gorev:
    st.subheader("Tamamlanmamış Görevler")
    if not df_gorevler.empty:
        st.dataframe(
            df_gorevler,
            column_config={
                "gorev_adi": "Görev",
                "atanan_kisi": "Sorumlu",
                "durum": "Durum",
                "baslama_tarihi": st.column_config.DateColumn("Başlama", format="DD-MM-YYYY")
            },
            use_container_width=True,
            hide_index=True
        )
    else:
        st.success("Harika! Tüm görevler tamamlanmış.")

# --- TAB 3: ARIZALAR ---
with tab_ariza:
    st.subheader("Aktif Arıza Bildirimleri")
    if not df_arizalar.empty:
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
        st.success("Sistemde çözülmemiş arıza yok.")

# --- TAB 4: İZİNLER ---
with tab_izin:
    st.subheader("Onay Bekleyen Tatil Talepleri")
    if not df_izinler.empty:
        st.dataframe(
            df_izinler,
            column_config={
                "kullanici_adi": "Personel",
                "baslangic_tarihi": st.column_config.DateColumn("Başlangıç", format="DD-MM-YYYY"),
                "bitis_tarihi": st.column_config.DateColumn("Bitiş", format="DD-MM-YYYY"),
                "talep_gun_sayisi": "Gün"
            },
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("Onay bekleyen izin talebi yok.")

# --- TAB 5: TOPLANTILAR ---
with tab_toplanti:
    st.subheader("Yaklaşan Toplantı Rezervasyonları")
    if not df_toplanti.empty:
        st.dataframe(
            df_toplanti,
            column_config={
                "salon_adi": "Salon",
                "konu": "Toplantı Konusu",
                "rezerve_eden_adi": "Rezerve Eden",
                "baslangic_zamani": st.column_config.DatetimeColumn("Başlama", format="D MMM, HH:mm")
            },
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("Yakın zamanda planlanmış toplantı yok.")

# --- TAB 6: DUYURULAR ---
with tab_duyuru:
    st.subheader("Son Duyurular")
    if not df_duyuru.empty:
        for index, row in df_duyuru.iterrows():
            with st.expander(f"📢 {row['baslik']} ({row['olusturma_tarihi'].strftime('%d-%m-%Y')})"):
                st.write(row['icerik'])
    else:
        st.info("Henüz duyuru yapılmamış.")
