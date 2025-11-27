# RACC: MSSP'ler ve Kurumlar İçin Trellix SIEM Yönetiminde Multi-Tenant Devrimi


**Sorun:** Geleneksel yöntemlerde analistler müşteriler arasında geçiş yaparken hata yapmaya açıktır.

**RACC Çözümü:** Proje, veritabanı seviyesinde sıkı bir tenant (müşteri) izolasyonu sağlar. `backend/utils/tenant_auth.py` modülü sayesinde, sisteme giriş yapan bir analist veya müşteri, sadece yetkili olduğu "Customer ID"ye ait kuralları ve alarmları görür. Bu, veri sızıntısı riskini mimari düzeyde engeller.

### 2. Tek Arayüzden Çoklu Yönetim

Danışmanlar için onlarca farklı ESM (Enterprise Security Manager) arayüzüne bağlanmak büyük zaman kaybıdır.

RACC, tüm müşterilerinizi tek bir dashboard üzerinden yönetmenize olanak tanır.

"A Müşterisi" için geliştirdiğiniz bir kural şablonunu, saniyeler içinde mantıksal operatörlerini değiştirerek "B Müşterisi"ne uyarlayabilirsiniz.

### 3. Karmaşık XML Yapılarına Son: Görsel Editör

Trellix/McAfee kuralları karmaşık XML yapıları gerektirir. Bir MSSP analisti, günde onlarca kural yazarken XML syntax hatalarıyla uğraşmamalıdır.

**Çözüm:** React ile geliştirdiğim sürükle-bırak destekli formlar, arka planda otomatik olarak validasyonu yapılmış (`lxml` kütüphanesi ile) hatasız XML çıktıları üretir. Bu, L1 ve L2 analistlerinin bile hata yapmadan karmaşık korelasyon kuralları yazabilmesini sağlar.

## Teknik Derinlik: Kaputun Altında Ne Var?

RACC, modern yazılım standartlarına göre geliştirilmiştir:

- **Backend:** Python Flask üzerinde çalışan, SQL Injection ve XSS korumaları (`backend/utils/security_config.py`) ile güçlendirilmiş güvenli bir API.
- **Frontend:** React ve modern UI bileşenleri ile hızlı, responsive ve kullanıcı dostu bir arayüz.
- **Performans:** Redis tabanlı caching mekanizması ile binlerce kural arasında milisaniyeler içinde arama ve filtreleme.
- **Audit Logging:** Bir MSSP için "Kim, Ne Zaman, Hangi Kuralı Değiştirdi?" sorusu hayati önem taşır. RACC, tüm işlemleri AuditLog mekanizması ile kayıt altına alır.

## Kurulum ve Dağıtım (Deployment)

### Seçenek 1: Docker ile Hızlı Kurulum (Önerilen)
Tüm sistemi (Backend, Frontend ve Veritabanı) tek komutla ayağa kaldırabilirsiniz.

1. **Gereksinimler:** Docker ve Docker Compose yüklü olmalıdır.

2. **SECRET_KEY Konfigürasyonu (ÖNEMLİ):**
   
   Uygulama güvenliği için güçlü bir SECRET_KEY oluşturun:
   
   ```bash
   # Güçlü bir secret key oluşturun
   python3 -c "import secrets; print(secrets.token_hex(32))"
   ```
   
   Çıktıyı `.env` dosyasına kaydedin:
   ```bash
   echo "SECRET_KEY=<yukarıdaki-komutun-çıktısı>" > .env
   ```
   
   Veya doğrudan export edin:
   ```bash
   export SECRET_KEY=<üretilen-anahtar>
   ```

3. **Çalıştırma:**
   ```bash
   # Cache kullanmadan temiz build
   docker-compose build --no-cache --pull
   
   # Container'ları başlatın
   docker-compose up -d
   
   # Logları kontrol edin
   docker-compose logs -f backend
   ```

4. **Erişim:**
   - Uygulama: `http://localhost:3000`
   - API: `http://localhost:5000`

5. **Sorun Giderme:**
   
   Eğer `TypeError: 'property' object is not iterable` hatası alıyorsanız:
   ```bash
   # Container'ları durdurun
   docker-compose down
   
   # Cache'i temizleyin
   docker system prune -a -f
   
   # SECRET_KEY'in ayarlandığından emin olun
   echo $SECRET_KEY
   
   # Yeniden build ve başlatın
   docker-compose build --no-cache --pull
   docker-compose up -d
   ```

### Seçenek 2: Manuel Prodüksiyon Kurulumu

