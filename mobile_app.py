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

# --- TASARIM İMZASI ---
st.markdown("""
    <style>
    @keyframes gentle-pulse-glow {
        0% { transform: scale(1); opacity: 0.9; }
        50% { transform: scale(1.02); opacity: 1; }
        100% { transform: scale(1); opacity: 0.9; }
    }
    .fixed-design-credit {
        position: fixed; top: 10px; left: 20px;
        font-family: 'Brush Script MT', cursive; font-size: 24px;
        background: linear-gradient(to right, #FF4B4B, #FF914D);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        font-weight: bold; z-index: 9999; animation: gentle-pulse-glow 3s infinite;
    }
    .stButton button { width: 100%; border-radius: 8px; }
    .metric-card { background-color: #f0f2f6; padding: 15px; border-radius: 10px; text-align: center; }
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
        st.error(f"⚠️ Bağlantı Hatası: {e}")
        return None

# VERİ OKUMA
def run_query(query, params=None):
    conn = get_connection()
    if not conn: return []
    try:
        conn.ping(reconnect=True)
        with conn.cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchall()
    except Exception as e:
        st.warning(f"Sorgu uyarısı: {e}") # Hata yerine uyarı verelim ki sayfa çökmesin
        return []

# VERİ GÜNCELLEME (UPDATE)
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
st.title("🏢 Merkez Genel Durum Raporu")

# Danimarka Saati
dk_saat = datetime.now(pytz.timezone('Europe/Copenhagen')).strftime('%d-%m-%Y %H:%M:%S')

col1, col2 = st.columns([3, 1])
col1.caption(f"📅 Rapor Saati (DK): {dk_saat}")
if col2.button("🔄 Yenile", type="primary"):
    st.cache_data.clear()
    st.rerun()

# --- VERİLERİ GÜVENLİ ÇEKME ---

# 1. Personel
df_personel = pd.DataFrame(run_query("SELECT * FROM zaman_kayitlari WHERE check_out IS NULL"))
if not df_personel.empty and 'check_in' in df_personel.columns:
    df_personel['check_in'] = pd.to_datetime(df_personel['check_in'], errors='coerce') + timedelta(hours=1)

# 2. Görevler
df_gorevler = pd.DataFrame(run_query("SELECT * FROM gorevler WHERE durum NOT IN ('Tamamlandı', 'Tamamlandi')"))

# 3. Arızalar (Hata vermemesi için SELECT * kullanıyoruz, sütunları Python'da seçeceğiz)
df_arizalar = pd.DataFrame(run_query("SELECT * FROM ariza_bildirimleri WHERE durum NOT IN ('Cozuldu', 'Çözüldü', 'İptal') ORDER BY id DESC"))
if not df_arizalar.empty:
    # Tarih sütununu bulmaya çalış (farklı isimler olabilir)
    date_col = next((col for col in ['bildirim_tarihi', 'tarih', 'created_at'] if col in df_arizalar.columns), None)
    if date_col:
        df_arizalar[date_col] = pd.to_datetime(df_arizalar[date_col], errors='coerce')

# 4. İzinler
df_izinler = pd.DataFrame(run_query("SELECT * FROM tatil_talepleri WHERE onay_durumu = 'Beklemede'"))

# 5. Toplantılar
df_toplanti = pd.DataFrame(run_query("SELECT * FROM rezervasyonlar WHERE baslangic_zamani >= CURDATE()"))

# 6. Duyurular
df_duyuru = pd.DataFrame(run_query("SELECT * FROM duyurular ORDER BY id DESC LIMIT 5"))

# --- KPI ÖZET ---
k1, k2, k3, k4 = st.columns(4)
k1.metric("👥 Personel", len(df_personel))
k2.metric("📋 Görev", len(df_gorevler))
k3.metric("⚠️ Arıza", len(df_arizalar), delta_color="inverse")
k4.metric("✈️ İzin", len(df_izinler))

st.markdown("---")

# ---------------------------------------------------------
# 4. DETAYLI SEKMELER
# ---------------------------------------------------------
tab_personel, tab_gorev, tab_ariza, tab_izin, tab_toplanti, tab_duyuru = st.tabs([
    "👷‍♂️ Personel", "📝 Görevler", "🛠️ Arıza İşlemleri", "✈️ İzinler", "📅 Toplantı", "📢 Duyurular"
])

# TAB 1: Personel
with tab_personel:
    if not df_personel.empty:
        # Sütun adı eşleştirme (kullanici_adi yoksa ad_soyad kullan vb.)
        isim_col = next((c for c in ['kullanici_adi', 'ad_soyad', 'personel'] if c in df_personel.columns), 'Bilinmiyor')
        st.dataframe(df_personel[[isim_col, 'check_in']], use_container_width=True, hide_index=True)
    else:
        st.info("İçeride kimse yok.")

# TAB 2: Görevler
with tab_gorev:
    if not df_gorevler.empty:
        g_ad = next((c for c in ['gorev_adi', 'baslik'] if c in df_gorevler.columns), 'Görev')
        g_kisi = next((c for c in ['atanan_kisi', 'sorumlu'] if c in df_gorevler.columns), 'Sorumlu')
        st.dataframe(df_gorevler[[g_ad, g_kisi, 'durum']], use_container_width=True, hide_index=True)
    else:
        st.success("Tüm görevler tamam.")

# TAB 3: Arızalar (GÜÇLENDİRİLMİŞ MOD)
with tab_ariza:
    st.subheader("🛠️ Arıza Yönetimi")
    
    if not df_arizalar.empty:
        for index, row in df_arizalar.iterrows():
            # Güvenli Veri Çekme (Sütun ismi yanlış olsa bile kod patlamaz)
            r_id = row.get('id', index)
            r_baslik = row.get('ariza_baslik', row.get('baslik', row.get('konu', 'Başlık Yok')))
            r_durum = row.get('durum', 'Belirsiz')
            r_gonderen = row.get('gonderen_kullanici_adi', row.get('kullanici_adi', 'Anonim'))
            
            # Tarihi formatla
            date_col = next((col for col in ['bildirim_tarihi', 'tarih'] if col in row.index), None)
            tarih_str = row[date_col].strftime('%d-%m %H:%M') if date_col and pd.notnull(row[date_col]) else "Tarih Yok"

            # Tasarım Kartı
            with st.expander(f"⚠️ #{r_id} {r_baslik} ({r_gonderen})"):
                c1, c2 = st.columns([2, 1])
                with c1:
                    st.write(f"**Tarih:** {tarih_str}")
                    st.write(f"**Bildiren:** {r_gonderen}")
                    st.info(f"Mevcut Durum: {r_durum}")
                    # Açıklama sütunu varsa göster
                    aciklama = row.get('aciklama', row.get('detay', None))
                    if aciklama:
                        st.write(f"**Detay:** {aciklama}")
                
                with c2:
                    st.write("**Durumu Değiştir:**")
                    yeni_durum = st.selectbox(
                        "Seçiniz:", 
                        ["Beklemede", "İşlemde", "Parça Bekleniyor", "Cozuldu", "İptal"],
                        key=f"sel_{r_id}",
                        index=0
                    )
                    
                    if st.button(f"💾 Kaydet (#{r_id})", key=f"btn_{r_id}", type="primary"):
                        if 'id' in row:
                            sql = "UPDATE ariza_bildirimleri SET durum = %s WHERE id = %s"
                            res = run_update(sql, (yeni_durum, row['id']))
                            if res:
                                st.success("Güncellendi!")
                                time.sleep(0.5)
                                st.rerun()
                            else:
                                st.error("Hata oluştu.")
                        else:
                            st.error("Bu kayıtta ID bulunamadı, güncellenemez.")
    else:
        st.success("Aktif arıza yok.")
        
        # DEBUG: Eğer veritabanı boşsa veya sorgu yanlışsa burası görünür
        with st.expander("Yönetici Kontrolü (Veri Gelmiyor mu?)"):
            st.write("Veritabanından çekilen ham satır sayısı:", len(df_arizalar))
            st.write("Kullanılan Sorgu: SELECT * FROM ariza_bildirimleri ...")
            if st.button("Tüm Filtreleri Kaldır ve Göster"):
                raw = run_query("SELECT * FROM ariza_bildirimleri LIMIT 5")
                st.write(raw)

# TAB 4: İzinler
with tab_izin:
    if not df_izinler.empty:
        st.dataframe(df_izinler, use_container_width=True, hide_index=True)
    else:
        st.info("Talep yok.")

# TAB 5: Toplantı
with tab_toplanti:
    if not df_toplanti.empty:
        st.dataframe(df_toplanti, use_container_width=True, hide_index=True)
    else:
        st.info("Toplantı yok.")

# TAB 6: Duyurular
with tab_duyuru:
    if not df_duyuru.empty:
        for i, row in df_duyuru.iterrows():
            d_tarih = row.get('olusturma_tarihi', row.get('tarih'))
            d_baslik = row.get('baslik', 'Duyuru')
            d_icerik = row.get('icerik', '')
            
            with st.expander(f"📢 {d_baslik}"):
                st.write(d_icerik)
                if pd.notnull(d_tarih): st.caption(f"Tarih: {d_tarih}")
    else:
        st.info("Duyuru yok.")
