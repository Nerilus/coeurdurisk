#!/usr/bin/env python3
"""
Génère un PDF d'explication de l'algorithme "Comment va votre coeur"
destiné à une cliente, en langage naturel et accessible.
"""

from fpdf import FPDF
from datetime import datetime


class ExplicationPDF(FPDF):

    BLEU = (41, 98, 255)
    BLEU_FONCE = (25, 60, 150)
    ROUGE_COEUR = (220, 50, 65)
    VERT = (46, 139, 87)
    ORANGE = (255, 152, 0)
    GRIS = (100, 100, 100)
    GRIS_CLAIR = (245, 245, 248)
    NOIR = (33, 37, 41)

    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=25)

    def header(self):
        if self.page_no() > 1:
            self.set_font("Helvetica", "I", 8)
            self.set_text_color(180, 180, 180)
            self.cell(0, 6, "Comment va votre coeur ? - Guide d'explication", align="C")
            self.ln(2)
            self.set_draw_color(220, 220, 220)
            self.line(15, self.get_y(), 195, self.get_y())
            self.ln(6)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 7)
        self.set_text_color(180, 180, 180)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")

    # ── Helpers ──

    def titre(self, texte, taille=22):
        self.set_font("Helvetica", "B", taille)
        self.set_text_color(*self.BLEU_FONCE)
        self.cell(0, taille * 0.5, texte, ln=True)
        self.ln(4)

    def sous_titre(self, texte, taille=14):
        self.set_font("Helvetica", "B", taille)
        self.set_text_color(*self.ROUGE_COEUR)
        self.cell(0, 10, texte, ln=True)
        self.ln(2)

    def paragraphe(self, texte, taille=10):
        self.set_font("Helvetica", "", taille)
        self.set_text_color(*self.NOIR)
        self.multi_cell(0, 5.5, texte)
        self.ln(3)

    def encadre(self, texte, couleur_fond=(240, 248, 255), couleur_bord=(41, 98, 255)):
        y = self.get_y()
        self.set_font("Helvetica", "", 9.5)
        lines = self._nb_lines(texte, 170)
        h = max(14, 8 + lines * 5)
        if y + h > 265:
            self.add_page()
            y = self.get_y()
        self.set_fill_color(*couleur_fond)
        self.set_draw_color(*couleur_bord)
        self.rect(15, y, 180, h, "DF")
        self.set_xy(20, y + 4)
        self.set_text_color(*self.NOIR)
        self.multi_cell(170, 5, texte)
        self.set_y(y + h + 4)

    def encadre_important(self, texte):
        self.encadre(texte, couleur_fond=(255, 243, 205), couleur_bord=(255, 180, 0))

    def _nb_lines(self, txt, w):
        # Utilise la police courante — le caller doit set_font avant d'appeler
        words = txt.split()
        line = ""
        n = 1
        for word in words:
            test = line + " " + word if line else word
            if self.get_string_width(test) > w:
                n += 1
                line = word
            else:
                line = test
        return n


