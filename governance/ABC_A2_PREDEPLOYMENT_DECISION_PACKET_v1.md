# ABC — A2 G01–G10: بسته تصمیم و تحویل برای بازبینی مستقل
**Document:** ABC-A2-EXIT-PACKET-v1 | **As-of:** 2026-11-06 | **Decision:** `PREDEPLOYMENT_EVIDENCE_INDEX_READY / A2_OPEN`  
**Code baseline (already executed):** `d8c7698bc060b859f5f4db52d572a00db656a2cd` | **Branch:** `implementation/w1-eng05-external-approval-gate-20261101` | **PR:** [#78](https://github.com/saleheebrahimi2029-hub/abc-platform/pull/78) open, unmerged

> **حدود ادعا:** این بسته، گزارش بررسی و نقشه شواهد مهندسی است؛ نه مصوبه معماری، نه استقرار مدیریت‌شده و نه امضای Security/SRE/متخصص. تمام نتایج اشاره‌شده متعلق به داده‌های مصنوعی و CI هستند. هیچ خدمت/پایگاه داده جدید و هیچ هزینه زیرساختی تأیید یا ایجاد نشده است.

## 1. خروجی‌های اجرایی این بسته
- **فهرست ۸۰ خانه:** `governance/ABC_A2_G01_G10_EVIDENCE_RECONCILIATION_v1.json`؛ هفت موتور ENG-01/02/03/04/05/06/14 + یک مسیر قدیمی `LEGACY_REVIEW_TRANSPORT` (این مسیر **ENG-19** نیست). برای هر خانه: الزام، کد و قرارداد، نام دقیق Test Case در صورت وجود، شناسه و URL Job، SHA کد مبنا، هش Artifact در صورت موجود بودن، سطح پوشش، بازبین مسئول و دلیل OPEN بودن.
- **ثبت ریسک:** `governance/ABC_A2_INDEPENDENT_RISK_REGISTER_v1.json`؛ ۱۴ ریسک با P0/P1، اقدام، مالک، پیوند به گیت و تفکیک وابستگی به محیط مستقل.
- **اعتبارسنج:** `scripts/validate_a2_closure_packet_v1.py`؛ تطبیق گیت‌های canonical با رجیستری، مسیر فایل‌ها، تعریف واقعی تابع آزمون، شواهد اجرای قبلی، عدم جعل هویت بازبین، عدم ادعای دریافت تأیید، مرجع قرارداد/هش و ثبات کد.
- **Workflow:** `.github/workflows/a2-closure-packet-integrity.yml`؛ فایل‌ها را اعتبارسنجی می‌کند؛ **نه سرویس جدید می‌سازد و نه کاربر واقعی را آزمایش می‌کند**.

## 2. تفکیک دقیق وضعیت‌ها
`CI_SUBCRITERION_EVIDENCED` یعنی برای آن خانه یک آزمون نام‌گذاری‌شده و Job موفق روی **Commit پایه** ثبت است؛ **وضعیت عملیاتی همان خانه همچنان OPEN است**. `NO_DIRECT_SCOPED_TEST_EVIDENCE` یعنی حتی این اتصال مشخص وجود ندارد. نتیجه Workflow سبز به‌تنهایی امضای گیت نیست.

| دامنه | خانه‌های دارای شاهد مشخص CI | خانه‌های فاقد شاهد مستقیم | وضعیت عملیاتی |
|---|---:|---:|---|
| ENG-01 — Orchestration | 5 | 5 | OPEN |
| ENG-02 — Consultation/Consent | 8 | 2 | OPEN |
| ENG-03 — Evidence | 7 | 3 | OPEN |
| ENG-04 — Analysis | 7 | 3 | OPEN |
| ENG-05 — Knowledge | 8 | 2 | OPEN |
| ENG-06 — Review-only Decision | 8 | 2 | OPEN |
| ENG-14 — Governance Policy | 6 | 4 | OPEN |
| Legacy Review Transport (غیر از ENG-19) | 6 | 4 | OPEN |
| **کل** | **55** | **25** | **80 OPEN / صفر تأیید مستقل** |

**معیارها در هر دامنه:** G01 معماری، G02 قابلیت دامنه، G03 قراردادها، G04 استقلال، G05 امنیت/حریم خصوصی، G06 تاب‌آوری، G07 کارایی، G08 تأیید حرفه‌ای، G09 عملیات/Observability، G10 امضای مستقل. برای یک خانه فاقد شاهد، `OPEN` به معنای `FAIL` نیست، بلکه به معنای `NOT YET ATTESTED` است.

## 3. شش مجموعه CI هم‌نسخه با کد مبنا
| Workflow | GitHub Actions run | مدرک |
|---|---|---|
| Full Phase04 | [#42208334348](https://github.com/saleheebrahimi2029-hub/abc-platform/actions/runs/42208334348) | 752 تست اصلی موفق + 16 تست تکمیلی؛ Job Log (Artifact جداگانه بازگردانده نشد) |
| Scoped Engines | [#42208334405](https://github.com/saleheebrahimi2029-hub/abc-platform/actions/runs/42208334405) | 11 Job موفق، Artifact و SHA256 مستقل برای هر 8 دامنه |
| ADR-003/004/005 security | [#42208334526](https://github.com/saleheebrahimi2029-hub/abc-platform/actions/runs/42208334526) | 56 آزمون اختصاصی JWT/mTLS/ENG14/PG؛ Artifact با Digest |
| G04/G05 network/PG | [#42208334592](https://github.com/saleheebrahimi2029-hub/abc-platform/actions/runs/42208334592) | شبکه کانتینرهای CI، موقت بودن CA/JWT، خطا و بازیابی PG؛ سه Artifact |
| G06 durable queue | [#42208334762](https://github.com/saleheebrahimi2029-hub/abc-platform/actions/runs/42208334762) | PostgreSQL16 واقعی ولی موقت، restart، lease/fence/replay؛ Artifact |
| G07/G09 | [#42208334598](https://github.com/saleheebrahimi2029-hub/abc-platform/actions/runs/42208334598) | 100 زنجیره مصنوعی / concurrency=4، p50=3.290s، p95=3.481s، p99=3.535s، throughput=1.218/s؛ 9 آزمون crash/recovery؛ Artifact |

تمام شش Run بالا در GitHub با `completed/success` و **یک SHA یکسان** دیده شده‌اند. CI روی GitHub-hosted Runner، نه Managed Staging انجام شده است. هش‌های Artifact برای بازبینی در فایل JSON درج شده‌اند؛ اگر یک Job فقط Log داشته، فیلد Artifact صریحاً `null` است و هش جعل نشده. **Commit این بسته مستنداتی، پس از کد مبنا است**؛ Workflow صحت عدم تغییر کد از SHA مبنا را کنترل می‌کند.

## 4. خروجی کارهای تکمیل‌شده، با محدودیت واقعی
- **G01/G03:** مالکیت منطقی 19 موتور، قراردادهای v1/v2 و آداپتورهای read-only موجودند؛ پیشنهاد ADR-ENG-005 ناسازگاری شماره‌گذاری ADR-004 را شفاف کرده و SPIFFE `spiffe://abc.internal/staging/eng-XX` در کد هماهنگ است. امضای Architecture Owner هنوز وجود ندارد.
- **ENG-02/G05:** پیش‌شرط رضایت فعال برای هر دو هدف `CAPTURE` و `AI_PROCESSING`، متخصص واجد صلاحیت، نشست و نسخه جاری در SQL فقط‌خواندنی بررسی می‌شود؛ با وجود رضایت معتبر، Upload همچنان `501 capability_not_implemented` است. **هیچ نویسنده تصویر ساخته یا مجاز نشده است**. برای آینده کنترل رضایت باید در همان تراکنش واقعیِ نوشتن تکرار شود.
- **G04/G06:** اتصال synthetic موقت TLS/JWT، PostgreSQL ledger، ممانعت JTI تکراری با 3 گیرنده/8 کلاینت مستقل و زنجیره 5 فرایند OS ارزیابی شده است. هیچ یک اثبات PKI خارجی، service-account management، شبکه خصوصی Provider یا TLS فیزیکی PostgreSQL مدیریتشده نیست.
- **G07:** معیارهای تصویب‌نشده برای CI (100 sample, 4 concurrency) و p95/p99 ثبت و آزموده شده‌اند؛ تأخیر مدل/تصویر واقعی یا SLO عملیاتی از این داده استنتاج نمی‌شود.
- **G09:** `os._exit`، idempotency، SQLite synthetic restore، disposable PostgreSQL recovery و **قواعد هشدار آفلاین** آزموده شده‌اند؛ تحویل Pager، PITR واقعی، RTO/RPO ارائه‌دهنده و Rollback عملیاتی ثابت نشده‌اند.
- **ENG-05/06/G08:** آزمون رد منابع تأییدنشده و توقف در خطر موفق است؛ صلاحیت و حقوق استفاده حرفه‌ای منابع **به تأیید متخصص حقیقی نیاز دارد**. ENG-06 در `REVIEW_ONLY` و انتقال به ENG-07 / مشتری `BLOCKED` است.
- **G10:** هیچ رأی امضاشده مستقل وجود ندارد. درخواست برای کارشناسان باز است، ولی پرونده باز به معنای موافقت نیست.

## 5. بسته بررسی مستقل — بدون نیاز به خرید زیرساخت
| مسئول مستقل | کار قابل شروع همین حالا | فایل و پرونده برای تصمیم | وضعیت |
|---|---|---|---|
| Architecture Owner | تعیین قطعی مالکیت 19 موتور، ADR-003/004 و شماره/مبنای اعتماد ADR-005، سازگاری Adapterها | `docs/04-platform/ADR_ENG_003_*.md`، `ADR_ENG_004_V2_*.md`، `ADR_ENG_005_*.md`، [#58](https://github.com/saleheebrahimi2029-hub/abc-platform/issues/58) | PENDING |
| Security | ممیزی کد JWT/SPIFFE/mTLS، RLS/DB role، Replay، رضایت و سناریوهای جعل؛ تفکیک شواهد آزمایشی و واقعی | `governance/ABC_A2_ADR003_004_005_PREDEPLOYMENT_SECURITY_REVIEW_PACKET_20261105.md`، [#84](https://github.com/saleheebrahimi2029-hub/abc-platform/issues/84) | PENDING |
| Qualified Specialist | بررسی صلاحیت و حقوق منابع حرفه‌ای، عدم قطعیت، Contraindications، STOP Conditions، محدودیت خدمات واقعی | `governance/ENG06_ISOLATED_REVIEW_ACCEPTANCE_20261103.md`، [#79](https://github.com/saleheebrahimi2029-hub/abc-platform/issues/79) | PENDING |
| SRE | بازبینی آستانه‌های G07، Runbook/Alert Policy/G09، سناریوهای RPO/RTO/Backup؛ تعیین آزمون‌های محیط واقعی | `governance/ABC_A2_G07_G09_SYNTHETIC_ACCEPTANCE_v1.review.json`، [#85](https://github.com/saleheebrahimi2029-hub/abc-platform/issues/85) | PENDING |
| Owner/Governance | پذیرش دامنه A2 synthetic، تصمیم مستقل درباره استثناها و تعیین حد هزینه و ارائه‌دهنده در آینده | [#63](https://github.com/saleheebrahimi2029-hub/abc-platform/issues/63)، [#81](https://github.com/saleheebrahimi2029-hub/abc-platform/issues/81) | HOLD |

**قالب تصمیم هر بازبین واقعی**: نام و هویت تأییدشده، استقلال از نویسنده کد، صلاحیت، حوزه دقیق، SHA کد/بسته، SHA256 شواهد مورد بازبینی، نتیجه `APPROVE / REQUEST_CHANGES / REJECT`، استثناها، تاریخ، انقضا و امضای معتبر. همه این فیلدها در وضعیت کنونی **تهی و تأییدنشده** هستند. OpenAI/assistant هیچ امضایی به نام انسان صادر نمی‌کند.

## 6. موارد باز مستقل از هزینه (اولویت به ترتیب)
1. **P0:** تصمیم Architecture Owner درباره ADR-003/004/005 و مالکیت/نسخه قرارداد؛ امضای مستقل واقعی.
2. **P0:** بازبینی Security کد و Threat Model همراه با نگاشت حداقل مجوزها و TOCTOU گیت ENG-02؛ رأی مستند.
3. **P0:** بررسی و امضای متخصص واجد صلاحیت برای منبع/خدمت/محدودیت ENG-05/06؛ هیچ دسترسی به کاربر واقعی نیاز نیست.
4. **P0:** جمع‌بندی 80 خانه، برطرف کردن خانه‌های `NO_DIRECT_SCOPED_TEST_EVIDENCE` که **واقعاً برای دامنه synthetic A2 نیاز به آزمون بیشتر دارند** و ثبت تصمیم/استثنای معماری برای خانه‌هایی مانند G10 که ذاتاً آزمون نرم‌افزاری ندارند.
5. **P1:** تصویب SLO/Alert/Restore/Incident Playbook پیشنهادی و تعیین مالک On-call بدون فعال‌سازی پیام‌رسان.
6. **P1:** ممیزی تناقض نام‌گذاری `LEGACY_REVIEW_TRANSPORT` و عدم انتساب خطا به ENG-19.
7. **P1:** همگام‌سازی تصمیم و شناسه Commit نهایی در پرونده [#81](https://github.com/saleheebrahimi2029-hub/abc-platform/issues/81) بدون ارتقای مصنوعی `OPEN` به `PASS`.

## 7. کنترل‌های موکول به استقرار مجاز و هزینه
صدور هویت‌های خارجی مدیریت‌شده، PKI/Key rotation، پذیرش واقعی `hostssl clientcert=verify-full`، ACL خصوصی و آزمون direct-IP/DNS از شبکه دوم، Backup/PITR واقعی، مانیتورینگ و تحویل Alert به On-call، سنجش RTO/RPO و Performance روی Resource Class تصویب‌شده. مالک قبلاً صراحتاً دستور داده است **استقرار مستقل و هر ایجاد منبع جدید تا تأیید هزینه متوقف باشد**؛ این بسته آن را تغییر نمی‌دهد.

## 8. تصمیم نهایی A2
```text
PREDEPLOYMENT_DOCUMENTATION_AND_EVIDENCE_INDEX = READY_FOR_REVIEW
G01_TO_G10_SCOPE_COUNT                     = 8 (7 ENGINES + 1 LEGACY TRANSPORT)
GATE_COUNT                                  = 80
CI_TEST_REFERENCE_PRESENT                   = 55
NO_DIRECT_SCOPED_TEST_REFERENCE            = 25
INDEPENDENT_GATE_PASS                       = 0
ARCHITECTURE_SIGNOFF                        = PENDING
SECURITY_SIGNOFF                            = PENDING
SRE_SIGNOFF                                 = PENDING
QUALIFIED_SPECIALIST_SIGNOFF                = PENDING
OWNER_STAGING_COST_HOLD                     = ACTIVE
INDEPENDENT_STAGING                         = NOT_DEPLOYED
PROFESSIONAL_ENG06_RELEASE                  = BLOCKED
A2_OPERATIONAL_CLOSURE                      = OPEN
```

**این گزارش به‌هیچ‌عنوان مجوز Merge به main، فعال‌سازی Billing، صدور اعتبار حرفه‌ای، دریافت تصویر مشتری یا آزادسازی ENG-06/ENG-07 نیست.** هرگونه تغییر آینده در Runtime پس از Commit مبنا، مستلزم آزمون مجدد همان نسخه و ثبت شواهد تازه است.
