const form = document.getElementById("patientForm");
const resultEl = document.getElementById("result");

function setupTabs() {
  const tabs = document.querySelectorAll(".tab");
  const tabQuestionnaire = document.getElementById("tab_questionnaire");
  const tabResultats = document.getElementById("tab_resultats");

  function setActive(name) {
    tabs.forEach((t) => t.classList.toggle("is-active", t.dataset.tab === name));
    tabQuestionnaire.classList.toggle("is-active", name === "questionnaire");
    tabResultats.classList.toggle("is-active", name === "resultats");
  }

  tabs.forEach((t) => {
    t.addEventListener("click", () => setActive(t.dataset.tab));
  });

  return { setActive };
}

function transformSelectsToRadios() {
  const selects = form.querySelectorAll("select");
  selects.forEach((select) => {
    // Evite double transformation si hot-reload
    if (select.dataset.radioified === "1") return;
    select.dataset.radioified = "1";

    const group = document.createElement("div");
    group.className = "radio-group";
    group.dataset.forSelectId = select.id;

    const groupName = `radio_${select.id}`;
    Array.from(select.options).forEach((opt, idx) => {
      const optionLabel = document.createElement("label");
      optionLabel.className = "radio-option";

      const input = document.createElement("input");
      input.type = "radio";
      input.name = groupName;
      input.value = opt.value;
      input.checked = opt.value === select.value || (idx === 0 && !select.value);

      input.addEventListener("change", () => {
        if (!input.checked) return;
        select.value = input.value;
        select.dispatchEvent(new Event("change", { bubbles: true }));
      });

      const text = document.createElement("span");
      text.textContent = opt.textContent ?? opt.value;

      optionLabel.appendChild(input);
      optionLabel.appendChild(text);
      group.appendChild(optionLabel);
    });

    // Synchronise quand valeur du select change (demo prefill)
    select.addEventListener("change", () => {
      const radios = group.querySelectorAll(`input[name="${groupName}"]`);
      radios.forEach((r) => {
        r.checked = r.value === select.value;
      });
    });

    // Cache le select original mais le garde pour la logique existante
    select.classList.add("is-hidden");
    select.insertAdjacentElement("afterend", group);
  });
}

function setAnswerMode(mode) {
  // mode: "radios" | "select"
  const useSelect = mode === "select";
  const selects = form.querySelectorAll("select");
  selects.forEach((select) => {
    const group = select.parentElement?.querySelector(`.radio-group[data-for-select-id="${select.id}"]`);
    if (useSelect) {
      select.classList.remove("is-hidden");
      if (group) group.classList.add("is-hidden");
    } else {
      select.classList.add("is-hidden");
      if (group) group.classList.remove("is-hidden");
    }
  });
}

function setupAnswerModeToggle() {
  const toggle = document.getElementById("toggleAnswerMode");
  if (!toggle) return;

  const saved = localStorage.getItem("answer_mode") || "radios";
  toggle.checked = saved === "select";
  setAnswerMode(saved === "select" ? "select" : "radios");

  toggle.addEventListener("change", () => {
    const mode = toggle.checked ? "select" : "radios";
    localStorage.setItem("answer_mode", mode);
    setAnswerMode(mode);
  });
}

function numOrNull(id) {
  const el = document.getElementById(id);
  const v = el.value;
  if (v === "" || v === null || v === undefined) return null;
  const f = Number(v);
  return Number.isFinite(f) ? f : null;
}

function setIfExists(id, value) {
  const el = document.getElementById(id);
  if (!el) return;
  el.value = value ?? "";
  el.dispatchEvent(new Event("change", { bubbles: true }));
}

function setButtonLoading(button, isLoading, loadingText) {
  if (!button) return;
  if (isLoading) {
    if (!button.dataset.originalText) button.dataset.originalText = button.textContent || "";
    button.disabled = true;
    button.classList.add("is-loading");
    button.textContent = loadingText;
  } else {
    button.disabled = false;
    button.classList.remove("is-loading");
    if (button.dataset.originalText) button.textContent = button.dataset.originalText;
  }
}

function renderLoading(message = "Chargement...") {
  resultEl.innerHTML = `
    <div class="loading-box">
      <span class="spinner" aria-hidden="true"></span>
      <span>${message}</span>
    </div>
  `;
}

