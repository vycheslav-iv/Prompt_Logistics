"""Функциональный тест Prompt logistics (Python) — матрица режимов §3 ТЗ."""

import importlib.util
import sys
from pathlib import Path

sys.dont_write_bytecode = True

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

NODE_FILE = Path(__file__).resolve().parent.parent / "prompt_logistics.py"

try:
    _spec = importlib.util.spec_from_file_location("prompt_logistics", NODE_FILE)
    node = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(node)
except Exception as exc:  # noqa: BLE001
    print(f"FAIL: не удалось загрузить {NODE_FILE}: {exc}")
    print("FAIL: 1")
    sys.exit(1)

S = node.PromptLogistics()
F = node.PromptLogisticsModel()

fails = []
checks = 0


def check(label, got, want):
    global checks
    checks += 1
    if got == want:
        print(f"ok   {label}")
    else:
        fails.append(label)
        print(f"FAIL {label}: получено {got!r}, ожидалось {want!r}")


P, M, I, L = "промпт", "мастер", "интерьер", "результат LLM"


def chain(prompt=P, master=M, int_prompt=I, llm_result=L, **toggles):
    """Полная проводка S -> LLM -> F, как на канвасе."""
    direct, llm, suffix, use_llm = S.compose(
        prompt=prompt, master=master, int_prompt=int_prompt, **toggles)
    final = F.finalize(llm_result=llm_result, direct=direct,
                       suffix=suffix, use_llm=use_llm)[0]
    return direct, llm, suffix, use_llm, final


# ── 1. Прямой маршрут: LLM Prompt OFF ─────────────────────────────────────
check("1: только ПрОб", chain(int_prompt="", llm_result="")[4], P)
check("1: STYLE Prompt добавляет ПрМаст", chain(style_prompt=True)[4], P + " " + M)
check("1: STYLE Prompt OFF не добавляет ПрМаст", chain()[4], P)
check("1: INT добавляет INT Prompt", chain(use_int=True)[4], P + " " + I)
check("1: INT OFF не добавляет INT Prompt", chain()[4], P)
check("2: INT + STYLE Prompt: ПрОб + INT + ПрМаст",
      chain(use_int=True, style_prompt=True)[4], P + " " + I + " " + M)
check("2: INT в LLM без INT ничего не включает",
      chain(int_in_llm=True)[4], P)
check("2: LLM OFF — INT в LLM не меняет модель",
      chain(use_int=True, int_in_llm=True)[4], P + " " + I)
check("STYLE в LLM при LLM OFF не трогает модель",
      chain(style_in_llm=True, llm_result="")[4], P)
check("STYLE в LLM + STYLE Prompt при LLM OFF — модель = ПрОб + ПрМаст",
      chain(style_in_llm=True, style_prompt=True, llm_result="")[4], P + " " + M)

# ── 2. LLM PROMPT (что уходит в LLM) ──────────────────────────────────────
check("LLM PROMPT: только ПрОб", chain()[1], P)
check("LLM PROMPT: INT в LLM + INT", chain(use_int=True, int_in_llm=True)[1], P + " " + I)
check("LLM PROMPT: INT в LLM без INT — INT не задействован",
      chain(int_in_llm=True)[1], P)
check("LLM PROMPT: INT без INT в LLM не попадает в LLM",
      chain(use_int=True)[1], P)
check("LLM PROMPT: STYLE в LLM без STYLE Prompt — ПрМаст в LLM не идёт",
      chain(style_in_llm=True)[1], P)
check("LLM PROMPT: STYLE Prompt + STYLE в LLM — ПрМаст в LLM",
      chain(style_prompt=True, style_in_llm=True)[1], P + " " + M)
check("LLM PROMPT: STYLE Prompt не влияет на LLM PROMPT",
      chain(style_prompt=True)[1], P)
check("LLM PROMPT: INT + STYLE в LLM без STYLE Prompt — только ПрОб, INT",
      chain(use_int=True, int_in_llm=True, style_in_llm=True)[1], P + " " + I)
