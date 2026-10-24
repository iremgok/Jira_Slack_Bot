# Canlı Test Rehberi (Gerçek Jira Cloud + Slack)

Bu rehber, botu `JIRA_MOCK_MODE=false` ve `SLACK_DRY_RUN=false` ile gerçek bir Jira Cloud
sitesine ve Slack çalışma alanına bağlayıp uçtan uca test etmeyi adım adım anlatır.

> Tahmini süre: 30–45 dakika. Üretim kanalı yerine **ayrı bir test kanalı** ve
> **ayrı bir test veritabanı** kullanmanız önerilir.

---

## 1. Jira Cloud hazırlığı

### 1.1 Jira sitesi ve test projesi

1. Bir Jira Cloud siteniz yoksa <https://www.atlassian.com/software/jira/free> adresinden ücretsiz
   site açın (ör. `https://sirketim-test.atlassian.net`).
2. **Projects → Create project** → *Scrum* (sprint filtresini de test etmek için) veya *Kanban* seçin.
3. Proje adı: `Bot Test`, **Key**: `BOT` (bu değer `JIRA_PROJECT_KEY` olacak).
4. Proje ayarlarında öncelik (Priority) alanının görünür olduğundan emin olun
   (varsayılan öncelikler: Highest, High, Medium, Low, Lowest).

### 1.2 API token oluşturma

1. <https://id.atlassian.com/manage-profile/security/api-tokens> adresine gidin.
2. **Create API token** butonuna tıklayın (kapsamsız/klasik token).
   > ⚠️ *"Create API token with scopes"* seçeneğini kullanmayın. Kapsamlı token'lar
   > `api.atlassian.com/ex/jira/<cloud-id>` adresini gerektirir; bot ise doğrudan
   > `https://<site>.atlassian.net` adresine Basic Auth (e-posta + token) ile bağlanır.
3. Etiket verin (ör. `jira-slack-bot-test`), son kullanma tarihini seçin, token'ı kopyalayın.
   Token yalnızca bir kez gösterilir.
4. Token'ın sahibi olan kullanıcının `BOT` projesini **görme (Browse projects)** yetkisi olmalıdır.

### 1.3 Bağlantıyı elle doğrulama

```bash
# Kimlik doğrulama -> 200 ve kullanıcı bilgisi dönmeli
curl -s -u "you@example.com:API_TOKEN" https://sirketim-test.atlassian.net/rest/api/3/myself

# Botun kullandığı arama uç noktası -> {"issues":[...]} dönmeli
curl -s -u "you@example.com:API_TOKEN" -G \
  --data-urlencode 'jql=project = "BOT"' --data-urlencode 'maxResults=1' \
  https://sirketim-test.atlassian.net/rest/api/3/search/jql
```

---

## 2. Slack hazırlığı

Önce Slack'te bir test kanalı açın, ör. `#jira-bot-test`. Ardından **iki yöntemden birini** seçin.

### Yöntem A — Incoming Webhook (en basit)

1. <https://api.slack.com/apps> → **Create New App** → **From scratch**.
2. Uygulama adı: `Jira Bot (Test)`, çalışma alanını seçin → **Create App**.
3. Sol menü **Incoming Webhooks** → **Activate Incoming Webhooks** anahtarını açın.
4. Sayfanın altındaki **Add New Webhook** butonuna tıklayın → `#jira-bot-test` kanalını seçin → **Allow**.
5. Oluşan `https://hooks.slack.com/services/T.../B.../...` adresini kopyalayın.
6. Doğrulama:

   ```bash
   curl -X POST -H 'Content-type: application/json' \
     --data '{"text":"Webhook testi ✅"}' https://hooks.slack.com/services/XXX/YYY/ZZZ
   ```

   Yanıt `ok` olmalı ve mesaj kanalda görünmeli.

> Webhook'lar için yan etkisiz bir sağlık kontrolü uç noktası yoktur. Bu yüzden `--check`
> webhook modunda Slack'i "OK" kabul eder. Asıl doğrulama yukarıdaki `curl` testidir.

### Yöntem B — Bot Token (`chat:write`)

1. <https://api.slack.com/apps> → **Create New App** → **From scratch** → ad + çalışma alanı.
2. **OAuth & Permissions** → **Bot Token Scopes** → **Add an OAuth Scope** → `chat:write`.
   (Botu kanala davet etmeden yazdırmak isterseniz `chat:write.public` da ekleyebilirsiniz.)
3. Sayfanın üstünde **Install to Workspace** → **Allow**.
4. **Bot User OAuth Token** (`xoxb-...`) değerini kopyalayın.
5. Slack'te `#jira-bot-test` kanalında `/invite @Jira Bot (Test)` yazarak botu kanala ekleyin.
6. Kanal ID'si: kanal adına tıklayın → **About** sekmesinin en altında `C0123ABCDEF` biçiminde görünür.
7. Doğrulama:

   ```bash
   curl -s -H "Authorization: Bearer xoxb-..." https://slack.com/api/auth.test
   # {"ok":true, "team":"...", ...}
   ```

