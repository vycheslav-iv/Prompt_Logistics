"""Prompt logistics — сборка промпта из независимых частей.

Две ноды, потому что ComfyUI отклоняет циклы графа: одна нода не может
одновременно отдать Промпт в LLM наружу и принять результат LLM обратно.

  Prompt logistics          — все пять переключателей и все входы; собирает
                              Промпт в LLM, прямой sys prompt mod и надбавку
                              к результату LLM
  Prompt logistics — MODEL  — без настроек: выбирает результат LLM или прямой
                              промпт и приклеивает надбавку

Только чистые функции: без таймеров, ожиданий, потоков и глобального
состояния. Текст частей не изменяется; непустые части склеиваются одним
пробелом.
"""


def _text(value):
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return str(value)


def _join(parts):
    kept = [part for part in (_text(p) for p in parts) if part.strip() != ""]
    return " ".join(kept)


class PromptLogistics:
    DESCRIPTION = (
        "Все настройки здесь. Входы: «Основной промпт», «Мастер-стиль», "
        "«Дополн. промпт» — любой дополнительный промпт.\n"
        "Выход «Промпт в LLM» = основной промпт "
        "[+ дополн. при «Дополн. промпт» и «Дополн. промпт в LLM»] "
        "[+ мастер-стиль при «Мастер-стиль» и «Мастер-стиль в LLM»].\n"
        "Выход «sys prompt mod» = основной промпт "
        "[+ дополн. при «Дополн. промпт»] [+ мастер-стиль при «Мастер-стиль»].\n"
        "Выход «sys prompt plus» = то, что добавляется к результату LLM: "
        "[дополн. при «Дополн. промпт» без «Дополн. промпт в LLM»] "
        "[+ мастер-стиль при «Мастер-стиль» и без «Мастер-стиль в LLM»].\n"
        "Порядок выходов: «Промпт в LLM», «sys prompt mod», "
        "«sys prompt plus», «sys use LLM».\n"
        "Подключите выходы к LLM и к ноде «Prompt logistics — MODEL»."
    )

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {},
            "optional": {
                "prompt": ("STRING", {
                    "forceInput": True,
                    "multiline": True,
                    "display_name": "Основной промпт",
                    "tooltip": "Основной промпт: человек/объект, окружение, действие.",
                }),
                "master": ("STRING", {
                    "forceInput": True,
                    "multiline": True,
                    "display_name": "Мастер-стиль",
                    "tooltip": "Мастер-стиль: стиль, качество, камера, свет. Попадает в "
                               "итог только при включённом «Мастер-стиль» ниже.",
                }),
                "int_prompt": ("STRING", {
                    "forceInput": True,
                    "multiline": True,
                    "display_name": "Дополн. промпт",
                    "tooltip": "Любой дополнительный промпт: обстановка, детали, уточнения, "
                               "второй объект — что угодно. Куда идёт — решают "
                               "«Дополн. промпт» и «Дополн. промпт в LLM» ниже.",
                }),
                "llm_prompt": ("BOOLEAN", {
                    "default": False,
                    "display_name": "LLM промпт",
                    "tooltip": "В модель идёт результат LLM («Промпт из LLM»), а не прямой "
                               "промпт. При OFF ветка LLM не запускается.",
                }),
                "style_prompt": ("BOOLEAN", {
                    "default": False,
                    "display_name": "Мастер-стиль",
                    "tooltip": "Главный выключатель входа «Мастер-стиль»: без него стиль "
                               "не идёт ни в LLM, ни в итоговый промпт.",
                }),
                "style_in_llm": ("BOOLEAN", {
                    "default": False,
                    "display_name": "Мастер-стиль в LLM",
                    "tooltip": "Куда идёт «Мастер-стиль»: в «Промпт в LLM» (вкл.) или в "
                               "«sys prompt plus» (выкл.). Работает только при "
                               "включённом «Мастер-стиль».",
                }),
                "use_int": ("BOOLEAN", {
                    "default": False,
                    "display_name": "Дополн. промпт",
                    "tooltip": "Участие входа «Дополн. промпт»: OFF — дополнительный промпт "
                               "не используется нигде.",
                }),
                "int_in_llm": ("BOOLEAN", {
                    "default": False,
                    "display_name": "Дополн. промпт в LLM",
                    "tooltip": "Куда идёт «Дополн. промпт»: в «Промпт в LLM» (вкл.) или в "
                               "«sys prompt plus» (выкл.). Работает только при "
                               "включённом «Дополн. промпт».",
                }),
            },
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING", "BOOLEAN")
    RETURN_NAMES = ("Промпт в LLM", "sys prompt mod", "sys prompt plus",
                    "sys use LLM")
    OUTPUT_TOOLTIPS = (
        "Промпт для внешней LLM: основной промпт [+ дополн. при «Дополн. промпт» "
        "и «Дополн. промпт в LLM»] [+ мастер-стиль при «Мастер-стиль» и "
        "«Мастер-стиль в LLM»].",
        "sys prompt mod — прямой промпт: основной промпт [+ дополн. при "
        "«Дополн. промпт»] [+ мастер-стиль при «Мастер-стиль»]. Подключите к "
        "входу «sys prompt mod» ноды «Prompt logistics — MODEL».",
        "sys prompt plus — надбавка к результату LLM: дополн. промпт и/или "
        "мастер-стиль. Подключите к одноимённому входу ноды "
        "«Prompt logistics — MODEL».",
        "sys use LLM — флаг «LLM промпт». Подключите к входу «sys use LLM» ноды "
        "«Prompt logistics — MODEL».",
    )
    FUNCTION = "compose"
    CATEGORY = "My_custom_nodes/Prompt Logistics"

    def compose(self, prompt="", master="", int_prompt="",
                llm_prompt=False, style_prompt=False, style_in_llm=False,
                use_int=False, int_in_llm=False):
        core = _join([prompt, int_prompt if use_int else None])
        direct = _join([core, master if (style_prompt and core) else None])
        llm = _join([
            prompt,
            int_prompt if (use_int and int_in_llm) else None,
            master if (style_prompt and style_in_llm) else None,
        ])
        suffix = _join([
            int_prompt if (llm_prompt and use_int and not int_in_llm) else None,
            master if (llm_prompt and style_prompt and not style_in_llm) else None,
        ])
        return (llm, direct, suffix, bool(llm_prompt))