function getPayload() {
  const payload = {
    // Profil
    sexe: document.getElementById("sexe").value,
    age: Number(document.getElementById("age").value),
    poids: Number(document.getElementById("poids").value),
    taille: Number(document.getElementById("taille").value),

    // Hérédité
    antecedents_familiaux: document.getElementById("antecedents_familiaux").value,

    // Mode de vie
    heures_assis: document.getElementById("heures_assis").value,
    activite_physique: document.getElementById("activite_physique").value,
    tabac: document.getElementById("tabac").value,
    tabac_passif: document.getElementById("tabac_passif").value,
    fruits_legumes: document.getElementById("fruits_legumes").value,
    ajout_sel: document.getElementById("ajout_sel").value,
    preparation_repas: document.getElementById("preparation_repas").value,
    charcuterie_fromage: document.getElementById("charcuterie_fromage").value,
    stress: document.getElementById("stress").value,
    coleres: document.getElementById("coleres").value,
    charge_familiale_seule: document.getElementById("charge_familiale_seule").value,
    alcool_excessif: document.getElementById("alcool_excessif").value,
    boissons_energisantes: document.getElementById("boissons_energisantes").value,

    // Données médicales
    hypertension: document.getElementById("hypertension").value,
    tension_systolique: numOrNull("tension_systolique"),
    tension_diastolique: numOrNull("tension_diastolique"),

    cholesterol_eleve: document.getElementById("cholesterol_eleve").value,
    cholesterol_total: numOrNull("cholesterol_total"),
    cholesterol_ldl: numOrNull("cholesterol_ldl"),
    cholesterol_hdl: numOrNull("cholesterol_hdl"),

    diabete: document.getElementById("diabete").value,
    glycemie: numOrNull("glycemie"),

    apnee_sommeil: document.getElementById("apnee_sommeil").value,
    troubles_sommeil: document.getElementById("troubles_sommeil").value,
  };
  return payload;
}

function renderResult(data) {
  const qual = data.qualitatif;

  const safe = (s) => String(s ?? "");

  const score2Block = (() => {
    if (!data.score2) {
      return `
        <div class="card">
          <div class="card-title">SCORE2 (ESC 2021)</div>
          <div class="card-sub">Non calculé</div>
          <div class="hint">Données manquantes : âge 40–89 + PAS + cholestérol total + HDL.</div>
        </div>
      `;
    }
    const s2 = data.score2;
    const risk = Number(s2.risque_pct).toFixed(1);
    const badgeClass =
      s2.couleur === "vert" ? "badge ok" : String(s2.couleur || "").includes("rouge") ? "badge danger" : "badge warn";
    return `
      <div class="card">
        <div class="card-title">SCORE2 (ESC 2021) <span class="${badgeClass}">${safe(s2.categorie)}</span></div>
        <div class="metric">
          <div class="metric-value">${risk}%</div>
          <div class="metric-label">Risque à 10 ans (${safe(s2.mode)})</div>
        </div>
      </div>
    `;
  })();

  const qualiBadgeClass =
    qual.couleur === "vert" ? "badge ok" : String(qual.couleur || "").includes("rouge") ? "badge danger" : "badge warn";

  const pointsForts = (qual.facteurs_positifs || []).map((x) => `<li>${safe(x)}</li>`).join("");
  const recos = (qual.recommandations || []).map((r) => `<li>${safe(r)}</li>`).join("");

  const detailsRows = (qual.details || [])
    .map((d) => {
      const [facteur, valeur, pts, pts_max] = d;
      const p = Number(pts);
      const m = Number(pts_max);
      const ratio = m > 0 ? Math.max(0, Math.min(1, p / m)) : 0;
      const w = Math.round(ratio * 100);
      return `
        <tr>
          <td class="td-factor" data-label="Facteur">${safe(facteur)}</td>
          <td class="td-value" data-label="Valeur">${safe(valeur)}</td>
          <td class="td-points" data-label="Points">${p}/${m}</td>
          <td class="td-bar" data-label="Jauge">
            <div class="bar"><div class="bar-fill" style="width:${w}%"></div></div>
          </td>
        </tr>
      `;
    })
    .join("");

  resultEl.innerHTML = `
    <div class="results">
      ${
        (data.warnings || []).length
          ? `<div class="card">
              <div class="card-title">Vérification de cohérence</div>
              <ul class="warn-list">
                ${(data.warnings || [])
                  .map((w) => `<li><span class="badge warn">Info</span> ${String(w)}</li>`)
                  .join("")}
              </ul>
              <div class="hint">Ces alertes aident à repérer des réponses potentiellement contradictoires. Elles ne sont pas un diagnostic.</div>
            </div>`
          : ""
      }
      <div class="results-grid">
        ${score2Block}

        <div class="card">
          <div class="card-title">Évaluation qualitative <span class="${qualiBadgeClass}">${safe(qual.categorie)}</span></div>
          <div class="metrics-row">
            <div class="metric mini">
              <div class="metric-value">${safe(qual.score_normalise)}%</div>
              <div class="metric-label">Score normalisé</div>
            </div>
            <div class="metric mini">
              <div class="metric-value">${safe(qual.score_brut)}/${safe(qual.score_max)}</div>
              <div class="metric-label">Points</div>
            </div>
            <div class="metric mini">
              <div class="metric-value">${safe(qual.imc)}</div>
              <div class="metric-label">IMC (${safe(qual.categorie_imc)})</div>
            </div>
          </div>
        </div>
      </div>

      <div class="card">
        <div class="card-title">Recommandations prioritaires</div>
        <ol class="reco-list">${recos || "<li>Aucune recommandation.</li>"}</ol>
      </div>

      ${
        pointsForts
          ? `<div class="card"><div class="card-title">Points forts</div><ul class="chips">${pointsForts}</ul></div>`
          : ""
      }

      <details class="card" open>
        <summary class="card-summary">Détail par facteur</summary>
        <div class="table-wrap">
          <table class="details-table">
            <thead>
              <tr>
                <th>Facteur</th>
                <th>Valeur</th>
                <th>Points</th>
                <th>Jauge</th>
              </tr>
            </thead>
            <tbody>
              ${detailsRows}
            </tbody>
          </table>
        </div>
      </details>
    </div>
  `;
}

