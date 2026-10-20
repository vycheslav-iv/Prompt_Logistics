"""Prompt logistics — сборка промпта из независимых частей.

Две ноды, потому что ComfyUI отклоняет циклы графа: одна нода не может
одновременно отдать LLM PROMPT наружу и принять результат LLM обратно.

  Prompt logistics          — все пять переключателей и все входы; собирает
                              LLM PROMPT, прямой MODEL PROMPT и надбавку
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
        "Все настройки здесь.\n"
        "LLM PROMPT = ПрОб [+ INT Prompt при «INT» и «INT в LLM»] "
        "[+ ПрМаст при «STYLE Prompt» и «STYLE в LLM»].\n"
        "MODEL PROMPT (прямой) = ПрОб [+ INT Prompt при «INT»] "
        "[+ ПрМаст при «STYLE Prompt»].\n"
        "«ДОП к ПрLLM» = то, что добавляется к результату LLM: "
        "[INT Prompt при «INT» без «INT в LLM»] "
        "[+ ПрМаст при «STYLE Prompt» и без «STYLE в LLM»].\n"
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
                    "display_name": "ПрОб",
                    "tooltip": "Основной промпт: человек/объект, окружение, действие.",
                }),
                "master": ("STRING", {
                    "forceInput": True,
                    "multiline": True,
                    "display_name": "ПрМаст",
                    "tooltip": "Мастер-промпт: стиль, качество, камера, свет.",
                }),
                "int_prompt": ("STRING", {
                    "forceInput": True,
                    "multiline": True,
                    "display_name": "INT Prompt",
                    "tooltip": "Интерьерный промпт: обстановка, мебель, материалы.",
                }),
                "llm_prompt": ("BOOLEAN", {
                    "default": False,
                    "display_name": "LLM Prompt",
                    "tooltip": "В модель идёт результат LLM, а не прямой промпт.",
                }),
                "style_prompt": ("BOOLEAN", {
                    "default": False,
                    "display_name": "STYLE Prompt",
                    "tooltip": "Главный выключатель ПрМаст: без него стиль "
                               "не идёт ни в LLM, ни в итоговый промпт.",
                }),
                "style_in_llm": ("BOOLEAN", {
                    "default": False,
                    "display_name": "STYLE в LLM",
                    "tooltip": "Куда идёт ПрМаст: в LLM PROMPT (вкл.) или в "
                               "итоговый промпт (выкл.). Работает только при "
                               "«STYLE Prompt».",
                }),
                "use_int": ("BOOLEAN", {
                    "default": False,
                    "display_name": "INT",
                    "tooltip": "Участие INT Prompt: в LLM или в промпт модели.",
                }),
                "int_in_llm": ("BOOLEAN", {
                    "default": False,
                    "display_name": "INT в LLM",
                    "tooltip": "Куда идёт INT Prompt: в LLM (вкл.) или в "
                               "итоговый промпт (выкл.). Работает только при «INT».",
                }),
            },
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING", "BOOLEAN")
    RETURN_NAMES = ("MODEL PROMPT (прямой)", "LLM PROMPT", "ДОП к ПрLLM", "USE LLM")
    OUTPUT_TOOLTIPS = (
        "Прямой промпт: ПрОб [+ INT Prompt] [+ ПрМаст]. Подключите к входу "
        "«MODEL PROMPT (прямой)» ноды «Prompt logistics — MODEL».",
        "Промпт для внешней LLM: ПрОб [+ INT Prompt при «INT» и «INT в LLM»] "
        "[+ ПрМаст при «STYLE Prompt» и «STYLE в LLM»].",
        "Надбавка к результату LLM: INT Prompt и/или ПрМаст. Подключите к "
        "одноимённому входу ноды «Prompt logistics — MODEL».",
        "Флаг «LLM Prompt». Подключите к входу «USE LLM» ноды "
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
        return (direct, llm, suffix, bool(llm_prompt))


class PromptLogisticsModel:
    DESCRIPTION = (
        "Итоговый MODEL PROMPT для модели. Настроек нет: все переключатели — "
        "на ноде «Prompt logistics».\n"
        "«LLM Prompt» выключен: MODEL PROMPT = прямой промпт, а LLM не "
        "запускается (вход «ПрLLM» ленивый).\n"
        "«LLM Prompt» включён: MODEL PROMPT = ПрLLM + надбавка (INT Prompt "
        "и/или ПрМаст).\n"
        "Пустой ПрLLM не заменяется исходным промптом."
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
                    "display_name": "ПрLLM",
                    "tooltip": "Результат внешней LLM. Ленивый вход: при "
                               "выключенном «LLM Prompt» ветка LLM не "
                               "выполняется.",
                }),
                "direct": ("STRING", {
                    "forceInput": True,
                    "multiline": True,
                    "display_name": "MODEL PROMPT (прямой)",
                    "tooltip": "Выход «MODEL PROMPT (прямой)» ноды «Prompt logistics».",
                }),
                "suffix": ("STRING", {
                    "forceInput": True,
                    "multiline": True,
                    "display_name": "ДОП к ПрLLM",
                    "tooltip": "Выход «ДОП к ПрLLM» ноды «Prompt logistics».",
                }),
                "use_llm": ("BOOLEAN", {
                    "forceInput": True,
                    "default": False,
                    "display_name": "USE LLM",
                    "tooltip": "Выход «USE LLM» ноды «Prompt logistics».",
                }),
            },
            "hidden": {
                "prompt": "PROMPT",
                "unique_id": "UNIQUE_ID",
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("MODEL PROMPT",)
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
