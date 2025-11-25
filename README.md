# RACC: MSSP'ler ve Kurumlar İçin Trellix SIEM Yönetiminde Multi-Tenant Devrimi

Siber güvenlik dünyasında, özellikle Managed Security Service Provider (MSSP) olarak hizmet veren firmalar veya birden fazla kurumsal müşteriye SIEM danışmanlığı yapan ekipler için en büyük kabuslardan biri "Yönetilebilirlik"tir.

Her müşteri için ayrı VPN'ler, farklı arayüzler, manuel kural kopyalamalar ve "Acaba A müşterisinin kuralını yanlışlıkla B müşterisine mi yükledim?" korkusu...

Geliştirdiğim **RACC (Rule & Alarm Control Center)**, tam da bu kaosu ortadan kaldırmak için tasarlandı. RACC, kurumsal firmaların kendi iç SIEM yönetimini kolaylaştırmasının ötesinde, MSSP'ler için gerçek bir Multi-Tenant (Çok Kiracılı) yönetim katmanı sunar.

## Neden RACC? Özellikle MSSP'ler İçin...

RACC, Trellix (eski adıyla McAfee) SIEM altyapısı için geliştirilmiş, Python (Flask) ve React tabanlı modern bir yönetim platformudur. Ancak onu sıradan bir editörden ayıran en büyük özellik mimarisidir.

### 1. Gerçek Multi-Tenant Mimarisi ve Veri İzolasyonu

MSSP'ler için en kritik konu müşteri verilerinin izolasyonudur.

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
2. **Çalıştırma:**
   ```bash
   docker-compose up --build -d
   ```
3. **Erişim:**
   - Uygulama: `http://localhost:3000`
   - API: `http://localhost:5000`

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
2. **Sunum:**
   `frontend/dist` klasöründeki dosyaları Nginx, Apache veya IIS gibi bir web sunucusu ile yayınlayın.

---
### Mock Veri Oluşturma (Demo)
Sistemi test etmek için örnek müşteri, kural ve alarm verileri oluşturabilirsiniz:

```bash
# Backend dizininde:
python backend/scripts/create_mock_data.py
```
Bu komut "Demo Customer" adında bir müşteri ve ilişkili örnek veriler oluşturacaktır.

## Yapılandırma (Configuration)

Prodüksiyon ortamında aşağıdaki ortam değişkenlerini ayarlamanız önerilir:

- `SECRET_KEY`: Güvenli oturum yönetimi için rastgele ve güçlü bir anahtar.
- `DATABASE_URL`: Veritabanı bağlantı adresi (Varsayılan: SQLite).
- `ALLOWED_ORIGINS`: CORS için izin verilen domainler (örn: `https://racc.example.com`).

## Veritabanı Kurulumu (Database Setup)

Proje ilk kez çalıştırıldığında, veritabanı dosyası (`backend/database/app.db`) otomatik olarak oluşturulur.

1. **Otomatik Oluşturma:** Uygulama başlatıldığında (`python main.py` veya Docker ile), sistem veritabanı dosyasının varlığını kontrol eder. Eğer yoksa, boş bir veritabanı oluşturur ve gerekli tabloları (`db.create_all()`) hazırlar.
2. **Veri Doldurma:** Yeni oluşturulan veritabanı boştur. Test verileriyle doldurmak için yukarıdaki "Mock Veri Oluşturma" adımını uygulayabilirsiniz.

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
