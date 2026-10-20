// Статический аудит Prompt_Logistics — без ComfyUI и браузера.
// Проверяет контракт двух нод, запрещённые приёмы и совместимость с Nodes 2.0.
//
// Запуск:  cd Prompt_Logistics && node tests/_audit_prompt_logistics.mjs
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = fileURLToPath(new URL("..", import.meta.url));
const BUNDLE = fileURLToPath(new URL("../..", import.meta.url));

const errors = [];
const checks = [];
const check = (label, cond, extra = "") => {
  checks.push(label);
  if (cond) {
    console.log(`  ok   ${label}`);
  } else {
    errors.push(label);
    console.log(`  FAIL ${label}${extra ? "  [" + extra + "]" : ""}`);
  }
};
const has = (text, re, label) => check(label, re.test(text), String(re));

const read = (rel) => {
  const file = path.join(ROOT, rel);
  if (!fs.existsSync(file)) return null;
  return fs.readFileSync(file, "utf8");
};

console.log("— файлы —");
const PY = read("prompt_logistics.py");
check("prompt_logistics.py существует", !!PY);
check("__init__.py существует", !!read("__init__.py"));
check("SPECIFICATION.md существует", !!read("SPECIFICATION.md"));
check("check.json существует", !!read("check.json"));
check("тест Python существует", !!read("tests/_test_prompt_logistics.py"));

