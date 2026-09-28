const tg = window.Telegram.WebApp;
tg.expand();
tg.ready();
tg.setHeaderColor(tg.backgroundColor);
const initData = tg.initData;
const $ = (id) => document.getElementById(id);

if ((tg.colorScheme || "light") === "dark") document.body.classList.add("dark");
tg.onEvent("themeChanged", () => {
  document.body.classList.toggle("dark", tg.colorScheme === "dark");
});

$("dateLine").textContent = new Date().toLocaleDateString("ru-RU", {
  weekday: "long", day: "numeric", month: "long",
});

async function api(path, opts = {}) {
  const r = await fetch(path, opts);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}
const fd = (obj) => { const f = new FormData(); for (const k in obj) f.append(k, obj[k]); return f; };
const esc = (s) => { const d = document.createElement("div"); d.textContent = s; return d.innerHTML; };

async function refresh() {
  const [t, w] = await Promise.all([
    api("/api/today?init_data=" + encodeURIComponent(initData)),
    api("/api/week?init_data=" + encodeURIComponent(initData)),
  ]);
  renderToday(t);
  renderWeek(w);
}

function renderToday({ goals, totals, meals }) {
  document.querySelectorAll(".ring").forEach((el) => {
    const k = el.dataset.key;
    const cur = totals[k] || 0, goal = goals[k] || 1;
    el.querySelector(".bar i").style.width = Math.min(cur / goal * 100, 100) + "%";
    el.classList.toggle("over", cur > goal);
    el.querySelector("b").textContent = Math.round(cur);
    el.querySelector("span").textContent = el.querySelector("span").textContent.split(" / ")[0] +
      " / " + Math.round(goal);
  });
  const box = $("meals");
  if (!meals.length) {
    box.innerHTML = '<div class="empty">Пока пусто — добавь фото еды</div>';
    return;
  }
  box.innerHTML = "";
  meals.forEach((m) => {
    const d = document.createElement("div");
    d.className = "meal";
    d.innerHTML = `<div><div class="name">${esc(m.dish)}</div>
      <div class="macros">${Math.round(m.kcal)} ккал · Б ${Math.round(m.protein)} · Ж ${Math.round(m.fat)} · У ${Math.round(m.carbs)}</div></div>
      <button class="del">✕</button>`;
    d.querySelector(".del").onclick = async () => {
      await api("/api/meals/" + m.id + "?init_data=" + encodeURIComponent(initData), { method: "DELETE" });
      refresh();
    };
    box.appendChild(d);
  });
}

function renderWeek({ days, goals }) {
  const goal = goals.kcal || 2000;
  const max = Math.max(goal, ...days.map((d) => d.kcal)) * 1.1;
  $("week").innerHTML = "";
  days.forEach((d) => {
    const isToday = days.indexOf(d) === days.length - 1;
    const el = document.createElement("div");
    el.className = "day" + (isToday ? " today" : "");
    el.innerHTML = `<div class="col"><div class="fill" style="height:0%"></div></div>
      <div class="lbl">${d.label}</div><div class="val">${Math.round(d.kcal)}</div>`;
    $("week").appendChild(el);
    requestAnimationFrame(() =>
      el.querySelector(".fill").style.height = Math.min(d.kcal / max * 100, 100) + "%");
  });
}

// фото
$("photoInput").addEventListener("change", async (e) => {
  const file = e.target.files[0];
  if (!file) return;
  $("scanLine").hidden = false;
  $("scanLine").textContent = "🔍 Анализирую фото...";
  try {
    const r = await api("/api/food", { method: "POST", body: fd({ init_data: initData, photo: file }) });
    $("scanLine").textContent = `✓ ${r.meal.dish} — ${Math.round(r.meal.kcal)} ккал`;
    tg.HapticFeedback.notificationOccurred("success");
    refresh();
  } catch (err) {
    $("scanLine").textContent = "Не получилось 😔 Попробуй ещё раз";
    tg.HapticFeedback.notificationOccurred("error");
  }
  e.target.value = "";
});

// цели
$("btnGoals").onclick = async () => {
  const { user } = await api("/api/init", { method: "POST", body: fd({ init_data: initData }) });
  gKcal.value = Math.round(user.kcal); gProtein.value = Math.round(user.protein);
  gFat.value = Math.round(user.fat); gCarbs.value = Math.round(user.carbs);
  $("goalsModal").hidden = false;
};
$("closeGoals").onclick = () => ($("goalsModal").hidden = true);
$("saveGoals").onclick = async () => {
  await api("/api/goals", {
    method: "PUT", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ init_data: initData, kcal: +gKcal.value,
      protein: +gProtein.value, fat: +gFat.value, carbs: +gCarbs.value }),
  });
  $("goalsModal").hidden = true;
  tg.HapticFeedback.notificationOccurred("success");
  refresh();
};

// чат
$("btnChat").onclick = () => { $("chatPanel").hidden = false; };
$("closeChat").onclick = () => ($("chatPanel").hidden = true);
function addMsg(text, me) {
  const d = document.createElement("div");
  d.className = "msg " + (me ? "me" : "bot");
  d.textContent = text;
  $("chatBody").appendChild(d);
  $("chatBody").scrollTop = 1e9;
  return d;
}
async function sendChat() {
  const text = $("chatText").value.trim();
  if (!text) return;
  $("chatText").value = "";
  addMsg(text, true);
  const t = addMsg("печатает...", false);
  t.classList.add("typing");
  try {
    const r = await api("/api/chat", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ init_data: initData, text }),
    });
    t.classList.remove("typing");
    t.textContent = r.reply;
    if (r.goals_saved) tg.HapticFeedback.notificationOccurred("success");
    refresh();
  } catch (e) {
    t.textContent = "Ошибка 😔 Попробуй ещё раз";
  }
}
$("sendChat").onclick = sendChat;
$("chatText").addEventListener("keydown", (e) => e.key === "Enter" && sendChat());

(async () => {
  await api("/api/init", { method: "POST", body: fd({ init_data: initData }) });
  await refresh();
})().catch((e) => { document.body.innerHTML = "<p style='padding:24px'>Ошибка загрузки 😔</p>"; });