def generer_explication():
    pdf = ExplicationPDF()
    pdf.alias_nb_pages()

    # ══════════════════════════════════════════════════════════════════
    # PAGE 1 : COUVERTURE
    # ══════════════════════════════════════════════════════════════════
    pdf.add_page()
    pdf.ln(30)

    # Cercle décoratif
    pdf.set_fill_color(*pdf.ROUGE_COEUR)
    pdf.ellipse(90, 40, 30, 30, "F")
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(255, 255, 255)
    pdf.set_xy(90, 47)
    pdf.cell(30, 14, "?", align="C")

    pdf.set_y(80)
    pdf.set_font("Helvetica", "B", 28)
    pdf.set_text_color(*pdf.NOIR)
    pdf.cell(0, 15, "Comment va votre coeur ?", align="C")
    pdf.ln(18)

    pdf.set_font("Helvetica", "", 14)
    pdf.set_text_color(*pdf.GRIS)
    pdf.cell(0, 8, "Guide d'explication de l'outil d'\xe9valuation", align="C")
    pdf.ln(6)
    pdf.cell(0, 8, "du risque cardiovasculaire", align="C")
    pdf.ln(20)

    pdf.set_draw_color(*pdf.BLEU)
    pdf.line(70, pdf.get_y(), 140, pdf.get_y())
    pdf.ln(15)

    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(*pdf.GRIS)
    pdf.cell(0, 7, "Bas\xe9 sur l'algorithme SCORE2", align="C")
    pdf.ln(5)
    pdf.cell(0, 7, "de la Soci\xe9t\xe9 Europ\xe9enne de Cardiologie (ESC 2021)", align="C")
    pdf.ln(5)
    pdf.cell(0, 7, "et les donn\xe9es des grandes \xe9tudes", align="C")
    pdf.ln(5)
    pdf.cell(0, 7, "\xe9pid\xe9miologiques internationales", align="C")
    pdf.ln(20)

    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(180, 180, 180)
    pdf.cell(0, 7, f"Document g\xe9n\xe9r\xe9 le {datetime.now().strftime('%d/%m/%Y')}", align="C")

    # ══════════════════════════════════════════════════════════════════
    # PAGE 2 : C'EST QUOI CE TEST ?
    # ══════════════════════════════════════════════════════════════════
    pdf.add_page()

    pdf.titre("\xc0 quoi sert ce test ?")

    pdf.paragraphe(
        "Ce test a \xe9t\xe9 cr\xe9\xe9 pour vous permettre de comprendre o\xf9 vous en "
        "\xeates avec votre sant\xe9 cardiaque. C'est un outil simple et p\xe9dagogique : "
        "vous r\xe9pondez \xe0 des questions sur votre vie quotidienne et, si vous les "
        "connaissez, vos chiffres de sant\xe9 (tension, cholest\xe9rol). En retour, "
        "l'outil vous donne une \xe9valuation de votre risque cardiovasculaire."
    )

    pdf.paragraphe(
        "L'id\xe9e, ce n'est pas de vous faire peur. C'est de vous montrer "
        "concr\xe8tement quels sont vos points forts, quels sont les points "
        "\xe0 am\xe9liorer, et surtout : ce qui changerait si vous modifiiez "
        "certaines habitudes. Par exemple, si vous arr\xeatez de fumer, "
        "vous pouvez voir directement comment votre score s'am\xe9liore."
    )

    pdf.encadre_important(
        "Important : ce test ne remplace pas une consultation m\xe9dicale. "
        "C'est un outil de sensibilisation. Si votre r\xe9sultat vous interpelle, "
        "parlez-en \xe0 votre m\xe9decin qui pourra faire un bilan complet."
    )
    pdf.ln(3)

    pdf.titre("Comment \xe7a marche, concr\xe8tement ?")

    pdf.paragraphe(
        "Le test vous pose 22 questions, r\xe9parties en 4 parties :"
    )

    # Les 4 parties visuelles
    parties = [
        ("Votre profil", "\xc2ge, sexe, poids, taille. Ce sont les bases pour "
         "calculer votre indice de masse corporelle (IMC) et adapter "
         "l'\xe9valuation \xe0 votre situation."),
        ("Votre h\xe9r\xe9dit\xe9", "Est-ce qu'un de vos parents proches a eu un probl\xe8me "
         "cardiaque avant 55 ans (p\xe8re, fr\xe8re) ou 65 ans (m\xe8re, soeur) ? "
         "C'est une information importante car il y a une part g\xe9n\xe9tique "
         "dans le risque cardiovasculaire."),
        ("Votre mode de vie", "C'est la partie la plus riche : on vous interroge sur "
         "le tabac, l'activit\xe9 physique, ce que vous mangez, le sel, le stress, "
         "l'alcool, le temps pass\xe9 assis... Tous ces \xe9l\xe9ments influencent "
         "directement la sant\xe9 de votre coeur."),
        ("Vos donn\xe9es m\xe9dicales", "Si vous les connaissez : votre tension, votre "
         "cholest\xe9rol, votre glyc\xe9mie. Si vous ne les connaissez pas, "
         "ce n'est pas grave : le test fonctionne quand m\xeame, mais en mode simplifi\xe9."),
    ]

    for i, (titre_p, desc) in enumerate(parties, 1):
        y = pdf.get_y()
        if y > 235:
            pdf.add_page()
            y = pdf.get_y()

        # Calculer la hauteur n\xe9cessaire avec la bonne police
        pdf.set_font("Helvetica", "", 9)
        lines = pdf._nb_lines(desc, 145)
        # 10 = padding haut (titre 6 + gap 4), lines * 4.5, +6 = padding bas
        h = max(22, 10 + lines * 4.5 + 6)

        pdf.set_fill_color(*pdf.GRIS_CLAIR)
        pdf.set_draw_color(200, 200, 200)
        pdf.rect(15, y, 180, h, "DF")

        # Num\xe9ro
        pdf.set_fill_color(*pdf.BLEU)
        pdf.rect(15, y, 22, h, "F")
        pdf.set_font("Helvetica", "B", 14)
        pdf.set_text_color(255, 255, 255)
        pdf.set_xy(15, y + h / 2 - 5)
        pdf.cell(22, 10, str(i), align="C")

        # Titre + desc
        pdf.set_xy(42, y + 4)
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(*pdf.NOIR)
        pdf.cell(100, 5, titre_p)
        pdf.set_xy(42, y + 11)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(*pdf.GRIS)
        pdf.multi_cell(145, 4.5, desc)
        pdf.set_y(y + h + 5)

    # ══════════════════════════════════════════════════════════════════
    # PAGE 3 : LES DEUX MODES
    # ══════════════════════════════════════════════════════════════════
    pdf.add_page()

    pdf.titre("Les deux modes de calcul")

    pdf.paragraphe(
        "L'outil utilise deux approches diff\xe9rentes et compl\xe9mentaires pour "
        "\xe9valuer votre risque. Selon les informations que vous pouvez fournir, "
        "vous obtenez un r\xe9sultat plus ou moins pr\xe9cis."
    )

    pdf.ln(2)
    pdf.sous_titre("Mode 1 : L'\xe9valuation par le mode de vie")

    pdf.paragraphe(
        "Ce mode fonctionne pour tout le monde, m\xeame si vous ne connaissez "
        "pas vos chiffres de sant\xe9. Il regarde l'ensemble de vos habitudes "
        "et de votre situation personnelle."
    )

    pdf.paragraphe(
        "Chaque facteur de risque re\xe7oit un nombre de points proportionnel "
        "\xe0 sa dangerosit\xe9 mesur\xe9e scientifiquement. Les poids sont calcul\xe9s \xe0 "
        "partir du logarithme du risque relatif (ln(RR)) publi\xe9 dans les grandes "
        "\xe9tudes \xe9pid\xe9miologiques mondiales : INTERHEART (Lancet 2004, 52 pays), "
        "Prospective Studies Collaboration (Lancet 2002, 1 million d'adultes), "
        "et d'autres m\xe9ta-analyses de r\xe9f\xe9rence."
    )

    pdf.paragraphe(
        "Voici comment les points sont r\xe9partis entre les diff\xe9rents facteurs :"
    )

    # Tableau visuel des pondérations — basé sur ln(RR) des études publiées
    facteurs = [
        ("\xc2ge", 14, "HR ~2.5/d\xe9cennie (PSC, Lancet 2002)"),
        ("Hypertension", 10, "HR 2x-4x (PSC, Lancet 2002)"),
        ("Tabac actif", 9, "OR 2.87 (INTERHEART, Lancet 2004)"),
        ("Cholest\xe9rol", 9, "OR 3.25 top quintile (INTERHEART)"),
        ("Stress chronique", 7, "OR 2.17 (INTERHEART, Lancet 2004)"),
        ("Diab\xe8te", 7, "HR 2.00 (ERFC, Lancet 2010)"),
        ("Poids (IMC)", 6, "HR 1.69 (97 cohortes, Lancet 2014)"),
        ("Ancien fumeur <5 ans", 5, "Risque r\xe9siduel ~50% (Kenfield 2008)"),
        ("Sexe", 5, "HR ~2.0 H vs F (EPIC-Norfolk 2024)"),
        ("S\xe9dentarit\xe9", 5, "HR 1.90 (AHA, Circulation 2016)"),
        ("H\xe9r\xe9dit\xe9 familiale", 5, "HR 1.74 (EPIC-Norfolk 2011)"),
        ("Apn\xe9e du sommeil", 5, "HR 1.82 (Dong, Int J Cardiol 2013)"),
        ("Col\xe8res / hostilit\xe9", 3, "HR 1.19-1.50 (Chida, JACC 2009)"),
        ("Troubles du sommeil", 3, "HR 1.45 (He, Eur J Prev Card 2017)"),
        ("Alimentation", 3, "OR 1.43 (INTERHEART, Lancet 2004)"),
        ("Alcool excessif", 3, "RR 1.35 (Zhao, JAMA Net Open 2023)"),
        ("Charge familiale", 2, "HR 1.29 (Valtorta, Heart 2016)"),
        ("Tabac passif", 2, "RR 1.25 (He, NEJM 1999)"),
        ("Activit\xe9 physique*", 2, "HR 1.24 (m\xe9ta-analyse 2012)"),
        ("Boissons \xe9nergisantes", 1, "Arythmie (Fletcher, JACC 2017)"),
        ("Sel", 1, "RR 1.13 (Graudal, Nutrients 2020)"),
    ]

    pdf.set_font("Helvetica", "B", 8)
    pdf.set_fill_color(*pdf.BLEU)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(55, 6, "  FACTEUR", fill=True)
    pdf.cell(20, 6, "POIDS", fill=True, align="C")
    pdf.cell(60, 6, "  SOURCE", fill=True)
    pdf.cell(55, 6, "  JAUGE", fill=True, ln=True)

    max_pts = 14
    for i, (nom, pts, raison) in enumerate(facteurs):
        bg = pdf.GRIS_CLAIR if i % 2 == 0 else (255, 255, 255)
        pdf.set_fill_color(*bg)
        pdf.set_text_color(*pdf.NOIR)
        pdf.set_font("Helvetica", "", 8)
        pdf.cell(55, 5.5, f"  {nom}", fill=True)
        pdf.set_font("Helvetica", "B", 8)
        pdf.cell(20, 5.5, f"{pts} pts", fill=True, align="C")
        pdf.set_font("Helvetica", "I", 7.5)
        pdf.set_text_color(*pdf.GRIS)
        pdf.cell(60, 5.5, f"  {raison}", fill=True)

        # Mini jauge
        gy = pdf.get_y() + 1.5
        gx = pdf.get_x() + 3
        gw = 48
        gh = 2.5
        pdf.set_fill_color(230, 230, 230)
        pdf.rect(gx, gy, gw, gh, "F")
        ratio = pts / max_pts
        if ratio > 0.7:
            c = pdf.ROUGE_COEUR
        elif ratio > 0.4:
            c = pdf.ORANGE
        else:
            c = pdf.VERT
        pdf.set_fill_color(*c)
        pdf.rect(gx, gy, gw * ratio, gh, "F")
        pdf.cell(55, 5.5, "", ln=True)

    pdf.ln(3)

    pdf.set_font("Helvetica", "I", 7.5)
    pdf.set_text_color(*pdf.GRIS)
    pdf.multi_cell(0, 4,
        "* Activit\xe9 physique : le HR 1.24 mesure l'effet ind\xe9pendant apr\xe8s ajustement pour "
        "les autres facteurs (poids, tension, cholest\xe9rol). L'effet total de l'exercice est "
        "plus important car il am\xe9liore aussi ces autres facteurs d\xe9j\xe0 compt\xe9s s\xe9par\xe9ment.")
    pdf.ln(3)

    pdf.paragraphe(
        "On additionne tous vos points, on divise par le maximum possible, "
        "et on obtient un pourcentage. Plus ce pourcentage est bas, mieux c'est."
    )

    # Échelle des résultats
    niveaux = [
        ("Risque faible", "0 \xe0 15%", pdf.VERT, "Bravo, continuez comme \xe7a !"),
        ("Faible \xe0 mod\xe9r\xe9", "15 \xe0 30%", (154, 205, 50), "Quelques points \xe0 am\xe9liorer."),
        ("Risque mod\xe9r\xe9", "30 \xe0 50%", pdf.ORANGE, "Il est temps d'agir sur certaines habitudes."),
        ("Mod\xe9r\xe9 \xe0 \xe9lev\xe9", "50 \xe0 65%", (255, 120, 0), "Plusieurs facteurs \xe0 corriger."),
        ("Risque \xe9lev\xe9", "65 \xe0 80%", pdf.ROUGE_COEUR, "Consultez votre m\xe9decin rapidement."),
        ("Tr\xe8s \xe9lev\xe9", "80% et +", (139, 0, 0), "Prise en charge m\xe9dicale urgente."),
    ]

    for nom, plage, couleur, msg in niveaux:
        y = pdf.get_y()
        if y > 265:
            pdf.add_page()
        pdf.set_fill_color(*couleur)
        pdf.rect(15, y, 4, 5, "F")
        pdf.set_xy(22, y)
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(*pdf.NOIR)
        pdf.cell(35, 5, nom)
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(*pdf.GRIS)
        pdf.cell(25, 5, f"({plage})")
        pdf.set_font("Helvetica", "I", 8)
        pdf.cell(100, 5, msg, ln=True)

    # ══════════════════════════════════════════════════════════════════
    # PAGE 4 : SCORE2
    # ══════════════════════════════════════════════════════════════════
    pdf.add_page()

    pdf.sous_titre("Mode 2 : Le calcul m\xe9dical SCORE2 (si vous avez vos chiffres)")

    pdf.paragraphe(
        "Si vous connaissez votre tension art\xe9rielle et vos taux de cholest\xe9rol "
        "(total et HDL), l'outil active un deuxi\xe8me moteur de calcul beaucoup "
        "plus pr\xe9cis. Il s'appelle SCORE2 et c'est l'algorithme officiel "
        "de la Soci\xe9t\xe9 Europ\xe9enne de Cardiologie, publi\xe9 en 2021."
    )

    pdf.paragraphe(
        "SCORE2 a \xe9t\xe9 construit \xe0 partir des donn\xe9es de 13 millions de "
        "personnes suivies en Europe. C'est l'un des outils les plus fiables "
        "au monde pour estimer le risque cardiovasculaire."
    )

    pdf.encadre(
        "Ce qu'il calcule : votre probabilit\xe9, en pourcentage, d'avoir un "
        "infarctus, un AVC, ou un d\xe9c\xe8s d'origine cardiaque dans les "
        "10 prochaines ann\xe9es."
    )
    pdf.ln(3)

    pdf.paragraphe(
        "Pour faire ce calcul, il utilise seulement 5 informations :"
    )

    infos_score2 = [
        ("Votre \xe2ge", "Le risque augmente naturellement avec le temps. L'algorithme "
         "adapte ses seuils selon que vous avez moins de 50 ans, entre 50 et 69 ans, "
         "ou 70 ans et plus."),
        ("Votre sexe", "Les hommes ont statistiquement un risque plus \xe9lev\xe9 avant 60 ans. "
         "Apr\xe8s la m\xe9nopause, le risque des femmes se rapproche de celui des hommes."),
        ("Fumez-vous ?", "Le tabac est le facteur le plus impactant dans le calcul. "
         "Un fumeur a un risque 2 \xe0 3 fois plus \xe9lev\xe9 qu'un non-fumeur."),
        ("Votre tension art\xe9rielle", "C'est le chiffre du haut (systolique) qui est utilis\xe9. "
         "La normale est autour de 120 mmHg. Au-dessus de 140, on parle d'hypertension."),
        ("Votre cholest\xe9rol", "L'algorithme utilise le cholest\xe9rol total et le HDL "
         "(le \xab bon \xbb cholest\xe9rol). Ce qui compte, c'est l'\xe9quilibre entre les deux."),
    ]

    for i, (titre_i, desc) in enumerate(infos_score2, 1):
        y = pdf.get_y()
        if y > 250:
            pdf.add_page()

        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(*pdf.BLEU)
        pdf.cell(8, 6, f"{i}.")
        pdf.set_text_color(*pdf.NOIR)
        pdf.cell(0, 6, titre_i, ln=True)
        pdf.set_x(23)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(*pdf.GRIS)
        pdf.multi_cell(167, 4.5, desc)
        pdf.ln(2)

    pdf.ln(3)
    pdf.paragraphe(
        "L'algorithme combine ces 5 informations dans une formule math\xe9matique "
        "qui a \xe9t\xe9 calibr\xe9e sp\xe9cialement pour la France (class\xe9e comme pays "
        "\xe0 bas risque cardiovasculaire en Europe). Le r\xe9sultat est un pourcentage."
    )

    # Tableau des seuils
    pdf.sous_titre("Comment lire votre r\xe9sultat SCORE2 ?")

    pdf.paragraphe(
        "Les seuils de risque d\xe9pendent de votre \xe2ge. C'est normal : "
        "\xe0 70 ans, un certain niveau de risque est attendu. Ce qui compte, "
        "c'est si votre risque est anormalement \xe9lev\xe9 pour votre tranche d'\xe2ge."
    )

    # Tableau
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(*pdf.BLEU)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(50, 7, "  VOTRE \xc2GE", fill=True)
    pdf.cell(45, 7, "  \xc7A VA", fill=True, align="C")
    pdf.cell(45, 7, "  ATTENTION", fill=True, align="C")
    pdf.cell(45, 7, "  DANGER", fill=True, align="C", ln=True)

    seuils = [
        ("Moins de 50 ans", "moins de 2.5%", "entre 2.5 et 7.5%", "plus de 7.5%"),
        ("50 \xe0 69 ans", "moins de 5%", "entre 5 et 10%", "plus de 10%"),
        ("70 ans et plus", "moins de 7.5%", "entre 7.5 et 15%", "plus de 15%"),
    ]

    for i, (age, ok, attention, danger) in enumerate(seuils):
        bg = pdf.GRIS_CLAIR if i % 2 == 0 else (255, 255, 255)
        pdf.set_fill_color(*bg)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*pdf.NOIR)
        pdf.cell(50, 7, f"  {age}", fill=True)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(*pdf.VERT)
        pdf.cell(45, 7, f"  {ok}", fill=True, align="C")
        pdf.set_text_color(*pdf.ORANGE)
        pdf.cell(45, 7, f"  {attention}", fill=True, align="C")
        pdf.set_text_color(*pdf.ROUGE_COEUR)
        pdf.cell(45, 7, f"  {danger}", fill=True, align="C", ln=True)

    # ══════════════════════════════════════════════════════════════════
    # PAGE 5 : POURQUOI C'EST UTILE + EXEMPLES
    # ══════════════════════════════════════════════════════════════════
    pdf.add_page()

    pdf.titre("Pourquoi c'est utile ?")

    pdf.paragraphe(
        "Le plus grand int\xe9r\xeat de cet outil, c'est qu'il n'est pas fig\xe9. "
        "Vous pouvez modifier vos r\xe9ponses et voir imm\xe9diatement ce qui "
        "changerait dans votre r\xe9sultat. C'est un vrai outil de motivation."
    )

    pdf.sous_titre("Quelques exemples concrets")

    exemples = [
        ("Arr\xeater de fumer",
         "C'est l'action la plus puissante sur les facteurs modifiables. "
         "Le tabac multiplie le risque d'infarctus par 2.87 (\xe9tude INTERHEART, "
         "Lancet 2004, 27 000 personnes dans 52 pays). "
         "Apr\xe8s 1 an d'arr\xeat, le risque diminue de 50 %. "
         "Apr\xe8s 5 ans, il rejoint celui d'un non-fumeur.",
         9),
        ("G\xe9rer son stress",
         "Surprise : le stress chronique est l'un des facteurs les plus sous-estim\xe9s. "
         "Il multiplie le risque d'infarctus par 2.17 (INTERHEART, Rosengren et al., "
         "Lancet 2004). La m\xe9ditation, l'activit\xe9 physique, ou un suivi psychologique "
         "peuvent faire une vraie diff\xe9rence.",
         7),
        ("Manger mieux",
         "Augmenter les fruits et l\xe9gumes (viser 5 par jour), r\xe9duire le sel, "
         "limiter la charcuterie et les plats industriels. Le manque de fruits "
         "et l\xe9gumes augmente le risque de 43 % (INTERHEART). La viande transform\xe9e "
         "ajoute 42 % par 50 g/jour (Micha et al., Circulation 2010).",
         10),
        ("Bouger 30 minutes par jour",
         "L'effet direct ind\xe9pendant de l'activit\xe9 physique est de -24 % sur "
         "le risque coronarien (HR 1.24, m\xe9ta-analyse 2012). \xc7a semble modeste, "
         "mais l'exercice agit aussi en am\xe9liorant votre poids, votre tension "
         "et votre cholest\xe9rol. L'effet total est donc beaucoup plus important "
         "que les 2 points directs dans le score.",
         2),
    ]

    for titre_ex, desc, impact in exemples:
        y = pdf.get_y()
        if y > 235:
            pdf.add_page()
            y = pdf.get_y()

        pdf.set_font("Helvetica", "", 9)
        lines = pdf._nb_lines(desc, 155)
        h = max(24, 12 + lines * 4.5 + 4)

        pdf.set_fill_color(245, 250, 245)
        pdf.set_draw_color(*pdf.VERT)
        pdf.rect(15, y, 180, h, "DF")

        pdf.set_xy(20, y + 3)
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(*pdf.VERT)
        pdf.cell(120, 6, titre_ex)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*pdf.BLEU)
        pdf.cell(40, 6, f"Impact : -{impact} pts", align="R")
        pdf.set_xy(20, y + 11)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(*pdf.NOIR)
        pdf.multi_cell(160, 4.5, desc)
        pdf.set_y(y + h + 5)

    # ══════════════════════════════════════════════════════════════════
    # PAGE 6 : CE QUE VEUT DIRE VOTRE RÉSULTAT
    # ══════════════════════════════════════════════════════════════════
    pdf.add_page()

    pdf.titre("Comment lire votre rapport ?")

    pdf.paragraphe(
        "Votre rapport personnalis\xe9 contient plusieurs sections. Voici "
        "comment les comprendre :"
    )

    sections = [
        ("Le profil patient",
         "C'est un r\xe9sum\xe9 de vos donn\xe9es : \xe2ge, sexe, poids, taille, IMC. "
         "L'IMC (Indice de Masse Corporelle) est calcul\xe9 automatiquement. "
         "C'est votre poids divis\xe9 par votre taille au carr\xe9. "
         "Entre 18.5 et 25, c'est normal. Entre 25 et 30, c'est du surpoids. "
         "Au-dessus de 30, c'est l'ob\xe9sit\xe9."),
        ("Le r\xe9sultat SCORE2",
         "Si vous avez fourni vos chiffres de sant\xe9 (tension, cholest\xe9rol), "
         "vous obtenez un pourcentage pr\xe9cis. Par exemple, \xab 5.3 % \xbb signifie "
         "que vous avez 5.3 chances sur 100 d'avoir un probl\xe8me cardiaque "
         "majeur dans les 10 prochaines ann\xe9es. C'est un chiffre calcul\xe9 "
         "par une formule scientifique valid\xe9e internationalement."),
        ("L'\xe9valuation qualitative",
         "C'est le tableau avec tous vos facteurs de risque. Pour chaque "
         "facteur, vous voyez le nombre de points que vous avez et une jauge "
         "de couleur. Vert = tout va bien. Jaune = \xe0 surveiller. Rouge = \xe0 "
         "corriger en priorit\xe9. C'est le tableau le plus utile pour savoir "
         "concr\xe8tement o\xf9 agir."),
        ("Les recommandations",
         "Ce sont des conseils personnalis\xe9s, g\xe9n\xe9r\xe9s en fonction de VOS "
         "r\xe9ponses. Les \xe9l\xe9ments marqu\xe9s avec \xab !! \xbb sont les plus urgents. "
         "Les autres sont class\xe9s par ordre d'impact. Vous n'\xeates pas oblig\xe9(e) "
         "de tout faire d'un coup : commencer par un seul changement est d\xe9j\xe0 "
         "un grand pas."),
        ("La m\xe9thodologie",
         "C'est la partie technique pour ceux qui veulent comprendre les d\xe9tails "
         "du calcul, les r\xe9f\xe9rences scientifiques, et les seuils officiels. "
         "Vous pouvez la montrer \xe0 votre m\xe9decin si vous le souhaitez."),
    ]

    for titre_s, desc in sections:
        y = pdf.get_y()
        if y > 240:
            pdf.add_page()

        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(*pdf.BLEU)
        pdf.cell(0, 7, titre_s, ln=True)
        pdf.set_font("Helvetica", "", 9.5)
        pdf.set_text_color(*pdf.NOIR)
        pdf.multi_cell(0, 5, desc)
        pdf.ln(5)

    # ══════════════════════════════════════════════════════════════════
    # PAGE 7 : CE QU'IL FAUT RETENIR
    # ══════════════════════════════════════════════════════════════════
    pdf.add_page()

    pdf.titre("Ce qu'il faut retenir")

    messages_cles = [
        ("Ce n'est pas un diagnostic",
         "Cet outil est p\xe9dagogique. Il est con\xe7u pour vous sensibiliser "
         "et vous encourager \xe0 prendre soin de votre coeur. Seul un m\xe9decin "
         "peut poser un diagnostic m\xe9dical apr\xe8s un examen complet."),
        ("Votre score n'est pas une fatalit\xe9",
         "La majorit\xe9 des facteurs de risque sont modifiables. Votre "
         "alimentation, votre activit\xe9 physique, le tabac, le stress : "
         "tout cela, vous pouvez le changer. Et chaque changement compte."),
        ("Les petits gestes comptent \xe9norm\xe9ment",
         "Vous n'avez pas besoin de tout r\xe9volutionner d'un coup. "
         "Marcher 30 minutes par jour, manger un fruit de plus, "
         "r\xe9duire le sel : ces petits changements, cumul\xe9s, "
         "peuvent r\xe9duire votre risque de mani\xe8re significative."),
        ("Parlez-en \xe0 votre m\xe9decin",
         "Si votre r\xe9sultat est mod\xe9r\xe9 ou \xe9lev\xe9, prenez rendez-vous "
         "pour en discuter. Votre m\xe9decin pourra prescrire un bilan sanguin "
         "(cholest\xe9rol, glyc\xe9mie) et mesurer votre tension pour affiner "
         "l'\xe9valuation."),
        ("Refaites le test r\xe9guli\xe8rement",
         "Vos habitudes \xe9voluent, votre sant\xe9 aussi. Refaire le test "
         "tous les 6 mois ou chaque ann\xe9e vous permet de suivre votre "
         "progression et de rester motiv\xe9(e)."),
    ]

    for i, (titre_m, desc) in enumerate(messages_cles, 1):
        y = pdf.get_y()
        if y > 235:
            pdf.add_page()
            y = pdf.get_y()

        pdf.set_font("Helvetica", "", 9)
        lines = pdf._nb_lines(desc, 150)
        h = max(22, 10 + lines * 4.5 + 6)

        pdf.set_fill_color(240, 248, 255)
        pdf.set_draw_color(*pdf.BLEU)
        pdf.rect(15, y, 180, h, "DF")

        # Numéro cercle
        pdf.set_fill_color(*pdf.BLEU)
        cx = 24
        cy = y + h / 2
        pdf.ellipse(cx - 5, cy - 5, 10, 10, "F")
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(255, 255, 255)
        pdf.set_xy(cx - 5, cy - 4)
        pdf.cell(10, 8, str(i), align="C")

        pdf.set_xy(37, y + 3)
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(*pdf.NOIR)
        pdf.cell(0, 5, titre_m, ln=True)
        pdf.set_x(37)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(*pdf.GRIS)
        pdf.multi_cell(153, 4.5, desc)
        pdf.set_y(y + h + 5)

    # Encadré final
    pdf.ln(5)
    y = pdf.get_y()
    if y > 240:
        pdf.add_page()
        y = pdf.get_y()

    pdf.set_fill_color(255, 240, 240)
    pdf.set_draw_color(*pdf.ROUGE_COEUR)
    pdf.rect(15, y, 180, 25, "DF")
    pdf.set_xy(20, y + 4)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(*pdf.ROUGE_COEUR)
    pdf.cell(170, 7, "Votre coeur vous accompagne toute votre vie.", align="C")
    pdf.set_xy(20, y + 13)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(*pdf.NOIR)
    pdf.cell(170, 7, "Prenez-en soin, il vous le rendra.", align="C")

    # ── Sauvegarde ──
    output_path = "guide_explication_coeur.pdf"
    pdf.output(output_path)
    return output_path


if __name__ == "__main__":
    path = generer_explication()
    print(f"PDF g\xe9n\xe9r\xe9 : {path}")
