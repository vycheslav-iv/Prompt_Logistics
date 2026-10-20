# Prompt Logistics — спецификация

Две ноды ComfyUI для сборки промпта из независимых частей и для маршрута
«промпт → внешняя LLM → итоговый промпт модели». Все пять переключателей
находятся на главной ноде; вторая нода настроек не имеет.

```
My_custom_nodes/Prompt Logistics
  Prompt logistics          — все входы и переключатели, LLM PROMPT,
                              прямой MODEL PROMPT и надбавка к результату LLM
  Prompt logistics — MODEL  — без настроек: выбирает LLM/прямой и приклеивает
                              надбавку
```

## 1. Почему две ноды, а не одна

ТЗ требует, чтобы `LLM PROMPT` уходил во внешнюю LLM и результат возвращался
во вход `ПрLLM` этой же ноды. Это цикл в графе. ComfyUI его отклоняет на
валидации, до выполнения:

```
POST /prompt → HTTP 400
{"type": "prompt_outputs_failed_validation", ...,
 "type": "dependency_cycle",
 "message": "Dependency cycle detected",
 "details": "1 (StringConcatenate) -> 2 (StringConcatenate) -> 1"}
```

Точки в коде ComfyUI 0.41.0: `execution.py` (валидация входов,
`dependency_cycle`), `comfy_execution/graph.py:308` (`DependencyCycleError`),
`comfy_execution/validation.py` (`validate_loops`).

Обходные пути отвергнуты: таймеры и опрос запрещены ТЗ; `PromptKeeper`
отдаёт текст прошлого прогона (ручное ожидание); `StartLoop/EndLoop` — это
три и более нод и повторные прогоны LLM.

Разрыв цикла: нода **S** отдаёт `LLM PROMPT` наружу, нода **F** принимает
результат LLM (`ПрLLM`) и прямой промпт от S. Провода идут только вперёд.

## 2. Prompt logistics (S) — все настройки здесь

Входы (все необязательные, link-only, STRING):

| Вход | display_name | Смысл |
|---|---|---|
| `prompt` | `ПрОб` | основной промпт |
| `master` | `ПрМаст` | мастер-промпт (стиль, качество) |
| `int_prompt` | `INT Prompt` | интерьерный промпт |

Переключатели (BOOLEAN, по умолчанию OFF, независимы):

| Ключ | display_name | Действие |
|---|---|---|
| `llm_prompt` | `LLM Prompt` | в модель идёт результат LLM, а не прямой промпт |
| `style_prompt` | `STYLE Prompt` | главный выключатель `ПрМаст`: без него стиль не идёт ни в LLM, ни в итог |
| `style_in_llm` | `STYLE в LLM` | маршрут `ПрМаст`: в `LLM PROMPT` (вкл.) или в `ДОП к ПрLLM` (выкл.); действует только при `STYLE Prompt` |
| `use_int` | `INT` | `INT Prompt` участвует в сборке |
| `int_in_llm` | `INT в LLM` | маршрут `INT Prompt`: в LLM (вкл.) или в `ДОП к ПрLLM` (выкл.); действует только при `INT` |

`INT в LLM` работает только вместе с `INT`: если `INT` выключен, `INT Prompt`
не задействован нигде.

Выходы:

| Выход | Тип | Формула |
|---|---|---|
| `MODEL PROMPT (прямой)` | STRING | `ПрОб` [`INT Prompt` при `INT`] [`ПрМаст` при `STYLE Prompt`] |
| `LLM PROMPT` | STRING | `ПрОб` [`INT Prompt` при `INT` и `INT в LLM`] [`ПрМаст` при `STYLE Prompt` и `STYLE в LLM`] |
| `ДОП к ПрLLM` | STRING | [`INT Prompt` при `LLM Prompt`, `INT` и не `INT в LLM`] [`ПрМаст` при `LLM Prompt`, `STYLE Prompt` и не `STYLE в LLM`] |
| `USE LLM` | BOOLEAN | значение `LLM Prompt` |

`MODEL PROMPT (прямой)` — прямой промпт для подключения к ноде F; итоговый
`MODEL PROMPT` выдаёт F. `ПрМаст` не образует промпт сам: если `ПрОб` и
`INT Prompt` пусты, прямой промпт пуст.

