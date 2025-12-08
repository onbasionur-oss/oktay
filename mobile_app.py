import streamlit as st
import pymysql
import pandas as pd
import time
from datetime import datetime, timedelta
import pytz

# ---------------------------------------------------------
# 1. AYARLAR VE TASARIM (Siren İkonlu 🚨)
# ---------------------------------------------------------
st.set_page_config(
    page_title="İş Takip Sistemi",
    page_icon="🚨",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- TASARIM İMZASI (GÖRÜNÜR & EFEKTLİ) ---
st.markdown("""
    <style>
    @keyframes gentle-pulse-glow {
        0% { transform: scale(1); text-shadow: 0 0 2px rgba(255, 75, 75, 0.3); opacity: 0.9; }
        50% { transform: scale(1.05); text-shadow: 0 0 15px rgba(255, 90, 90, 0.8), 0 0 30px rgba(255, 145, 77, 0.6); opacity: 1; }
        100% { transform: scale(1); text-shadow: 0 0 2px rgba(255, 75, 75, 0.3); opacity: 0.9; }
    }

    .fixed-design-credit {
        position: fixed;
        top: 15px;
        left: 20px;
        font-family: 'Brush Script MT', 'Comic Sans MS', cursive;
        font-size: 28px;
        background: linear-gradient(to right, #FF4B4B, #FF914D, #FF4B4B);
        background-size: 200% auto;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: bold;
        z-index: 999999; /* En üstte durması için */
        pointer-events: none;
        white-space: nowrap;
        animation: gentle-pulse-glow 3s ease-in-out infinite;
    }
    
    .stButton button { width: 100%; border-radius: 8px; font-weight: bold; }
    </style>
    <div class="fixed-design-credit">Design by Oktay</div>
    """, unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. VERİTABANI BAĞLANTISI
# ---------------------------------------------------------
@st.cache_resource
def get_connection():
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
        st.error(f"⚠️ Veritabanı Bağlantı Hatası: {e}")
        return None

# Veri Okuma
def run_query(query, params=None):
    conn = get_connection()
    if not conn: return []
    try:
        conn.ping(reconnect=True)
        with conn.cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchall()
    except Exception as e:
        st.warning(f"Veri okunurken hata/uyarı: {e}")
        return []

# Veri Güncelleme
def run_update(query, params=None):
    conn = get_connection()
    if not conn: return False
    try:
        conn.ping(reconnect=True)
        with conn.cursor() as cursor:
            cursor.execute(query, params)
            conn.commit()
            return True
    except Exception as e:
        st.error(f"Güncelleme Hatası: {e}")
        return False

# ---------------------------------------------------------
# 3. VERİ HAZIRLIĞI
# ---------------------------------------------------------

st.title("🚨 Merkez Genel Durum Raporu")

# Danimarka Saati
dk_saat = datetime.now(pytz.timezone('Europe/Copenhagen')).strftime('%d-%m-%Y %H:%M:%S')

col1, col2 = st.columns([3, 1])
col1.caption(f"📅 Rapor Saati (DK): {dk_saat}")
if col2.button("🔄 Verileri Canlı Yenile", type="primary"):
    st.cache_data.clear()
    st.rerun()

# --- VERİLERİ ÇEKME ---

# 1. PERSONEL (HEM AKTİF HEM GEÇMİŞ)
# Not: Check_out NULL olabilir veya '0000...' olabilir, ikisini de kontrol ediyoruz.
sql_personel_aktif = """
    SELECT * FROM zaman_kayitlari 
    WHERE check_out IS NULL 
       OR check_out = '' 
       OR check_out LIKE '0000%'
"""
df_personel_aktif = pd.DataFrame(run_query(sql_personel_aktif))

# Tüm kayıtları da çekelim (Log için)
sql_personel_tum = "SELECT * FROM zaman_kayitlari ORDER BY id DESC LIMIT 50"
df_personel_tum = pd.DataFrame(run_query(sql_personel_tum))

# Tarihleri düzelt (Aktif Personel için)
if not df_personel_aktif.empty:
    col_in = next((c for c in ['check_in', 'giris_zamani', 'giris'] if c in df_personel_aktif.columns), None)
    if col_in:
        df_personel_aktif[col_in] = pd.to_datetime(df_personel_aktif[col_in], errors='coerce') + timedelta(hours=1)

# Tarihleri düzelt (Tüm Liste için)
if not df_personel_tum.empty:
    col_in = next((c for c in ['check_in', 'giris'] if c in df_personel_tum.columns), None)
    col_out = next((c for c in ['check_out', 'cikis'] if c in df_personel_tum.columns), None)
    if col_in: df_personel_tum[col_in] = pd.to_datetime(df_personel_tum[col_in], errors='coerce')
    if col_out: df_personel_tum[col_out] = pd.to_datetime(df_personel_tum[col_out], errors='coerce')

# 2. Görevler
df_gorevler = pd.DataFrame(run_query("SELECT * FROM gorevler WHERE durum NOT IN ('Tamamlandı', 'Tamamlandi', 'Bitti')"))

# 3. Arızalar
df_arizalar = pd.DataFrame(run_query("SELECT * FROM ariza_bildirimleri WHERE durum NOT IN ('Cozuldu', 'Çözüldü', 'İptal') ORDER BY id DESC"))
if not df_arizalar.empty:
    t_col = next((c for c in ['bildirim_tarihi', 'tarih'] if c in df_arizalar.columns), None)
    if t_col: df_arizalar[t_col] = pd.to_datetime(df_arizalar[t_col], errors='coerce')

# 4. İzinler & Toplantı
df_izinler = pd.DataFrame(run_query("SELECT * FROM tatil_talepleri WHERE onay_durumu = 'Beklemede'"))
df_toplanti = pd.DataFrame(run_query("SELECT * FROM rezervasyonlar WHERE baslangic_zamani >= CURDATE()"))
df_duyuru = pd.DataFrame(run_query("SELECT * FROM duyurular ORDER BY id DESC LIMIT 5"))

# KPI
k1, k2, k3, k4 = st.columns(4)
k1.metric("👥 Aktif Personel", len(df_personel_aktif))
k2.metric("📋 Açık Görev", len(df_gorevler))
k3.metric("🚨 Arızalar", len(df_arizalar), delta_color="inverse")
k4.metric("✈️ İzinler", len(df_izinler))

st.markdown("---")

# ---------------------------------------------------------
# 4. DETAYLI SEKMELER
# ---------------------------------------------------------

tab_personel, tab_gorev, tab_ariza, tab_izin, tab_toplanti, tab_duyuru = st.tabs([
    "👷‍♂️ Personel Takibi", "📝 Görevler", "🛠️ Arızalar", "✈️ İzinler", "📅 Toplantı", "📢 Duyurular"
])

# --- TAB 1: PERSONEL (GELİŞMİŞ GÖRÜNÜM) ---
with tab_personel:
    col_aktif, col_log = st.columns(2)
    
    # 1. BÖLÜM: Sadece İçeride Olanlar
    with col_aktif:
        st.subheader("🟢 Şu An İçeride Olanlar")
        if not df_personel_aktif.empty:
            isim_col = next((c for c in ['kullanici_adi', 'ad_soyad', 'personel'] if c in df_personel_aktif.columns), df_personel_aktif.columns[0])
            zaman_col = next((c for c in ['check_in', 'giris'] if c in df_personel_aktif.columns), df_personel_aktif.columns[1])
            
            st.dataframe(
                df_personel_aktif[[isim_col, zaman_col]], 
                column_config={
                    isim_col: "Personel Adı",
                    zaman_col: st.column_config.DatetimeColumn("Giriş Saati", format="HH:mm")
                },
                use_container_width=True, hide_index=True
            )
        else:
            st.info("Şu an içeride aktif görünen personel yok.")

    # 2. BÖLÜM: Son Hareketler (Giriş & Çıkış Listesi)
    with col_log:
        st.subheader("📋 Son Giriş/Çıkış Hareketleri")
        if not df_personel_tum.empty:
            # Sütunları otomatik bul
            isim_c = next((c for c in ['kullanici_adi', 'ad_soyad'] if c in df_personel_tum.columns), None)
            giris_c = next((c for c in ['check_in', 'giris'] if c in df_personel_tum.columns), None)
            cikis_c = next((c for c in ['check_out', 'cikis'] if c in df_personel_tum.columns), None)
            
            cols_to_show = [c for c in [isim_c, giris_c, cikis_c] if c is not None]
            
            st.dataframe(
                df_personel_tum[cols_to_show],
                column_config={
                    isim_c: "Personel",
                    giris_c: st.column_config.DatetimeColumn("Giriş", format="DD/MM HH:mm"),
                    cikis_c: st.column_config.DatetimeColumn("Çıkış", format="DD/MM HH:mm")
                },
                use_container_width=True, hide_index=True
            )
        else:
            st.warning("Veritabanında hiç kayıt bulunamadı.")

# --- TAB 2: GÖREVLER ---
with tab_gorev:
    st.subheader("📝 Görev Listesi")
    if not df_gorevler.empty:
        for i, row in df_gorevler.iterrows():
            g_id = row.get('id')
            g_ad = row.get('gorev_adi', row.get('baslik', 'Görev'))
            g_kisi = row.get('atanan_kisi', row.get('sorumlu', '-'))
            g_durum = row.get('durum', 'Beklemede')
            g_tarih = row.get('baslama_tarihi', '-')

            with st.expander(f"📌 {g_ad} ({g_kisi})"):
                c1, c2 = st.columns([2, 1])
                with c1:
                    st.write(f"**Başlama:** {g_tarih}")
                    st.write(f"**Durum:** `{g_durum}`")
                    st.progress(100 if g_durum in ['Tamamlandı', 'Bitti'] else 50 if 'Devam' in g_durum else 10)
                with c2:
                    yeni_d = st.selectbox("Durum:", ["Beklemede", "Devam Ediyor", "Tamamlandı"], key=f"g_sel_{g_id if g_id else i}")
                    if st.button("Kaydet", key=f"g_btn_{g_id if g_id else i}"):
                        if g_id:
                            run_update("UPDATE gorevler SET durum=%s WHERE id=%s", (yeni_d, g_id))
                            st.success("Güncellendi!"); time.sleep(0.5); st.rerun()
    else:
        st.success("Tüm görevler tamam.")

# --- TAB 3: ARIZALAR ---
with tab_ariza:
    st.subheader("🚨 Arıza Listesi")
    if not df_arizalar.empty:
        for i, row in df_arizalar.iterrows():
            a_id = row.get('id')
            a_baslik = row.get('ariza_baslik', row.get('baslik', 'Arıza'))
            a_kisi = row.get('gonderen_kullanici_adi', '-')
            a_durum = row.get('durum', 'Beklemede')
            t_col = next((c for c in ['bildirim_tarihi', 'tarih'] if c in row.index), None)
            t_str = row[t_col].strftime('%d-%m %H:%M') if t_col and pd.notnull(row[t_col]) else ""

            with st.expander(f"⚠️ #{a_id} {a_baslik} ({a_kisi})"):
                c1, c2 = st.columns([2, 1])
                with c1:
                    st.write(f"**Tarih:** {t_str}")
                    st.info(f"Durum: {a_durum}")
                    if row.get('aciklama'): st.write(f"Detay: {row['aciklama']}")
                with c2:
                    yeni_a = st.selectbox("Durum:", ["Beklemede", "İşlemde", "Parça Bekleniyor", "Cozuldu"], key=f"a_sel_{a_id if a_id else i}")
                    if st.button("Kaydet", key=f"a_btn_{a_id if a_id else i}"):
                        if a_id:
                            run_update("UPDATE ariza_bildirimleri SET durum=%s WHERE id=%s", (yeni_a, a_id))
                            st.success("Güncellendi!"); time.sleep(0.5); st.rerun()
    else:
        st.success("Aktif arıza yok.")

# --- DİĞER SEKMELER ---
with tab_izin:
    if not df_izinler.empty: st.dataframe(df_izinler, use_container_width=True, hide_index=True)
    else: st.info("İzin talebi yok.")

with tab_toplanti:
    if not df_toplanti.empty: st.dataframe(df_toplanti, use_container_width=True, hide_index=True)
    else: st.info("Toplantı yok.")

with tab_duyuru:
    if not df_duyuru.empty:
        for i, row in df_duyuru.iterrows():
            with st.expander(f"📢 {row.get('baslik','Duyuru')}"): st.write(row.get('icerik',''))
    else: st.info("Duyuru yok.")
