# Echo-агент

Минимальный пример агента для платформы. Используется как:

1. **Reference-имплементация** — образец того, как пользоваться `portal_sdk`.
2. **Smoke-test портала** — после деплоя одним запуском проверяется, что вся цепочка работает.

## Локальный запуск без портала

```bash
cd packages/portal-sdk-python && source .venv/bin/activate && cd ../..
portal-sdk-run-local agents/echo
```

Появится интерактивный prompt с полями из manifest. Артефакты — в `./_local_output/`.

## Что в манифесте

- `inputs`: text + number + checkbox — все три простых типа полей
- `files`: пусто (агент не принимает файлов)
- `outputs`: 2 артефакта — Word (primary) и JSON

Если хочешь увидеть как обрабатываются файлы — смотри `agents/proverka` (после Спека 1.4).