`MODEL PROMPT (прямой)` всегда содержит `INT Prompt` при включённом `INT`,
в том числе когда `INT в LLM` ON: роутер перенаправляет `INT Prompt` в
`LLM PROMPT`, но из прямого выхода его не убирает. Дубля в итоговом
`MODEL PROMPT` при этом нет — прямой выход используется только при
выключенном `LLM Prompt`, а `ДОП к ПрLLM` маршрутизированные части не содержит.

## 3. Prompt logistics — MODEL (F) — без настроек

Входы (все необязательные, link-only):

| Вход | display_name | Тип | Смысл |
|---|---|---|---|
| `llm_result` | `ПрLLM` | STRING | результат внешней LLM |
| `direct` | `MODEL PROMPT (прямой)` | STRING | выход S |
| `suffix` | `ДОП к ПрLLM` | STRING | выход S: что добавить к результату LLM |
| `use_llm` | `USE LLM` | BOOLEAN | выход S: флаг `LLM Prompt` |

Выход `MODEL PROMPT`:

```
база = ПрLLM, если USE LLM, иначе прямой промпт
база пуста → ""
иначе база [ + " " + ДОП к ПрLLM]
```

Вся логика условий посчитана в S, поэтому F — чистая склейка двух строк.
`INT Prompt` на этом шаге повторно не добавляется. Пустой `ПрLLM` не
заменяется исходным промптом: в режиме LLM при пустом результате выход пуст.

### 3.1. Ленивый `ПрLLM` — LLM не запускается зря

Вход `llm_result` помечен `"lazy": True`, у F есть `check_lazy_status`.
Пока `USE LLM` не пришёл включённым, ComfyUI **не запрашивает** ветку LLM:
Ollama и всё, что стоит за ней, не выполняется — на первом прогоне тоже
(кэш не нужен).

```
check_lazy_status(llm_result, direct, suffix, use_llm, prompt, unique_id):
    not use_llm или llm_result уже есть → []
    иначе, если в prompt[unique_id] вход llm_result — связь [id, slot] → ["llm_result"]
    иначе → []          # вход не подключён или литерал: ComfyUI упал бы NodeInputError
```

Запрос ленивого входа, который не подключён (или подключён литералом),
`Graph.make_input_strong_link` превращает в `NodeInputError`, поэтому
проверка связи обязательна. Скрытые входы `prompt` (`PROMPT`) и `unique_id`
(`UNIQUE_ID`) объявлены в `INPUT_TYPES` и принимаются `finalize` как
необязательные параметры — на результат они не влияют.

Это тот же приём, что в рабочей схеме пользователя с `ComfySwitchNode`
(переключатель между выходом Ollama и `LLM PROMPT`), но без третьей ноды и
без потери наглядности: ленивость решает сам ComfyUI по графу.

## 4. Режимы

| LLM Prompt | STYLE в LLM | INT | INT в LLM | STYLE Prompt | LLM PROMPT | MODEL PROMPT |
|---|---|---|---|---|---|---|
| OFF | OFF | OFF | — | OFF | `ПрОб` | `ПрОб` |
| OFF | OFF | ON | — | OFF | `ПрОб` | `ПрОб INT` |
| OFF | ON | OFF | — | OFF | `ПрОб` | `ПрОб` |
| OFF | ON | ON | ON | OFF | `ПрОб INT` | `ПрОб INT` |
| OFF | OFF | ON | — | ON | `ПрОб` | `ПрОб INT ПрМаст` |
| ON | OFF | OFF | — | OFF | `ПрОб` | `ПрLLM` |
| ON | OFF | OFF | — | ON | `ПрОб` | `ПрLLM ПрМаст` |
| ON | OFF | ON | ON | OFF | `ПрОб INT` | `ПрLLM` |
| ON | OFF | ON | ON | ON | `ПрОб INT` | `ПрLLM ПрМаст` |
| ON | OFF | ON | OFF | OFF | `ПрОб` | `ПрLLM INT` |
| ON | OFF | ON | OFF | ON | `ПрОб` | `ПрLLM INT ПрМаст` |
| ON | ON | OFF | — | OFF | `ПрОб` | `ПрLLM` |
| ON | ON | OFF | — | ON | `ПрОб ПрМаст` | `ПрLLM` |
| ON | ON | ON | ON | ON | `ПрОб INT ПрМаст` | `ПрLLM` |
| ON | ON | ON | ON | OFF | `ПрОб INT` | `ПрLLM` |

