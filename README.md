# Transfer Index

Transfer Index; oyuncu profillerini, sezon performansını, gelişmiş istatistikleri, piyasa değeri geçmişini, transfer kayıtlarını ve kulüp bağlamını bir araya getirerek hem oyuncu kalitesini hem de olası transfer uyumunu değerlendiren bir futbol scouting ve transfer istihbaratı platformudur.

**Geliştirme Durumu:** Aktif Geliştirme

## Ön İzleme

![Transfer Index ana sayfa ön izlemesi](docs/images/transfer-index-preview.png)

## Genel Bakış

Futbolcu transfer kararları yalnızca öne çıkan birkaç istatistiğe dayanmaz. Transfer Index, scouting iş akışının farklı parçalarını tek bir uygulamada birleştirir:

- oyuncu profilleri ve mevcut kulüp bilgileri;
- sezon performansı ve pozisyona uygun gelişmiş metrikler;
- geçmiş piyasa değerleri ve kariyer transferleri;
- sunucu taraflı oyuncu arama ve filtreleme;
- kulüp kadrosu, yaş, milliyet, tercih edilen ayak ve finansal özetler;
- deterministik oyuncu puanlama ve hedef kulübe özel transfer analizi.

Proje, birbiriyle ilişkili ancak farklı iki soruyu ayrı değerlendirir:

1. **Oyuncu değerlendirmesi:** Oyuncu, hedef kulüpten bağımsız olarak ne kadar güçlü?
2. **Oyuncu → hedef kulüp uyumu:** Oyuncu, belirli bir kulübün kadro ve finansal bağlamına ne kadar uygun?

## Temel Özellikler

### Oyuncu Veritabanı

- Aranabilir ve sayfalanmış oyuncu kayıtları
- Oyuncu adı, yaş, milliyet, pozisyon, tercih edilen ayak, kulüp ve lig bilgileri
- Mevcutsa güncel piyasa değeri, sözleşme verileri, fiziksel profil ve sezon performansı
- Oyuncu ve kulüpler için özel detay sayfaları
- Yan yana oyuncu karşılaştırması
- Profil ve performans özelliklerine dayalı benzer oyuncu önerileri

### Oyuncu Analitiği

- Maç, ilk 11, dakika, gol, asist ve 90 dakika başına üretim verileri
- Forvet, kanat, orta saha, defansif orta saha, stoper, bek ve kaleciler için pozisyona duyarlı gelişmiş istatistikler
- Kulüpten bağımsız deterministik oyuncu puanı; kalite derecesi, güçlü yönler ve riskler
- Eksik isteğe bağlı veriler oyuncuyu veritabanından çıkarmak yerine `null`/kullanılamıyor olarak korunur

### Piyasa Değeri İstihbaratı

- Güncel ve en yüksek piyasa değeri
- Kaydedilen en düşük değer ve geçmiş büyüme hesabı
- Oyuncu sayfasında geçmiş piyasa değeri grafiği

### Kariyer Transfer Geçmişi

- Önceki ve yeni kulüpler
- Transfer tarihi ve sezonu
- Piyasa değeri ve transfer bedeli
- Kaynak veride mevcutsa kiralama, kiralıktan dönüş ve bedelsiz transfer dahil transfer türleri

### Scouting Veritabanı

Scouting sayfası filtrelemeyi sunucu tarafında gerçekleştirir ve aşağıdaki filtrelerin birlikte kullanılmasını destekler:

- oyuncu arama;
- pozisyon;
- milliyet;
- lig;
- kulüp;
- tercih edilen ayak;
- minimum ve maksimum yaş;
- minimum ve maksimum piyasa değeri;
- minimum dakika;
- minimum gol;
- minimum asist.

Arama alanında debounce uygulanır, sayısal aralıklar doğrulanır, filtre seçenekleri veritabanı değerlerinden üretilir ve filtreleri sıfırlamak varsayılan oyuncu listesini geri getirir.

### Transfer Senaryosu Analizörü

```text
Oyuncu + Hedef Kulüp
          ↓
Deterministik Transfer Uyum Analizi
```

Analizör, seçilen oyuncunun yapılandırılmış bağlamını hedef kulübün kadro yapısı ve finansal profiliyle birleştirir. Oyuncunun mevcut kulübünün hedef olarak seçilmesi backend doğrulamasıyla reddedilir.

### Deterministik Transfer Uyum Motoru

Transfer Uyum Puanı bir dil modeli tarafından değil, uygulama mantığı tarafından hesaplanır. Güncel faktörler ve ağırlıkları:

