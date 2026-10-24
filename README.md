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
├── database/            # db (engine/session), tables (ORM), repository (veri erişimi)
└── jobs/                # issue_poller, daily_report (orkestrasyon)
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

## Docker

```bash
docker compose up -d --build
docker compose logs -f jira_bot
```

Compose, PostgreSQL'i de başlatır; `.env` içinde `POSTGRES_PASSWORD` tanımlı olmalıdır.

## Testler

```bash
pytest
```

## Notlar

- Jira Cloud'un güncel arama uç noktası `/rest/api/3/search/jql` (token tabanlı sayfalama) kullanılır.
- JQL'de mutlak tarih yerine göreli süreler (`updated >= -15m`) kullanılır; böylece Jira kullanıcı
  profilinin saat dilimi sonucu etkilemez. Günlük raporun gün sınırı botun `TIMEZONE` ayarına göre hesaplanır.
