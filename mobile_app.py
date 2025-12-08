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

# --- TASARIM İMZASI ---
st.markdown("""
    <style>
    @keyframes gentle-pulse-glow {
        0% { transform: scale(1); text-shadow: 0 0 2px rgba(255, 75, 75, 0.3); opacity: 0.9; }
        50% { transform: scale(1.05); text-shadow: 0 0 15px rgba(255, 90, 90, 0.8), 0 0 30px rgba(255, 145, 77, 0.6); opacity: 1; }
        100% { transform: scale(1); text-shadow: 0 0 2px rgba(255, 75, 75, 0.3); opacity: 0.9; }
    }
    .fixed-design-credit {
        position: fixed; top: 15px; left: 20px;
        font-family: 'Brush Script MT', 'Comic Sans MS', cursive;
        font-size: 28px;
        background: linear-gradient(to right, #FF4B4B, #FF914D, #FF4B4B);
        background-size: 200% auto; -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        font-weight: bold; z-index: 999999; pointer-events: none;
        white-space: nowrap; animation: gentle-pulse-glow 3s ease-in-out infinite;
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

def run_query(query, params=None):
    conn = get_connection()
    if not conn: return []
    try:
        conn.ping(reconnect=True)
        with conn.cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchall()
    except Exception as e:
        return []

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
dk_saat = datetime.now(pytz.timezone('Europe/Copenhagen')).strftime('%d-%m-%Y %H:%M:%S')

col1, col2 = st.columns([3, 1])
col1.caption(f"📅 Rapor Saati (DK): {dk_saat}")
if col2.button("🔄 Verileri Canlı Yenile", type="primary"):
    st.cache_data.clear()
    st.rerun()

# --- 1. PERSONEL VERİSİ (GARANTİ YÖNTEM) ---
# Limiti artırdık (500) ki aktif olanlar listenin sonunda kalmasın
raw_personel = run_query("SELECT * FROM zaman_kayitlari ORDER BY id DESC LIMIT 500")
df_tum_hareketler = pd.DataFrame(raw_personel)
df_aktif_personel = pd.DataFrame()

if not df_tum_hareketler.empty:
    # Sütun isimlerini bul
    col_giris = next((c for c in ['check_in', 'giris', 'giris_zamani'] if c in df_tum_hareketler.columns), None)
    col_cikis = next((c for c in ['check_out', 'cikis', 'cikis_zamani'] if c in df_tum_hareketler.columns), None)

    # Giriş Saatlerini Formatla (+1 Saat Ekle)
    if col_giris:
        df_tum_hareketler[col_giris] = pd.to_datetime(df_tum_hareketler[col_giris], errors='coerce') + timedelta(hours=1)

    # --- KİM İÇERİDE? (MANTIKSAL FİLTRELEME) ---
    if col_cikis:
        # Geçici bir sütun oluşturup tarih mi değil mi kontrol ediyoruz
        # errors='coerce' sayesinde '0000-00-00', boşluk veya NULL olanlar NaT (Yok) olur.
        temp_cikis_series = pd.to_datetime(df_tum_hareketler[col_cikis], errors='coerce')
        
        # Çıkış saati formatla (Görsel Liste İçin)
        df_tum_hareketler[col_cikis] = temp_cikis_series + timedelta(hours=1)
        
        # AKTİF FİLTRESİ: Dönüştürüldüğünde "NaT" (Tarih Yok) kalanlar hala içeridedir.
        df_aktif_personel = df_tum_hareketler[temp_cikis_series.isna()].copy()
    else:
        # Çıkış sütunu hiç yoksa hepsi içeride varsayılır
        df_aktif_personel = df_tum_hareketler.copy()

# 2. Görevler
df_gorevler = pd.DataFrame(run_query("SELECT * FROM gorevler WHERE durum NOT IN ('Tamamlandı', 'Tamamlandi', 'Bitti')"))

# 3. Arızalar
df_arizalar = pd.DataFrame(run_query("SELECT * FROM ariza_bildirimleri WHERE durum NOT IN ('Cozuldu', 'Çözüldü', 'İptal') ORDER BY id DESC"))
if not df_arizalar.empty:
    t_col = next((c for c in ['bildirim_tarihi', 'tarih'] if c in df_arizalar.columns), None)
    if t_col: df_arizalar[t_col] = pd.to_datetime(df_arizalar[t_col], errors='coerce')

# 4. Diğerleri
df_izinler = pd.DataFrame(run_query("SELECT * FROM tatil_talepleri WHERE onay_durumu = 'Beklemede'"))
df_toplanti = pd.DataFrame(run_query("SELECT * FROM rezervasyonlar WHERE baslangic_zamani >= CURDATE()"))
df_duyuru = pd.DataFrame(run_query("SELECT * FROM duyurular ORDER BY id DESC LIMIT 5"))

# KPI
k1, k2, k3, k4 = st.columns(4)
k1.metric("👥 Aktif Personel", len(df_aktif_personel))
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

# --- TAB 1: PERSONEL ---
with tab_personel:
    col_sol, col_sag = st.columns(2)
    
    # SOL: Aktif Olanlar (Sadece Girenler)
    with col_sol:
        st.subheader("🟢 Şu An İçeride Olanlar")
        if not df_aktif_personel.empty:
            ad_col = next((c for c in ['kullanici_adi', 'ad_soyad', 'personel'] if c in df_aktif_personel.columns), df_aktif_personel.columns[0])
            giris_col = next((c for c in ['check_in', 'giris'] if c in df_aktif_personel.columns), None)
            
            cols_show = [ad_col]
            if giris_col: cols_show.append(giris_col)
            
            st.dataframe(
                df_aktif_personel[cols_show],
                column_config={
                    ad_col: "Personel Adı",
                    giris_col: st.column_config.DatetimeColumn("Giriş Saati", format="HH:mm")
                },
                use_container_width=True, hide_index=True
            )
        else:
            st.info("Kimse içeride görünmüyor.")

    # SAĞ: Tüm Hareketler (Giriş ve Çıkış Saatleri ile)
    with col_sag:
        st.subheader("📋 Son Giriş/Çıkış Hareketleri")
        if not df_tum_hareketler.empty:
            ad_c = next((c for c in ['kullanici_adi', 'ad_soyad'] if c in df_tum_hareketler.columns), None)
            g_c = next((c for c in ['check_in', 'giris'] if c in df_tum_hareketler.columns), None)
            c_c = next((c for c in ['check_out', 'cikis'] if c in df_tum_hareketler.columns), None)
            
            # Sütunları seç
            cols_log = [c for c in [ad_c, g_c, c_c] if c]
            
            st.dataframe(
                df_tum_hareketler[cols_log],
                column_config={
                    ad_c: "Personel",
                    g_c: st.column_config.DatetimeColumn("Giriş", format="DD/MM HH:mm"),
                    c_c: st.column_config.DatetimeColumn("Çıkış Saati", format="DD/MM HH:mm")
                },
                use_container_width=True, hide_index=True
            )
        else:
            st.warning("Veri yok.")

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
                    if st.button("Kaydet", key=f"g_btn_{g_id if g_id else i}", type="primary"):
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
                    if st.button("Kaydet", key=f"a_btn_{a_id if a_id else i}", type="primary"):
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