| Faktör | Ağırlık |
| --- | ---: |
| Oyuncu Kalitesi | %20 |
| Kadro Uyumu | %15 |
| Finansal Uyum | %15 |
| Performans | %15 |
| Gelişmiş İstatistikler | %10 |
| Yaş Profili | %8 |
| Sözleşme | %7 |
| Kültürel Uyum | %5 |
| Baskıya Hazırlık | %3 |
| Transfer Riski | %2 |

`transfer_risk_score` risk seviyesini ifade ettiği için final uyum hesabındaki katkısı ters çevrilir. Doğrulanmış veriden hesaplanamayan bir alt puan `null` olarak kalır; eksik veri sıfır kabul edilmez ve final puanı yalnızca mevcut alt puanların ağırlıkları normalize edilerek hesaplanır.

Dereceler aşağıdaki aralıkları kullanır:

| Puan | Derece |
| --- | --- |
| 85–100 | Elite Fit |
| 70–84 | Strong Fit |
| 55–69 | Moderate Fit |
| 40–54 | Risky Fit |
| 0–39 | Poor Fit |

### AI Scout Analizi — Planlandı / Geliştirme Aşamasında

Transfer Scenario için OpenAI sağlayıcısı şu anda etkin değildir. Hazır durumdaki altyapı:

```text
Deterministik Motor
        ↓
Kompakt Context Builder
        ↓
Kararlı JSON + SHA256 Context Hash
        ↓
7 Günlük Cache Kontrolü
        ↓
AI Yorumlama (planlandı)
```

Cache kaydı bulunmadığında güncel endpoint, `source: "fallback"` ile deterministik sonucu döndürür; OpenAI çağrısı yapmaz ve fallback sonucunu cache'e kaydetmez. Planlanan AI katmanı yapılandırılmış analizi yorumlayacaktır; Transfer Uyum Puanı'nı üretmeyecek veya değiştirmeyecektir.

Repository ayrıca OpenRouter tabanlı ayrı bir oyuncu raporu endpoint'i içerir. Bu eski rapor servisi, deterministik Transfer Scenario AI mimarisinden bağımsızdır.

## Veri Kaynakları

### Transfermarkt Türevli CSV Verileri

Import scriptleri; Transfermarkt benzeri şemalara sahip CSV dosyalarından oyuncu meta verilerini, kulüpleri, turnuvaları, maç katılımlarını, piyasa değerlerini ve transfer geçmişini içe aktarmayı destekler.

### FBref Türevli Gelişmiş İstatistikler

Gelişmiş istatistik import süreci; 2024/25 sezonuna ait beklenen gol, beklenen asist, şut, top ilerletme, pozisyon üretimi, savunma aksiyonları, hava topu ve mevcut kaleci istatistiklerini destekler.

Transfer Index bağımsız bir eğitim ve portföy projesidir. Transfermarkt veya FBref ile bağlantılı değildir. Verilerin mülkiyeti ve kullanım hakları ilgili sağlayıcılara ve veri seti sahiplerine aittir. Repository, ana Transfermarkt CSV klasörünü takip dışı bırakır; veri setlerini geçerli kullanım şartlarına uygun biçimde edinin ve kullanın.

## Teknoloji Yığını

| Katman | Teknolojiler |
| --- | --- |
| Backend | Python, FastAPI, SQLAlchemy, PostgreSQL, Pandas, Pydantic |
| Frontend | React, Vite, Tailwind CSS, React Router, Recharts |
| AI durumu | Transfer Scenario yorumlaması için OpenAI API — planlandı/geliştirme aşamasında |
| İsteğe bağlı eski AI servisi | OpenAI Python client üzerinden OpenRouter uyumlu oyuncu raporu servisi |
| Test | Python `unittest`, FastAPI `TestClient` |

## Mimari

```mermaid
flowchart LR
    UI[React / Vite Frontend] -->|HTTP JSON| API[FastAPI API]
    API --> SERVICES[Bağlam ve Analiz Servisleri]
    SERVICES --> DB[(PostgreSQL)]
    IMPORTS[CSV Import Scriptleri] --> DB
    TM[Transfermarkt Türevli Veriler] --> IMPORTS
    FB[FBref Türevli Veriler] --> IMPORTS
```

```mermaid
flowchart TD
    PLAYER[Oyuncu Bağlamı] --> ENGINE[Deterministik Transfer Uyum Motoru]
    CLUB[Hedef Kulüp Bağlamı] --> ENGINE
    ENGINE --> SCORE[Uyum Puanı, Alt Puanlar, Güçlü Yönler, Riskler]
    SCORE --> COMPACT[Kompakt AI Bağlamı ve SHA256 Hash]
    COMPACT --> FALLBACK[Deterministik Fallback]
    COMPACT -. planlandı .-> AI[AI Yorumlama]
```

## Proje Yapısı

