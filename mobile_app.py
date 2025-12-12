import streamlit as st
import pymysql
import pandas as pd
import time
from datetime import datetime, timedelta
import pytz

# ---------------------------------------------------------
# 1. AYARLAR & SAYFA YAPILANDIRMASI
# ---------------------------------------------------------
st.set_page_config(
    page_title="Merkez Mobil Takip",
    page_icon="📱",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ---------------------------------------------------------
# 2. ULTRA-MODERN MOBİL CSS
# ---------------------------------------------------------
st.markdown("""
    <style>
    /* GENEL APP STİLİ */
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;700&display=swap');
    
    .stApp { 
        background-color: #0f1116 !important; 
        font-family: 'Roboto', sans-serif;
    }
    
    /* GEREKSİZLERİ GİZLE */
    header, footer, .stAppDeployButton, [data-testid="stStatusWidget"] { display: none !important; }
    
    /* ÜST SABİT BAR (HEADER) */
    .mobile-header {
        position: fixed; top: 0; left: 0; width: 100%;
        background: rgba(15, 17, 22, 0.95);
        backdrop-filter: blur(10px);
        border-bottom: 1px solid #333;
        z-index: 9999;
        padding: 10px 20px;
        display: flex; justify-content: space-between; align-items: center;
        box-shadow: 0 4px 20px rgba(0,0,0,0.4);
    }
    
    .header-title {
        font-size: 1.2rem; font-weight: 700;
        background: linear-gradient(90deg, #FF4B4B, #FF914D);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    }

    /* İÇERİK BOŞLUĞU (Header altı) */
    .block-container { padding-top: 5rem !important; padding-bottom: 3rem !important; }

    /* KPI KARTLARI (İstatistikler) */
    div[data-testid="metric-container"] {
        background: #1e212b;
        border: 1px solid #333;
        border-radius: 12px;
        padding: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.2);
        transition: transform 0.2s;
    }
    div[data-testid="metric-container"]:active { transform: scale(0.98); }
    label[data-testid="stMetricLabel"] { color: #aaa !important; font-size: 0.8rem !important; }
    div[data-testid="stMetricValue"] { color: #fff !important; font-size: 1.5rem !important; }

    /* MOBİL KART TASARIMI (Tablolar yerine) */
    .data-card {
        background: #1A1D24;
        border-left: 4px solid #FF4B4B;
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 12px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.2);
        position: relative;
    }
    
    .data-card.green { border-left-color: #00D26A; } /* Çalışıyor / Tamamlandı */
    .data-card.yellow { border-left-color: #F2C94C; } /* Beklemede */
    .data-card.blue { border-left-color: #2D9CDB; } /* İşlemde */
    
    .card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px; }
    .card-title { font-weight: bold; color: white; font-size: 1rem; }
    .card-sub { font-size: 0.8rem; color: #888; }
    .card-badge { 
        padding: 3px 8px; border-radius: 12px; 
        font-size: 0.7rem; font-weight: bold; 
        background: rgba(255,255,255,0.1); color: #fff;
    }

    /* TAB TASARIMI */
    .stTabs [data-baseweb="tab-list"] { gap: 5px; overflow-x: auto; white-space: nowrap; }
    .stTabs [data-baseweb="tab"] {
        height: 40px; border-radius: 20px; background-color: #262730; border: none; color: white; padding: 0 15px;
    }
    .stTabs [aria-selected="true"] { background-color: #FF4B4B !important; color: white !important; }

    /* EXPANDER (AÇILIR KUTU) MODİFİYESİ */
    .streamlit-expanderHeader { background-color: #262730 !important; border-radius: 8px !important; }
    div[data-testid="stExpander"] { border: none !important; background-color: transparent !important; }

    /* İMZA */
    .designer-credit {
        text-align: center; font-family: 'Brush Script MT', cursive; color: #555; margin-top: 30px; font-size: 1rem; opacity: 0.6;
    }
    </style>
    
    <div class="mobile-header">
        <div class="header-title">🏢 Merkez İş Takip</div>
        <div style="font-size:0.8rem; color:#aaa;">Oktay Design</div>
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
    except Exception:
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
# 4. YARDIMCI HTML KART FONKSİYONU
# ---------------------------------------------------------
def render_mobile_card(title, subtitle, badge_text, color_class="blue", extra_info=None):
    html = f"""
    <div class="data-card {color_class}">
        <div class="card-header">
            <span class="card-title">{title}</span>
            <span class="card-badge">{badge_text}</span>
        </div>
        <div class="card-sub">{subtitle}</div>
    """
    if extra_info:
        html += f"<div style='margin-top:5px; font-size:0.85rem; color:#ccc;'>{extra_info}</div>"
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)

# ---------------------------------------------------------
# 5. VERİ ÇEKME VE HAZIRLIK
# ---------------------------------------------------------
# Zaman
tr_timezone = pytz.timezone('Europe/Istanbul') # Veya 'Europe/Copenhagen'
simdi = datetime.now(tr_timezone)
saat_str = simdi.strftime('%H:%M')
tarih_str = simdi.strftime('%d %B %Y')

# Veriler
raw_personel = run_query("SELECT * FROM zaman_kayitlari ORDER BY id DESC LIMIT 200")
df_tum = pd.DataFrame(raw_personel)
df_aktif = pd.DataFrame()

if not df_tum.empty:
    c_in = next((c for c in ['check_in', 'giris'] if c in df_tum.columns), None)
    c_out = next((c for c in ['check_out', 'cikis'] if c in df_tum.columns), None)
    if c_in: df_tum[c_in] = pd.to_datetime(df_tum[c_in], errors='coerce') # Saat dilimi ayarını buraya ekleyebilirsiniz
    if c_out:
        temp = pd.to_datetime(df_tum[c_out], errors='coerce')
        df_tum[c_out] = temp
        df_aktif = df_tum[temp.isna()].copy()
    else:
        df_aktif = df_tum.copy()

df_gorev = pd.DataFrame(run_query("SELECT * FROM gorevler WHERE durum NOT IN ('Tamamlandı', 'Bitti')"))
df_ariza = pd.DataFrame(run_query("SELECT * FROM ariza_bildirimleri WHERE durum NOT IN ('Cozuldu', 'Çözüldü', 'İptal') ORDER BY id DESC"))
df_izin = pd.DataFrame(run_query("SELECT * FROM tatil_talepleri WHERE onay_durumu = 'Beklemede'"))
df_duyuru = pd.DataFrame(run_query("SELECT * FROM duyurular ORDER BY id DESC LIMIT 5"))

# ---------------------------------------------------------
# 6. ARAYÜZ (UI)
# ---------------------------------------------------------

# --- KPI ALANI (MOBİL UYUMLU) ---
c1, c2 = st.columns(2)
with c1:
    st.metric("👥 Aktif", len(df_aktif))
    st.metric("🚨 Arıza", len(df_ariza))
with c2:
    st.metric("📋 Görev", len(df_gorev))
    st.metric("✈️ İzin", len(df_izin))

# Otomatik Yenileme ve Saat
st.caption(f"🕒 Son Güncelleme: {saat_str} | {tarih_str}")
if st.button("🔄 Verileri Yenile", use_container_width=True, type="primary"):
    st.cache_data.clear()
    st.rerun()

# --- ANA MENÜ (SEKMELER) ---
tabs = st.tabs(["👥 Ekip", "📝 İşler", "🛠️ Arıza", "📅 Diğer"])

# --- TAB 1: PERSONEL ---
with tabs[0]:
    st.markdown("### 🟢 Şu An Çalışanlar")
    if not df_aktif.empty:
        for _, row in df_aktif.iterrows():
            ad = row.get('kullanici_adi', row.get('ad_soyad', 'Personel'))
            giris_zamani = row.get('check_in', row.get('giris'))
            giris_str = giris_zamani.strftime('%H:%M') if pd.notnull(giris_zamani) else "--:--"
            
            render_mobile_card(
                title=ad, 
                subtitle=f"Giriş Saati: {giris_str}", 
                badge_text="OFİSTE", 
                color_class="green"
            )
    else:
        st.info("Kimse ofiste görünmüyor.")

    with st.expander("🕰️ Son Hareketler (Log)"):
        if not df_tum.empty:
            # Sadece son 10 hareketi göster (Mobil hız için)
            for _, row in df_tum.head(10).iterrows():
                ad = row.get('kullanici_adi', row.get('ad_soyad'))
                g_saat = row.get('check_in', row.get('giris'))
                c_saat = row.get('check_out', row.get('cikis'))
                
                g_fmt = g_saat.strftime('%d.%m %H:%M') if pd.notnull(g_saat) else "-"
                c_fmt = c_saat.strftime('%H:%M') if pd.notnull(c_saat) else "..."
                
                # Çıkış yapmışsa gri, yapmamışsa yeşil
                renk = "green" if pd.isnull(c_saat) else "yellow"
                durum = "İçeride" if pd.isnull(c_saat) else "Çıktı"
                
                render_mobile_card(ad, f"Giriş: {g_fmt} | Çıkış: {c_fmt}", durum, renk)

# --- TAB 2: GÖREVLER ---
with tabs[1]:
    st.markdown("### 📋 Açık Görevler")
    if not df_gorev.empty:
        for i, r in df_gorev.iterrows():
            gid = r.get('id')
            gad = r.get('gorev_adi', 'Görev')
            gk = r.get('atanan_kisi', '-')
            gd = r.get('durum', 'Beklemede')
            g_aciklama = r.get('aciklama', r.get('gorev_aciklamasi', ''))

            # Duruma göre renk
            renk = "blue"
            if "Devam" in gd: renk = "yellow"
            
            # Kart Görünümü (HTML)
            render_mobile_card(gad, f"Atanan: {gk}", gd, renk, extra_info=g_aciklama)
            
            # Aksiyon Butonları (Expander içinde gizli)
            with st.expander(f"✏️ {gad} Düzenle"):
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if st.button("Devam Ediyor", key=f"devam_{gid}"):
                        run_update("UPDATE gorevler SET durum='Devam Ediyor' WHERE id=%s", (gid,))
                        st.success("Güncellendi")
                        time.sleep(0.5); st.rerun()
                with col_btn2:
                    if st.button("✅ Tamamla", key=f"bitir_{gid}", type="primary"):
                        run_update("UPDATE gorevler SET durum='Tamamlandı' WHERE id=%s", (gid,))
                        st.success("Bitti!"); time.sleep(0.5); st.rerun()
    else:
        st.success("Tüm görevler tamamlandı! 🎉")

# --- TAB 3: ARIZALAR ---
with tabs[2]:
    st.markdown("### ⚠️ Arıza Bildirimleri")
    if not df_ariza.empty:
        for i, r in df_ariza.iterrows():
            aid = r.get('id')
            baslik = r.get('ariza_baslik', 'Arıza')
            kisi = r.get('gonderen_kullanici_adi', '-')
            durum = r.get('durum', '')
            
            render_mobile_card(f"#{aid} {baslik}", f"Bildiren: {kisi}", durum.upper(), "data-card", extra_info=r.get('aciklama',''))
            
            with st.expander("🛠️ Durumu Değiştir"):
                new_status = st.selectbox("Durum Seç:", ["İşlemde", "Parça Bekleniyor", "Cozuldu"], key=f"ariza_sel_{aid}")
                if st.button("Kaydet", key=f"ariza_btn_{aid}"):
                    run_update("UPDATE ariza_bildirimleri SET durum=%s WHERE id=%s", (new_status, aid))
                    st.success("Kaydedildi"); time.sleep(0.5); st.rerun()
    else:
        st.success("Hiç arıza yok! Sistem stabil. ✅")

# --- TAB 4: DİĞER (İZİN & DUYURU) ---
with tabs[3]:
    st.info("📢 Duyurular")
    if not df_duyuru.empty:
        for i, r in df_duyuru.iterrows():
            st.warning(f"**{r.get('baslik')}**: {r.get('icerik')}")
    
    st.markdown("---")
    st.info("✈️ İzin Talepleri")
    if not df_izin.empty:
        for i, r in df_izin.iterrows():
             render_mobile_card(r.get('ad_soyad'), f"{r.get('baslangic')} - {r.get('bitis')}", r.get('tur', 'Yıllık'), "yellow")
    else:
        st.write("Bekleyen izin talebi yok.")

# İmza
st.markdown("<div class='designer-credit'>Design by Oktay • 2025</div>", unsafe_allow_html=True)
