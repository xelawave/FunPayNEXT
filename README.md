# FunPayNEXT

FunPayNEXT автоматизирует работу продавца на FunPay. Бот отвечает на сообщения, выдаёт товары по оплаченным заказам, управляет лотами и отправляет уведомления в Telegram.

## Что изменилось

- Удалены рассылки разработчика и рекламные ссылки из Telegram и установщика.
- Новые сообщения, отзывы и изображения отправляются без водяных знаков. Предыдущие сообщения бота распознаются при чтении истории.
- Установщик, обновления и ссылки в боте используют репозиторий FunPayNEXT.
- Для существующих установок поддерживаются старые конфиги и импорты плагинов.

## Возможности

- Автовыдача товаров и настройка шаблонов с переменными.
- Автоответы на команды, приветствия и ответы на отзывы.
- Поднятие лотов, восстановление после продажи и отключение при исчерпании товара.
- Уведомления о сообщениях, заказах, выдаче и отзывах в одном или нескольких чатах Telegram.
- Панель управления в Telegram и расширение функций через Python-плагины.

## Установка

Для запуска из исходников нужен Python 3.11 или новее. Мастер настройки запрашивает `golden_key` аккаунта FunPay, токен Telegram-бота и пароль для панели управления. Имя пользователя Telegram-бота должно начинаться с `funpay`.

### Windows

1. Установите Python и включите `Add python.exe to PATH`. [Python для Windows](https://www.python.org/downloads/windows/)
2. Распакуйте архив исходников. [Скачать FunPayNEXT](https://github.com/xelawave/FunPayNEXT/archive/refs/heads/main.zip)
3. Запустите `Setup.bat`, затем `Start.bat` и пройдите первичную настройку.
4. Запустите `Start.bat` повторно и отправьте Telegram-боту `/menu`.

### Linux с systemd

На Ubuntu загрузите и запустите установщик. Он создаст службу для выбранного пользователя.

```bash
curl -fLO https://raw.githubusercontent.com/xelawave/FunPayNEXT/main/install-funpaynext.sh
bash install-funpaynext.sh
```

Установщик по умолчанию берёт исходники из `main`. Чтобы закрепить версию, скачайте скрипт из нужного тега или коммита и передайте этот же идентификатор через `FUNPAYNEXT_REF`. Состояние службы показывает `systemctl status funpaynext@ИМЯ_ПОЛЬЗОВАТЕЛЯ`.

### Docker Compose

Склонируйте репозиторий или распакуйте архив и выполните команды из папки проекта.

```bash
docker compose build
docker compose run --rm funpaynext
docker compose up -d
```

Вторая команда запускает мастер первоначальной настройки. Логи доступны через `docker compose logs -f`. Каталоги `configs`, `storage`, `plugins` и `logs` хранятся на хосте.

## Переход с FunPay Cardinal

1. Остановите старый экземпляр. Для systemd используйте `sudo systemctl stop FunPayCardinal@ИМЯ_ПОЛЬЗОВАТЕЛЯ`. Для Docker запустите `docker compose down` в старой папке.
2. Создайте резервную копию `configs`, `storage`, `plugins` и `logs`, затем скопируйте эти каталоги в отдельную папку FunPayNEXT. При установке через systemd это `/home/ИМЯ_ПОЛЬЗОВАТЕЛЯ/funpaynext`.
3. Запустите FunPayNEXT и проверьте вход, уведомления и плагины. Устаревшие настройки рассылок и `watermark` можно оставить в конфиге.
4. После проверки отключите автозапуск старой службы. Для отката остановите FunPayNEXT и запустите старую установку из её папки.

Команды `/check_updates` и `/update` используют стабильные выпуски FunPayNEXT. Если выпусков пока нет, обновите исходники вручную после резервного копирования. [Выпуски FunPayNEXT](https://github.com/xelawave/FunPayNEXT/releases)

## Плагины и разработка

Установка плагина доступна в Telegram через `/menu` → **Плагины** → **Добавить плагин**. Используйте файлы из источников, которым доверяете.

Новые плагины могут импортировать `FunPayNEXT` и `get_app` из `funpaynext`. Для существующих плагинов доступны `cardinal.Cardinal`, `cardinal.get_cardinal` и `Utils.cardinal_tools`. Пакет `FunPayAPI` можно использовать отдельно.

Тесты запускаются после установки зависимостей из `requirements.txt`.

```bash
python -m unittest discover -s tests -v
```

## Обратная связь

Ошибки и предложения можно оставить в Issues. [FunPayNEXT Issues](https://github.com/xelawave/FunPayNEXT/issues)

FunPayNEXT основан на FunPay Cardinal, созданном Woopertail и sidor0912. [Исходный проект](https://github.com/sidor0912/FunPayCardinal)