```text
transfer-index/
├── backend/
│   ├── .env.example
│   ├── app/
│   │   ├── api/
│   │   │   └── routes.py
│   │   ├── data/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── scripts/
│   │   ├── services/
│   │   ├── utils/
│   │   ├── database.py
│   │   └── main.py
│   └── tests/
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── assets/
│   │   ├── pages/
│   │   │   ├── ClubPage.jsx
│   │   │   ├── ComparePage.jsx
│   │   │   ├── Home.jsx
│   │   │   ├── PlayerPage.jsx
│   │   │   └── Scouting.jsx
│   │   ├── utils/
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── package.json
│   └── vite.config.js
└── README.md
```

## Başlangıç

### Gereksinimler

- Python 3.11 veya üzeri
- Vite 8 ile uyumlu Node.js
- PostgreSQL

### Backend Kurulumu

Repository'de şu anda commit edilmiş bir `requirements.txt` veya `pyproject.toml` bulunmamaktadır. Kodun kullandığı backend paketlerini açıkça kurun:

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install fastapi "uvicorn[standard]" sqlalchemy psycopg2-binary pandas python-dotenv pydantic openai
```

macOS veya Linux üzerinde sanal ortamı şu komutla etkinleştirin:

```bash
source .venv/bin/activate
```

`backend/.env.example` dosyasını `backend/.env` olarak kopyalayın ve sunucu ortamını yapılandırın. `.env` dosyasını hiçbir zaman commit etmeyin.

### Veritabanı Yapılandırması

Backend, PostgreSQL bağlantısını `DATABASE_URL` üzerinden okur:

```dotenv
DATABASE_URL=postgresql://username:password@localhost:5432/transfer_index
```

API'yi başlatmadan önce veritabanını oluşturun. Güncel uygulama başlangıçta SQLAlchemy `Base.metadata.create_all()` çağrısını yapar; henüz bir migration altyapısı bulunmamaktadır.

Uzun süre çalışan bir sunucu başlatmadan eşlenen tabloları hazırlamak için:

```powershell
python -c "import app.main"
```

### Veri Setini İçe Aktarma

Import komutlarını `backend/` klasöründen çalıştırın. Scriptler kullanıcı tarafından sağlanan şu dosyaları bekler:

```text
app/data/transfermarkt/players.csv
app/data/transfermarkt/national_teams.csv
app/data/transfermarkt/clubs.csv
app/data/transfermarkt/competitions.csv
app/data/transfermarkt/appearances.csv
app/data/transfermarkt/games.csv
app/data/transfermarkt/player_valuations.csv
app/data/transfermarkt/transfers.csv
app/data/fbref_player_stats.csv
```

Uygulanabilir bir import sırası:

```powershell
python -m app.scripts.import_transfermarkt
python -m app.scripts.import_clubs
python -m app.scripts.import_player_club_ids
python -m app.scripts.import_player_stats
python -m app.scripts.import_player_valuations
python -m app.scripts.import_transfers
python -m app.scripts.import_fbref_advanced_stats
```

Import scriptleri zorunlu sütunları doğrular ve atlanan ya da eşleşmeyen satırları raporlar. Bazı import süreçleri ilgili geçmiş kayıtlarını yeniden oluşturduğu için mevcut bir veritabanında çalıştırmadan önce scriptleri inceleyin.

### Backend'i Çalıştırma

`backend/` klasöründen:

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

API `http://127.0.0.1:8000`, interaktif dokümantasyon ise `http://127.0.0.1:8000/docs` adresinde kullanılabilir.

### Frontend Kurulumu

```powershell
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

Tarayıcıda `http://127.0.0.1:5173` adresini açın. Geliştirme CORS yapılandırması `http://localhost:5173` adresine de izin verir.

### Testler

`backend/` klasöründen:

```powershell
python -m unittest discover -s tests -v
```

Frontend build ve lint kontrollerini `frontend/` klasöründen çalıştırın:

```powershell
npm run build
npm run lint
```

Mevcut durumda production build başarılıdır. Lint komutu çalışır ancak uygulama kodundaki mevcut React hook/saflık kuralları ve kullanılmayan değişken nedeniyle hata raporlar; README güncellemesi bu kaynak dosyalarını değiştirmez.

## Ortam Değişkenleri

| Değişken | Durum | Amaç |
| --- | --- | --- |
| `DATABASE_URL` | Zorunlu | PostgreSQL SQLAlchemy bağlantı dizesi |
| `OPENROUTER_API_KEY` | Eski AI rapor servisi tarafından kullanılır | `AIScoutService` isteklerinin kimlik doğrulaması |
| `OPENROUTER_MODEL` | İsteğe bağlı | Eski OpenRouter modelini değiştirir; varsayılan değer `openai/gpt-3.5-turbo` |
| `OPENAI_API_KEY` | Ayrıldı / henüz kullanılmıyor | Planlanan Transfer Scenario OpenAI sağlayıcısı için placeholder |