> İki yöntem birlikte tanımlanırsa **webhook önceliklidir**. Bot token'ı test etmek için
> `SLACK_WEBHOOK_URL` değerini boş bırakın.

---

## 3. `.env` yapılandırması

```env
JIRA_BASE_URL=https://sirketim-test.atlassian.net
JIRA_EMAIL=you@example.com
JIRA_API_TOKEN=<1.2'de oluşturulan token>
JIRA_PROJECT_KEY=BOT
JIRA_MOCK_MODE=false

# Yöntem A
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/XXX/YYY/ZZZ
# Yöntem B (webhook boşken kullanılır)
SLACK_BOT_TOKEN=
SLACK_CHANNEL=
SLACK_DRY_RUN=false

# Canlı test için ayrı, silinip yeniden oluşturulabilir bir veritabanı
DATABASE_URL=sqlite:///live_test.db

TIMEZONE=Europe/Istanbul
POLL_INTERVAL_SECONDS=60
INITIAL_LOOKBACK_MINUTES=60
LOG_LEVEL=DEBUG
```

Test durumunu sıfırlamak için botu durdurup `live_test.db` dosyasını silmeniz yeterlidir.
Şema bir sonraki çalıştırmada Alembic ile yeniden oluşturulur.

---

### 3.1 Docker ile canlı test (isteğe bağlı)

Aynı `.env` dosyasına `POSTGRES_PASSWORD=<url-güvenli-bir-şifre>` ekleyip senaryoları konteyner içinde
PostgreSQL ile de çalıştırabilirsiniz. `DATABASE_URL` değeri compose tarafından otomatik ayarlanır:

```bash
docker compose up -d postgres
docker compose run --rm jira_bot python -m src.main --check
docker compose run --rm jira_bot python -m src.main --once poll
docker compose run --rm jira_bot python -m src.main --once report
docker compose up -d jira_bot && docker compose logs -f jira_bot     # zamanlayıcı
docker compose down -v                                              # her şeyi (veri dahil) sil
```

---

## 4. Test senaryoları

Her çalıştırmanın ilk log satırı, sırlar hariç etkin yapılandırmayı gösterir. Testten önce bunu kontrol edin:

```text
Config: jira=https://sirketim-test.atlassian.net project=BOT extra_jql='' | slack=incoming webhook | db=sqlite:///live_test.db (auto-migrate=True) | tz=Europe/Istanbul
```

Tüm komutlar proje kök dizininde, sanal ortam aktifken çalıştırılır.

> Jira arama indeksi, değişikliklerin arama sonuçlarına yansıması için birkaç saniye ile
> birkaç dakika arası gecikebilir. Bir değişiklik görünmezse ~30 saniye bekleyip tekrar deneyin.

| # | Adım | Komut | Beklenen sonuç |
|---|------|-------|----------------|
| 0 | Bağlantı kontrolü | `python -m src.main --check` | Log: `Jira: OK \| Slack: OK`, çıkış kodu `0` |
| 1 | Jira'da 3 issue açın: **A** (Priority *High*, kendinize atanmış), **B** (*Medium*, atanmamış), **C** (*Highest*, başlığında `<test> & özel karakter` olsun) | `python -m src.main --once poll` | Slack'te 3 adet **🆕 New Jira Issue** mesajı. Başlıklara tıklayınca `.../browse/BOT-x` açılmalı. C'nin başlığı bozulmadan görünmeli. Log: `new=3` |
| 2 | Hiçbir şey değiştirmeden tekrar çalıştırın | `python -m src.main --once poll` | **Mesaj yok.** Log: `new=0 updated=0` |
| 3 | **A**'nın durumunu *In Progress* yapın, **B**'yi kendinize atayın | `python -m src.main --once poll` | 2 adet **✏️ Jira Issue Updated** mesajı: `Status: To Do → In Progress` ve `Assignee: Unassigned → <adınız>` |
| 4 | **B**'ye sadece yorum ekleyin | `python -m src.main --once poll` | **Mesaj yok** (takip edilen alan değişmedi). DEBUG logda `updated without tracked field changes` |
| 5 | **A**'yı *Done* durumuna taşıyın | `python -m src.main --once poll` | `Status: In Progress → Done` güncelleme mesajı |
| 6 | Günlük raporu elle gönderin | `python -m src.main --once report` | **📊 Daily Jira Report** mesajı. Opened today: **3**, Closed today: **1** (A), Open critical: **1** (C; A kapandı, B Medium), Most loaded: sizin adınız (B) ve `Unassigned` (C) |
| 7 | Raporu tekrar gönderin | `python -m src.main --once report` | Rapor yine gönderilir (`--once report` zorlamalıdır) |
| 8 | Zamanlayıcı testi: `live_test.db`'yi silin, `DAILY_REPORT_CRON` değerini 2–3 dakika sonrasına ayarlayın (ör. saat 15:45 için `45 15 * * *`) | `python -m src.main` | Açılışta hemen bir poll çalışır, sonra her 60 sn'de bir tekrarlar. Ayarlanan saatte rapor tek sefer gönderilir. `Ctrl+C` ile temiz kapanır |
| 9 | (Scrum) `JIRA_EXTRA_JQL=sprint in openSprints()` ayarlayın; bir issue'yu aktif sprinte alın, diğerini backlog'da bırakıp ikisini de güncelleyin | `python -m src.main --once poll` | Yalnızca sprintteki issue için bildirim gelir |