`STYLE Prompt` — главный выключатель стиля, `STYLE в LLM` — только маршрут
(куда идёт `ПрМаст` при включённом `STYLE Prompt`). `STYLE Prompt` OFF →
`ПрМаст` не попадает ни в `LLM PROMPT`, ни в итог, даже если `STYLE в LLM`
включён. `STYLE Prompt` ON + `STYLE в LLM` OFF → `ПрМаст` добавляется к итогу
после LLM. `STYLE Prompt` ON + `STYLE в LLM` ON → `ПрМаст` уходит в
`LLM PROMPT` и в `ДОП к ПрLLM` не повторяется. Дубля нет ни в одном режиме.
`INT` — такой же главный выключатель, `INT в LLM` — его маршрут: при
выключенном `INT` `INT Prompt` не участвует нигде.

## 5. Склейка

- Части сохраняются без изменений (внутренние пробелы и переносы строк — как есть).
- Неподключённые, пустые и пробельные части пропускаются.
- Между непустыми частями — ровно один пробел; в начале и конце результата
  пробелы не добавляются.
- Служебные подписи (`ПрОб`, `INT`, `LLM` и т. п.) в результат не попадают.
- Порядок частей фиксирован: `ПрОб`, `INT Prompt`, `ПрМаст`.

## 6. Совместимость с Nodes 2.0

- Чистый Python (`INPUT_TYPES`/`RETURN_TYPES`), без JS-расширения, без
  `WEB_DIRECTORY`, без canvas-виджетов и `computeSize`.
- Подписи входов и переключателей заданы через `display_name` — Nodes 2.0
  читает его как `localized_name`/`label` (frontend: `services/litegraphService.ts`).
- Никаких таймеров, `sleep`, потоков, сети, файлов и глобального состояния.
- Ленивый вход — штатная механика ComfyUI (`lazy` + `check_lazy_status`), не
  таймер и не ручное ожидание.
- Ноды детерминированы и кэшируются ComfyUI по входам.

## 7. Установка

Исходник: `F:\AI_projects\Custom_node_ComfyUI\Prompt_Logistics\`.

```bash
python sync.py Prompt_Logistics
```

Рабочая копия: `D:\ComfyUI_windows_portable\ComfyUI\custom_nodes\Prompt_Logistics\`.
После синхронизации — перезапуск ComfyUI и обновление страницы (Ctrl+F5).

## 8. Проверки

```bash
cd Prompt_Logistics
python tests/_test_prompt_logistics.py
node tests/_audit_prompt_logistics.mjs
python ../_process/check.py Prompt_Logistics
```

Python-песочница (123 проверки): все режимы ТЗ, `STYLE Prompt`/`INT` как
главные выключатели, `STYLE в LLM`/`INT в LLM` как маршруты (при выключенном
выключателе часть не попадает ни в LLM, ни в итог), правило
«`ПрМаст` без дубля», ленивый `ПрLLM` (`check_lazy_status` на всех ветках, включая
неподключённый вход и литерал), контракт `INPUT_TYPES`.

Аудит (78 проверок): контракт двух нод, пять переключателей только на S,
F без настроек, `lazy` + `check_lazy_status` + скрытые `PROMPT`/`UNIQUE_ID`,
gate `style_prompt and style_in_llm` / `use_int and int_in_llm`, отсутствие
таймеров/сети/глобального состояния и legacy-canvas.

Живая проба (48 проверок, `tests/_probe_live_prompt_logistics.py`, нужен
запущенный ComfyUI): те же режимы на живом сервере, кейс 6b (`STYLE Prompt` +
`STYLE в LLM` через провод) и ленивость по времени — с медленной нодой в
ветке LLM прогон с выключенным `LLM Prompt` завершается быстро (0.2 c),
с включённым — ждёт её (4.0 c).