#### Backend
1. **Kurulum:**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```
2. **Prodüksiyon Modunda Başlatma:**
   Windows:
   ```powershell
   $env:FLASK_CONFIG="production"
   python production_server.py
   ```
   Linux/Mac:
   ```bash
   export FLASK_CONFIG=production
   python production_server.py
   ```

#### Frontend
1. **Derleme (Build):**
   ```bash
   cd frontend
   npm install
   npm run build
   ```
2. **Nginx ile Sunma (Production):**
   ```bash
   # Build edilmiş dosyalar frontend/dist dizininde
   # Nginx veya başka bir web server ile sunun
   ```

## Ortam Değişkenleri (Environment Variables)

Uygulama davranışını özelleştirmek için aşağıdaki ortam değişkenlerini kullanabilirsiniz:

### Güvenlik Ayarları

- **`SECRET_KEY`** (Zorunlu): Flask session yönetimi için kriptografik anahtar.
  - **Üretim ortamında mutlaka değiştirin!**
  - Oluşturma: `python3 -c "import secrets; print(secrets.token_hex(32))"`
  - Minimum 32 karakter, rastgele ve tahmin edilemez olmalı
  - Örnek: `5f352379324c22463451387a0aec5d2f9b8c1a2d3e4f5a6b7c8d9e0f1a2b3c4d`

### Veritabanı Ayarları

- **`DATABASE_URL`**: Veritabanı bağlantı URL'i
  - Varsayılan: `sqlite:///backend/database/app.db`
  - PostgreSQL örnek: `postgresql://user:password@localhost/racc_db`

### CORS Ayarları

- **`ALLOWED_ORIGINS`**: İzin verilen kaynak domainler (virgülle ayrılmış)
  - Varsayılan: `http://localhost:3000,http://localhost:5173`
  - Üretim örnek: `https://racc.example.com`

### Alarm Varsayılanları

- **`DEFAULT_ALARM_MIN_VERSION`**: Varsayılan minimum alarm versiyonu (Varsayılan: `11.6.14`)
- **`DEFAULT_ASSIGNEE_ID`**: Varsayılan atanan kişi ID (Varsayılan: `655372`)
- **`DEFAULT_ESC_ASSIGNEE_ID`**: Varsayılan eskalasyon ID (Varsayılan: `90118`)

### Diğer Ayarlar

- **`FLASK_CONFIG`**: Flask yapılandırma modu (`development`, `production`, `testing`)
- **`LOG_LEVEL`**: Log seviyesi (Varsayılan: `DEBUG`)
- **`MAX_CONTENT_LENGTH`**: Maksimum upload boyutu byte cinsinden (Varsayılan: `16777216`)

### Örnek .env Dosyası

```bash
# Güvenlik
SECRET_KEY=5f352379324c22463451387a0aec5d2f9b8c1a2d3e4f5a6b7c8d9e0f1a2b3c4d

# Uygulama
FLASK_CONFIG=production

# CORS
ALLOWED_ORIGINS=https://racc.example.com

# Log
LOG_LEVEL=INFO
```

## Veritabanı Kurulumu (Database Setup)

Proje ilk kez çalıştırıldığında, veritabanı dosyası (`backend/database/app.db`) otomatik olarak oluşturulur.

1. **Otomatik Oluşturma:** Uygulama başlatıldığında (`python main.py` veya Docker ile), sistem veritabanı dosyasının varlığını kontrol eder. Eğer yoksa, boş bir veritabanı oluşturur ve gerekli tabloları (`db.create_all()`) hazırlar.


## Proje Yapısı

- `backend/`: Flask tabanlı REST API.
  - `routes/`: API endpoint tanımları.
  - `models/`: Veritabanı şemaları.
  - `utils/`: Yardımcı araçlar (XML parser, loglama vb.).
- `frontend/`: React tabanlı kullanıcı arayüzü.
  - `src/components/`: UI bileşenleri ve sayfalar.
- `docker-compose.yml`: Docker dağıtım konfigürasyonu.

---
*Geliştirici Notu: Bu proje, güvenlik operasyonlarını merkezileştirmek ve ölçeklenebilir hale getirmek amacıyla tasarlanmıştır.*

## Ekran Görüntüleri (Screenshots)

| Analysis | Reporting | Rule Flowchart |
|:---:|:---:|:---:|
| ![Analysis](screenshot_analysis.png) | ![Reporting](screenshot_reporting.png) | ![Rule Flowchart](screenshot_flowchart.png) |
