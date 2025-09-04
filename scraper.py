import os
import re
import json
import requests
import concurrent.futures
from datetime import datetime

# --- LİG BİLGİLERİ ---
# Süper Lig sezon ID'leri ve karşılık gelen sezon adları
super_lig_sezonlar = {
    32: '2010/2011', 30: '2011/2012', 25: '2012/2013',
    34: '2013/2014', 37: '2014/2015', 24: '2015/2016',
    29: '2016/2017', 23: '2017/2018', 20: '2018/2019',
    994: '2019/2020', 3189: '2020/2021', 3308: '2021/2022',
    3438: '2022/2023', 3580: '2023/2024', 3746: '2024/2025',
    3853: '2025/2026', 
}

# Süper Lig sezonların hafta aralıkları
super_lig_haftalar = {
    32: range(1, 35), 30: range(1, 35), 25: range(1, 35),
    34: range(1, 35), 37: range(1, 35), 24: range(1, 35),
    29: range(1, 35), 23: range(1, 35), 20: range(1, 35),
    994: range(1, 35), 3189: range(1, 43), 3308: range(1, 39),
    3438: range(1, 39), 3580: range(1, 39), 3746: range(1, 39),
    3853: range(1, 39),
}

# Süper Lig sezonların ST kodları (genellikle 0)
super_lig_st = {
    32: 0, 30: 0, 25: 0, 34: 0, 37: 0, 24: 0,
    29: 0, 23: 0, 20: 0, 994: 0, 3189: 0, 3308: 0,
    3438: 0, 3580: 0, 3746: 0, 3853: 0,
}

