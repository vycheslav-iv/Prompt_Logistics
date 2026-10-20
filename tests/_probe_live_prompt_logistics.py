"""Живая проба Prompt_Logistics на запущенном ComfyUI (нужен сервер).

Запуск:  python tests/_probe_live_prompt_logistics.py
Сервер:  COMFYUI_URL или http://127.0.0.1:8188

Проверяет: регистрацию обеих нод, подписи входов/переключателей, что все
пять переключателей — виджеты на S, а F без настроек; прямой маршрут,
маршрут через LLM (LLM заменена эхом StringConcatenate), INT до и после
LLM, пустой результат LLM, отсутствие dependency_cycle в графе и главное —
ленивость: с медленной нодой KJNodes Sleep в ветке LLM прогон с выключенным
LLM Prompt завершается быстро, а с включённым ждёт Sleep.
"""

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

BASE = os.environ.get("COMFYUI_URL", "http://127.0.0.1:8188").rstrip("/")
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


def get_json(path):
    with urllib.request.urlopen(BASE + path, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def post_prompt(prompt):
    body = json.dumps({"prompt": prompt}, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(BASE + "/prompt", data=body,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return json.loads(exc.read().decode("utf-8"))


def run(prompt, timeout=20.0):
    sent = post_prompt(prompt)
    if "prompt_id" not in sent:
        return None, sent
    pid = sent["prompt_id"]
    deadline = time.time() + timeout
    while time.time() < deadline:
        hist = get_json("/history/" + urllib.parse.quote(pid))
        if pid in hist:
            entry = hist[pid]
            if entry.get("status", {}).get("completed"):
                return entry.get("outputs", {}), entry.get("status")
        time.sleep(0.2)
    return None, {"error": "timeout", "prompt_id": pid}


def text_of(outputs, node_id):
    node = outputs.get(str(node_id), {})
    values = node.get("text") or node.get("string") or []
    return values[0] if values else None


def preview(node_id, source):
    return {
        str(node_id): {"class_type": "PreviewAny", "inputs": {"source": source}},
    }


# ── 1. Регистрация и подписи ──────────────────────────────────────────────
info_s = get_json("/object_info/PromptLogistics")
info_f = get_json("/object_info/PromptLogisticsModel")
check("нода S зарегистрирована", "PromptLogistics" in info_s, True)
check("нода F зарегистрирована", "PromptLogisticsModel" in info_f, True)

s_def = info_s.get("PromptLogistics", {})
f_def = info_f.get("PromptLogisticsModel", {})
check("S display_name", s_def.get("display_name"), "Prompt logistics")
check("F display_name", f_def.get("display_name"), "Prompt logistics — MODEL")
check("S выходы", s_def.get("output"), ["STRING", "STRING", "STRING", "BOOLEAN"])
check("S имена выходов", s_def.get("output_name"),
      ["MODEL PROMPT (прямой)", "LLM PROMPT", "ДОП к ПрLLM", "USE LLM"])
check("F возвращает STRING", f_def.get("output"), ["STRING"])
check("F имя выхода", f_def.get("output_name"), ["MODEL PROMPT"])

s_opt = s_def.get("input", {}).get("optional", {})
f_opt = f_def.get("input", {}).get("optional", {})
check("S обязательных входов нет", s_def.get("input", {}).get("required", {}), {})
check("F обязательных входов нет", f_def.get("input", {}).get("required", {}), {})
check("S входы", sorted(s_opt),
      ["int_in_llm", "int_prompt", "llm_prompt", "master", "prompt",
       "style_in_llm", "style_prompt", "use_int"])
check("F входы", sorted(f_opt), ["direct", "llm_result", "suffix", "use_llm"])
check("S подписи", [s_opt[k][1].get("display_name") for k in ("prompt", "master", "int_prompt")],
      ["ПрОб", "ПрМаст", "INT Prompt"])
check("F подписи", [f_opt[k][1].get("display_name")
                    for k in ("llm_result", "direct", "suffix", "use_llm")],
      ["ПрLLM", "MODEL PROMPT (прямой)", "ДОП к ПрLLM", "USE LLM"])


def widgets(inputs):
    return [opts[1].get("display_name") for opts in inputs.values()
            if opts[0] == "BOOLEAN" and not opts[1].get("forceInput")]


check("пять переключателей — виджеты S", sorted(widgets(s_opt)),
      sorted(["LLM Prompt", "STYLE Prompt", "STYLE в LLM", "INT", "INT в LLM"]))
check("F без настроек", widgets(f_opt), [])
check("USE LLM — link-only BOOLEAN", f_opt["use_llm"][1].get("forceInput"), True)
check("ПрLLM помечен lazy (сервер)", f_opt["llm_result"][1].get("lazy"), True)
check("F объявляет скрытые PROMPT/UNIQUE_ID",
      f_def.get("input", {}).get("hidden"),
      {"prompt": "PROMPT", "unique_id": "UNIQUE_ID"})
check("переключатели по умолчанию OFF",
      all(opts[1].get("default") is False for opts in s_opt.values()
          if opts[0] == "BOOLEAN"), True)

# ── 2. Прямой маршрут без LLM ─────────────────────────────────────────────
wf = {
    "10": {"class_type": "PromptLogistics", "inputs": {
        "prompt": "сцена", "master": "стиль", "int_prompt": "комната"}},
}
wf.update(preview(11, ["10", 0]))
wf.update(preview(12, ["10", 1]))
wf.update(preview(13, ["10", 2]))
wf.update(preview(14, ["10", 3]))
out, status = run(wf)
check("прямой: граф выполнен", status.get("status_str"), "success")
check("прямой: MODEL PROMPT = ПрОб", text_of(out or {}, 11), "сцена")
check("прямой: LLM PROMPT = ПрОб", text_of(out or {}, 12), "сцена")
check("прямой: ДОП пуст", text_of(out or {}, 13), "")
check("прямой: USE LLM = False", text_of(out or {}, 14), "False")

# ── 3. Прямой + INT + STYLE Prompt ────────────────────────────────────────
wf = {
    "10": {"class_type": "PromptLogistics", "inputs": {
        "prompt": "сцена", "master": "стиль", "int_prompt": "комната",
        "use_int": True, "style_prompt": True}},
    "20": {"class_type": "PromptLogisticsModel", "inputs": {
        "direct": ["10", 0], "suffix": ["10", 2], "use_llm": ["10", 3]}},
}
wf.update(preview(21, ["20", 0]))
out, status = run(wf)
check("прямой+INT+STYLE: граф выполнен", status.get("status_str"), "success")
check("прямой+INT+STYLE: MODEL PROMPT", text_of(out or {}, 21), "сцена комната стиль")

# ── 4. INT уходит в LLM (INT в LLM) ───────────────────────────────────────
wf = {
    "10": {"class_type": "PromptLogistics", "inputs": {
        "prompt": "сцена", "master": "стиль", "int_prompt": "комната",
        "llm_prompt": True, "use_int": True, "int_in_llm": True,
        "style_in_llm": True}},
    "20": {"class_type": "PromptLogisticsModel", "inputs": {
        "llm_result": "результат LLM", "direct": ["10", 0],
        "suffix": ["10", 2], "use_llm": ["10", 3]}},
}
wf.update(preview(21, ["20", 0]))
wf.update(preview(22, ["10", 1]))
wf.update(preview(23, ["10", 2]))
out, status = run(wf)
check("INT в LLM: граф выполнен", status.get("status_str"), "success")
check("INT в LLM (STYLE в LLM без STYLE Prompt): LLM PROMPT без ПрМаст",
      text_of(out or {}, 22), "сцена комната")
check("INT в LLM: ДОП пуст", text_of(out or {}, 23), "")
check("INT в LLM: MODEL PROMPT = только ПрLLM", text_of(out or {}, 21), "результат LLM")

# ── 5. INT после LLM + STYLE Prompt ───────────────────────────────────────
wf = {
    "10": {"class_type": "PromptLogistics", "inputs": {
        "prompt": "сцена", "master": "стиль", "int_prompt": "комната",
        "llm_prompt": True, "use_int": True, "style_prompt": True}},
    "20": {"class_type": "PromptLogisticsModel", "inputs": {
        "llm_result": "результат LLM", "direct": ["10", 0],
        "suffix": ["10", 2], "use_llm": ["10", 3]}},
}
wf.update(preview(21, ["20", 0]))
out, status = run(wf)
check("INT после LLM: граф выполнен", status.get("status_str"), "success")
check("INT после LLM: MODEL PROMPT", text_of(out or {}, 21), "результат LLM комната стиль")

# ── 6. Полный граф с LLM-эхом (провод LLM PROMPT → LLM → ПрLLM) ───────────
wf = {
    "10": {"class_type": "PromptLogistics", "inputs": {
        "prompt": "сцена", "master": "стиль", "int_prompt": "комната",
        "llm_prompt": True, "style_in_llm": True}},
    "15": {"class_type": "StringConcatenate", "inputs": {
        "string_a": ["10", 1], "string_b": "", "delimiter": ""}},
    "20": {"class_type": "PromptLogisticsModel", "inputs": {
        "llm_result": ["15", 0], "direct": ["10", 0],
        "suffix": ["10", 2], "use_llm": ["10", 3]}},
}
wf.update(preview(21, ["20", 0]))
out, status = run(wf)
check("граф S → LLM → F: нет dependency_cycle", status.get("status_str"), "success")
check("граф S → LLM → F (STYLE в LLM без STYLE Prompt): MODEL PROMPT без ПрМаст",
      text_of(out or {}, 21), "сцена")

# ── 6b. STYLE Prompt + STYLE в LLM — ПрМаст идёт в LLM через провод ───────
wf = {
    "10": {"class_type": "PromptLogistics", "inputs": {
        "prompt": "сцена", "master": "стиль", "llm_prompt": True,
        "style_prompt": True, "style_in_llm": True}},
    "15": {"class_type": "StringConcatenate", "inputs": {
        "string_a": ["10", 1], "string_b": "", "delimiter": ""}},
    "20": {"class_type": "PromptLogisticsModel", "inputs": {
        "llm_result": ["15", 0], "direct": ["10", 0],
        "suffix": ["10", 2], "use_llm": ["10", 3]}},
}
wf.update(preview(21, ["20", 0]))
wf.update(preview(22, ["10", 1]))
out, status = run(wf)
check("6b: граф выполнен", status.get("status_str"), "success")
check("6b: LLM PROMPT = ПрОб + ПрМаст", text_of(out or {}, 22), "сцена стиль")
check("6b: MODEL PROMPT = ПрLLM без дубля ПрМаст", text_of(out or {}, 21), "сцена стиль")

# ── 7. LLM Prompt ON, пустой ПрLLM — без подстановки ПрОб ─────────────────
wf = {
    "10": {"class_type": "PromptLogistics", "inputs": {
        "prompt": "сцена", "master": "стиль", "llm_prompt": True,
        "style_prompt": True}},
    "20": {"class_type": "PromptLogisticsModel", "inputs": {
        "llm_result": "", "direct": ["10", 0],
        "suffix": ["10", 2], "use_llm": ["10", 3]}},
}
wf.update(preview(21, ["20", 0]))
out, status = run(wf)
check("пустой ПрLLM: граф выполнен", status.get("status_str"), "success")
check("пустой ПрLLM: MODEL PROMPT пуст", text_of(out or {}, 21), "")

# ── 8. Ленивый ПрLLM: ветка LLM не выполняется при LLM Prompt OFF ─────────
try:
    sleep_def = get_json("/object_info/Sleep").get("Sleep")
except urllib.error.HTTPError:
    sleep_def = None
check("медленная нода Sleep доступна (KJNodes)", bool(sleep_def), True)


def lazy_workflow(llm_on):
    return {
        "10": {"class_type": "PromptLogistics", "inputs": {
            "prompt": "сцена", "llm_prompt": llm_on}},
        "15": {"class_type": "Sleep", "inputs": {
            "input": ["10", 1], "minutes": 0, "seconds": 4.0}},
        "20": {"class_type": "PromptLogisticsModel", "inputs": {
            "llm_result": ["15", 0], "direct": ["10", 0],
            "suffix": ["10", 2], "use_llm": ["10", 3]}},
        "21": {"class_type": "PreviewAny", "inputs": {"source": ["20", 0]}},
    }


t0 = time.monotonic()
out, status = run(lazy_workflow(False), timeout=30)
off_elapsed = time.monotonic() - t0
print(f"     LLM Prompt OFF: {off_elapsed:.2f} c (Sleep 4 c в ветке LLM)")
check("lazy OFF: граф выполнен", status.get("status_str"), "success")
check("lazy OFF: MODEL PROMPT = прямой промпт", text_of(out or {}, 21), "сцена")
check("lazy OFF: ветка LLM не выполнялась (< 2.5 c)", off_elapsed < 2.5, True)

t0 = time.monotonic()
out, status = run(lazy_workflow(True), timeout=30)
on_elapsed = time.monotonic() - t0
print(f"     LLM Prompt ON:  {on_elapsed:.2f} c (Sleep 4 c в ветке LLM)")
check("lazy ON: граф выполнен", status.get("status_str"), "success")
check("lazy ON: MODEL PROMPT = результат LLM", text_of(out or {}, 21), "сцена")
check("lazy ON: ветка LLM выполнялась (>= 3.5 c)", on_elapsed >= 3.5, True)

check("lazy: включение LLM добавляет задержку > 2.5 c",
      (on_elapsed - off_elapsed) > 2.5, True)

print()
if fails:
    print(f"FAIL: {len(fails)} из {checks}")
    for item in fails:
        print(f"  - {item}")
    sys.exit(1)
print(f"FAIL: 0 (проверок {checks})")
print("ЖИВАЯ ПРОБА ПРОЙДЕНА")
