# Prompt Logistics

Две ноды для сборки промпта и маршрута «промпт → LLM → итоговый промпт»
в ComfyUI (Nodes 2.0). Все пять переключателей — на первой ноде; вторая
настроек не имеет.

## Зачем две ноды

ComfyUI не пропускает цикл «нода → LLM → та же нода» (HTTP 400,
`dependency_cycle`). Поэтому маршрут разорван на две ноды, провода идут
только вперёд:

```
ПрОб ─────┬─> Prompt logistics ──> LLM PROMPT ──> LLM
ПрМаст ───┤        │  MODEL PROMPT (прямой)      │
INT Prompt┘        │  ДОП к ПрLLM                │
                   │  USE LLM                   │
                   v                            v
            Prompt logistics — MODEL <──────────┘
                   │
                   v
              MODEL PROMPT ──> CLIP Text Encode
```

## Prompt logistics — все настройки здесь

Входы: `ПрОб`, `ПрМаст`, `INT Prompt` (все необязательные).
Переключатели: `LLM Prompt`, `STYLE Prompt`, `STYLE в LLM`, `INT`, `INT в LLM`.
Выходы: `MODEL PROMPT (прямой)`, `LLM PROMPT`, `ДОП к ПрLLM`, `USE LLM`.

- `INT в LLM` работает только при включённом `INT`; при выключенном `INT`
  интерьерный промпт не участвует нигде.
- `STYLE Prompt` — главный выключатель стиля, `STYLE в LLM` — только маршрут.
  `STYLE Prompt` OFF → `ПрМаст` не идёт ни в LLM, ни в итог, даже если
  `STYLE в LLM` включён. `STYLE Prompt` ON: `STYLE в LLM` ON → `ПрМаст` в
  `LLM PROMPT`, `STYLE в LLM` OFF → `ПрМаст` добавляется к итогу после LLM.
  Дубля нет ни в одном режиме.

## Prompt logistics — MODEL — без настроек

Входы: `ПрLLM` (результат LLM), `MODEL PROMPT (прямой)`, `ДОП к ПрLLM`,
`USE LLM` — все четыре подключаются к выходам первой ноды.
Выход: `MODEL PROMPT`.

- `USE LLM` OFF — берётся прямой промпт.
- `USE LLM` ON — берётся `ПрLLM` плюс `ДОП к ПрLLM`; пустой результат **не**
  заменяется исходным промптом.
- `ДОП к ПрLLM` содержит `INT Prompt` (если `INT` включён, а `INT в LLM` нет)
  и `ПрМаст` (если `STYLE Prompt` включён, а `STYLE в LLM` нет).

## LLM не запускается зря

Вход `ПрLLM` — ленивый (`lazy` + `check_lazy_status`). Пока `LLM Prompt`
выключен, ComfyUI не запрашивает ветку LLM: Ollama не выполняется даже на
первом прогоне (кэш для этого не нужен). Это тот же результат, что даёт
`ComfySwitchNode` в рабочей схеме, но без третьей ноды.

## Правила склейки

Части не изменяются; пустые пропускаются; между частями ровно один пробел;
служебные подписи в промпт не попадают.

## Установка

```bash
python sync.py Prompt_Logistics
```

Затем перезапустить ComfyUI и обновить страницу (Ctrl+F5).

## Проверки

```bash
cd Prompt_Logistics
python tests/_test_prompt_logistics.py
node tests/_audit_prompt_logistics.mjs
python tests/_probe_live_prompt_logistics.py    # нужен запущенный ComfyUI
```

Подробности — в `SPECIFICATION.md`.