console.log("— Python: контракт —");
if (PY) {
  has(PY, /^class PromptLogistics:/m, "python: class PromptLogistics");
  has(PY, /^class PromptLogisticsModel:/m, "python: class PromptLogisticsModel");
  has(PY, /RETURN_TYPES\s*=\s*\("STRING",\s*"STRING",\s*"STRING",\s*"BOOLEAN"\)/,
    "python: S возвращает три STRING + флаг LLM");
  has(PY, /RETURN_NAMES\s*=\s*\("MODEL PROMPT \(прямой\)",\s*"LLM PROMPT",\s*"ДОП к ПрLLM",\s*"USE LLM"\)/,
    "python: S MODEL PROMPT (прямой) + LLM PROMPT + ДОП + USE LLM");
  has(PY, /RETURN_TYPES\s*=\s*\("STRING",\)/, "python: F возвращает один STRING");
  has(PY, /FUNCTION\s*=\s*"compose"/, "python: S FUNCTION = compose");
  has(PY, /FUNCTION\s*=\s*"finalize"/, "python: F FUNCTION = finalize");
  has(PY, /CATEGORY\s*=\s*"My_custom_nodes\/Prompt Logistics"/, "python: CATEGORY = My_custom_nodes/Prompt Logistics");
  has(PY, /"PromptLogistics":\s*PromptLogistics/, "python: NODE_CLASS_MAPPINGS S");
  has(PY, /"PromptLogisticsModel":\s*PromptLogisticsModel/, "python: NODE_CLASS_MAPPINGS F");
  has(PY, /"PromptLogistics":\s*"Prompt logistics"/, "python: display name S = Prompt logistics");
  has(PY, /"PromptLogisticsModel":\s*"Prompt logistics — MODEL"/, "python: display name F");

  check("python: нет import time/asyncio/threading/multiprocessing",
    !/^\s*(import|from)\s+(time|asyncio|threading|multiprocessing)\b/m.test(PY));
  check("python: нет sleep/timeout/ожиданий",
    !/(sleep|wait|timeout|setTimeout|setInterval|delay)\s*\(/i.test(PY));
  check("python: нет while-циклов", !/\bwhile\s+/m.test(PY));
  check("python: нет глобального состояния", !/^\s*global\s+/m.test(PY) && !/^[A-Z_]+\s*=\s*\[\]/m.test(PY));
  check("python: нет сети и файлов",
    !/(urlopen|requests\.|socket\.|open\s*\(\s*["']|Path\s*\()/m.test(PY));
  check("python: нет случайности", !/\brandom\b/.test(PY));
  check("python: нет print (нода молчит в консоли)", !/\bprint\s*\(/m.test(PY));
  check("python: текст не изменяется (нет .replace)",
    !/\.replace\s*\(/.test(PY));
  check("python: нет импортов ComfyUI на уровне модуля",
    !/^\s*(import|from)\s+(comfy|folder_paths|server|nodes)\b/m.test(PY));

  const bools = PY.match(/\(\s*"BOOLEAN",\s*\{/g) || [];
  check("python: шесть BOOLEAN-полей (5 переключателей + USE LLM)",
    bools.length === 6, `найдено ${bools.length}`);
  check("python: USE LLM — link-only BOOLEAN, а не виджет",
    /"use_llm":\s*\("BOOLEAN",\s*\{[\s\S]{0,220}?"forceInput":\s*True/.test(PY));
  const esc = (text) => text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  for (const name of ["LLM Prompt", "STYLE Prompt", "STYLE в LLM", "INT", "INT в LLM"]) {
    const count = (PY.match(new RegExp(`"display_name":\\s*"${esc(name)}"`, "g")) || []).length;
    check(`python: переключатель «${name}» ровно один раз`, count === 1, `найдено ${count}`);
  }
  for (const name of ["ПрОб", "ПрМаст", "ПрLLM", "INT Prompt",
                      "MODEL PROMPT (прямой)", "ДОП к ПрLLM", "USE LLM"]) {
    const count = (PY.match(new RegExp(`"display_name":\\s*"${esc(name)}"`, "g")) || []).length;
    check(`python: вход «${name}» присутствует`, count >= 1, `найдено ${count}`);
  }
  check("python: все шесть BOOLEAN-полей по умолчанию OFF",
    (PY.match(/"default":\s*False/g) || []).length === 6,
    `найдено ${(PY.match(/"default":\s*False/g) || []).length}`);
  check("python: link-only входы (forceInput)",
    (PY.match(/"forceInput":\s*True/g) || []).length === 7,
    `найдено ${(PY.match(/"forceInput":\s*True/g) || []).length}`);
  check("python: только две секции required = {}", (PY.match(/"required":\s*\{\}/g) || []).length === 2);
  check("python: у всех входов tooltip",
    (PY.match(/"tooltip":/g) || []).length >= 12,
    `найдено ${(PY.match(/"tooltip":/g) || []).length}`);
  has(PY, /"llm_result":\s*\("STRING",\s*\{[\s\S]{0,260}?"lazy":\s*True/,
    "python: ПрLLM — ленивый вход (ветка LLM не запускается зря)");
  has(PY, /def check_lazy_status\s*\(self/,
    "python: F объявляет check_lazy_status");
  has(PY, /return \["llm_result"\]/,
    "python: check_lazy_status запрашивает только llm_result");
  has(PY, /if not use_llm or llm_result is not None:/,
    "python: check_lazy_status молчит при LLM Prompt OFF и готовом ПрLLM");
  has(PY, /"hidden":\s*\{[\s\S]{0,120}?"prompt":\s*"PROMPT"/,
    "python: скрытый PROMPT для проверки связи");
  has(PY, /"unique_id":\s*"UNIQUE_ID"/, "python: скрытый UNIQUE_ID");
  has(PY, /master if \(style_prompt and style_in_llm\) else None,/,
    "python: ПрМаст в LLM только при STYLE Prompt и STYLE в LLM");
  has(PY, /master if \(llm_prompt and style_prompt and not style_in_llm\)/,
    "python: ПрМаст не дублируется, если уже ушёл в LLM");
  has(PY, /int_prompt if \(use_int and int_in_llm\) else None,/,
    "python: INT в LLM только при INT и INT в LLM");
}

console.log("— Nodes 2.0 —");
const JS_FILES = [];
const walk = (dir) => {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (entry.name === "tests" || entry.name.startsWith(".") || entry.name === "__pycache__") continue;
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) walk(full);
    else if (entry.name.endsWith(".js") || entry.name.endsWith(".mjs")) JS_FILES.push(full);
  }
};
walk(ROOT);
check("нет JS-расширения — нода не зависит от legacy canvas", JS_FILES.length === 0,
  JS_FILES.map((f) => path.relative(ROOT, f)).join(", "));
check("__init__.py не объявляет WEB_DIRECTORY", !(read("__init__.py") || "").includes("WEB_DIRECTORY"));
const INIT = read("__init__.py") || "";
check("__init__.py экспортирует оба маппинга",
  INIT.includes("NODE_CLASS_MAPPINGS") && INIT.includes("NODE_DISPLAY_NAME_MAPPINGS"));
if (PY) {
  check("Nodes 2.0: нет перезаписи computeSize", !/computeSize/.test(PY));
  check("Nodes 2.0: нет canvas draw", !/\bdraw\s*\(/.test(PY));
  check("Nodes 2.0: нет addDOMWidget", !/addDOMWidget/.test(PY));
  check("Nodes 2.0: нет scripts/app.js", !/scripts\/app\.js/.test(PY));
}

console.log("— check.json —");
const CHECK = read("check.json");
if (CHECK) {
  let cfg = null;
  try { cfg = JSON.parse(CHECK); } catch { /* ниже */ }
  check("check.json валиден", !!cfg);
  check("check.json: две проверки", Array.isArray(cfg?.checks) && cfg.checks.length === 2);
  for (const item of cfg?.checks ?? []) {
    check(`check.json: ${item.label} — есть cmd`, typeof item.cmd === "string" && item.cmd.length > 0);
    check(`check.json: ${item.label} — есть expect`, Array.isArray(item.expect) && item.expect.length > 0);
  }
  const all = (cfg?.checks ?? []).map((c) => c.cmd).join(" ");
  check("check.json: запускает Python-тест", all.includes("_test_prompt_logistics.py"));
  check("check.json: запускает аудит", all.includes("_audit_prompt_logistics.mjs"));
}

console.log("— документация и карта папки —");
const SPEC = read("SPECIFICATION.md") || "";
check("SPECIFICATION: описано ограничение цикла",
  /цикл/i.test(SPEC) && /dependency_cycle|отклоня/i.test(SPEC));
check("SPECIFICATION: две ноды описаны", SPEC.includes("Prompt logistics") && SPEC.includes("Prompt logistics — MODEL"));
check("SPECIFICATION: пять переключателей",
  ["LLM Prompt", "STYLE Prompt", "STYLE в LLM", "INT", "INT в LLM"]
    .every((name) => SPEC.includes(name)));
check("SPECIFICATION: ленивый ПрLLM описан",
  /ленив/i.test(SPEC) && /check_lazy_status/.test(SPEC));
check("SPECIFICATION: ПрМаст без дубля описан", /без дубля|не дублир/i.test(SPEC));
check("SPECIFICATION: STYLE Prompt — выключатель, STYLE в LLM — маршрут",
  /главный выключатель/i.test(SPEC) && /только маршрут/i.test(SPEC));
const ROOT_README = read("../README.md") || "";
check("README папки: проект в карте", ROOT_README.includes("Prompt_Logistics"));
check("README папки: у проекта свои проверки",
  new RegExp("`Prompt_Logistics`[^\\n]*check\\.json").test(ROOT_README));

check("нет __pycache__ в исходнике", !fs.existsSync(path.join(ROOT, "__pycache__")));
check("нет .pyc в исходнике", !walkFiles(ROOT).some((f) => f.endsWith(".pyc")));

function walkFiles(dir) {
  const out = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (entry.name.startsWith(".") || entry.name === "__pycache__") continue;
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) out.push(...walkFiles(full));
    else out.push(full);
  }
  return out;
}

console.log();
if (errors.length) {
  console.log(`FAIL: ${errors.length} из ${checks.length}`);
  for (const item of errors) console.log(`  - ${item}`);
  process.exit(1);
}
console.log(`FAIL: 0 (проверок ${checks.length})`);
console.log("аудит чист");
