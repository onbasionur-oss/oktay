import streamlit as st
import pymysql
import pandas as pd
import time
from datetime import datetime, timedelta
import pytz

# ---------------------------------------------------------
# 1. AYARLAR VE GÜÇLÜ TASARIM (Siren İkonlu 🚨)
# ---------------------------------------------------------
st.set_page_config(
    page_title="İş Takip Sistemi",
    page_icon="🚨",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- TASARIM İMZASI (GÖRÜNÜR HALE GETİRİLDİ) ---
st.markdown("""
    <style>
    /* 1. Animasyon Tanımı: Parlama Efekti */
    @keyframes gentle-pulse-glow {
        0% { transform: scale(1); text-shadow: 0 0 2px rgba(255, 75, 75, 0.3); opacity: 0.9; }
        50% { transform: scale(1.05); text-shadow: 0 0 15px rgba(255, 90, 90, 0.8), 0 0 30px rgba(255, 145, 77, 0.6); opacity: 1; }
        100% { transform: scale(1); text-shadow: 0 0 2px rgba(255, 75, 75, 0.3); opacity: 0.9; }
    }

    /* 2. Sabit Yazı Stili (En Üst Katman) */
    .fixed-design-credit {
        position: fixed;
        top: 12px;     /* Yukarıdan boşluk */
        left: 20px;    /* Soldan boşluk */
        
        font-family: 'Brush Script MT', 'Comic Sans MS', cursive;
        font-size: 26px;
        
        /* Renk Gradyanı */
        background: linear-gradient(to right, #FF4B4B, #FF914D, #FF4B4B);
        background-size: 200% auto;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        
        font-weight: bold;
        /* Z-Index çok yüksek olmalı ki Streamlit menüsünün üstünde kalsın */
        z-index: 1000002 !important; 
        pointer-events: none;
        white-space: nowrap;
        
        animation: gentle-pulse-glow 3s ease-in-out infinite;
    }
    
    /* Tablo ve Buton İyileştirmeleri */
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

# --- Veri OKUMA (SELECT) ---
def run_query(query, params=None):
    conn = get_connection()
    if not conn: return []
    try:
        conn.ping(reconnect=True)
        with conn.cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchall()
    except Exception as e:
        st.warning(f"Veri okunurken uyarı: {e}")
        return []

# --- Veri GÜNCELLEME (UPDATE) ---
def run_update(query, params=None):
    conn = get_connection()
    if not conn: return False
    try:
        conn.ping(reconnect=True)
        with conn.cursor() as cursor:
            cursor.execute(query, params)
            conn.commit() # Değişikliği Kalıcı Yap
            return True
    except Exception as e:
        st.error(f"Güncelleme Hatası: {e}")
        return False

# ---------------------------------------------------------
# 3. VERİ HAZIRLIĞI VE KPI
# ---------------------------------------------------------

st.title("🚨 Merkez Genel Durum Raporu")

# Danimarka Saati
dk_saat = datetime.now(pytz.timezone('Europe/Copenhagen')).strftime('%d-%m-%Y %H:%M:%S')

col1, col2 = st.columns([3, 1])
col1.caption(f"📅 Rapor Saati (DK): {dk_saat}")

if col2.button("🔄 Verileri Canlı Yenile", type="primary"):
    st.cache_data.clear()
    st.rerun()

# --- VERİLERİ ÇEK ---

# 1. Personel
df_personel = pd.DataFrame(run_query("SELECT * FROM zaman_kayitlari WHERE check_out IS NULL"))
if not df_personel.empty and 'check_in' in df_personel.columns:
    df_personel['check_in'] = pd.to_datetime(df_personel['check_in'], errors='coerce') + timedelta(hours=1)

# 2. Görevler (Tamamlanmamış Olanlar)
df_gorevler = pd.DataFrame(run_query("SELECT * FROM gorevler WHERE durum NOT IN ('Tamamlandı', 'Tamamlandi', 'Bitti')"))

# 3. Arızalar (Çözülmemiş Olanlar)
df_arizalar = pd.DataFrame(run_query("SELECT * FROM ariza_bildirimleri WHERE durum NOT IN ('Cozuldu', 'Çözüldü', 'İptal') ORDER BY id DESC"))
if not df_arizalar.empty:
    # Tarih sütununu bul ve formatla
    t_col = next((c for c in ['bildirim_tarihi', 'tarih', 'created_at'] if c in df_arizalar.columns), None)
    if t_col: df_arizalar[t_col] = pd.to_datetime(df_arizalar[t_col], errors='coerce')

# 4. İzinler & Toplantılar & Duyurular
df_izinler = pd.DataFrame(run_query("SELECT * FROM tatil_talepleri WHERE onay_durumu = 'Beklemede'"))
df_toplanti = pd.DataFrame(run_query("SELECT * FROM rezervasyonlar WHERE baslangic_zamani >= CURDATE()"))
df_duyuru = pd.DataFrame(run_query("SELECT * FROM duyurular ORDER BY id DESC LIMIT 5"))

# --- KPI KARTLARI ---
k1, k2, k3, k4 = st.columns(4)
k1.metric("👥 Personel", len(df_personel))
k2.metric("📋 Açık Görev", len(df_gorevler))
k3.metric("🚨 Arızalar", len(df_arizalar), delta_color="inverse")
k4.metric("✈️ İzinler", len(df_izinler))

st.markdown("---")

# ---------------------------------------------------------
# 4. DETAYLI SEKMELER VE GÜNCELLEME İŞLEMLERİ
# ---------------------------------------------------------

tab_personel, tab_gorev, tab_ariza, tab_izin, tab_toplanti, tab_duyuru = st.tabs([
    "👷‍♂️ Personel", "📝 Görev Yönetimi", "🛠️ Arıza Yönetimi", "✈️ İzinler", "📅 Toplantı", "📢 Duyurular"
])

# --- TAB 1: PERSONEL ---
with tab_personel:
    if not df_personel.empty:
        isim_col = next((c for c in ['kullanici_adi', 'ad_soyad'] if c in df_personel.columns), df_personel.columns[0])
        st.dataframe(df_personel[[isim_col, 'check_in']], use_container_width=True, hide_index=True)
    else:
        st.info("İçeride kimse yok.")

# --- TAB 2: GÖREVLER (GÜNCELLEME ÖZELLİKLİ) ---
with tab_gorev:
    st.subheader("📝 Görev Listesi ve Durum Değiştirme")
    
    if not df_gorevler.empty:
        for i, row in df_gorevler.iterrows():
            # Veri Güvenliği (Sütun isimlerini tahmin etme)
            g_id = row.get('id')
            g_ad = row.get('gorev_adi', row.get('baslik', 'Görev'))
            g_kisi = row.get('atanan_kisi', row.get('sorumlu', 'Sorumlu Yok'))
            g_durum = row.get('durum', 'Beklemede')
            g_tarih = row.get('baslama_tarihi', '-')

            # Görev Kartı
            with st.expander(f"📌 {g_ad} (Atanan: {g_kisi})"):
                c1, c2 = st.columns([2, 1])
                
                with c1:
                    st.write(f"**Başlama:** {g_tarih}")
                    st.write(f"**Mevcut Durum:** `{g_durum}`")
                    st.progress(100 if g_durum in ['Tamamlandı', 'Bitti'] else 50 if g_durum == 'Devam Ediyor' else 20)

                with c2:
                    st.write("**Yeni Durum:**")
                    yeni_durum_g = st.selectbox(
                        "Seçiniz:",
                        ["Beklemede", "Devam Ediyor", "Tamamlandı", "İptal"],
                        key=f"tsk_sel_{g_id if g_id else i}",
                        index=0
                    )
                    
                    if st.button("Görevi Kaydet", key=f"tsk_btn_{g_id if g_id else i}", type="primary"):
                        if g_id:
                            sql = "UPDATE gorevler SET durum = %s WHERE id = %s"
                            res = run_update(sql, (yeni_durum_g, g_id))
                            if res:
                                st.success("Görev güncellendi! Yenileniyor...")
                                time.sleep(0.5)
                                st.rerun()
                        else:
                            st.error("Bu görevin ID bilgisi veritabanında bulunamadı.")
    else:
        st.success("Tüm görevler tamamlanmış!")

# --- TAB 3: ARIZALAR (GÜNCELLEME ÖZELLİKLİ) ---
with tab_ariza:
    st.subheader("🚨 Arıza Bildirimleri ve İşlemler")
    
    if not df_arizalar.empty:
        for i, row in df_arizalar.iterrows():
            a_id = row.get('id')
            a_baslik = row.get('ariza_baslik', row.get('baslik', 'Arıza'))
            a_gonderen = row.get('gonderen_kullanici_adi', 'Bilinmiyor')
            a_durum = row.get('durum', 'Belirsiz')
            
            # Tarih
            t_col = next((c for c in ['bildirim_tarihi', 'tarih'] if c in row.index), None)
            t_str = row[t_col].strftime('%d-%m %H:%M') if t_col and pd.notnull(row[t_col]) else "Tarih Yok"

            # Arıza Kartı
            with st.expander(f"⚠️ #{a_id} - {a_baslik} ({a_gonderen})"):
                c1, c2 = st.columns([2, 1])
                
                with c1:
                    st.markdown(f"**📅 Tarih:** {t_str}")
                    st.markdown(f"**👤 Bildiren:** {a_gonderen}")
                    st.info(f"Durum: {a_durum}")
                    # Açıklama varsa göster
                    aciklama = row.get('aciklama', row.get('detay'))
                    if aciklama: st.write(f"**Detay:** {aciklama}")
                
                with c2:
                    st.write("**Durumu Değiştir:**")
                    yeni_durum_a = st.selectbox(
                        "Seçiniz:",
                        ["Beklemede", "İşlemde", "Parça Bekleniyor", "Cozuldu", "İptal"],
                        key=f"arz_sel_{a_id if a_id else i}"
                    )
                    
                    if st.button("Arızayı Kaydet", key=f"arz_btn_{a_id if a_id else i}", type="primary"):
                        if a_id:
                            sql = "UPDATE ariza_bildirimleri SET durum = %s WHERE id = %s"
                            res = run_update(sql, (yeni_durum_a, a_id))
                            if res:
                                st.success("Arıza güncellendi! Yenileniyor...")
                                time.sleep(0.5)
                                st.rerun()
                        else:
                            st.error("ID hatası.")
    else:
        st.success("Aktif arıza yok.")

# --- DİĞER SEKMELER ---
with tab_izin:
    if not df_izinler.empty:
        st.dataframe(df_izinler, use_container_width=True, hide_index=True)
    else:
        st.info("İzin talebi yok.")

with tab_toplanti:
    if not df_toplanti.empty:
        st.dataframe(df_toplanti, use_container_width=True, hide_index=True)
    else:
        st.info("Toplantı yok.")

with tab_duyuru:
    if not df_duyuru.empty:
        for i, row in df_duyuru.iterrows():
            d_baslik = row.get('baslik', 'Duyuru')
            d_icerik = row.get('icerik', '')
            d_tarih = row.get('olusturma_tarihi')
            
            baslik_str = f"📢 {d_baslik}"
            if d_tarih: baslik_str += f" ({d_tarih})"
            
            with st.expander(baslik_str):
                st.write(d_icerik)
    else:
        st.info("Duyuru yok.")
