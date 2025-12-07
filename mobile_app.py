import streamlit as st
import pymysql
import pandas as pd

# -------------------------------------------
# 1. AYARLAR VE BAĞLANTI (GÜVENLİ VERSİYON)
# -------------------------------------------
st.set_page_config(page_title="İş Takip Raporu", page_icon="📊", layout="centered")

# Veritabanı bağlantısını önbelleğe alıyoruz
@st.cache_resource
def get_connection():
    # Şifreler 'st.secrets' içinden güvenli şekilde çekilir
    # DİKKAT: Buradaki girinti (boşluk) çok önemlidir!
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
        st.error(f"Veritabanı hatası: {e}")
        return []

# -------------------------------------------
# 2. ANA EKRAN TASARIMI
# -------------------------------------------

st.title("📊 Yönetici Durum Raporu")

if st.button("🔄 Verileri Yenile"):
    st.cache_data.clear()
    st.rerun()

# --- BÖLÜM 1: KPI (ÖZET RAKAMLAR) ---
col1, col2, col3 = st.columns(3)

aktif_calisanlar = run_query("SELECT kullanici_adi FROM zaman_kayitlari WHERE check_out IS NULL")
aktif_arizalar = run_query("SELECT id FROM ariza_bildirimleri WHERE durum IN ('Yeni', 'Inceleniyor')")
bekleyen_tatiller = run_query("SELECT id FROM tatil_talepleri WHERE onay_durumu = 'Beklemede'")

with col1:
    st.metric(label="🟢 İşteki Kişi", value=len(aktif_calisanlar))

with col2:
    st.metric(label="⚠️ Açık Arıza", value=len(aktif_arizalar), delta_color="inverse")

with col3:
    st.metric(label="✈️ Tatil Talebi", value=len(bekleyen_tatiller))

st.markdown("---")

# --- BÖLÜM 2: DETAYLI SEKMELER ---
tab1, tab2, tab3, tab4 = st.tabs(["👥 İştekiler", "🛠️ Arızalar", "📋 Görevler", "📅 Rezervasyon"])

with tab1:
    st.subheader("Şu An Çalışan Personel")
    if aktif_calisanlar:
        df_calisan = pd.DataFrame(aktif_calisanlar)
        st.dataframe(df_calisan, use_container_width=True, hide_index=True)
    else:
        st.info("Şu an içeride kimse görünmüyor.")

with tab2:
    st.subheader("Aktif Arıza Bildirimleri")
    arizalar = run_query("SELECT ariza_baslik, gonderen_kullanici_adi, bildirim_tarihi, durum FROM ariza_bildirimleri WHERE durum != 'Cozuldu' ORDER BY id DESC")
    if arizalar:
        df_ariza = pd.DataFrame(arizalar)
        st.dataframe(df_ariza, use_container_width=True, hide_index=True)
    else:
        st.success("Çözülmemiş arıza bulunmuyor.")

with tab3:
    st.subheader("Son Görev Durumları")
    gorevler = run_query("SELECT gorev_adi, atanan_kisi, durum FROM gorevler WHERE durum != 'Tamamlandı' ORDER BY id DESC LIMIT 10")
    if gorevler:
        df_gorev = pd.DataFrame(gorevler)
        st.dataframe(df_gorev, use_container_width=True, hide_index=True)
    else:
        st.info("Aktif görev yok.")

with tab4:
    st.subheader("Bugünkü Salon Rezervasyonları")
    rezervasyonlar = run_query("SELECT salon_adi, baslangic_zamani, konu FROM rezervasyonlar WHERE baslangic_zamani >= CURDATE() ORDER BY baslangic_zamani")
    if rezervasyonlar:
        df_rez = pd.DataFrame(rezervasyonlar)
        st.table(df_rez)
    else:
        st.info("Bugün için rezervasyon yok.")
