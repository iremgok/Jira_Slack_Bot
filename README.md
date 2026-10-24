# Jira Issue Takip & Slack Rapor Botu

Jira'daki yeni/güncellenen issue'ları periyodik olarak takip edip Slack'e bildiren ve
her gün (varsayılan 18:00) özet rapor gönderen bot.

## Özellikler

- **Issue poller:** Son başarılı çalıştırmadan bu yana güncellenen issue'ları JQL ile çeker;
  yeni issue'lar ve *Status / Priority / Assignee / Summary* değişiklikleri için Slack bildirimi atar.
  Bildirim gönderilemezse bir sonraki turda tekrar dener, aynı değişikliği iki kez göndermez.
- **Günlük rapor:** Bugün açılan, bugün kapatılan, açıkta kalan kritik issue'lar ve en çok
  açık işi olan kişiler. Aynı gün için rapor yalnızca bir kez gönderilir.
- **Block Kit mesajları:** Her issue başlığı `https://<domain>/browse/KEY-123` linkine tıklanabilir.
- **Güvenli yapılandırma:** Tüm gizli bilgiler `.env`'den okunur, `SecretStr` ile loglara sızmaz,
  eksik ayar varsa uygulama açılışta anlaşılır bir hata verir.
- **SQLite veya PostgreSQL**, Docker desteği, mock (Jira'sız) ve dry-run (Slack'siz) modları.

## Mimari

```text
src/
├── main.py              # Composition root: bağımlılıkları kurar, scheduler/CLI'yi başlatır
├── core/                # config (pydantic-settings), logger, exceptions
├── models/              # Pydantic domain modelleri (JiraIssue, DailyReport) + saf iş mantığı
├── services/            # Dış dünya: jira_client, jira_mock, slack_client (transport), slack_blocks (mesaj şablonları)
├── database/            # db (engine/session), tables (ORM), repository (veri erişimi), migrations (Alembic)
└── jobs/                # issue_poller, daily_report (orkestrasyon)
alembic/                 # Migration ortamı (env.py) ve sürümler (versions/)
alembic.ini
docs/LIVE_TEST.md        # Gerçek Jira + Slack ile adım adım test rehberi
```

Bağımlılık yönü: `jobs → services / database → models → core`. Joblar somut sınıflar yerine
`IssueSource` protokolüne bağlıdır; bu sayede gerçek Jira istemcisi ile mock istemci
birbirinin yerine kullanılabilir ve testlerde sahte nesneler enjekte edilir.

