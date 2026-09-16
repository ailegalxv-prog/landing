# orbita-ix.com — лендінг «Автоматизація юридичних бізнес-процесів»

Статичний односторінковий сайт. Хостинг: **GitHub Pages** (репозиторій `ailegalxv-prog/landing`, публічний). Домен: **orbita-ix.com** (реєстратор і DNS — «Хостинг Україна», панель adm.tools).


## Структура

| Файл | Призначення |
|---|---|
| `public/index.html` | Лендінг (CSS і JS вбудовані, зовнішніх залежностей немає) |
| `public/404.html` | Сторінка «не знайдено» |
| `public/CNAME` | Власний домен для GitHub Pages — рядок `orbita-ix.com` |
| `public/favicon.svg`, `favicon.ico`, `apple-touch-icon.png` | Іконки |
| `public/og-image.png` | Превʼю посилання в месенджерах (1200×630) |
| `public/robots.txt`, `sitemap.xml` | Для пошуковиків |
| `.github/workflows/deploy.yml` | `check` у pull request, `deploy` — публікація після merge у `main` |

## Робочий процес

1. Гілка `feature/…` → pull request → рев'ю → merge у `main`.
2. Після merge job `deploy` публікує `public/` у Pages (2–3 хвилини).
3. Пряма робота в `main` не ведеться (гілка захищена).

Локальний перегляд: `python3 -m http.server -d public 8000` → http://localhost:8000

## Що перевіряє CI (job `check`)

- усі обовʼязкові файли лежать у `public/`, включно з `CNAME`;
- `public/CNAME` містить рівно `orbita-ix.com`;
- canonical `https://orbita-ix.com/` на місці;
- усі три кнопки ведуть у Telegram-бот із мітками джерела `hero`, `dock`, `contact`.

## Домен і SSL

**Settings → Pages** у репозиторії:

1. **Source** = `GitHub Actions`.
2. **Custom domain** = `orbita-ix.com` → Save. GitHub запустить перевірку DNS.
3. Після успішної перевірки — галочка **Enforce HTTPS** (сертифікат Let's Encrypt видається автоматично, до 1 години).

**adm.tools → Домени → orbita-ix.com → DNS-записи:**

| Імʼя | Тип | Значення |
|---|---|---|
| `@` | A | `185.199.108.153` |
| `@` | A | `185.199.109.153` |
| `@` | A | `185.199.110.153` |
| `@` | A | `185.199.111.153` |
| `@` | AAAA | `2606:50c0:8000::153` |
| `@` | AAAA | `2606:50c0:8001::153` |
| `@` | AAAA | `2606:50c0:8002::153` |
| `@` | AAAA | `2606:50c0:8003::153` |
| `www` | CNAME | `ailegalxv-prog.github.io` |

Старий A-запис `91.206.201.54` (парковка хостера) — видалити.

⚠️ **MX-запис (`mx.services`) і TXT-запис SPF (`v=spf1 include:_spf.ukraine.com.ua ~all`) не змінювати.** На домені працює пошта; A/AAAA і MX — незалежні записи, але випадкове видалення MX зламає пошту.

IP-адреси — з документації GitHub: https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/managing-a-custom-domain-for-your-github-pages-site

## Заявки

Усі три кнопки ведуть у Telegram-бот `@ai_legal_practice_bot` із різними мітками джерела:

| Кнопка | Посилання |
|---|---|
| У шапці, «Безкоштовний розбір процесів» | `?start=hero` |
| Плаваюча, «Записатись на розбір» | `?start=dock` |
| У блоці контактів, «Записатись на розбір у Telegram» | `?start=contact` |

Мітка приходить у бот першим повідомленням — за нею видно, яка кнопка приносить заявки.

## Rollback

- Контент: `Revert` у змердженому pull request → після merge CI перепублікує попередню версію.
- Сайт повністю: **Settings → Pages → Source = None** (або видалити `deploy.yml`).
- Домен: видалити A/AAAA/CNAME-записи в adm.tools (MX не чіпати).
