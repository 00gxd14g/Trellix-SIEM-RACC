# RACC: Trellix SIEM Kural ve Alarm Yönetim Merkezi

RACC (Rule & Alarm Control Center), Trellix SIEM (eski adıyla McAfee ESM) yöneticileri ve MSSP analistleri için geliştirilmiş, kural ve alarm yönetimini kolaylaştıran modern bir web arayüzüdür.

Bu proje, karmaşık XML düzenlemeleriyle uğraşmadan, görsel bir arayüz üzerinden korelasyon kuralları ve alarmlar oluşturmanızı, doğrulamanızı ve yönetmenizi sağlar.

## 🚀 Temel Özellikler

### 1. Görsel Kural Analizi ve Akış Diyagramları
Trellix kuralları karmaşık mantıksal yapılara sahiptir. RACC, bu kuralları anlaşılır akış diyagramlarına dönüştürerek:
- Karmaşık kural mantığını (AND, OR, NOT ilişkileri) görselleştirir.
- Kural ve alarm arasındaki ilişkileri net bir şekilde gösterir.
- Analistlerin mevcut kuralları hızlıca anlamasını ve hata ayıklamasını sağlar.

### 2. Çoklu Müşteri Yönetimi (Multi-Customer)
MSSP'ler için tasarlanmış yapı sayesinde:
- Birden fazla müşterinin kural ve alarmlarını tek bir arayüzden yönetebilirsiniz.
- Müşteriler arasında mantıksal ayrım (Logical Separation) sağlar.
- Müşteri bazlı istatistikler ve raporlar sunar.

### 3. Toplu İşlemler ve Verimlilik
- **Bulk Import/Export:** Kuralları ve alarmları toplu olarak içe/dışa aktarın.
- **Gelişmiş Arama:** Binlerce kural arasında anında arama ve filtreleme.
- **Klonlama:** Mevcut bir kuralı veya alarmı tek tıkla kopyalayıp başka bir müşteri için uyarlayın.

### 4. Analiz ve Raporlama
- Kural ve alarm ilişkilerini görselleştiren akış diyagramları.
- Müşteri bazlı kural/alarm dağılım grafikleri.
- Sistem logları ve audit kayıtları.

## 🛠 Teknik Altyapı

RACC, modern, güvenli ve performanslı teknolojiler üzerine inşa edilmiştir:

- **Backend:** Python Flask (REST API)
- **Frontend:** React + Vite + Tailwind CSS (Modern UI)
- **Veritabanı:** SQLite (Varsayılan) / PostgreSQL (Opsiyonel)
- **Güvenlik:** 
  - CSRF Koruması
  - Secure Headers (Helmet)
  - Input Validation
  - Rate Limiting

## 📦 Kurulum ve Dağıtım

### Seçenek 1: Docker ile Hızlı Kurulum (Önerilen)

Tüm sistemi (Backend, Frontend ve Veritabanı) tek komutla ayağa kaldırabilirsiniz.

1. **Gereksinimler:** Docker ve Docker Compose yüklü olmalıdır.

2. **Güvenlik Ayarı (ÖNEMLİ):**
   Uygulama güvenliği için güçlü bir `SECRET_KEY` oluşturun:
   
   ```bash
   # Güçlü bir anahtar üretin
   python3 -c "import secrets; print(secrets.token_hex(32))"
   ```
   
   Bu anahtarı `.env` dosyasına kaydedin veya environment variable olarak tanımlayın:
   ```bash
   export SECRET_KEY=<urettiginiz-anahtar>
   ```

3. **Çalıştırma:**
   ```bash
   # Cache kullanmadan temiz kurulum
   docker-compose build --no-cache --pull
   
   # Servisleri başlatın
   docker-compose up -d
   
   # Logları izleyin
   docker-compose logs -f backend
   ```

4. **Erişim:**
   - **Arayüz:** `http://localhost:3000`
   - **API:** `http://localhost:5000`

### Seçenek 2: Manuel Kurulum

#### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Production modunda başlatma
export FLASK_CONFIG=production  # Windows: $env:FLASK_CONFIG="production"
python production_server.py
```

#### Frontend
```bash
cd frontend
npm install
npm run build
# 'dist' klasöründeki dosyaları bir web sunucusu (Nginx vb.) ile sunun.
```

## ⚙️ Konfigürasyon (Environment Variables)

Uygulama ayarlarını değiştirmek için aşağıdaki ortam değişkenlerini kullanabilirsiniz:

| Değişken | Açıklama | Varsayılan |
|----------|----------|------------|
| `SECRET_KEY` | **Zorunlu.** Session güvenliği için gizli anahtar. | (Yok - Ayarlanmalı) |
| `FLASK_CONFIG` | Çalışma modu (`development`, `production`). | `development` |
| `DATABASE_URL` | Veritabanı bağlantı adresi. | `sqlite:///backend/database/app.db` |
| `ALLOWED_ORIGINS` | CORS için izin verilen domainler. | `http://localhost:3000` |
| `LOG_LEVEL` | Log detay seviyesi (`DEBUG`, `INFO`, `WARNING`). | `DEBUG` |

## 📂 Proje Yapısı

```
Trellix-RACC/
├── backend/                # Python Flask API
│   ├── models/            # Veritabanı modelleri
│   ├── routes/            # API endpoint'leri
│   ├── utils/             # Yardımcı araçlar (XML parser, Auth vb.)
│   └── config.py          # Konfigürasyon dosyası
├── frontend/               # React UI
│   ├── src/
│   │   ├── components/    # UI bileşenleri ve sayfalar
│   │   └── context/       # State yönetimi
│   └── vite.config.js     # Build ayarları
└── docker-compose.yml      # Docker konfigürasyonu
```

---
*Geliştirici Notu: Bu proje, güvenlik operasyonlarını merkezileştirmek ve manuel hata riskini azaltmak amacıyla tasarlanmıştır.*