API kimlik bilgileri yalnızca backend ortamında tutulmalıdır. Bunları Vite değişkenleri, frontend kodu veya kaynak kontrolü üzerinden açığa çıkarmayın.

## API Özeti

| Metot | Endpoint | Amaç |
| --- | --- | --- |
| `GET` | `/players/search` | Sayfalanmış oyuncu arama ve birleşik scouting filtreleri |
| `GET` | `/players/filter-options` | Veritabanından üretilen filtre seçenekleri |
| `GET` | `/players/{player_id}` | Oyuncu profili |
| `GET` | `/players/{player_id}/player-score` | Kulüpten bağımsız deterministik oyuncu puanı |
| `GET` | `/players/{player_id}/advanced-stats` | Sezon gelişmiş istatistikleri |
| `GET` | `/players/{player_id}/valuations` | Piyasa değeri özeti ve geçmişi |
| `GET` | `/players/{player_id}/transfers` | Kariyer transfer geçmişi |
| `GET` | `/players/compare` | İki oyuncunun karşılaştırması |
| `GET` | `/clubs/search` | Mevcut kulübü hariç tutma destekli hedef kulüp araması |
| `GET` | `/clubs/{club_name}/context` | Yapılandırılmış kulüp istihbaratı bağlamı |
| `POST` | `/transfer-scenarios/analyze` | Deterministik oyuncu-kulüp transfer analizi |
| `POST` | `/transfer-scenarios/ai-analyze` | Cache kontrolü ve deterministik fallback; harici sağlayıcı şu anda devre dışı |

## Transfer Uyum Felsefesi

Oyuncu kalitesi ile transfer uyumu aynı şey değildir. Yüksek kaliteli bir oyuncu; aynı pozisyonda güçlü derinliği bulunan, finansal kapasitesi sınırlı olan, yaş profili uyuşmayan veya zor bir sözleşme durumuna sahip bir kulüp için yine de kötü bir hedef olabilir. Transfer Index önce oyuncu kalitesini bağımsız biçimde değerlendirir; ardından seçilen hedef için kadro ihtiyacı, finansal bağlam, yaş, sözleşme, performans, gelişmiş metrikler ve nesnel adaptasyon sinyallerini analiz eder.

## Sorumlu AI ve Veri Sınırlamaları

- AI yorumu, sağlanan yapılandırılmış bağlama ve deterministik analize dayanmalıdır.
- Sistem özel hayat, kişilik, taktik, sağlık veya soyunma odası hakkında veri dışı iddialar üretmemelidir.
- Eksik bilgi tahmin edilmez veya sıfır kalite olarak puanlanmaz; kullanılamıyor olarak gösterilir.
- Transfer Uyumu, analitik karar desteğidir; transferin gerçekleşeceğini veya gelecekteki performansı garanti etmez.
- Veri setinin kapsamı, eşleştirme kalitesi ve güncelliği sonuçları doğrudan etkiler.
- Finansal uyum günümüzde mevcut piyasa değeri bağlamını kullanır; doğrulanmış bir kulüp transfer bütçesi veya maaş modeli değildir.

## Yol Haritası

- [x] Oyuncu veritabanı ve oyuncu detay sayfaları
- [x] Kulüp sayfaları ve oyuncu karşılaştırması
- [x] Piyasa değeri geçmişi ve kariyer transfer geçmişi
- [x] Sezon performansı ve gelişmiş istatistik görünümleri
- [x] Sunucu taraflı scouting araması ve birleşik filtreler
- [x] Kulüp bağlamı ve kadro profili oluşturucu
- [x] Transfer Scenario modalı ve hedef kulüp doğrulaması
- [x] Deterministik Transfer Uyum motoru
- [x] Kompakt AI bağlamı, kararlı hash ve yedi günlük cache altyapısı
- [x] Deterministik puanlama ve AI altyapısı için backend regresyon testleri
- [ ] Transfer Scenario OpenAI yorumlama sağlayıcısını etkinleştirme
- [ ] Commit edilmiş Python bağımlılık manifesti ekleme
- [ ] Veritabanı migration ve deployment yapılandırması ekleme
- [ ] Veri kalitesi, API ve frontend uçtan uca test kapsamını genişletme
- [ ] Kaynak verinin izin verdiği ölçüde kulüp/logo ve veri seti zenginleştirmesine devam etme

## Yasal Uyarı

Transfer Index bağımsız bir eğitim ve portföy projesidir. Transfermarkt, FBref, futbol kulüpleri veya futbol ligleriyle bağlantılı değildir. Veriler ilgili sağlayıcılara ve sahiplerine aittir.

## Geliştirici

Baran Doğrular
