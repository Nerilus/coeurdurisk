from __future__ import annotations

import os
import smtplib
import tempfile
import time
import uuid
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Literal, Optional

from email.message import EmailMessage

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, ConfigDict
from starlette.background import BackgroundTask
from starlette.requests import Request

from coeur_risk import PatientData, evaluer_risque, generer_pdf


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
INDEX_FILE = STATIC_DIR / "index.html"
PROJECT_DIR = BASE_DIR.parent
LOG_DIR = PROJECT_DIR / "logs"

app = FastAPI(title="Coeur Risk", version="1.0.0")

app.mount("/static", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
app.mount("/assets", StaticFiles(directory=str(BASE_DIR), html=False), name="assets")

logger = logging.getLogger("coeur_risk")
if not logger.handlers:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    log_file = os.getenv("LOG_FILE", str(LOG_DIR / "coeur_risk.log"))

    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")

    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(log_level)
    stream_handler.setFormatter(formatter)

    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=int(os.getenv("LOG_MAX_BYTES", "2000000")),  # ~2MB
        backupCount=int(os.getenv("LOG_BACKUP_COUNT", "5")),
        encoding="utf-8",
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)

    logger.setLevel(log_level)
    logger.addHandler(stream_handler)
    logger.addHandler(file_handler)


@app.middleware("http")
async def request_logging(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    start = time.perf_counter()
    response = None
    try:
        response = await call_next(request)
    except Exception:
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        client_ip = request.client.host if request.client else "-"
        logger.exception(
            "api_request_error request_id=%s ip=%s method=%s path=%s elapsed_ms=%s",
            request_id,
            client_ip,
            request.method,
            request.url.path,
            elapsed_ms,
        )
        raise
    finally:
        if response is not None:
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            client_ip = request.client.host if request.client else "-"
            content_type = response.headers.get("content-type", "-")
            content_length = response.headers.get("content-length", "-")
            logger.info(
                "api_request request_id=%s ip=%s method=%s path=%s status=%s elapsed_ms=%s content_type=%s content_length=%s",
                request_id,
                client_ip,
                request.method,
                request.url.path,
                response.status_code,
                elapsed_ms,
                content_type,
                content_length,
            )
    response.headers["x-request-id"] = request_id
    return response


def jsonable(x: Any) -> Any:
    """Convert non-JSON types (tuples) into JSON-safe structures."""
    if isinstance(x, tuple):
        return [jsonable(v) for v in x]
    if isinstance(x, list):
        return [jsonable(v) for v in x]
    if isinstance(x, dict):
        return {k: jsonable(v) for k, v in x.items()}
    return x


def coherence_warnings(inp: PatientInput) -> list[str]:
    """
    Retourne une liste d'avertissements de cohérence (anonymes, sans valeurs brutes).
    Objectif : détecter des réponses contradictoires ou des valeurs improbables.
    """
    warn: list[str] = []

    # Hypertension vs pression artérielle
    if inp.hypertension == "non" and inp.tension_systolique is not None:
        if inp.tension_systolique >= 140:
            warn.append("HTA_NON_MAIS_PAS_ELEVEE")
    if inp.hypertension == "oui" and inp.tension_systolique is None:
        warn.append("HTA_OUI_MAIS_PAS_SAISIE")

    # Cholestérol vs valeurs
    if inp.cholesterol_eleve == "non" and inp.cholesterol_total is not None:
        if inp.cholesterol_total >= 6.2:
            warn.append("CHOLESTEROL_NON_MAIS_TOTAL_ELEVE")
    if inp.cholesterol_eleve == "oui" and inp.cholesterol_total is None:
        warn.append("CHOLESTEROL_OUI_MAIS_TOTAL_PAS_SAISI")

    # Diabète vs glycémie
    if inp.diabete == "non" and inp.glycemie is not None:
        if inp.glycemie >= 1.26:
            warn.append("DIABETE_NON_MAIS_GLYCEMIE_ELEVEE")
    if inp.diabete == "oui" and inp.glycemie is None:
        warn.append("DIABETE_OUI_MAIS_GLYCEMIE_PAS_SAISIE")

    # Valeurs plausibles (sans bloquer, uniquement warnings)
    if inp.tension_systolique is not None and (inp.tension_systolique < 70 or inp.tension_systolique > 250):
        warn.append("PAS_HORS_PLAUSIBLE")
    if inp.cholesterol_total is not None and (inp.cholesterol_total < 2 or inp.cholesterol_total > 15):
        warn.append("TCHOL_HORS_PLAUSIBLE")
    if inp.cholesterol_hdl is not None and (inp.cholesterol_hdl < 0.3 or inp.cholesterol_hdl > 5):
        warn.append("HDL_HORS_PLAUSIBLE")
    if inp.glycemie is not None and (inp.glycemie < 0.3 or inp.glycemie > 5):
        warn.append("GLYCEMIE_HORS_PLAUSIBLE")

    # SCORE2 : si âge dans la plage mais données manquantes
    if 40 <= inp.age <= 89:
        if inp.tension_systolique is None or inp.cholesterol_total is None or inp.cholesterol_hdl is None:
            warn.append("SCORE2_POSSIBLE_MAIS_DONNEES_MANQUANTES")

    return warn


class PatientInput(BaseModel):
    model_config = ConfigDict(extra="ignore")
    # Profil
    sexe: Literal["H", "F"]
    age: int = Field(ge=0, le=120)
    poids: float = Field(gt=0)
    taille: float = Field(gt=0)  # cm

    # Hérédité
    antecedents_familiaux: Literal["oui", "non", "ne_sais_pas"]

    # Mode de vie
    heures_assis: Literal["<3h", "3-7h", ">7h"]
    activite_physique: Literal["<30min", "~30min", ">30min"]
    tabac: Literal["oui", "ancien_5ans", "non"]
    tabac_passif: Literal["oui", "non"]
    fruits_legumes: Literal["<2/sem", "2-5/sem", "2-4/jour", "5+/jour"]
    ajout_sel: Literal["oui", "non"]
    preparation_repas: Literal["industriel", "maison", "conserves"]
    charcuterie_fromage: Literal["oui", "non"]
    stress: Literal["jamais", "occasionnel", "permanent"]
    coleres: Literal["jamais", "peu", "frequent", "tres_frequent"]
    charge_familiale_seule: Literal["oui", "non"]
    alcool_excessif: Literal["oui", "non"]
    boissons_energisantes: Literal["oui", "non"]

    # Données médicales
    hypertension: Literal["oui", "non"]
    tension_systolique: Optional[float] = None
    tension_diastolique: Optional[float] = None

    cholesterol_eleve: Literal["oui", "non"]
    cholesterol_total: Optional[float] = None
    cholesterol_ldl: Optional[float] = None
    cholesterol_hdl: Optional[float] = None

    diabete: Literal["oui", "non"]
    glycemie: Optional[float] = None

    apnee_sommeil: Literal["oui", "non"]
    troubles_sommeil: Literal["oui", "non"]


class EmailRequest(PatientInput):
    email_to: str = Field(..., description="Adresse email du destinataire")
    email_subject: Optional[str] = Field(
        default="Votre rapport cardiovasculaire",
        description="Objet du message",
    )
    email_body: Optional[str] = Field(
        default="Bonjour,\n\nVeuillez trouver ci-joint votre rapport d'évaluation cardiovasculaire.\n",
        description="Corps du message (texte)",
    )


def smtp_config() -> dict:
    """
    Chargement de la config SMTP via variables d'environnement.
    Attendus :
      - SMTP_HOST
      - SMTP_PORT (ex: 587)
      - SMTP_USERNAME
      - SMTP_PASSWORD
      - SMTP_FROM (expéditeur)
    Optionnel :
      - SMTP_USE_STARTTLS (1 par défaut, mettre 0 pour désactiver)
    """
    required = ["SMTP_HOST", "SMTP_PORT", "SMTP_USERNAME", "SMTP_PASSWORD", "SMTP_FROM"]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        raise RuntimeError(f"SMTP non configuré. Variables manquantes : {', '.join(missing)}")

    return {
        "host": os.getenv("SMTP_HOST", ""),
        "port": int(os.getenv("SMTP_PORT", "587")),
        "username": os.getenv("SMTP_USERNAME", ""),
        "password": os.getenv("SMTP_PASSWORD", ""),
        "from_addr": os.getenv("SMTP_FROM", ""),
        "use_starttls": os.getenv("SMTP_USE_STARTTLS", "1") not in ("0", "false", "False"),
    }


def send_email_with_pdf(
    *,
    smtp: dict,
    email_to: str,
    subject: str,
    body: str,
    pdf_path: str,
    resultats: dict,
) -> None:
    msg = EmailMessage()
    msg["From"] = smtp["from_addr"]
    msg["To"] = email_to
    msg["Subject"] = subject
    msg.set_content(body)

    # Résumé texte (évite que l’utilisateur doive ouvrir le PDF)
    if "score2" in resultats:
        s2 = resultats["score2"]
        summary = (
            f"\nSCORE2 : {s2.get('mode')} — {s2.get('risque_pct')}%\n"
            f"Classification : {s2.get('categorie')}\n"
        )
    else:
        summary = "\nSCORE2 : non calculé (données médicales manquantes)\n"
    msg.set_content(body + summary)

    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    msg.add_attachment(
        pdf_bytes,
        maintype="application",
        subtype="pdf",
        filename="rapport_cardiovasculaire.pdf",
    )

    with smtplib.SMTP(smtp["host"], smtp["port"], timeout=30) as server:
        if smtp["use_starttls"]:
            server.starttls()
        server.login(smtp["username"], smtp["password"])
        server.send_message(msg)


def to_patient_data(inp: PatientInput) -> PatientData:
    return PatientData(
        sexe=inp.sexe,
        age=inp.age,
        poids=inp.poids,
        taille=inp.taille,
        antecedents_familiaux=inp.antecedents_familiaux,
        heures_assis=inp.heures_assis,
        activite_physique=inp.activite_physique,
        tabac=inp.tabac,
        tabac_passif=inp.tabac_passif,
        fruits_legumes=inp.fruits_legumes,
        ajout_sel=inp.ajout_sel,
        preparation_repas=inp.preparation_repas,
        charcuterie_fromage=inp.charcuterie_fromage,
        stress=inp.stress,
        coleres=inp.coleres,
        charge_familiale_seule=inp.charge_familiale_seule,
        alcool_excessif=inp.alcool_excessif,
        boissons_energisantes=inp.boissons_energisantes,
        hypertension=inp.hypertension,
        tension_systolique=inp.tension_systolique,
        tension_diastolique=inp.tension_diastolique,
        cholesterol_eleve=inp.cholesterol_eleve,
        cholesterol_total=inp.cholesterol_total,
        cholesterol_ldl=inp.cholesterol_ldl,
        cholesterol_hdl=inp.cholesterol_hdl,
        diabete=inp.diabete,
        glycemie=inp.glycemie,
        apnee_sommeil=inp.apnee_sommeil,
        troubles_sommeil=inp.troubles_sommeil,
    )


@app.get("/")
def index() -> FileResponse:
    if not INDEX_FILE.exists():
        raise HTTPException(500, "index.html introuvable")
    return FileResponse(str(INDEX_FILE))


@app.post("/api/calc")
def calc(inp: PatientInput) -> JSONResponse:
    patient = to_patient_data(inp)
    resultats = evaluer_risque(patient)
    warns = coherence_warnings(inp)
    resultats["warnings"] = warns
    # Logs anonymisés : uniquement des résultats agrégés
    try:
        qual = resultats.get("qualitatif", {})
        score2 = resultats.get("score2")
        logger.info(
            "calc_done",
            extra={
                "score2_computed": bool(score2),
                "score2_mode": score2.get("mode") if score2 else None,
                "score2_risk_pct": score2.get("risque_pct") if score2 else None,
                "qual_score_norm": qual.get("score_normalise"),
                "qual_category": qual.get("categorie"),
                "warning_count": len(warns),
                "warning_codes": warns[:10],  # codes only, no values
            },
        )
    except Exception:
        logger.exception("calc_log_failed")
    return JSONResponse(content=jsonable(resultats))


@app.post("/api/pdf")
def pdf(inp: PatientInput) -> FileResponse:
    patient = to_patient_data(inp)
    resultats = evaluer_risque(patient)

    tmp = tempfile.NamedTemporaryFile(prefix="coeur_risk_", suffix=".pdf", delete=False)
    tmp_path = tmp.name
    tmp.close()

    try:
        generer_pdf(patient, resultats, filename=tmp_path)
    except Exception as e:
        # Cleanup best-effort
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise HTTPException(500, f"Erreur génération PDF: {e}")

    try:
        score2 = resultats.get("score2")
        qual = resultats.get("qualitatif", {})
        logger.info(
            "pdf_generated",
            extra={
                "score2_computed": bool(score2),
                "score2_risk_pct": score2.get("risque_pct") if score2 else None,
                "qual_score_norm": qual.get("score_normalise"),
            },
        )
    except Exception:
        logger.exception("pdf_log_failed")

    background = BackgroundTask(lambda: os.path.exists(tmp_path) and os.unlink(tmp_path))
    return FileResponse(
        tmp_path,
        media_type="application/pdf",
        filename="rapport_cardiovasculaire.pdf",
        background=background,
    )


@app.post("/api/email")
def email(req: EmailRequest) -> JSONResponse:
    """
    Génère le PDF puis l’envoie par email (pièce jointe).
    SMTP configuré via variables d’environnement (voir smtp_config()).
    """
    try:
        smtp = smtp_config()
    except Exception as e:
        raise HTTPException(500, f"SMTP non configuré : {e}")

    patient = to_patient_data(req)
    resultats = evaluer_risque(patient)

    tmp = tempfile.NamedTemporaryFile(prefix="coeur_risk_", suffix=".pdf", delete=False)
    tmp_path = tmp.name
    tmp.close()

    try:
        generer_pdf(patient, resultats, filename=tmp_path)
        send_email_with_pdf(
            smtp=smtp,
            email_to=req.email_to,
            subject=req.email_subject or "Votre rapport cardiovasculaire",
            body=req.email_body or "",
            pdf_path=tmp_path,
            resultats=resultats,
        )
    except Exception as e:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        logger.exception("email_send_failed")
        raise HTTPException(500, f"Erreur envoi email : {e}")

    try:
        logger.info(
            "email_sent",
            extra={
                "score2_computed": "score2" in resultats,
            },
        )
    except Exception:
        logger.exception("email_log_failed")

    background = BackgroundTask(lambda: os.path.exists(tmp_path) and os.unlink(tmp_path))
    return JSONResponse(
        content={"ok": True, "message": "Email envoyé.", "cleanup_scheduled": True},
        background=background,
    )

