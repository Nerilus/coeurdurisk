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
      input.checked = opt.value === select.value;

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

function clearFormOnLoad() {
  const selects = form.querySelectorAll("select");
  selects.forEach((select) => {
    select.selectedIndex = -1;
    select.value = "";
    select.dispatchEvent(new Event("change", { bubbles: true }));
  });

  const numberAndTextInputs = form.querySelectorAll('input[type="number"], input[type="email"], input[type="text"]');
  numberAndTextInputs.forEach((input) => {
    input.value = "";
  });

  const checkboxes = form.querySelectorAll('input[type="checkbox"]');
  checkboxes.forEach((checkbox) => {
    checkbox.checked = false;
    checkbox.dispatchEvent(new Event("change", { bubbles: true }));
  });
}

function setupUnknownToggle(inputIds, checkboxId) {
  const checkbox = document.getElementById(checkboxId);
  const inputs = inputIds.map((id) => document.getElementById(id)).filter(Boolean);
  if (!checkbox || inputs.length === 0) return;

  const sync = () => {
    inputs.forEach((input) => {
      if (checkbox.checked) {
        input.value = "";
        input.disabled = true;
      } else {
        input.disabled = false;
      }
    });
  };

  checkbox.addEventListener("change", sync);
  sync();
}

function setupUnknownToggles() {
  setupUnknownToggle(["tension_systolique", "tension_diastolique"], "tension_inconnue");
  setupUnknownToggle(["cholesterol_total"], "cholesterol_total_inconnu");
  setupUnknownToggle(["cholesterol_hdl"], "cholesterol_hdl_inconnu");
  setupUnknownToggle(["glycemie"], "glycemie_inconnue");
}

function numOrNull(id) {
  const el = document.getElementById(id);
  if (!el) return null;
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
  const sommeil = document.getElementById("apnee_sommeil").value;

  const payload = {
    // Profil
    sexe: document.getElementById("sexe").value,
    age: Number(document.getElementById("age").value),
    poids: Number(document.getElementById("poids").value),
    taille: Number(document.getElementById("taille").value),

    // Hérédité
    antecedents_familiaux: document.getElementById("antecedents_familiaux").value,
    bilan_cardiaque: document.getElementById("bilan_cardiaque").value,
    consultation_cardiologue: document.getElementById("consultation_cardiologue").value,
    activite_weekend: document.getElementById("activite_weekend").value,

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
    coleres: "jamais",
    charge_familiale_seule: "non",
    alcool_excessif: document.getElementById("alcool_excessif").value,
    boissons_energisantes: document.getElementById("boissons_energisantes").value,

    // Données médicales
    hypertension: document.getElementById("hypertension").value,
    tension_systolique: document.getElementById("tension_inconnue")?.checked ? null : numOrNull("tension_systolique"),
    tension_diastolique: document.getElementById("tension_inconnue")?.checked ? null : numOrNull("tension_diastolique"),

    cholesterol_eleve: document.getElementById("cholesterol_eleve").value,
    cholesterol_total: document.getElementById("cholesterol_total_inconnu")?.checked ? null : numOrNull("cholesterol_total"),
    cholesterol_ldl: numOrNull("cholesterol_ldl"),
    cholesterol_hdl: document.getElementById("cholesterol_hdl_inconnu")?.checked ? null : numOrNull("cholesterol_hdl"),

    diabete: document.getElementById("diabete").value,
    glycemie: document.getElementById("glycemie_inconnue")?.checked ? null : numOrNull("glycemie"),

    apnee_sommeil: sommeil,
    troubles_sommeil: sommeil,
  };
  return payload;
}

