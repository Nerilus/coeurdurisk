// =============================================================================
// Service Worker — Coeur Risk
// Stratégie : cache-first pour tous les assets GET statiques.
// Les requêtes POST (/api/calc, /api/pdf, /api/email) ne sont jamais interceptées.
// =============================================================================

const CACHE_NAME = "coeur-risk-cache-v10";

// Assets téléchargés et mis en cache dès l'installation du SW
// (première visite avec internet). Disponibles immédiatement hors ligne.
const ASSETS = [
  "/",
  "/static/styles.css",
  "/static/score2.js",
  "/static/app.js",
  "/static/manifest.json",
  "/assets/ffc-logo-national.png",
  "/assets/icon-ffc-192.png",
  "/assets/icon-ffc-512.png"
];

// ── Installation ──────────────────────────────────────────────────────────────
// Pré-charge tous les ASSETS dans le cache, puis prend la main immédiatement
// sans attendre la fermeture des onglets ouverts.
self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => cache.addAll(ASSETS))
      .then(() => self.skipWaiting())
  );
});

// ── Activation ────────────────────────────────────────────────────────────────
// Supprime les anciens caches (v1, etc.) puis prend le contrôle de tous
// les onglets ouverts sans rechargement.
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) =>
        Promise.all(
          keys.map((key) => {
            if (key !== CACHE_NAME) return caches.delete(key);
          })
        )
      )
      .then(() => self.clients.claim())
  );
});

// ── Fetch ─────────────────────────────────────────────────────────────────────
// Stratégie cache-first pour les requêtes GET uniquement.
// Les POST (API) passent directement sans interception.
self.addEventListener("fetch", (event) => {
  const { request } = event;

  // Laisser passer toutes les requêtes non-GET (POST /api/calc, /api/pdf, /api/email)
  if (request.method !== "GET") return;

  event.respondWith(
    caches.open(CACHE_NAME).then((cache) =>
      cache.match(request).then((cached) => {
        // Trouvé en cache → on le retourne directement, pas de réseau
        if (cached) return cached;

        // Pas en cache → on va chercher sur le réseau
        return fetch(request).then((response) => {
          // On ne met en cache que les réponses valides (200, same-origin)
          // Évite de stocker des 404 ou des réponses d'erreur serveur
          if (response && response.status === 200 && response.type !== "opaque") {
            cache.put(request, response.clone());
          }
          return response;
        });
        // Si fetch échoue et rien en cache → le navigateur gère l'erreur
        // (ne se produit pas pour les ASSETS car ils sont pré-chargés à l'install)
      })
    )
  );
});