check("LLM PROMPT: LLM Prompt OFF не меняет LLM PROMPT", chain()[1], P)

# ── 3. Маршрут через LLM: LLM Prompt ON ───────────────────────────────────
check("3: LLM Prompt ON -> ПрLLM", chain(llm_prompt=True)[4], L)
check("3: ПрОб в модель не попадает", chain(llm_prompt=True)[4], L)
check("4: ПрLLM + STYLE Prompt", chain(llm_prompt=True, style_prompt=True)[4], L + " " + M)
check("4: ПрLLM без STYLE Prompt", chain(llm_prompt=True)[4], L)
check("5: INT без INT в LLM добавляется к ПрLLM",
      chain(llm_prompt=True, use_int=True)[4], L + " " + I)
check("5: INT + STYLE Prompt -> ПрLLM + INT + ПрМаст",
      chain(llm_prompt=True, use_int=True, style_prompt=True)[4], L + " " + I + " " + M)
check("5: INT + INT в LLM -> INT уходит в LLM, к ПрLLM не добавляется",
      chain(llm_prompt=True, use_int=True, int_in_llm=True)[4], L)
check("5: INT + INT в LLM + STYLE Prompt -> ПрLLM + ПрМаст",
      chain(llm_prompt=True, use_int=True, int_in_llm=True, style_prompt=True)[4],
      L + " " + M)
check("3: INT в LLM + STYLE в LLM + STYLE Prompt — оба в LLM PROMPT",
      chain(llm_prompt=True, use_int=True, int_in_llm=True,
            style_in_llm=True, style_prompt=True)[1],
      P + " " + I + " " + M)
check("3: INT в LLM — только маршрутизация: INT OFF — INT в LLM пуст",
      chain(llm_prompt=True, int_in_llm=True)[1], P)
check("3: STYLE в LLM — только маршрутизация: STYLE Prompt OFF — ПрМаст не в LLM",
      chain(llm_prompt=True, style_in_llm=True)[1], P)
check("3: INT OFF — INT не попадает ни в LLM, ни в модель",
      chain(llm_prompt=True, int_in_llm=True)[4], L)
check("3: INT OFF + INT в LLM + STYLE в LLM — LLM PROMPT только ПрОб",
      chain(llm_prompt=True, int_in_llm=True, style_in_llm=True)[1], P)

# ── 4. Надбавка «ДОП к ПрLLM» ─────────────────────────────────────────────
check("ДОП: LLM Prompt OFF — пусто", chain(use_int=True, style_prompt=True)[2], "")
check("ДОП: LLM Prompt ON, INT без INT в LLM", chain(llm_prompt=True, use_int=True)[2], I)
check("ДОП: LLM Prompt ON, INT в LLM — пусто", chain(llm_prompt=True, use_int=True, int_in_llm=True)[2], "")
check("ДОП: LLM Prompt ON, STYLE Prompt", chain(llm_prompt=True, style_prompt=True)[2], M)
check("ДОП: LLM Prompt ON, INT + STYLE", chain(llm_prompt=True, use_int=True, style_prompt=True)[2], I + " " + M)
check("ДОП: LLM Prompt ON, INT OFF, STYLE в LLM — пусто",
      chain(llm_prompt=True, style_in_llm=True)[2], "")

# ── 5. Флаг USE LLM ───────────────────────────────────────────────────────
check("USE LLM: OFF по умолчанию", chain()[3], False)
check("USE LLM: ON при LLM Prompt", chain(llm_prompt=True)[3], True)
check("USE LLM: BOOLEAN, а не строка", type(chain(llm_prompt=True)[3]), bool)

# ── 6. ПрМаст не дублируется, если уже ушёл в LLM (схема эталона) ─────────
check("без дубля: STYLE в LLM + STYLE Prompt -> итог без второго ПрМаст",
      chain(llm_prompt=True, style_in_llm=True, style_prompt=True)[4], L)
