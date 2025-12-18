# PM2 — Руководство

## Установка

```bash
npm install -g pm2
npm install -g pm2-windows-startup
```

## Автозапуск Windows

```bash
pm2-startup install    # включить автозапуск
pm2-startup uninstall  # выключить автозапуск
```

## Запуск бота

```bash
pm2 start bot.py --interpreter python   # запустить
pm2 save                                 # сохранить для автозапуска
```

## Управление

```bash
pm2 status          # статус всех процессов
pm2 logs            # логи в реальном времени
pm2 logs bot        # логи конкретного процесса
pm2 restart bot     # перезапустить
pm2 stop bot        # остановить
pm2 delete bot      # удалить из pm2
pm2 list            # список процессов
```

## Полное удаление

```bash
pm2 stop all                # остановить все
pm2 delete all              # удалить все процессы
pm2-startup uninstall       # убрать из автозапуска
npm uninstall -g pm2        # удалить pm2
npm uninstall -g pm2-windows-startup
```

