import csv
import os
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import warnings
from bs4 import XMLParsedAsHTMLWarning

def main():
    # BeautifulSoup Uyarılarını Gizleme
    warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

    url = "https://www.tcmb.gov.tr/kurlar/today.xml"
    print("TCMB'den veriler çekiliyor...")
    
    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Veri çekme sırasında hata oluştu: {e}")
        return

    soup = BeautifulSoup(response.content, "html.parser")
    currencies = soup.find_all("currency")
    
    istenen_kurlar = ["USD", "EUR", "GBP", "CHF", "KWD"]
    
    csv_dosya_adi = "data.csv"
    dosya_var = os.path.exists(csv_dosya_adi)
    sifirdan_olustur = not dosya_var
    
    # Geçmiş verileri okuyup son kur tutarlarını ayıklıyoruz
    son_degerler = {}
    
    if dosya_var:
        with open(csv_dosya_adi, mode="r", encoding="utf-8") as file:
            reader = csv.reader(file)
            headers = next(reader, [])
            
            # Eğer önceki tabloda "Tarih" sütunu yoksa yapıyı baştan oluşturmamız gerekecek (eski formatı düzeltmek için)
            if headers and "Tarih" not in headers:
                sifirdan_olustur = True
                
            # Sütun sırasını bul (Eski ve yeni tabloda yerleri farklı olabilir)
            kod_idx = headers.index("Para Birimi Kodu") if "Para Birimi Kodu" in headers else (0 if sifirdan_olustur else 1)
            alis_idx = headers.index("Döviz Alış") if "Döviz Alış" in headers else (2 if sifirdan_olustur else 3)
            
            for row in reader:
                if len(row) > max(kod_idx, alis_idx):
                    kod = row[kod_idx]
                    alis = row[alis_idx]
                    try:
                        # Tablodaki en son değeri sözlükte günceller (en alttaki satır son kayıtlı gündür)
                        son_degerler[kod] = float(alis)
                    except ValueError:
                        pass
                        
    # O anki tarih
    bugun = datetime.now().strftime("%Y-%m-%d")
    
    csv_veri = []

    for currency in currencies:
        kod = currency.get("kod")
        
        # Filtreleme
        if kod not in istenen_kurlar:
            continue
            
        isim_tag = currency.find("isim")
        alis_tag = currency.find("forexbuying")
        satis_tag = currency.find("forexselling")
        
        isim = isim_tag.text if isim_tag else ""
        alis = alis_tag.text if alis_tag else ""
        satis = satis_tag.text if satis_tag else ""
        
        degisim_durumu = "İlk Kayıt"
        
        if kod and alis:
            try:
                guncel_alis_float = float(alis)
                # Geçmiş günün verisi sözlükte kayıtlıysa yüzdelik oran hesaplıyoruz:
                if kod in son_degerler:
                    eski_alis_float = son_degerler[kod]
                    
                    if eski_alis_float > 0:
                        oransal_degisim = ((guncel_alis_float - eski_alis_float) / eski_alis_float) * 100
                        
                        if oransal_degisim > 0:
                            degisim_durumu = f"+%{oransal_degisim:.2f}"
                        elif oransal_degisim < 0:
                            degisim_durumu = f"-%{abs(oransal_degisim):.2f}"
                        else:
                            degisim_durumu = "%0.00"
                    else:
                        degisim_durumu = "%0.00"
            except ValueError:
                pass
                
            # Alt satıra yazılacak yeni format
            csv_veri.append([bugun, kod, isim, alis, satis, degisim_durumu])
            
    # Eğer dosya hiç yoksa veya eski formattaysa (Tarih sütunu eksikse) baştan yaz ("w")
    # Dosya zaten yeni formattaysa altına satır ekle/append ("a")
    dosya_modu = "w" if sifirdan_olustur else "a"
    
    try:
        with open(csv_dosya_adi, mode=dosya_modu, newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            # Eğer baştan oluşturuyorsak en tepeye başlıkları da at
            if sifirdan_olustur:
                writer.writerow(["Tarih", "Para Birimi Kodu", "İsim", "Döviz Alış", "Döviz Satış", "Değişim Yönü"])
            
            writer.writerows(csv_veri)
            
        if sifirdan_olustur:
            print(f"Başarılı! Tablo ('{csv_dosya_adi}') yeni şablon ile oluşturuldu.")
        else:
            print(f"Başarılı! Günün kurları dosyaya yeni bir satır olarak eklendi.")
            
    except Exception as e:
        print(f"Dosyaya yazarken hata oluştu: {e}")

if __name__ == "__main__":
    main()
