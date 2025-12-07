import streamlit as st
import pymysql
import pandas as pd
import time

# -------------------------------------------
# 1. AYARLAR VE BAĞLANTI (GÜVENLİ VERSİYON)
# -------------------------------------------
st.set_page_config(page_title="İş Takip Raporu", page_icon="📊", layout="centered")

# Veritabanı bağlantısını önbelleğe alıyoruz
@st.cache_resource
def get_connection():
    # Şifreleri 'st.secrets' içinden çekiyoruz. Kodda şifre yok!
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

# ... Kodun geri kalanı (Ekran tasarımı) aynı kalacak ...