function renderResult(data) {
  const qual = data.qualitatif;

  const safe = (s) => String(s ?? "");
  const scoreNorm = Number(qual.score_normalise || 0);
  const gaugePct = Math.max(3, Math.min(97, scoreNorm));
  const riskTone =
    qual.couleur === "vert"
      ? "ok"
      : String(qual.couleur || "").includes("rouge")
      ? "danger"
      : "warn";
  const detailsMap = Object.fromEntries((qual.details || []).map((d) => [String(d[0]), String(d[1])]));

  const hasHighSedentarity = detailsMap["Sédentarité (temps assis)"] === ">7h";
  const hasLowActivity = detailsMap["Activité physique"] === "<30min";
  const hasAlcoholRisk = detailsMap["Alcool excessif"] === "oui";
  const hasEnergyDrinkRisk = detailsMap["Boissons énergisantes"] === "oui";
  const hasFoodRisk =
    detailsMap["Fruits et légumes"] === "<2/sem" ||
    detailsMap["Fruits et légumes"] === "2-5/sem" ||
    detailsMap["Ajout de sel"] === "oui" ||
    detailsMap["Préparation des repas"] === "industriel" ||
    detailsMap["Charcuterie/Fromage régulier"] === "oui";
  const hasDiabetesRisk = detailsMap["Diabète"] === "oui";
  const hasHypertensionRisk = detailsMap["Hypertension"] === "oui";
  const hasCholRisk = detailsMap["Cholestérol élevé"] === "oui";
  const hasSleepRisk = detailsMap["Troubles du sommeil"] === "oui" || detailsMap["Apnée du sommeil"] === "oui";

  const conseilsAdaptes = [];
  if (hasLowActivity || hasHighSedentarity) {
    conseilsAdaptes.push(`
      <li>
        <b>Activité physique et sédentarité</b><br />
        Pratiquer 30 minutes d'activité physique quotidienne diminue d'environ un tiers le risque cardiovasculaire.
        L'objectif est d'atteindre 150 minutes d'activité modérée ou 75 minutes d'activité soutenue par semaine, réparties sur plusieurs jours.
        Évitez les longues périodes assises, surtout au-delà de 7 h/jour : levez-vous quelques minutes toutes les 2 heures.
      </li>
    `);
  }
  if (hasAlcoholRisk || hasEnergyDrinkRisk) {
    conseilsAdaptes.push(`
      <li>
        <b>Alcool et boissons énergisantes</b><br />
        L'excès d'alcool augmente le risque de maladies cardiovasculaires, neurologiques et de cancers.
        Recommandation générale : ne pas dépasser 2 verres/jour, pas tous les jours, avec au moins 2 jours sans alcool par semaine.
        Les boissons énergisantes peuvent majorer le risque de palpitations et d'hypertension : il est conseillé de les limiter fortement.
      </li>
    `);
  }
  if (hasFoodRisk) {
    conseilsAdaptes.push(`
      <li>
        <b>Alimentation</b><br />
        Une alimentation de type méditerranéen aide à réduire le risque cardiovasculaire :
        plus de fruits/légumes, poissons, huiles végétales (olive), et moins de produits transformés.
        Limitez le sel, la charcuterie, les fromages en excès et les plats préparés.
      </li>
    `);
  }
  if (hasDiabetesRisk) {
    conseilsAdaptes.push(`
      <li>
        <b>Diabète</b><br />
        Le diabète est un facteur majeur de risque cardiovasculaire. L'activité physique, la perte de poids si besoin
        et le suivi médical régulier sont essentiels pour améliorer l'équilibre glycémique.
      </li>
    `);
  }
  if (hasHypertensionRisk) {
    conseilsAdaptes.push(`
      <li>
        <b>Hypertension artérielle</b><br />
        Une pression artérielle élevée augmente fortement le risque d'accident cardiaque et d'AVC.
        Les mesures hygiéno-diététiques (poids, sel, alcool, activité physique) sont utiles, mais un traitement peut être nécessaire avec votre médecin.
      </li>
    `);
  }
  if (hasCholRisk) {
    conseilsAdaptes.push(`
      <li>
        <b>Cholestérol</b><br />
        Un cholestérol élevé contribue au risque d'athérosclérose. Un bilan lipidique régulier, une alimentation adaptée
        et un suivi médical permettent de réduire ce risque.
      </li>
    `);
  }
  if (hasSleepRisk) {
    conseilsAdaptes.push(`
      <li>
        <b>Troubles du sommeil</b><br />
        Des troubles du sommeil persistants augmentent le risque cardiovasculaire.
        Une meilleure hygiène de sommeil et, si besoin, une consultation spécialisée sont recommandées.
      </li>
    `);
  }

  const conseilsAdaptesHtml =
    conseilsAdaptes.length > 0
      ? `<ol class="reco-list">${conseilsAdaptes.join("")}</ol>`
      : "<p>Aucun facteur majeur supplémentaire détecté sur ces thèmes. Continuez vos efforts de prévention.</p>";

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
      <div class="results-heading">VOS RÉSULTATS :</div>

      <div class="risk-hero">
        <p class="risk-hero-intro">
          Ce test a pour objectif de sensibiliser l'utilisateur sur sa situation cardio-vasculaire et de le conseiller
          avec des actions simples à réaliser pour agir, la consultation du médecin traitant ou du cardiologue doit être
          privilégiée pour toutes les situations spécifiques.
        </p>

        <div class="risk-gauge-wrap">
          <div class="risk-gauge">
            <div class="risk-segment risk-segment-ok"></div>
            <div class="risk-segment risk-segment-warn"></div>
            <div class="risk-segment risk-segment-danger"></div>
            <div class="risk-needle" style="left:${gaugePct}%"></div>
          </div>
        </div>

        <div class="risk-hero-title">Votre risque d'un accident cardiovasculaire est :</div>
        <div class="risk-hero-pill risk-${riskTone}">${safe(qual.categorie)}</div>

        <div class="risk-hero-imc">
          Votre indice de masse corporelle est de <b>${safe(qual.imc)}</b>. <b>${safe(qual.categorie_imc)}</b>
        </div>
        <p class="risk-hero-note">
          Le surpoids et l'obésité favorisent plusieurs facteurs de risque cardiovasculaires comme l'hypertension artérielle,
          le diabète, l'hypercholestérolémie. Il est important de maintenir si possible un poids normal tout au long de la vie
          et, en cas de prise de poids, d'essayer de le réduire.
        </p>

        <button type="button" id="btnSimulerRisque" class="btn btn-secondary risk-hero-btn">
          Simuler une diminution des risques
        </button>
      </div>

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

      <div class="card" id="card_recommandations">
        <div class="card-title">Recommandations prioritaires</div>
        <ol class="reco-list">${recos || "<li>Aucune recommandation.</li>"}</ol>
      </div>

      <div class="card">
        <div class="card-title">Conseils adaptés</div>
        ${conseilsAdaptesHtml}
        <p class="hint">
          Conseil prévention : pour toute question médicale, contactez votre médecin ou votre cardiologue.
          Ressources FFC : <a href="https://www.fedecardio.org/" target="_blank" rel="noopener noreferrer">Lien vers nos publications</a>.
        </p>
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

  const btnSimuler = document.getElementById("btnSimulerRisque");
  const cardRecos = document.getElementById("card_recommandations");
  if (btnSimuler && cardRecos) {
    btnSimuler.addEventListener("click", () => {
      cardRecos.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  }
}

function clearErrors() {
  form.querySelectorAll(".field-error").forEach((el) => el.remove());
  form.querySelectorAll(".field.has-error").forEach((el) => el.classList.remove("has-error"));
}

function addError(field, message) {
  if (field.querySelector(".field-error")) return; // éviter les doublons
  field.classList.add("has-error");
  const err = document.createElement("div");
  err.className = "field-error";
  err.textContent = message;
  field.appendChild(err);
}

function validateForm() {
  clearErrors();
  let valid = true;
  let firstErrorField = null;

  // Valider les selects (transformés en radios)
  form.querySelectorAll("select").forEach((select) => {
    if (!select.value) {
      const field = select.closest(".field");
      if (field) {
        addError(field, "Veuillez sélectionner une réponse.");
        valid = false;
        if (!firstErrorField) firstErrorField = field;
      }
    }
  });

  // Valider les champs numériques obligatoires (age, poids, taille)
  ["age", "poids", "taille"].forEach((id) => {
    const input = document.getElementById(id);
    if (!input) return;
    const val = Number(input.value);
    if (!input.value || val <= 0) {
      const field = input.closest(".field");
      if (field) {
        addError(field, "Veuillez remplir ce champ.");
        valid = false;
        if (!firstErrorField) firstErrorField = field;
      }
    }
  });

  // Ouvrir les accordéons contenant des erreurs pour les rendre visibles
  if (!valid) {
    form.querySelectorAll(".field.has-error").forEach((field) => {
      const details = field.closest("details");
      if (details && !details.open) details.open = true;
    });
  }

  if (firstErrorField) {
    firstErrorField.scrollIntoView({ behavior: "smooth", block: "center" });
  }

  return valid;
}

async function calcAndRender() {
  if (!validateForm()) {
    return;
  }

  const submitBtn = form.querySelector('button[type="submit"]');
  setButtonLoading(submitBtn, true, "Calcul en cours...");
  renderLoading("Calcul des résultats en cours...");
  try {
    const payload = getPayload();
    // Calcul toujours en local (mode offline)
    const data = evaluerRisque(payload);
    renderResult(data);
    // Affiche automatiquement l'onglet résultats après calcul
    const tabBtn = document.querySelector('.tab[data-tab="resultats"]');
    if (tabBtn) tabBtn.click();
    // Scroll vers le haut pour voir les résultats
    window.scrollTo({ top: 0, behavior: "smooth" });
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

document.getElementById("btnReset").addEventListener("click", () => {
  clearFormOnLoad();
  clearErrors();
  resultEl.innerHTML = "";
  const tabBtn = document.querySelector('.tab[data-tab="questionnaire"]');
  if (tabBtn) tabBtn.click();
});

transformSelectsToRadios();
const tabs = setupTabs();
setupUnknownToggles();
clearFormOnLoad();

// ── Gestion du mode offline ──────────────────────────────────────────────────

function updateOfflineUI() {
  const banner = document.getElementById("offlineBanner");
  if (banner) banner.hidden = !(!navigator.onLine);
}

window.addEventListener("online",  updateOfflineUI);
window.addEventListener("offline", updateOfflineUI);
updateOfflineUI();

// Enregistrement du Service Worker pour mode PWA
if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker
      .register("/sw.js", { scope: "/" })
      .catch((err) => {
        console.error("Service worker registration failed:", err);
      });
  });
}

