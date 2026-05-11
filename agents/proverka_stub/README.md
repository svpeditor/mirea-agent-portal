# proverka_stub

Stub-агент под контракт SDK v0.1 (План 1.4, milestone-0).

Имитирует работу `proverka` — анализ конкурсных работ школьников. Сканирует папку, считает файлы и размер, возвращает сводный Word и zip с per-work заглушками. Real-версия живёт в локальном репо Дани и подтянется в milestone-1 (см. `docs/superpowers/plans/2026-05-10-1.4-agents-port.md`).

## Запуск без Docker

```bash
# из корня репо
pip install -e packages/portal-sdk-python python-docx
mkdir -p /tmp/proverka_input/works/work-1 /tmp/proverka_input/works/work-2
echo "test" > /tmp/proverka_input/works/work-1/draft.pdf
echo "test" > /tmp/proverka_input/works/work-2/draft.docx

PARAMS_FILE=/tmp/proverka_params.json
echo '{"competition":"ВНТК-2025","grade_level":"10-11"}' > $PARAMS_FILE

INPUT_DIR=/tmp/proverka_input \
OUTPUT_DIR=/tmp/proverka_output \
PARAMS_FILE=$PARAMS_FILE \
python agents/proverka_stub/agent.py
```

Или через CLI:

```bash
portal-sdk-run-local agents/proverka_stub --params '{"competition":"ВНТК","grade_level":"10-11"}'
```

## Публикация через портал

```bash
curl -X POST http://localhost:8000/api/admin/agents \
  -b admin-cookies.txt \
  -H "Content-Type: application/json" \
  -d '{"git_url": "<репо со stub-агентом>", "git_ref": "main"}'
```

Когда Даня даст ОК, manifest и контракт останутся теми же, поменяется только `agent.py` + `requirements.txt` под реальный код проверки работ.
