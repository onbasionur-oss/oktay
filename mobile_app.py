import streamlit as st
import pandas as pd
import pymysql
from datetime import datetime
import pytz  # Saat dilimi kütüphanesi

# ==========================================
# AYARLAR: VERİTABANI BİLGİLERİNİ GİRİNİZ
# ==========================================
DB_CONFIG = {
    'host': 'localhost',          # Sunucu IP adresi veya domain
    'user': 'root',               # Veritabanı kullanıcı adı
    'password': '',               # Veritabanı şifresi
    'database': 'test_db',        # Veritabanı adı
    'port': 3306,
    'cursorclass': pymysql.cursors.DictCursor
}

# Danimarka Saat Dilimi
TIMEZONE = 'Europe/Copenhagen'

# ==========================================
# YARDIMCI FONKSİYONLAR
# ==========================================

def get_db_connection():
    """Veritabanına bağlanır."""
    try:
        connection = pymysql.connect(**DB_CONFIG)
        return connection
    except pymysql.MySQLError as e:
        st.error(f"Veritabanı bağlantı hatası: {e}")
        return None

def get_current_time_denmark():
    """Anlık saati Danimarka dilimine göre döndürür."""
    denmark_zone = pytz.timezone(TIMEZONE)
    return datetime.now(denmark_zone)

def add_log(user, action):
    """Veritabanına log kaydı atar."""
    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor() as cursor:
                # Danimarka saatini al
                now_dk = get_current_time_denmark()
                
                # SQL Sorgusu (Tablo adı: is_takip_loglari)
                sql = """
                INSERT INTO is_takip_loglari (kullanici_adi, islem_tipi, islem_zamani)
                VALUES (%s, %s, %s)
                """
                cursor.execute(sql, (user, action, now_dk))
            conn.commit()
            return now_dk
        except Exception as e:
            st.error(f"Kayıt sırasında hata: {e}")
            return None
        finally:
            conn.close()
    return None

def get_last_logs():
    """Son 10 kaydı listeler."""
    conn = get_db_connection()
    if conn:
        try:
            sql = "SELECT * FROM is_takip_loglari ORDER BY islem_zamani DESC LIMIT 10"
            df = pd.read_sql(sql, conn)
            return df
        except Exception as e:
            st.error(f"Veri çekme hatası: {e}")
            return pd.DataFrame() # Boş döndür
        finally:
            conn.close()
    return pd.DataFrame()

# ==========================================
# ANA UYGULAMA (UI)
# ==========================================

def main():
    st.set_page_config(page_title="İş Takip", page_icon="🇩🇰")
    
    st.title("🇩🇰 Mobil İş Takip")
    
    # Anlık Saati Göster (Kontrol Amaçlı)
    simdi = get_current_time_denmark()
    st.caption(f"Sunucu Saati (Danimarka): {simdi.strftime('%d.%m.%Y %H:%M:%S')}")

    st.divider()

    # Kullanıcı Girişi
    kullanici = st.text_input("Adınız Soyadınız:", placeholder="Örn: Ahmet Yılmaz")

    # Butonlar (Yan Yana)
    col1, col2 = st.columns(2)

    with col1:
        if st.button("🟢 İşe Başla", use_container_width=True):
            if not kullanici:
                st.warning("Lütfen önce adınızı girin!")
            else:
                kayit_zamani = add_log(kullanici, "Giris")
                if kayit_zamani:
                    saat_str = kayit_zamani.strftime('%H:%M')
                    st.success(f"Başladınız! Saat: {saat_str}")

    with col2:
        if st.button("🔴 Paydos", use_container_width=True):
            if not kullanici:
                st.warning("Lütfen önce adınızı girin!")
            else:
                kayit_zamani = add_log(kullanici, "Cikis")
                if kayit_zamani:
                    saat_str = kayit_zamani.strftime('%H:%M')
                    st.info(f"Çıkış yapıldı. Saat: {saat_str}")

    st.divider()

    # Geçmiş Kayıtları Göster
    st.subheader("📋 Son Hareketler")
    if st.checkbox("Listeyi Göster/Yenile"):
        df = get_last_logs()
        if not df.empty:
            # Tabloyu daha şık göstermek için sütun adlarını düzenleyelim
            df = df.rename(columns={
                'kullanici_adi': 'Personel',
                'islem_tipi': 'Durum',
                'islem_zamani': 'Zaman'
            })
            st.dataframe(df, use_container_width=True)
        else:
            st.info("Henüz kayıt bulunmuyor.")

if __name__ == "__main__":
    main()