async function calcAndRender() {
  const submitBtn = form.querySelector('button[type="submit"]');
  setButtonLoading(submitBtn, true, "Calcul en cours...");
  renderLoading("Calcul des résultats en cours...");
  try {
    const payload = getPayload();
    const res = await fetch("/api/calc", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const msg = await res.text();
      throw new Error(msg || `Erreur HTTP ${res.status}`);
    }
    const data = await res.json();
    renderResult(data);
    // Affiche automatiquement l’onglet résultats après calcul
    const tabBtn = document.querySelector('.tab[data-tab="resultats"]');
    if (tabBtn) tabBtn.click();
  } catch (e) {
    resultEl.innerHTML = `<span class="danger"><b>Erreur</b> : ${e.message}</span>`;
  } finally {
    setButtonLoading(submitBtn, false);
  }
}

form.addEventListener("submit", (ev) => {
  ev.preventDefault();
  calcAndRender();
});

document.getElementById("btnPdf").addEventListener("click", async () => {
  const btnPdf = document.getElementById("btnPdf");
  setButtonLoading(btnPdf, true, "Génération PDF...");
  renderLoading("Préparation du PDF...");
  try {
    const payload = getPayload();
    const res = await fetch("/api/pdf", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const msg = await res.text();
      throw new Error(msg || `Erreur HTTP ${res.status}`);
    }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);

    const a = document.createElement("a");
    a.href = url;
    a.download = "rapport_cardiovasculaire.pdf";
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  } catch (e) {
    resultEl.innerHTML = `<span class="danger"><b>Erreur PDF</b> : ${e.message}</span>`;
  } finally {
    setButtonLoading(btnPdf, false);
  }
});

document.getElementById("btnEmail").addEventListener("click", async () => {
  const btnEmail = document.getElementById("btnEmail");
  setButtonLoading(btnEmail, true, "Envoi en cours...");
  try {
    const emailTo = document.getElementById("email_to")?.value?.trim();
    if (!emailTo) {
      resultEl.innerHTML = `<span class="danger"><b>Email</b> : renseignez une adresse destinataire.</span>`;
      return;
    }
    renderLoading("Envoi de l'email en cours...");

    const payload = getPayload();
    payload.email_to = emailTo;
    payload.email_subject = "Votre rapport cardiovasculaire";
    payload.email_body = "Bonjour,\n\nVeuillez trouver ci-joint votre rapport d'évaluation cardiovasculaire.\n\nCordialement.";

    const res = await fetch("/api/email", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const msg = await res.text();
      throw new Error(msg || `Erreur HTTP ${res.status}`);
    }

    const data = await res.json();
    if (data && data.ok) {
      resultEl.innerHTML = `<span class="ok"><b>Email envoyé</b></span>`;
    } else {
      resultEl.innerHTML = `<span class="danger"><b>Email</b> : envoi incertain.</span>`;
    }
  } catch (e) {
    resultEl.innerHTML = `<span class="danger"><b>Erreur</b> : ${e.message}</span>`;
  } finally {
    setButtonLoading(btnEmail, false);
  }
});