> **Senaryo 8 notu:** Zamanlanmış rapor aynı gün için yalnızca bir kez gönderilir. `--once report`
> o günü "gönderildi" olarak işaretler. Bu yüzden zamanlayıcı testinden önce veritabanını sıfırlayın.

> **İlk poll notu:** Veritabanı boşken ilk poll yalnızca son `INITIAL_LOOKBACK_MINUTES` (varsayılan 60)
> dakikada güncellenen issue'ları bildirir. Daha eski issue'lar sessizce atlanır.

### Hata senaryoları (isteğe bağlı)

| Değişiklik | Beklenen log |
|------------|--------------|
| `JIRA_API_TOKEN` yanlış | `JiraAuthError: Jira rejected the credentials (HTTP 401)...`, çıkış kodu `1` |
| `JIRA_BASE_URL` yanlış site / Jira Server | `Jira endpoint not found (/rest/api/3/search/jql). JIRA_BASE_URL must point to a Jira Cloud site...` |
| `JIRA_PROJECT_KEY=YOKBOYLE` | `Invalid Jira request: The value 'YOKBOYLE' does not exist for the field 'project'.` (HTTP 400) |
| `JIRA_EXTRA_JQL=foo = bar` | `Invalid Jira request: Field 'foo' does not exist...` |
| Bot token var, bot kanalda değil | `Slack API error: not_in_channel -> invite the bot: /invite @<app-name> ...` |
| Yanlış kanal ID'si (ör. `#jira-bot-test` yazılmış) | `Slack API error: channel_not_found -> SLACK_CHANNEL must be a channel ID like C0123ABCDEF` |
| Webhook URL'si iptal edilmiş | `Slack webhook returned HTTP 404: no_service -> the webhook was removed or the URL is wrong` |
| İnternet / Slack erişilemiyor | `Slack delivery failed for BOT-1: Could not reach Slack webhook (ConnectionError). Deferring N issue(s) to the next poll.`, çıkış kodu `1`. Webhook URL'si loga **yazılmaz** |
| PostgreSQL kapalı (Docker) | `Waiting for database ... (attempt n)` uyarıları, süre dolunca `RepositoryError: Database ... not reachable after 60s` (şifre `***` ile maskelenir) |
| `JIRA_EMAIL` boş | Açılışta `Invalid configuration: ... Missing required configuration: JIRA_EMAIL`, çıkış kodu `2` |

Slack bildirimi başarısız olursa o turdaki kalan issue'lar için tekrar denenmez. Bu issue'lar veritabanına
kaydedilmez ve poll imleci ilerletilmez; hata giderildiğinde bir sonraki poll kaçırılan bildirimleri gönderir.
Zamanlanmış günlük rapor başarısız olursa 10 dakika arayla en fazla 3 kez yeniden denenir.

Beklenen hatalar (Jira/Slack/DB) traceback olmadan tek satırla loglanır. Ayrıntı için
`LOG_LEVEL=DEBUG` kullanın; beklenmeyen hatalar her zaman tam traceback ile loglanır.

---

## 5. Sorun giderme

| Belirti | Olası neden / çözüm |
|---------|---------------------|
| `401` / `403` | E-posta ile token aynı hesaba ait değil, token süresi dolmuş ya da kapsamlı (scoped) token kullanılmış |
| Issue'lar hiç gelmiyor | Proje anahtarı yanlış, kullanıcının proje yetkisi yok, issue'lar `INITIAL_LOOKBACK_MINUTES`'tan eski ya da arama indeksi henüz güncellenmemiş |
| "Closed today" 0 görünüyor | Issue'nun durum kategorisi gerçekten *Done* mı? (Ör. özel bir "Closed" durumu *In Progress* kategorisinde olabilir.) Proje ayarları → Workflow'u kontrol edin |
| Rapor gün sınırı kaymış | `TIMEZONE` ayarını kontrol edin. Gün sınırı Jira profilinin değil botun saat dilimine göre hesaplanır |
| Slack'te link yerine düz metin | Mesaj, kanal yerine bildirim önizlemesinde görüntüleniyor olabilir (önizleme fallback `text` alanını gösterir) |

---

## 6. Temizlik

- Test bittikten sonra Jira API token'ını <https://id.atlassian.com/manage-profile/security/api-tokens>
  adresinden **Revoke** edin.
- Slack uygulamasını silin veya webhook'u iptal edin (**Incoming Webhooks → Remove**).
- `live_test.db` ve `logs/` klasörünü silin. `.env` dosyası `.gitignore` içindedir, asla commit etmeyin.