llm_out = chain(llm_prompt=True, style_in_llm=True, style_prompt=True)[1]
check("без дубля: ПрМаст есть в LLM PROMPT", M in llm_out, True)
check("без дубля: ДОП пуст, когда ПрМаст уже в LLM PROMPT",
      chain(llm_prompt=True, style_in_llm=True, style_prompt=True)[2], "")
check("без дубля: STYLE Prompt без STYLE в LLM — ПрМаст один",
      chain(llm_prompt=True, style_prompt=True)[4], L + " " + M)
check("без дубля: STYLE Prompt + STYLE в LLM — ПрМаст в LLM ровно один раз",
      chain(llm_prompt=True, style_prompt=True, style_in_llm=True)[1].count(M), 1)

# ── 7. Пустые и неподключённые входы ──────────────────────────────────────
check("пусто: все входы пусты", chain(prompt="", master="", int_prompt="", llm_result="")[4], "")
check("пусто: ПрОб пуст, ПрМаст есть, STYLE ON",
      chain(prompt="", llm_result="", style_prompt=True)[4], "")
check("пусто: ПрОб пуст, INT есть — остаётся INT",
      chain(prompt="", llm_result="", use_int=True)[4], I)
check("пусто: ПрОб пуст, INT в LLM при LLM OFF — INT остаётся в модели",
      chain(prompt="", llm_result="", use_int=True, int_in_llm=True)[4], I)
check("пусто: LLM ON, ПрLLM пуст — НЕ подставляется ПрОб",
      chain(llm_prompt=True, llm_result="")[4], "")
check("пусто: LLM ON, ПрLLM пуст, STYLE ON — не остаётся один ПрМаст",
      chain(llm_prompt=True, llm_result="", style_prompt=True)[4], "")
check("пусто: LLM ON, ПрLLM пуст, INT — не остаётся один INT",
      chain(llm_prompt=True, llm_result="", use_int=True)[4], "")
check("пусто: пробельный ПрLLM = пустой",
      chain(llm_prompt=True, llm_result="   ", style_prompt=True)[4], "")
check("пусто: пробельные части пропускаются",
      chain(prompt="  ", master=" ", int_prompt="\n", llm_prompt=True, llm_result="")[1], "")
check("пусто: неподключённые optional-входы", S.compose(), ("", "", "", False))
check("пусто: финализатор без входов", F.finalize(), ("",))

# ── 8. Склейка: ровно один пробел, текст не режется ───────────────────────
check("склейка: один пробел", chain(prompt="A", master="B", int_prompt="C",
                                    llm_prompt=True, use_int=True)[4], L + " C")
check("склейка: прямой промпт", chain(prompt="A", master="B", int_prompt="C",
                                      use_int=True)[4], "A C")
check("склейка: внутренние пробелы части сохранены",
      chain(prompt="A  A", int_prompt="", llm_result="")[1], "A  A")
check("склейка: перенос строки части сохранён",
      chain(prompt="A\nB", int_prompt="", llm_result="")[1], "A\nB")
check("склейка: модель не меняет результат LLM",
      chain(llm_prompt=True, llm_result="A\nB", int_prompt="")[4], "A\nB")
check("склейка: не-строка приводится к строке", F.finalize(llm_result=123, use_llm=True), ("123",))

# ── 9. Независимость переключателей ───────────────────────────────────────
for name, kw, idx, want in [
    ("INT", dict(use_int=True), 1, P),
    ("INT в LLM", dict(int_in_llm=True), 0, P),
    ("STYLE в LLM", dict(style_in_llm=True), 0, P),
    ("STYLE Prompt", dict(style_prompt=True), 1, P),
]:
    direct, llm, _suffix, _use, _final = chain(**kw)
    check(f"независимость: {name} не меняет чужой выход",
          (direct if idx == 0 else llm), want)

# ── 10. Детерминизм ───────────────────────────────────────────────────────
check("детерминизм: повторный вызов S",
      S.compose(prompt=P, int_prompt=I, use_int=True),
      S.compose(prompt=P, int_prompt=I, use_int=True))