const demoHigh = {
  sexe: "H",
  age: 52,
  poids: 85,
  taille: 178,
  antecedents_familiaux: "oui",
  heures_assis: ">7h",
  activite_physique: "<30min",
  tabac: "oui",
  tabac_passif: "oui",
  fruits_legumes: "2-5/sem",
  ajout_sel: "oui",
  preparation_repas: "industriel",
  charcuterie_fromage: "oui",
  stress: "permanent",
  coleres: "frequent",
  charge_familiale_seule: "non",
  alcool_excessif: "non",
  boissons_energisantes: "oui",
  hypertension: "oui",
  tension_systolique: 148,
  tension_diastolique: 92,
  cholesterol_eleve: "oui",
  cholesterol_total: 6.8,
  cholesterol_ldl: 4.2,
  cholesterol_hdl: 1.1,
  diabete: "non",
  glycemie: 1.05,
  apnee_sommeil: "non",
  troubles_sommeil: "oui",
};

const demoHealthy = {
  sexe: "F",
  age: 35,
  poids: 60,
  taille: 165,
  antecedents_familiaux: "non",
  heures_assis: "<3h",
  activite_physique: ">30min",
  tabac: "non",
  tabac_passif: "non",
  fruits_legumes: "5+/jour",
  ajout_sel: "non",
  preparation_repas: "maison",
  charcuterie_fromage: "non",
  stress: "jamais",
  coleres: "jamais",
  charge_familiale_seule: "non",
  alcool_excessif: "non",
  boissons_energisantes: "non",
  hypertension: "non",
  tension_systolique: null,
  tension_diastolique: null,
  cholesterol_eleve: "non",
  cholesterol_total: null,
  cholesterol_ldl: null,
  cholesterol_hdl: null,
  diabete: "non",
  glycemie: null,
  apnee_sommeil: "non",
  troubles_sommeil: "non",
};

function loadDemo(d) {
  setIfExists("sexe", d.sexe);
  setIfExists("age", d.age);
  setIfExists("poids", d.poids);
  setIfExists("taille", d.taille);
  setIfExists("antecedents_familiaux", d.antecedents_familiaux);
  setIfExists("heures_assis", d.heures_assis);
  setIfExists("activite_physique", d.activite_physique);
  setIfExists("tabac", d.tabac);
  setIfExists("tabac_passif", d.tabac_passif);
  setIfExists("fruits_legumes", d.fruits_legumes);
  setIfExists("ajout_sel", d.ajout_sel);
  setIfExists("preparation_repas", d.preparation_repas);
  setIfExists("charcuterie_fromage", d.charcuterie_fromage);
  setIfExists("stress", d.stress);
  setIfExists("coleres", d.coleres);
  setIfExists("charge_familiale_seule", d.charge_familiale_seule);
  setIfExists("alcool_excessif", d.alcool_excessif);
  setIfExists("boissons_energisantes", d.boissons_energisantes);
  setIfExists("hypertension", d.hypertension);
  setIfExists("tension_systolique", d.tension_systolique);
  setIfExists("tension_diastolique", d.tension_diastolique);
  setIfExists("cholesterol_eleve", d.cholesterol_eleve);
  setIfExists("cholesterol_total", d.cholesterol_total);
  setIfExists("cholesterol_ldl", d.cholesterol_ldl);
  setIfExists("cholesterol_hdl", d.cholesterol_hdl);
  setIfExists("diabete", d.diabete);
  setIfExists("glycemie", d.glycemie);
  setIfExists("apnee_sommeil", d.apnee_sommeil);
  setIfExists("troubles_sommeil", d.troubles_sommeil);
}

document.getElementById("btnDemoHigh").addEventListener("click", () => loadDemo(demoHigh));
document.getElementById("btnDemoHealthy").addEventListener("click", () => loadDemo(demoHealthy));

transformSelectsToRadios();
const tabs = setupTabs();
setupAnswerModeToggle();

// Valeurs par défaut = démo haut risque
loadDemo(demoHigh);

// Enregistrement du Service Worker pour mode PWA
if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker
      .register("/static/sw.js")
      .catch((err) => {
        console.error("Service worker registration failed:", err);
      });
  });
}