## Kurulum

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate   |   Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # ardından değerleri doldurun
```

Gerekli ayarlar:

| Değişken | Açıklama |
|---|---|
| `JIRA_BASE_URL` | `https://<domain>.atlassian.net` |
| `JIRA_EMAIL`, `JIRA_API_TOKEN` | Jira Cloud API token ([oluştur](https://id.atlassian.com/manage-profile/security/api-tokens)) |
| `JIRA_PROJECT_KEY` | Takip edilecek proje, ör. `KAN` |
| `SLACK_WEBHOOK_URL` **veya** `SLACK_BOT_TOKEN` + `SLACK_CHANNEL` | Slack hedefi (bot için `chat:write` scope'u gerekir) |

İsteğe bağlı: `JIRA_EXTRA_JQL` (ör. `sprint in openSprints()`), `POLL_INTERVAL_SECONDS`,
`DAILY_REPORT_CRON` (5 alanlı cron, `TIMEZONE`'a göre), `CRITICAL_PRIORITIES`, `TOP_ASSIGNEE_COUNT`.
Tam liste için `.env.example` dosyasına bakın.

## Çalıştırma

```bash
python -m src.main                  # zamanlayıcıyı başlatır (poller + günlük rapor)
python -m src.main --once poll      # poller'ı bir kez çalıştırır
python -m src.main --once report    # bugünün raporunu hemen gönderir
python -m src.main --check          # Jira ve Slack bağlantısını test eder
```

Jira hesabı olmadan denemek için `.env` içinde:

```env
JIRA_MOCK_MODE=true
SLACK_DRY_RUN=true
```

Bu modda örnek issue'lar kullanılır ve Slack mesajları gönderilmek yerine loglara yazılır.

Gerçek Jira Cloud ve Slack ile uçtan uca test için: **[docs/LIVE_TEST.md](docs/LIVE_TEST.md)**
(Jira test projesi ve API token, Slack webhook / bot token kurulumu, senaryolar ve beklenen sonuçlar).

## Veritabanı migrasyonları (Alembic)

Şema `src/database/tables.py` içinde tanımlanır ve **Alembic** ile yönetilir. Alembic de aynı
`DATABASE_URL` değerini okur (`.env` veya ortam değişkeni); Jira/Slack bilgileri gerekmez.

- `DB_AUTO_MIGRATE=true` (varsayılan): uygulama her açılışta `upgrade head` çalıştırır.
- Alembic'ten önce `create_all` ile oluşturulmuş mevcut veritabanları otomatik olarak
  başlangıç sürümüne (baseline) *stamp*'lenir, veri kaybı olmaz. Bu eski veritabanlarında
  `alembic check`, `sent_reports.report_date` için isimsiz unique kısıtı yüzünden kozmetik bir fark
  raporlayabilir. Kısıt yine çalışır; sıfırdan oluşturulan veritabanlarında bu fark yoktur.

```bash
alembic upgrade head                                 # bekleyen migrasyonları uygula
alembic current                                      # veritabanının mevcut sürümü
alembic history                                      # migrasyon geçmişi
alembic downgrade -1                                 # bir adım geri al
alembic upgrade head --sql                           # SQL'i çalıştırmadan yazdır (DBA incelemesi için)
```

**Şema değişikliği akışı:**

1. `src/database/tables.py` içinde tabloyu/kolonu değiştirin.
2. `alembic revision --autogenerate -m "add xyz column"` komutunu çalıştırın.
3. `alembic/versions/` altında oluşan dosyayı **gözden geçirin** (autogenerate her şeyi yakalayamaz;
   ör. kolon yeniden adlandırma drop+add olarak çıkar).
4. `alembic upgrade head` ile uygulayın ve `pytest` çalıştırın. `tests/test_migrations.py`,
   migrasyonlar ile `tables.py` arasında fark kalırsa testi başarısız yapar.

SQLite'ta `ALTER TABLE` kısıtlı olduğu için migrasyonlar *batch mode* ile üretilir. Kısıtlama adları
sabit bir naming convention ile belirlenir. Böylece aynı migrasyon SQLite ve PostgreSQL'de aynı sonucu verir.

## Docker

```bash
docker compose up -d --build
docker compose logs -f jira_bot
```

Compose, PostgreSQL'i de başlatır; `.env` içinde `POSTGRES_PASSWORD` tanımlı olmalıdır.
Migrasyonlar konteyner açılırken otomatik uygulanır. Elle çalıştırmak için:
`docker compose run --rm jira_bot alembic upgrade head`.

## Testler

```bash
pytest
```

## Git notları

IDE ve yerel dosyalar (`.idea/`, `.vscode/`, `.env`, `*.db`, `logs/`) `.gitignore` içindedir.
Daha önce commit edilmiş bir klasörü takipten çıkarmak için (dosyalar diskte kalır):

```bash
git rm -r --cached .idea
git commit -m "Stop tracking IDE settings"
```

Dikkat: Bu commit'i *pull* eden diğer geliştiricilerin çalışma kopyasında git, takip edilen `.idea/`
dosyalarını siler. IDE klasörü yeniden oluşturur, ancak kişisel ayarlar kaybolabilir. Gerekirse pull öncesinde yedekleyin.

## Notlar

- Jira Cloud'un güncel arama uç noktası `/rest/api/3/search/jql` (token tabanlı sayfalama) kullanılır.
- JQL'de mutlak tarih yerine göreli süreler (`updated >= -15m`) kullanılır; böylece Jira kullanıcı
  profilinin saat dilimi sonucu etkilemez. Günlük raporun gün sınırı botun `TIMEZONE` ayarına göre hesaplanır.
- Birçok Jira iş akışı Done'a geçişte `resolution` alanını doldurmaz. "Bugün kapatılan" hesabı bu yüzden
  `resolutiondate` yoksa `statuscategorychangedate` alanını kullanır.
