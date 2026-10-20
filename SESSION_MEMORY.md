# Память сессии — Prompt_Logistics (2026-10-20)

> Покажи этот файл агенту, чтобы продолжить работу.
> Всегда сверяйся с `AGENTS.md` и `SPECIFICATION.md`.

---

## 1. Что делали в этой сессии
- Починили семантику `STYLE`: `STYLE Prompt` — главный выключатель, `STYLE в LLM` —
  только маршрут. До фикса `master` уходил в LLM при `STYLE Prompt` OFF.
- Добавили красные тесты, обновили доки/аудит/пробу, перезапустили ComfyUI и
  подтвердили «после» живой пробой (48/0). Сервер после проверки остановлен.
- Создали скил `comfyui-lazy-input` и завели git-репозиторий.

## 2. Итоговое состояние кода
- `prompt_logistics.py:112` — `PromptLogistics.compose` — `llm` = `ПрОб` +
  `INT` при `use_int and int_in_llm` + `master` при `style_prompt and style_in_llm`.
- `prompt_logistics.py:120` — `direct` = `ПрОб`+`INT` при `INT` + `master` при
  `style_prompt` (роутер из прямого выхода не убирает `INT`).
- `prompt_logistics.py:125` — `suffix` = `INT`/`master` только при `llm_prompt`,
  включённом выключателе и `not ..._in_llm`.
- `prompt_logistics.py:177` — `check_lazy_status` — `["llm_result"]` только при
  `use_llm`, `None` и реальной связи `[id, slot]`; иначе `[]`.
- `prompt_logistics.py:191` — `finalize` — `llm_result` при `USE LLM`, иначе `direct`.
- Проверки: Python **123**, аудит **78**, живая проба **48** — все `FAIL: 0`.

## 3. Проблемы, которые встречались (и как решали)
- «`ПрМаст` в LLM при `STYLE Prompt` OFF» — в `llm` не было гейта `style_prompt`;
  добавлен `master if (style_prompt and style_in_llm) else None`, тесты 4 → RED → GREEN.
- Аудит «`ПрМаст` без дубля» покраснел после переноса строки в SPEC — фраза должна
  оставаться на одной строке (`/без дубля/`).
- Живая проба на старом сервере давала `'сцена комната стиль'` вместо
  `'сцена комната'` — это и было доказательство «до»; после рестарта 48/0.

## 4. Что важно не сломать
- Цикл `S → LLM → S` невозможен: ComfyUI отклоняет `dependency_cycle` (HTTP 400).
  Разрыв — вторая нода F, провода только вперёд.
- `STYLE Prompt`/`INT` — выключатели; `STYLE в LLM`/`INT в LLM` — только маршруты.
- `ДОП к ПрLLM` наполняется только при `LLM Prompt` ON и никогда не содержит
  часть, ушедшую в LLM (`not ..._in_llm`).
- `check_lazy_status` обязан молчать без реальной связи, иначе `NodeInputError`.
- `MODEL PROMPT (прямой)` всегда содержит `INT` при `INT` (это не дубль: выход
  используется только при `LLM Prompt` OFF).
- `display_name` — единственный источник подписей в Nodes 2.0; без JS и
  `WEB_DIRECTORY`. Синхронизация: `python sync.py Prompt_Logistics` + рестарт.

## 5. Следующие шаги
- При необходимости — кейс `ComfySwitchNode` в живой пробе (третья нода не нужна).
- Прогонять `_process/check.py` и живую пробу после любых правок `compose`.

## 6. Связанные файлы
- `prompt_logistics.py`, `SPECIFICATION.md`, `README.md`, `check.json`
- `tests/_test_prompt_logistics.py`, `tests/_audit_prompt_logistics.mjs`,
  `tests/_probe_live_prompt_logistics.py`
- Скилы: `comfyui-cycle-node-split`, `comfyui-lazy-input`