check("детерминизм: повторный вызов F",
      F.finalize(llm_result=L, use_llm=True, suffix=M),
      F.finalize(llm_result=L, use_llm=True, suffix=M))

# ── 11. Контракт INPUT_TYPES / выходов ────────────────────────────────────
si = S.INPUT_TYPES()
fi = F.INPUT_TYPES()


def is_widget(opts):
    return not opts.get("forceInput", False)


check("S: required пуст", si["required"], {})
check("S: все входы optional", sorted(si["optional"]),
      ["int_in_llm", "int_prompt", "llm_prompt", "master", "prompt",
       "style_in_llm", "style_prompt", "use_int"])
check("S: ПрОб — link-only STRING", si["optional"]["prompt"][1]["forceInput"], True)
check("S: ПрМаст — link-only STRING", si["optional"]["master"][1]["forceInput"], True)
check("S: INT Prompt — link-only STRING", si["optional"]["int_prompt"][1]["forceInput"], True)
check("S: подписи входов", [si["optional"][k][1]["display_name"] for k in
                            ("prompt", "master", "int_prompt")],
      ["ПрОб", "ПрМаст", "INT Prompt"])
check("S: подписи переключателей",
      [si["optional"][k][1]["display_name"] for k in
       ("llm_prompt", "style_prompt", "style_in_llm", "use_int", "int_in_llm")],
      ["LLM Prompt", "STYLE Prompt", "STYLE в LLM", "INT", "INT в LLM"])
check("S: переключатели по умолчанию OFF",
      [si["optional"][k][1]["default"] for k in
       ("llm_prompt", "style_prompt", "style_in_llm", "use_int", "int_in_llm")],
      [False, False, False, False, False])
check("S: RETURN_TYPES", S.RETURN_TYPES, ("STRING", "STRING", "STRING", "BOOLEAN"))
check("S: RETURN_NAMES", S.RETURN_NAMES,
      ("MODEL PROMPT (прямой)", "LLM PROMPT", "ДОП к ПрLLM", "USE LLM"))
check("S: FUNCTION", S.FUNCTION, "compose")
check("S: CATEGORY", S.CATEGORY, "My_custom_nodes/Prompt Logistics")

check("F: required пуст", fi["required"], {})
check("F: все входы optional", sorted(fi["optional"]),
      ["direct", "llm_result", "suffix", "use_llm"])
check("F: ПрLLM — link-only STRING", fi["optional"]["llm_result"][1]["forceInput"], True)
check("F: прямой промпт — link-only STRING", fi["optional"]["direct"][1]["forceInput"], True)
check("F: надбавка — link-only STRING", fi["optional"]["suffix"][1]["forceInput"], True)
check("F: USE LLM — link-only BOOLEAN", fi["optional"]["use_llm"][1]["forceInput"], True)
check("F: подписи входов", [fi["optional"][k][1]["display_name"] for k in
                            ("llm_result", "direct", "suffix", "use_llm")],
      ["ПрLLM", "MODEL PROMPT (прямой)", "ДОП к ПрLLM", "USE LLM"])
check("F: RETURN_TYPES", F.RETURN_TYPES, ("STRING",))
check("F: RETURN_NAMES", F.RETURN_NAMES, ("MODEL PROMPT",))
check("F: FUNCTION", F.FUNCTION, "finalize")
check("F: CATEGORY", F.CATEGORY, "My_custom_nodes/Prompt Logistics")

# ── 11a. Ленивый ПрLLM: при LLM Prompt OFF ветка LLM не запрашивается ─────
WITH_LLM = {"2": {"class_type": "PromptLogisticsModel",
                  "inputs": {"llm_result": ["1", 0], "use_llm": ["9", 0]}}}
NO_LLM = {"2": {"class_type": "PromptLogisticsModel",
                "inputs": {"use_llm": ["9", 0]}}}
LITERAL = {"2": {"class_type": "PromptLogisticsModel",
                 "inputs": {"llm_result": "текст", "use_llm": ["9", 0]}}}