# --- DİNAMİK VERİ ÇEKME FONKSİYONU ---
def Birinci_Lig_URLlerini_Dinamik_Olarak_Al():
    """
    BeIN SPORTS TFF 1. Lig sayfasından URL'leri çeker
    Returns:
        list: (url, grup_adı) tuple'larından oluşan liste
    """
    sayfa_url = "https://www.beinsports.com.tr/mac-ozetleri-goller/tff-1-lig"
    cekilecek_urler = []
    
    try:
        print("Trendyol 1. Lig verileri çekilmeye başlanıyor...")
        yanıt = requests.get(sayfa_url, timeout=20, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        yanıt.raise_for_status()
        
        # Sayfa kaynakındaki JSON'u bul
        eşleşme = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', yanıt.text, re.DOTALL)
        if not eşleşme:
            print("HATA: 1. Lig için veri betiği bulunamadı")
            return []
            
        veri = json.loads(eşleşme.group(1))
        öne_cikan_veriler = veri.get("props", {}).get("pageProps", {}).get("initialReduxState", {}).get("highlights", {}).get("data", [])
        
        if not öne_cikan_veriler:
            print("HATA: Beklenen veri bulunamadı")
            return []
            
        # İlk lig verisi TFF 1. Lig olmalı
        lig_bilgisi = öne_cikan_veriler[0]
        sezonlar = lig_bilgisi.get("seasons", [])
        
        for sezon in sezonlar:
            sezon_adi = sezon.get("name")
            sezon_id = sezon.get("id")
            raundlar = sezon.get("rounds", [])
            
            grup_basligi = f"Trendyol 1. Lig {sezon_adi}"
            for raund_bilgisi in raundlar:
                raund_numarasi = raund_bilgisi.get("round")
                st_kodu = raund_bilgisi.get("st", 0)
                
                if sezon_id and raund_numarasi:
                    url = f"https://beinsports.com.tr/api/highlights/events?sp=1&o=130&s={sezon_id}&r={raund_numarasi}&st={st_kodu}"
                    cekilecek_urler.append((url, grup_basligi))
                    
        print(f"Başarılı: {len(cekilecek_urler)} adet Trendyol 1. Lig URL'si bulundu")
        return cekilecek_urler
        
    except requests.exceptions.RequestException as e:
        print(f"Ağ hatası: {e}")
        return []
    except (json.JSONDecodeError, KeyError) as e:
        print(f"Veri parse hatası: {e}")
        return []

# --- ANA KOD ---
def Veri_Cek_ve_Parse_et(url_bilgisi):
    """
    Verilen URL'den veriyi çeker ve M3U formatına dönüştürür.
    
    Args:
        url_bilgisi: (url, grup_adı) tuple'ı
        
    Returns:
        list: (grup_adı, satır1, satır2) tuple'larından oluşan liste
    """
    url, grup_adı = url_bilgisi
    try:
        print(f"Veri çekiliyor: {url}")
        yanıt = requests.get(url, timeout=10, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        yanıt.raise_for_status()
        
        veri = yanıt.json()
        etkinlikler = veri.get('Data', {}).get('events', [])
        sonuç = []
        
        for etkinlik in etkinlikler:
            ev_sahibi = etkinlik.get('homeTeam', {}).get('name', 'Ev Sahibi')
            ev_skoru = etkinlik.get('homeTeam', {}).get('matchScore', '-')
            deplasman = etkinlik.get('awayTeam', {}).get('name', 'Deplasman')
            dep_skoru = etkinlik.get('awayTeam', {}).get('matchScore', '-')
            video_url = etkinlik.get('highlightVideoUrl')
            logo = etkinlik.get('highlightThumbnail', '')
            maç_id = etkinlik.get('matchId', '')
            
            if video_url:
                baslik = f"{ev_sahibi} {ev_skoru}-{dep_skoru} {deplasman}"
                satır1 = f'#EXTINF:-1 tvg-id="{maç_id}" tvg-logo="{logo}" group-title="{grup_adı}",{baslik}\n'
                satır2 = f"{video_url}\n"
                sonuç.append((grup_adı, satır1, satır2))
                
        return sonuç
        
    except requests.exceptions.RequestException as e:
        print(f"URL alınırken hata oluştu: {url} - Hata: {e}")
        return []
    except Exception as e:
        print(f"Veri işlenirken bir hata oluştu: {url} - Hata: {e}")
        return []

def Ana_Fonksiyon():
    çıktı_klasörü = 'playsport'
    os.makedirs(çıktı_klasörü, exist_ok=True)
    
    # Tüm lig URL'lerini hazırla
    tüm_çekilecek_urler = []
    
    # Süper Lig URL'leri (manuel)
    for sezon_id, sezon_adi in super_lig_sezonlar.items():
        haftalar = super_lig_haftalar.get(sezon_id, range(1, 39))
        st = super_lig_st.get(sezon_id, 0)
        grup_basligi = f"Süper Lig {sezon_adi}"
        
        for hafta in haftalar:
            url = f"https://beinsports.com.tr/api/highlights/events?sp=1&o=18&s={sezon_id}&r={hafta}&st={st}"
            tüm_çekilecek_urler.append((url, grup_basligi))
    
    # Trendyol 1. Lig URL'leri (dinamik)
    birinci_lig_urleri = Birinci_Lig_URLlerini_Dinamik_Olarak_Al()
    tüm_çekilecek_urler.extend(birinci_lig_urleri)
    
    print(f"\nToplam {len(tüm_çekilecek_urler)} URL üzerinde işlem yapılacak")
    
    # Sonuçları saklamak için sözlük
    gruplanmış_sonuçlar = {}
    
    # Eşzamanlı veri çekme
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as yürütücü:
        gelecekteki_sonuçlar = yürütücü.map(Veri_Cek_ve_Parse_et, tüm_çekilecek_urler)
        
        for sonuç_listesi in gelecekteki_sonuçlar:
            for grup_adı, satır1, satır2 in sonuç_listesi:
                if grup_adı not in gruplanmış_sonuçlar:
                    gruplanmış_sonuçlar[grup_adı] = []
                gruplanmış_sonuçlar[grup_adı].append((satır1, satır2))
    
    # Dosyalara yazma
    tüm_satırlar_birleştirildi = []
    for grup_adı, satırlar in sorted(gruplanmış_sonuçlar.items()):
        güvenli_klasör_adı = grup_adı.replace('/', '-').replace(' ', '_')
        klasör_yolu = os.path.join(çıktı_klasörü, güvenli_klasör_adı)
        os.makedirs(klasör_yolu, exist_ok=True)
        
        dosya_yolu = os.path.join(klasör_yolu, f"{güvenli_klasör_adı}.m3u")
        
        with open(dosya_yolu, 'w', encoding='utf-8') as f:
            f.write("#EXTM3U\n\n")
            for satır1, satır2 in satırlar:
                f.write(satır1)
                f.write(satır2)
                tüm_satırlar_birleştirildi.append((satır1, satır2))
    
    # Master M3U dosyası
    tüm_m3u_yolu = os.path.join(çıktı_klasörü, 'all_leagues.m3u')
    with open(tüm_m3u_yolu, 'w', encoding='utf-8') as f:
        f.write("#EXTM3U\n\n")
        for satır1, satır2 in tüm_satırlar_birleştirildi:
            f.write(satır1)
            f.write(satır2)
    
    print(f"\nİşlem tamamlandı! '{çıktı_klasörü}' klasöründe {len(gruplanmış_sonuçlar)} lig/sezon dosyası oluşturuldu")

if __name__ == "__main__":
    Ana_Fonksiyon()
