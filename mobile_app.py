import streamlit as st
import pymysql
import pandas as pd
import time
from datetime import datetime, timedelta
import pytz

# ---------------------------------------------------------
# 1. AYARLAR VE TASARIM
# ---------------------------------------------------------
st.set_page_config(
    page_title="İş Takip Raporu",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- TASARIM İMZASI (SOLA YANAŞIK & EFEKTLİ) ---
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
    /* Tablo ve Buton Düzenlemeleri */
    .stButton button { width: 100%; }
    </style>
    <div class="fixed-design-credit">Design by Oktay</div>
    """, unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. VERİTABANI BAĞLANTISI
# ---------------------------------------------------------
@st.cache_resource
def get_connection():
    """Veritabanı bağlantısını oluşturur."""
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

# --- VERİ OKUMA FONKSİYONU ---
def run_query(query, params=None):
    conn = get_connection()
    if conn is None: return []
    try:
        conn.ping(reconnect=True)
        with conn.cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchall()
    except Exception as e:
        st.error(f"Veri Çekme Hatası: {e}")
        return []

# --- VERİ GÜNCELLEME FONKSİYONU (UPDATE İÇİN) ---
def run_update(query, params=None):
    conn = get_connection()
    if conn is None: return False
    try:
        conn.ping(reconnect=True)
        with conn.cursor() as cursor:
            cursor.execute(query, params)
            conn.commit() # Değişikliği kaydet
            return True
    except Exception as e:
        st.error(f"Güncelleme Hatası: {e}")
        return False

# ---------------------------------------------------------
# 3. ÜST PANEL VE VERİ HAZIRLIĞI
# ---------------------------------------------------------

st.title("🏢 Merkez Genel Durum Raporu 📢")

# --- Danimarka Saati ---
denmark_zone = pytz.timezone('Europe/Copenhagen')
dk_saat = datetime.now(denmark_zone).strftime('%d-%m-%Y %H:%M:%S')

col1, col2 = st.columns([3, 1])
with col1:
    st.caption(f"📅 Rapor Saati (DK): {dk_saat}")
with col2:
    if st.button("🔄 Verileri Canlı Yenile", type="primary"):
        st.cache_data.clear()
        st.rerun()

# --- VERİLERİ ÇEK ---

# 1. Personel
df_personel = pd.DataFrame(run_query("SELECT kullanici_adi, check_in FROM zaman_kayitlari WHERE check_out IS NULL"))
if not df_personel.empty and 'check_in' in df_personel.columns:
    df_personel['check_in'] = pd.to_datetime(df_personel['check_in'], errors='coerce') + timedelta(hours=1)

# 2. Görevler (Tamamlanmamışlar)
df_gorevler = pd.DataFrame(run_query("SELECT gorev_adi, atanan_kisi, durum, baslama_tarihi FROM gorevler WHERE durum NOT IN ('Tamamlandı', 'Tamamlandi') ORDER BY baslama_tarihi ASC"))

# 3. Arızalar (Çözülmemişler) - 'aciklama' sütunu kaldırıldı (Hata önleme)
ariza_sorgusu = """
    SELECT id, ariza_baslik, durum, gonderen_kullanici_adi, bildirim_tarihi 
    FROM ariza_bildirimleri 
    WHERE durum NOT IN ('Cozuldu', 'Çözüldü', 'İptal')
    ORDER BY bildirim_tarihi DESC
"""
df_arizalar = pd.DataFrame(run_query(ariza_sorgusu))
if not df_arizalar.empty and 'bildirim_tarihi' in df_arizalar.columns:
    df_arizalar['bildirim_tarihi'] = pd.to_datetime(df_arizalar['bildirim_tarihi'], errors='coerce')

# 4. İzinler (Bekleyenler)
df_izinler = pd.DataFrame(run_query("SELECT kullanici_adi, baslangic_tarihi, bitis_tarihi, talep_gun_sayisi FROM tatil_talepleri WHERE onay_durumu = 'Beklemede'"))

# 5. Toplantılar
df_toplanti = pd.DataFrame(run_query("SELECT salon_adi, baslangic_zamani, konu, rezerve_eden_adi FROM rezervasyonlar WHERE baslangic_zamani >= CURDATE() ORDER BY baslangic_zamani"))

# 6. Duyurular
df_duyuru = pd.DataFrame(run_query("SELECT baslik, icerik, olusturma_tarihi FROM duyurular ORDER BY id DESC LIMIT 5"))
if not df_duyuru.empty and 'olusturma_tarihi' in df_duyuru.columns:
    df_duyuru['olusturma_tarihi'] = pd.to_datetime(df_duyuru['olusturma_tarihi'], errors='coerce')

# --- ÖZET KUTUCUKLARI (KPI) ---
k1, k2, k3, k4 = st.columns(4)
k1.metric("👥 Aktif Personel", len(df_personel))
k2.metric("📋 Açık Görev", len(df_gorevler))
k3.metric("⚠️ Aktif Arıza", len(df_arizalar), delta_color="inverse")
k4.metric("✈️ Bekleyen İzin", len(df_izinler))

st.markdown("---")

# ---------------------------------------------------------
# 4. DETAYLI SEKMELER
# ---------------------------------------------------------

tab_personel, tab_gorev, tab_ariza, tab_izin, tab_toplanti, tab_duyuru = st.tabs([
    "👷‍♂️ Personel", "📝 Görevler", "🛠️ Arıza İşlemleri", "✈️ İzinler", "📅 Toplantı", "📢 Duyurular"
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

# --- TAB 3: ARIZALAR (GÜNCELLEME ÖZELLİKLİ & HATASIZ) ---
with tab_ariza:
    st.subheader("🛠️ Arıza Listesi ve Durum Güncelleme")
    
    if not df_arizalar.empty:
        # Her bir arıza satırı için döngü
        for index, row in df_arizalar.iterrows():
            
            # Expander Başlığı
            baslik = f"⚠️ #{row['id']} - {row['ariza_baslik']} ({row['gonderen_kullanici_adi']})"
            
            with st.expander(baslik):
                c_detay, c_aksiyon = st.columns([2, 1])
                
                with c_detay:
                    # Tarih Gösterimi
                    tarih_str = row['bildirim_tarihi'].strftime('%d-%m-%Y %H:%M') if pd.notnull(row['bildirim_tarihi']) else "Belirsiz"
                    st.markdown(f"**📅 Tarih:** {tarih_str}")
                    st.markdown(f"**👤 Bildiren:** {row['gonderen_kullanici_adi']}")
                    st.info(f"Mevcut Durum: **{row['durum']}**")

                with c_aksiyon:
                    st.write("**Durumu Güncelle:**")
                    # Seçim Kutusu
                    yeni_durum = st.selectbox(
                        "Seçiniz:",
                        ["Beklemede", "İşlemde", "Parça Bekleniyor", "Cozuldu", "İptal"],
                        key=f"sel_{row['id']}",
                        index=0
                    )
                    
                    # Güncelle Butonu
                    if st.button(f"💾 Kaydet (ID: {row['id']})", key=f"btn_{row['id']}", type="primary"):
                        sql = "UPDATE ariza_bildirimleri SET durum = %s WHERE id = %s"
                        basari = run_update(sql, (yeni_durum, row['id']))
                        
                        if basari:
                            st.success("✅ Güncellendi! Sayfa yenileniyor...")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("❌ Hata oluştu.")
    else:
        st.success("🎉 Harika! Şu an aktif bir arıza yok.")

# --- TAB 4: İZİNLER ---
with tab_izin:
    st.subheader("Onay Bekleyen Talepler")
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
    st.subheader("Yaklaşan Toplantılar")
    if not df_toplanti.empty:
        st.dataframe(
            df_toplanti,
            column_config={
                "salon_adi": "Salon",
                "konu": "Konu",
                "rezerve_eden_adi": "Rezerve Eden",
                "baslangic_zamani": st.column_config.DatetimeColumn("Zaman", format="D MMM, HH:mm")
            },
            use_container_width=True, hide_index=True
        )
    else:
        st.info("Planlanmış toplantı yok.")

# --- TAB 6: DUYURULAR ---
with tab_duyuru:
    st.subheader("Son Duyurular")
    if not df_duyuru.empty:
        for index, row in df_duyuru.iterrows():
            t_str = row['olusturma_tarihi'].strftime('%d-%m-%Y') if pd.notnull(row['olusturma_tarihi']) else "-"
            with st.expander(f"📢 {row['baslik']} ({t_str})"):
                st.write(row['icerik'])
    else:
        st.info("Henüz duyuru yok.")