NOT_LINK = {"2": {"class_type": "PromptLogisticsModel",
                  "inputs": {"llm_result": ["a", "b"], "use_llm": ["9", 0]}}}

check("lazy: ПрLLM помечен lazy", fi["optional"]["llm_result"][1].get("lazy"), True)
check("lazy: метод check_lazy_status объявлен",
      callable(getattr(F, "check_lazy_status", None)), True)
check("lazy: LLM Prompt OFF — ветка LLM не запрашивается",
      F.check_lazy_status(use_llm=False, prompt=WITH_LLM, unique_id="2"), [])
check("lazy: LLM Prompt OFF без ПрLLM — тоже пусто",
      F.check_lazy_status(use_llm=False), [])
check("lazy: LLM Prompt ON — ПрLLM запрашивается",
      F.check_lazy_status(use_llm=True, prompt=WITH_LLM, unique_id="2"),
      ["llm_result"])
check("lazy: LLM Prompt ON, ПрLLM уже посчитан — не запрашивается",
      F.check_lazy_status(llm_result="готово", use_llm=True,
                          prompt=WITH_LLM, unique_id="2"), [])
check("lazy: ПрLLM не подключён — не запрашивается (нет падения)",
      F.check_lazy_status(use_llm=True, prompt=NO_LLM, unique_id="2"), [])
check("lazy: ПрLLM литералом — не запрашивается",
      F.check_lazy_status(use_llm=True, prompt=LITERAL, unique_id="2"), [])
check("lazy: не-связь [a, b] — не запрашивается (нет падения)",
      F.check_lazy_status(use_llm=True, prompt=NOT_LINK, unique_id="2"), [])
check("lazy: промпт недоступен — не запрашивается",
      F.check_lazy_status(use_llm=True), [])
check("lazy: id узла числом — ключ всё равно найден",
      F.check_lazy_status(use_llm=True, prompt=WITH_LLM, unique_id=2),
      ["llm_result"])
check("lazy: скрытый PROMPT объявлен", fi["hidden"]["prompt"], "PROMPT")
check("lazy: скрытый UNIQUE_ID объявлен", fi["hidden"]["unique_id"], "UNIQUE_ID")
check("lazy: finalize принимает скрытые входы",
      F.finalize(llm_result="A", use_llm=True, prompt={}, unique_id="2"), ("A",))

# ── 12. Пять переключателей — только на главной ноде ──────────────────────
s_widgets = [si["optional"][k][1]["display_name"] for k in si["optional"]
             if si["optional"][k][0] == "BOOLEAN" and is_widget(si["optional"][k][1])]
f_widgets = [fi["optional"][k][1]["display_name"] for k in fi["optional"]
             if fi["optional"][k][0] == "BOOLEAN" and is_widget(fi["optional"][k][1])]
check("пять переключателей на главной", sorted(s_widgets),
      sorted(["LLM Prompt", "STYLE Prompt", "STYLE в LLM", "INT", "INT в LLM"]))
check("финализатор без настроек", f_widgets, [])
check("всего BOOLEAN-переключателей пять", len(s_widgets) + len(f_widgets), 5)
for label in ("LLM Prompt", "STYLE Prompt", "STYLE в LLM", "INT", "INT в LLM"):
    check(f"{label} ровно один раз", (s_widgets + f_widgets).count(label), 1)

# ── 13. Состав промпта не содержит служебных подписей ─────────────────────
out = chain(use_int=True, style_prompt=True, llm_result="")[4]
check("без служебных подписей", out, "промпт интерьер мастер")
for word in ("ПрОб", "ПрМаст", "INT", "Prompt", "MODEL", "LLM", "ДОП", "USE"):
    check(f"нет подписи {word!r} в результате", word not in out, True)

print()
if fails:
    print(f"FAIL: {len(fails)} из {checks}")
    for item in fails:
        print(f"  - {item}")
    sys.exit(1)
print(f"FAIL: 0 (проверок {checks})")
print("ТЕСТ ПРОЙДЕН")