class PromptLogisticsModel:
    DESCRIPTION = (
        "Итоговый промпт для модели. Настроек нет: все переключатели — "
        "на ноде «Prompt logistics».\n"
        "«LLM промпт» выключен: берётся вход «sys prompt mod» (прямой промпт), "
        "а LLM не запускается (вход «Промпт из LLM» ленивый).\n"
        "«LLM промпт» включён: берётся «Промпт из LLM» + вход «sys prompt plus» "
        "(дополн. промпт и/или мастер-стиль).\n"
        "Пустой «Промпт из LLM» не заменяется исходным промптом."
    )

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {},
            "optional": {
                "llm_result": ("STRING", {
                    "forceInput": True,
                    "multiline": True,
                    "lazy": True,
                    "display_name": "Промпт из LLM",
                    "tooltip": "Результат внешней LLM. Ленивый вход: при "
                               "выключенном «LLM промпт» ветка LLM не "
                               "выполняется.",
                }),
                "direct": ("STRING", {
                    "forceInput": True,
                    "multiline": True,
                    "display_name": "sys prompt mod",
                    "tooltip": "Выход «sys prompt mod» ноды «Prompt logistics»: прямой "
                               "промпт (без результата LLM).",
                }),
                "suffix": ("STRING", {
                    "forceInput": True,
                    "multiline": True,
                    "display_name": "sys prompt plus",
                    "tooltip": "Выход «sys prompt plus» ноды «Prompt logistics»: что "
                               "добавить к результату LLM.",
                }),
                "use_llm": ("BOOLEAN", {
                    "forceInput": True,
                    "default": False,
                    "display_name": "sys use LLM",
                    "tooltip": "Выход «sys use LLM» ноды «Prompt logistics»: флаг "
                               "«LLM промпт» — брать результат LLM или прямой промпт.",
                }),
            },
            "hidden": {
                "prompt": "PROMPT",
                "unique_id": "UNIQUE_ID",
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("Итоговый промпт",)
    OUTPUT_TOOLTIPS = (
        "Итоговый промпт: результат LLM или прямой промпт, плюс надбавка.",
    )
    FUNCTION = "finalize"
    CATEGORY = "My_custom_nodes/Prompt Logistics"

    def check_lazy_status(self, llm_result=None, direct="", suffix="",
                          use_llm=False, prompt=None, unique_id=None):
        if not use_llm or llm_result is not None:
            return []
        link = None
        if isinstance(prompt, dict):
            node = prompt.get(str(unique_id))
            if not isinstance(node, dict):
                node = prompt.get(unique_id)
            if isinstance(node, dict):
                link = (node.get("inputs") or {}).get("llm_result")
        if (isinstance(link, (list, tuple)) and len(link) == 2
                and isinstance(link[1], int) and not isinstance(link[1], bool)):
            return ["llm_result"]
        return []

    def finalize(self, llm_result="", direct="", suffix="", use_llm=False,
                 prompt=None, unique_id=None):
        base = _text(llm_result) if use_llm else _text(direct)
        if base.strip() == "":
            return ("",)
        return (_join([base, suffix]),)


NODE_CLASS_MAPPINGS = {
    "PromptLogistics": PromptLogistics,
    "PromptLogisticsModel": PromptLogisticsModel,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PromptLogistics": "Prompt logistics",
    "PromptLogisticsModel": "Prompt logistics — MODEL",
}
