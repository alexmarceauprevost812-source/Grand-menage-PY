#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GRAND MÉNAGE (grand-menage.py, v0.2) : UN seul outil qui lance tous les autres, un par un,
puis te donne UN résultat final.

Les outils, dans l'ordre :
  1. fuites    : ton courriel dans les fuites de données connues (XposedOrNot)
  2. gravatar  : ton courriel a-t-il un avatar public (Gravatar)
  3. holehe    : sites où ce courriel a un compte
  4. sherlock  : profils portant ton pseudo
  5. maigret   : profils portant ton pseudo (autre base de sites)
  6. archives  : copies des profils trouvés dans la Wayback Machine

Ensuite l'outil fusionne tout (un site trouvé par plusieurs outils = une seule ligne),
note la confiance de chaque résultat, et écrit dans ~/grand-menage/<date>/ :
  RESULTAT_FINAL.md   le rapport complet + le plan d'action à cocher
  resultat.json       les mêmes données, pour d'autres programmes
  lettres/            une lettre de demande de suppression par site

Ce que l'outil NE fait PAS : supprimer à ta place. Chaque site exige que tu te
connectes ou que tu confirmes ton identité. L'outil te donne la liste, les liens
et les lettres.

À utiliser seulement avec TON adresse courriel.

Fonctionne sur Kali Linux (et les autres Linux) et sur Windows 10/11.

Installation des outils (une seule fois) : lance le menu et choisis l'option 6.
Elle propose d'installer ce qui manque, avec les bonnes commandes pour ton système.
À la main, si tu préfères :
    Kali     : sudo apt install pipx sherlock maigret && pipx install holehe && pipx ensurepath
    Windows  : py -m pip install --user holehe sherlock-project maigret

Utilisation (sous Windows : remplace python3 par py -3, ou tape grand-menage dans le terminal) :
    python3 grand-menage.py                          ouvre le menu
    python3 grand-menage.py ton.adresse@hotmail.com
    python3 grand-menage.py ton.adresse@hotmail.com --pseudo tonpseudo --nom "Ton Nom"
    python3 grand-menage.py ton.adresse@hotmail.com --sauter maigret,archives
"""

import argparse
import datetime
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import sysconfig
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from dataclasses import dataclass, field
from types import SimpleNamespace

VERSION = "0.2"
UA = {"User-Agent": "grand-menage/" + VERSION}

INSTALLER = "option 6 du menu pour l'installer"
COULEURS_OK = True   # devient False si le terminal Windows ne sait pas afficher les couleurs


def est_kali():
    try:
        with open("/etc/os-release", encoding="utf-8") as f:
            return "kali" in f.read().lower()
    except OSError:
        return False


def nom_systeme():
    return "Windows" if os.name == "nt" else ("Kali Linux" if est_kali() else "Linux")


def completer_path():
    """pip et pipx rangent leurs commandes dans des dossiers qui ne sont pas toujours dans PATH.
    On les ajoute pour que les outils installés soient retrouvés tout de suite."""
    candidats = [os.path.expanduser("~/.local/bin")]
    try:
        candidats.append(sysconfig.get_path("scripts", "nt_user" if os.name == "nt" else "posix_user"))
    except (KeyError, ValueError):
        pass
    actuel = os.environ.get("PATH", "")
    for dossier in candidats:
        if dossier and os.path.isdir(dossier) and dossier not in actuel.split(os.pathsep):
            actuel += os.pathsep + dossier
    os.environ["PATH"] = actuel


def activer_couleurs_windows():
    """Windows 10/11 : active l'affichage des couleurs (codes ANSI) dans la console."""
    try:
        import ctypes
        noyau = ctypes.windll.kernel32
        sortie = noyau.GetStdHandle(-11)
        mode = ctypes.c_ulong()
        if not noyau.GetConsoleMode(sortie, ctypes.byref(mode)):
            return False
        return bool(noyau.SetConsoleMode(sortie, mode.value | 0x0004))
    except Exception:
        return False


def preparer_terminal():
    """À lancer au démarrage : rend l'outil identique sous Windows et sous Linux."""
    global COULEURS_OK
    # 1. Les accents et le logo ne doivent jamais faire planter l'affichage (surtout sous Windows)
    for flux in (sys.stdout, sys.stderr):
        try:
            options = {"errors": "replace"}
            if not flux.isatty():
                options["encoding"] = "utf-8"
            flux.reconfigure(**options)
        except (AttributeError, ValueError):
            pass
    # 2. Windows : activer les couleurs de la console
    if os.name == "nt" and sys.stdout.isatty():
        COULEURS_OK = activer_couleurs_windows()
    # 3. Retrouver les outils installés par pip/pipx même si PATH n'est pas à jour
    completer_path()


SOURCES_COURRIEL = {"holehe", "gravatar"}   # partent du courriel : preuve forte
SOURCES_PSEUDO = {"sherlock", "maigret"}    # partent du pseudo : à vérifier
PAS_DES_COMPTES = {"fuites", "archives"}    # résultats d'un autre genre

LIENS_NETTOYAGE = [
    ("Voir où ton courriel a fuité (Have I Been Pwned)", "https://haveibeenpwned.com"),
    ("Liens directs pour supprimer un compte (JustDeleteMe)", "https://justdeleteme.xyz"),
    ("Google : demander le retrait de tes infos perso des résultats", "https://g.co/resultsaboutyou"),
    ("Commission d'accès à l'information du Québec (si un site refuse)", "https://www.cai.gouv.qc.ca"),
]


# ====================================================================== outils de base
@dataclass
class Resultat:
    """Ce que rapporte un outil après son passage."""
    cle: str
    nom: str
    statut: str = "non lancé"        # ok / absent / erreur / interrompu
    trouves: list = field(default_factory=list)   # [{"site": ..., "url": ...}]
    note: str = ""
    duree: float = 0.0


def sans_couleurs(texte):
    return re.sub(r"\x1b\[[0-9;]*m", "", texte)


def lancer(commande, timeout=900, repli=None):
    """Lance une commande dans un dossier temporaire (pour ne pas semer de fichiers).
    Retourne (code de retour, sortie texte), ou None si le délai est dépassé.
    Si une option n'existe pas dans ta version de l'outil, on réessaie avec `repli`."""
    def une_fois(cmd):
        with tempfile.TemporaryDirectory() as dossier:
            env = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}
            r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                               errors="replace", timeout=timeout, cwd=dossier, env=env)
            return r.returncode, sans_couleurs((r.stdout or "") + (r.stderr or ""))
    try:
        code, sortie = une_fois(commande)
        if repli and "unrecognized arguments" in sortie:
            code, sortie = une_fois(repli)
        return code, sortie
    except subprocess.TimeoutExpired:
        return None


def domaine_de(texte):
    """'https://www.reddit.com/user/x' -> 'reddit.com' ; 'twitter.com' -> 'twitter.com'"""
    if "://" in texte:
        texte = urllib.parse.urlparse(texte).netloc
    texte = texte.lower().split(":")[0]
    return texte[4:] if texte.startswith("www.") else texte


SUFFIXES_DEUX_NIVEAUX = {"co", "com", "net", "org", "gov", "gouv", "edu", "ac", "or", "ne", "go",
                         "nom", "ltd", "plc", "sch", "mil", "qc", "on", "bc", "ab"}


def racine(domaine):
    """Domaine à qui écrire : 'mail.google.com' -> 'google.com' ; 'news.bbc.co.uk' -> 'bbc.co.uk'.
    Sous un code pays (.uk, .au...), sans suffixe connu, on garde le domaine trouvé en entier :
    mieux vaut une adresse un peu longue qu'une adresse qui vise un autre organisme."""
    morceaux = domaine.split(".")
    if len(morceaux) <= 2 or len(morceaux[-1]) > 2:   # .com, .org, .net... : les deux derniers suffisent
        return ".".join(morceaux[-2:])
    if morceaux[-2] in SUFFIXES_DEUX_NIVEAUX:
        return ".".join(morceaux[-3:])
    return domaine


# ====================================================================== les outils
def outil_fuites(ctx, res):
    url = "https://api.xposedornot.com/v1/check-email/" + urllib.parse.quote(ctx.email, safe="")
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20) as rep:
            data = json.load(rep)
    except urllib.error.HTTPError as e:
        if e.code == 404:   # le service répond 404 quand rien n'est trouvé
            res.statut, res.note = "ok", "aucune fuite connue"
            return
        res.statut, res.note = "erreur", f"erreur HTTP {e.code}"
        return
    except Exception as e:
        res.statut, res.note = "erreur", f"service injoignable ({e})"
        return
    noms = []
    for fuite in data.get("breaches", []):
        noms.extend(str(x) for x in fuite) if isinstance(fuite, list) else noms.append(str(fuite))
    res.trouves = [{"site": n, "url": None} for n in noms]
    res.statut = "ok"


def outil_gravatar(ctx, res):
    empreinte = hashlib.sha256(ctx.email.strip().lower().encode()).hexdigest()
    url = f"https://gravatar.com/avatar/{empreinte}"
    try:
        with urllib.request.urlopen(urllib.request.Request(url + "?d=404", headers=UA), timeout=15):
            res.trouves = [{"site": "gravatar.com", "url": url}]
            res.statut = "ok"
    except urllib.error.HTTPError as e:
        if e.code == 404:
            res.statut, res.note = "ok", "aucun avatar public"
        else:
            res.statut, res.note = "erreur", f"erreur HTTP {e.code}"
    except Exception as e:
        res.statut, res.note = "erreur", f"service injoignable ({e})"


def _externe(res, programme, indice, commande, repli, analyseur, timeout=900):
    """Façon commune de lancer un outil externe (Kali ou Windows) et de lire son résultat."""
    chemin = shutil.which(programme)
    if not chemin:
        res.statut, res.note = "absent", f"non installé ({indice})"
        return
    commande = [chemin] + commande[1:]           # chemin complet : marche aussi avec les .exe de Windows
    repli = [chemin] + repli[1:] if repli else None
    print("  (patience, ça peut prendre plusieurs minutes...)")
    retour = lancer(commande, timeout=timeout, repli=repli)
    if retour is None:
        res.statut, res.note = "erreur", "délai dépassé"
        return
    code, sortie = retour
    res.trouves = analyseur(sortie)
    if code != 0 and not res.trouves:   # l'outil a planté : ne pas faire croire que tout est propre
        lignes = [l.strip() for l in sortie.splitlines() if l.strip()]
        res.statut = "erreur"
        res.note = f"échec (code {code})" + (f" : {lignes[-1][:150]}" if lignes else "")
        return
    res.statut = "ok"
    if code != 0:
        res.note = f"terminé avec le code {code} : résultats peut-être incomplets"


def analyser_holehe(sortie):
    trouves = []
    for ligne in sortie.splitlines():
        m = re.match(r"^\[\+\]\s+(\S+)", ligne.strip())
        if m and "." in m.group(1):   # on ignore la légende « [+] Email used »
            trouves.append({"site": m.group(1).lower(), "url": None})
    return trouves


def analyser_profils(sortie):
    return [{"site": s.strip(), "url": u}
            for s, u in re.findall(r"\[\+\]\s+(.+?):\s+(https?://\S+)", sortie)]


def outil_holehe(ctx, res):
    _externe(res, "holehe", INSTALLER,
             ["holehe", "--only-used", "--no-color", ctx.email], None, analyser_holehe, 600)


def outil_sherlock(ctx, res):
    _externe(res, "sherlock", INSTALLER,
             ["sherlock", ctx.pseudo, "--print-found", "--timeout", "10"], None, analyser_profils)


def outil_maigret(ctx, res):
    _externe(res, "maigret", INSTALLER,
             ["maigret", ctx.pseudo, "--no-color", "--timeout", "10", "--retries", "0"],
             ["maigret", ctx.pseudo], analyser_profils)


def outil_archives(ctx, res):
    """Cherche des copies des profils trouvés : elles survivent à la suppression du compte."""
    urls = []
    for r in ctx.resultats:
        if r.cle in SOURCES_PSEUDO:
            urls += [t["url"] for t in r.trouves if t.get("url")]
    urls = sorted(set(urls))[:ctx.max_archives]
    if not urls:
        res.statut, res.note = "ok", "aucun profil à vérifier"
        return
    pannes = 0
    for u in urls:
        api = "https://archive.org/wayback/available?url=" + urllib.parse.quote(u, safe="")
        try:
            with urllib.request.urlopen(urllib.request.Request(api, headers=UA), timeout=20) as rep:
                data = json.load(rep)
            copie = data.get("archived_snapshots", {}).get("closest")
            if copie and copie.get("url"):
                res.trouves.append({"site": u, "url": copie["url"]})
        except Exception:
            pannes += 1
    res.statut = "erreur" if pannes == len(urls) else "ok"
    if pannes:
        res.note = f"{pannes}/{len(urls)} vérification(s) échouée(s)"


OUTILS = [
    ("fuites",   "Fuites de données connues (XposedOrNot)", outil_fuites),
    ("gravatar", "Avatar public lié au courriel (Gravatar)", outil_gravatar),
    ("holehe",   "Comptes liés au courriel (holehe)", outil_holehe),
    ("sherlock", "Profils avec ton pseudo (sherlock)", outil_sherlock),
    ("maigret",  "Profils avec ton pseudo (maigret)", outil_maigret),
    ("archives", "Copies archivées des profils (Wayback Machine)", outil_archives),
]


# ====================================================================== le chef d'orchestre
def executer(outils, ctx):
    """Lance les outils un par un. Ctrl+C = sauter l'outil en cours (ou tout arrêter)."""
    total = len(outils)
    for i, (cle, nom, fonction) in enumerate(outils, 1):
        print(f"\n[{i}/{total}] {nom}")
        res = Resultat(cle, nom)
        debut = time.time()
        arreter = False
        try:
            fonction(ctx, res)
        except KeyboardInterrupt:
            res.statut = "interrompu"
            rep = input("\n  Outil interrompu. Entrée = passer au suivant, q = arrêter et faire le rapport : ")
            arreter = rep.strip().lower() == "q"
        except Exception as e:   # un outil qui plante ne doit pas arrêter les autres
            res.statut, res.note = "erreur", str(e)
        res.duree = time.time() - debut
        ctx.resultats.append(res)
        detail = f"{len(res.trouves)} résultat(s)" if res.statut == "ok" and res.trouves else res.note
        print(f"  -> {res.statut} en {res.duree:.0f} s  {('- ' + detail) if detail else ''}")
        if arreter:
            break


def consolider(resultats):
    """Fusionne tous les outils : un site trouvé par plusieurs outils = une seule ligne."""
    comptes = {}
    for r in resultats:
        if r.cle in PAS_DES_COMPTES:
            continue
        for t in r.trouves:
            dom = domaine_de(t["url"] or t["site"])
            c = comptes.setdefault(dom, {"domaine": dom, "sources": set(), "urls": set()})
            c["sources"].add(r.cle)
            if t.get("url"):
                c["urls"].add(t["url"])
    for c in comptes.values():
        if c["sources"] & SOURCES_COURRIEL:
            c["confiance"] = "forte"        # lié au courriel : c'est presque sûrement à toi
        elif len(c["sources"]) >= 2:
            c["confiance"] = "moyenne"      # trouvé par deux outils de pseudo
        else:
            c["confiance"] = "faible"       # pseudo seulement : peut être quelqu'un d'autre
    ordre = {"forte": 0, "moyenne": 1, "faible": 2}
    return sorted(comptes.values(), key=lambda c: (ordre[c["confiance"]], c["domaine"]))


def trouves_de(resultats, cle):
    for r in resultats:
        if r.cle == cle:
            return r.trouves
    return []


def plan_action(comptes, fuites, archives):
    forts = [c["domaine"] for c in comptes if c["confiance"] == "forte"]
    moyens = [c["domaine"] for c in comptes if c["confiance"] == "moyenne"]
    faibles = [c for c in comptes if c["confiance"] == "faible"]

    def liste(x):
        return ", ".join(x[:15]) + (" ..." if len(x) > 15 else "")

    plan = []
    if fuites:
        plan.append(f"Change le mot de passe de tout compte qui a pu être exposé ({len(fuites)} fuite(s) "
                    "trouvée(s)), ne le réutilise nulle part et active la double authentification.")
    if forts:
        plan.append(f"Supprime ces comptes liés à ton courriel : {liste(forts)}")
    if moyens:
        plan.append(f"Vérifie que ces profils sont bien à toi, puis supprime-les : {liste(moyens)}")
    if faibles:
        plan.append(f"{len(faibles)} profil(s) trouvé(s) seulement par le pseudo : probablement pas à toi, "
                    "ignore-les sauf si tu les reconnais (liste dans le tableau).")
    if forts or moyens:
        plan.append("Pour les sites sans bouton de suppression, envoie la lettre du dossier `lettres/`.")
    plan.append("Demande à Google de retirer tes infos des résultats : https://g.co/resultsaboutyou")
    if archives:
        plan.append(f"{len(archives)} copie(s) archivée(s) existent : demande le retrait à archive.org "
                    "(info@archive.org) après avoir supprimé les comptes.")
    plan.append("Relance cet outil dans quelques semaines pour voir ce qui reste.")
    return plan


# ====================================================================== lettres et rapport
def lettre_site(email, nom, compte):
    dom = compte["domaine"]
    r = racine(dom)
    identifiants = [f"- courriel : {email}"] + [f"- profil : {u}" for u in sorted(compte["urls"])]
    return f"""À : privacy@{r}, dpo@{r}
(adresses probables : vérifie la page « confidentialité » du site pour le bon contact)

Objet : Demande de suppression de mes renseignements personnels

Bonjour,

Je vous demande de supprimer tous les renseignements personnels me concernant
liés à votre service ({dom}), y compris mon compte, mon profil, mon historique et
les copies de sauvegarde, et de cesser de les diffuser ou de les utiliser.

Identifiants concernés :
{chr(10).join(identifiants)}

Cette demande est faite conformément aux lois applicables sur la protection des
renseignements personnels, dont la Loi 25 au Québec et, le cas échéant,
l'article 17 du RGPD.

Merci de me confirmer la suppression par écrit dans un délai de 30 jours.

Cordialement,
{nom}
{email}
"""


def lien_suppression(domaine):
    q = urllib.parse.quote_plus(f"comment supprimer mon compte {domaine}")
    return "https://www.google.com/search?q=" + q


def liens_recherche(email, pseudo):
    liens = []
    for q in (f'"{email}"', f'"{pseudo}"'):
        qq = urllib.parse.quote_plus(q)
        liens.append((f"Google {q}", "https://www.google.com/search?q=" + qq))
        liens.append((f"DuckDuckGo {q}", "https://duckduckgo.com/?q=" + qq))
    return liens


def ouvrir_prive(chemin):
    """Ouvre un fichier en écriture, lisible par toi seul (0600 sous Linux) :
    le rapport contient ton courriel, ton nom, tes fuites et tes comptes."""
    fd = os.open(chemin, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    if os.name != "nt":
        os.fchmod(fd, 0o600)   # aussi pour un fichier qui existait déjà avec d'autres droits
    return open(fd, "w", encoding="utf-8")


def ecrire_fichiers(dossier, ctx, comptes, fuites, archives, plan, recherches):
    os.makedirs(os.path.join(dossier, "lettres"), mode=0o700, exist_ok=True)

    # lettres : seulement pour les résultats forts ou moyens
    nb_lettres = 0
    for c in comptes:
        if c["confiance"] in ("forte", "moyenne"):
            chemin = os.path.join(dossier, "lettres", re.sub(r"[^\w.-]", "_", c["domaine"]) + ".txt")
            with ouvrir_prive(chemin) as f:
                f.write(lettre_site(ctx.email, ctx.nom, c))
            nb_lettres += 1

    # rapport Markdown
    md = [f"# Résultat final : {ctx.email}",
          f"_Généré le {datetime.datetime.now():%Y-%m-%d %H:%M} par Grand Ménage {VERSION} "
          f"(pseudo cherché : « {ctx.pseudo} »)_",
          "\n## Plan d'action\n"]
    md += [f"- [ ] {etape}" for etape in plan]

    md.append("\n## Comptes et profils trouvés\n")
    if comptes:
        md.append("| Site | Confiance | Trouvé par | Liens | Supprimer |")
        md.append("|---|---|---|---|---|")
        for c in comptes:
            liens = " ".join(f"[lien]({u})" for u in sorted(c["urls"])) or "-"
            md.append(f"| {c['domaine']} | {c['confiance']} | {', '.join(sorted(c['sources']))} | "
                      f"{liens} | [comment]({lien_suppression(c['domaine'])}) |")
    else:
        md.append("_Rien trouvé._")

    md.append("\n## Fuites de données\n")
    md += [f"- {f['site']}" for f in fuites] or ["_Aucune fuite connue (ou service non vérifié)._"]

    md.append("\n## Copies archivées (Wayback Machine)\n")
    md += [f"- {a['site']} -> [copie]({a['url']})" for a in archives] or ["_Aucune copie trouvée (ou non vérifié)._"]

    md.append("\n## État des outils\n")
    md.append("| Outil | Statut | Durée | Note |")
    md.append("|---|---|---|---|")
    for r in ctx.resultats:
        md.append(f"| {r.nom} | {r.statut} | {r.duree:.0f} s | {r.note or len(r.trouves)} |")

    md.append("\n## Recherches à faire toi-même\n")
    md += [f"- [{nom}]({url})" for nom, url in recherches]
    md.append("\n## Liens utiles\n")
    md += [f"- [{nom}]({url})" for nom, url in LIENS_NETTOYAGE]

    chemin_md = os.path.join(dossier, "RESULTAT_FINAL.md")
    with ouvrir_prive(chemin_md) as f:
        f.write("\n".join(md) + "\n")

    # JSON
    donnees = {
        "version": VERSION, "courriel": ctx.email, "pseudo": ctx.pseudo,
        "comptes": [{**c, "sources": sorted(c["sources"]), "urls": sorted(c["urls"])} for c in comptes],
        "fuites": [f["site"] for f in fuites],
        "archives": archives,
        "outils": [{"outil": r.cle, "statut": r.statut, "duree_s": round(r.duree), "note": r.note,
                    "nb": len(r.trouves)} for r in ctx.resultats],
        "plan": plan,
    }
    with ouvrir_prive(os.path.join(dossier, "resultat.json")) as f:
        json.dump(donnees, f, ensure_ascii=False, indent=2)

    return chemin_md, nb_lettres


# ====================================================================== programme principal
def afficher_resultat_final(ctx, comptes, fuites, archives, plan, dossier, nb_lettres):
    print()
    barre("RÉSULTAT FINAL")
    print(f"  Courriel : {ctx.email}    Pseudo : {ctx.pseudo}\n")

    print("  Outils :")
    for r in ctx.resultats:
        print(f"    {r.cle:<9} {r.statut:<10} {r.note or str(len(r.trouves)) + ' résultat(s)'}")

    nb = {k: sum(1 for c in comptes if c["confiance"] == k) for k in ("forte", "moyenne", "faible")}
    print(f"\n  Fuites de données : {len(fuites)}")
    print(f"  Comptes/profils   : {len(comptes)} (forte : {nb['forte']}, "
          f"moyenne : {nb['moyenne']}, faible : {nb['faible']})")
    print(f"  Copies archivées  : {len(archives)}")

    if comptes:
        print(f"\n  {'SITE':<34}{'CONFIANCE':<11}TROUVÉ PAR")
        for c in comptes[:40]:
            print(f"  {c['domaine']:<34}{c['confiance']:<11}{', '.join(sorted(c['sources']))}")
        if len(comptes) > 40:
            print(f"  ... {len(comptes) - 40} de plus dans le rapport")

    print("\n  PLAN D'ACTION")
    for n, etape in enumerate(plan, 1):
        print(f"   {n}. {etape}")

    print(f"\n  Dossier  : {dossier}")
    print(f"  Rapport  : RESULTAT_FINAL.md   Lettres : {nb_lettres} dans lettres/")


LOGO = r"""
 ██████╗ ██████╗  █████╗ ███╗   ██╗██████╗
██╔════╝ ██╔══██╗██╔══██╗████╗  ██║██╔══██╗
██║  ███╗██████╔╝███████║██╔██╗ ██║██║  ██║
██║   ██║██╔══██╗██╔══██║██║╚██╗██║██║  ██║
╚██████╔╝██║  ██║██║  ██║██║ ╚████║██████╔╝
 ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝╚═════╝
███╗   ███╗███████╗███╗   ██╗ █████╗  ██████╗ ███████╗
████╗ ████║██╔════╝████╗  ██║██╔══██╗██╔════╝ ██╔════╝
██╔████╔██║█████╗  ██╔██╗ ██║███████║██║  ███╗█████╗
██║╚██╔╝██║██╔══╝  ██║╚██╗██║██╔══██║██║   ██║██╔══╝
██║ ╚═╝ ██║███████╗██║ ╚████║██║  ██║╚██████╔╝███████╗
╚═╝     ╚═╝╚══════╝╚═╝  ╚═══╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝
"""


LARGEUR = max(len(l) for l in LOGO.strip("\n").split("\n")) + 4

# Bleu du drapeau du Québec (#003DA5). Selon ton terminal : vraie couleur, 256 couleurs ou bleu de base.
def _fond_bleu_quebec():
    if os.name == "nt":   # Windows 10/11 gère la vraie couleur une fois les codes activés
        return "\033[48;2;0;61;165m"
    if os.environ.get("COLORTERM", "").lower() in ("truecolor", "24bit"):
        return "\033[48;2;0;61;165m"
    if "256" in os.environ.get("TERM", ""):
        return "\033[48;5;25m"
    return "\033[44m"


def styles():
    """Couleurs du terminal. Vides si la sortie est redirigée ou si NO_COLOR est défini."""
    if not sys.stdout.isatty() or os.environ.get("NO_COLOR") or not COULEURS_OK:
        return SimpleNamespace(bleu="", gris="", gras="", fin="")
    # fond bleu Québec + texte blanc gras : lisible sur n'importe quel terminal, sombre ou clair
    return SimpleNamespace(bleu=_fond_bleu_quebec() + "\033[1;97m", gris="\033[2m",
                           gras="\033[1m", fin="\033[0m")


def barre(texte):
    """Bande bleue pleine largeur avec un titre centré."""
    st = styles()
    if st.bleu:
        print(st.bleu + texte.center(LARGEUR) + st.fin)
    else:
        print(f" {texte} ".center(LARGEUR, "-"))


def filet():
    st = styles()
    print(st.gris + "─" * LARGEUR + st.fin)


def banniere(effacer=True):
    """Affiche le titre sur une plaque bleu Québec, en haut du terminal
    (efface l'écran d'abord si c'est un vrai terminal)."""
    st = styles()
    if effacer and sys.stdout.isatty():
        if COULEURS_OK:
            print("\033[2J\033[H", end="")
        elif os.name == "nt":
            os.system("cls")

    def ligne(texte="", centrer=False):
        t = texte.center(LARGEUR) if centrer else ("  " + texte).ljust(LARGEUR)
        print(st.bleu + t + st.fin if st.bleu else t.rstrip())

    ligne()
    for l in LOGO.strip("\n").split("\n"):
        ligne(l)
    ligne()
    ligne(f"Grand Ménage v{VERSION}  -  nettoie tes traces sur le web", centrer=True)
    ligne()
    print(f"\n  {st.gris}Un seul outil, tous les outils : fuites, comptes, profils, archives{st.fin}\n")


EMAIL_RE = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"

OUTILS_EXTERNES = ("holehe", "sherlock", "maigret")
PAQUETS_PIP = {"holehe": "holehe", "sherlock": "sherlock-project", "maigret": "maigret"}


def confirmer_adresse(email):
    rep = input(f"  Cette adresse ({email}) est bien la tienne ? (oui/non) : ")
    return rep.strip().lower() in ("oui", "o", "yes", "y")


def nouveau_dossier(sortie):
    """Crée un dossier neuf par lancement : deux ménages en même temps ne se mélangent pas.
    os.mkdir échoue si le dossier existe déjà, ce qui le réserve sans course entre deux lancements."""
    os.makedirs(sortie, mode=0o700, exist_ok=True)
    base = os.path.join(sortie, datetime.datetime.now().strftime("%Y%m%d_%H%M%S"))
    n = 1
    while True:
        dossier = base if n == 1 else f"{base}-{n}"
        try:
            os.mkdir(dossier, 0o700)
            return dossier
        except FileExistsError:
            n += 1


def faire_le_menage(ctx, outils, sortie):
    """Lance les outils un par un, fusionne, écrit les fichiers et affiche le résultat final."""
    try:   # avant les outils : si le dossier est impossible à créer, on le sait tout de suite
        dossier = nouveau_dossier(sortie)
    except OSError as e:
        print(f"  Impossible de créer le dossier des résultats dans {sortie} ({e}).")
        print("  Choisis un autre dossier avec --sortie. Aucun outil n'a été lancé.")
        return None
    ctx.resultats = []
    executer(outils, ctx)
    comptes = consolider(ctx.resultats)
    fuites = trouves_de(ctx.resultats, "fuites")
    archives = trouves_de(ctx.resultats, "archives")
    plan = plan_action(comptes, fuites, archives)
    recherches = liens_recherche(ctx.email, ctx.pseudo)
    _, nb_lettres = ecrire_fichiers(dossier, ctx, comptes, fuites, archives, plan, recherches)
    afficher_resultat_final(ctx, comptes, fuites, archives, plan, dossier, nb_lettres)
    return dossier


# ---------------------------------------------------------------- réglages mémorisés
def charger_config(sortie):
    try:
        with open(os.path.join(sortie, "config.json"), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def sauver_config(sortie, ctx):
    try:
        os.makedirs(sortie, mode=0o700, exist_ok=True)
        with ouvrir_prive(os.path.join(sortie, "config.json")) as f:
            json.dump({"email": ctx.email, "pseudo": ctx.pseudo, "nom": ctx.nom},
                      f, ensure_ascii=False, indent=2)
    except OSError:
        pass


# ---------------------------------------------------------------- le menu
def saisir(question, defaut=""):
    rep = input(f"  {question}" + (f" [{defaut}]" if defaut else "") + " : ").strip()
    return rep or defaut


def regler_identite(ctx, sortie):
    email = saisir("Ton courriel (Entrée = annuler)", ctx.email)
    if not email:
        return
    if not re.match(EMAIL_RE, email):
        print("  Adresse courriel invalide.")
        return
    if email != ctx.email and not confirmer_adresse(email):
        print("  Outil réservé à tes propres adresses. Rien n'a été changé.")
        return
    derive = email.split("@")[0]
    ctx.pseudo = saisir("Pseudo à chercher", ctx.pseudo if email == ctx.email and ctx.pseudo else derive)
    nom_actuel = "" if ctx.nom == "[Ton nom]" else ctx.nom
    ctx.nom = saisir("Ton nom (pour les lettres)", nom_actuel) or "[Ton nom]"
    ctx.email = email
    sauver_config(sortie, ctx)
    print("  Réglages enregistrés.")


def choisir_outils(outils):
    print("\n  Outils disponibles :")
    for i, (_, nom, _) in enumerate(outils, 1):
        print(f"   {i}) {nom}")
    rep = input("\n  Numéros à lancer, séparés par des virgules (Entrée = annuler) : ").strip()
    if not rep:
        return []
    voulus = set()
    for morceau in rep.split(","):
        if morceau.strip().isdigit() and 1 <= int(morceau) <= len(outils):
            voulus.add(int(morceau) - 1)
    return [o for i, o in enumerate(outils) if i in voulus]


def dernier_dossier(sortie, contenant=None):
    """Dossier de résultats le plus récent. Avec `contenant`, seulement un dossier qui a ce fichier
    (un ménage interrompu peut laisser un dossier sans rapport)."""
    try:
        dossiers = sorted(d for d in os.listdir(sortie)
                          if re.match(r"^\d{8}_\d{4}(\d{2})?(-\d+)?$", d) and os.path.isdir(os.path.join(sortie, d)))
    except OSError:
        return None
    for d in reversed(dossiers):
        if not contenant or os.path.isfile(os.path.join(sortie, d, contenant)):
            return os.path.join(sortie, d)
    return None


def voir_dernier_resultat(sortie):
    d = dernier_dossier(sortie, "RESULTAT_FINAL.md")
    if not d:
        print("  Aucun résultat pour l'instant. Lance d'abord le grand ménage (option 1).")
        return
    print(f"\n  Dossier : {d}\n")
    try:
        with open(os.path.join(d, "RESULTAT_FINAL.md"), encoding="utf-8", errors="replace") as f:
            print(f.read())
    except OSError as e:
        print(f"  Impossible de lire le rapport ({e}).")


def ouvrir_chemin(chemin):
    """Ouvre un dossier dans l'explorateur de fichiers (Windows, Linux ou macOS)."""
    try:
        if os.name == "nt":
            os.startfile(chemin)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", chemin])
        elif shutil.which("xdg-open"):
            subprocess.Popen(["xdg-open", chemin], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            return False
        return True
    except OSError:
        return False


def ouvrir_dossier(sortie):
    d = dernier_dossier(sortie) or sortie
    if os.path.isdir(d) and ouvrir_chemin(d):
        print(f"  Ouverture de {d}")
    else:
        print(f"  Dossier : {d}")


def plan_installation(manquants):
    """Liste de (nom, commande, commande_de_secours) adaptée au système."""
    plan = []
    if os.name == "nt":   # Windows : pip suffit
        for prog in manquants:
            plan.append((prog, [sys.executable, "-m", "pip", "install", "--user", PAQUETS_PIP[prog]], None))
        return plan
    pipx = ["pipx"]
    if not shutil.which("pipx"):
        gestionnaires = [   # (commande à chercher, commande d'installation de pipx)
            ("apt-get", ["sudo", "apt-get", "install", "-y", "pipx"]),
            ("dnf", ["sudo", "dnf", "install", "-y", "pipx"]),
            ("pacman", ["sudo", "pacman", "-S", "--noconfirm", "python-pipx"]),
            ("zypper", ["sudo", "zypper", "install", "-y", "python3-pipx"]),
            ("brew", ["brew", "install", "pipx"]),
        ]
        commande = next((c for g, c in gestionnaires if shutil.which(g)), None)
        if commande:
            plan.append(("pipx", commande, None))
        else:   # aucun gestionnaire connu : pipx par pip, lancé ensuite par Python lui-même
            plan.append(("pipx", [sys.executable, "-m", "pip", "install", "--user", "pipx"], None))
            pipx = [sys.executable, "-m", "pipx"]
    for prog in manquants:
        par_pipx = pipx + ["install", PAQUETS_PIP[prog]]
        if est_kali() and prog in ("sherlock", "maigret"):
            plan.append((prog, ["sudo", "apt-get", "install", "-y", prog], par_pipx))   # apt d'abord, pipx si ça échoue
        else:
            plan.append((prog, par_pipx, None))
    return plan


def _lancer_visible(commande):
    """Lance la commande en laissant tout s'afficher (sudo peut ainsi demander le mot de passe)."""
    try:
        return subprocess.run(commande).returncode == 0
    except OSError as e:
        print(f"  ! {e}")
        return False


def installer_outils(manquants):
    plan = plan_installation(manquants)
    print("\n  Commandes qui vont être lancées :\n")
    for _, commande, _ in plan:
        print("    " + " ".join(commande))
    if input("\n  Les lancer maintenant ? (oui/non) : ").strip().lower() not in ("oui", "o", "yes", "y"):
        print("  Rien n'a été installé.")
        return False
    for nom, commande, secours in plan:
        print(f"\n  >>> {nom}")
        ok = _lancer_visible(commande)
        if not ok and secours:
            print("  Échec. Nouvel essai avec : " + " ".join(secours))
            ok = _lancer_visible(secours)
        print("  Terminé." if ok else "  ÉCHEC (on continue avec les suivants)")
    completer_path()
    return True


def verifier_installation():
    print(f"\n  Système : {nom_systeme()}\n")
    print("  Outils utilisés par Grand Ménage :\n")
    manquants = [p for p in OUTILS_EXTERNES if not shutil.which(p)]
    for programme in OUTILS_EXTERNES:
        print(f"   [{'MANQUANT' if programme in manquants else 'OK':<8}] {programme}")
    print("\n  Les autres outils (fuites, Gravatar, archives) n'ont rien à installer.")
    if manquants and installer_outils(manquants):
        print("\n  Après installation :\n")
        for programme in manquants:
            print(f"   [{'OK' if shutil.which(programme) else 'MANQUANT':<8}] {programme}")


def menu(ctx, sortie, outils_base, sans_effacer):
    while True:
        banniere(not sans_effacer)
        print(f"  Courriel : {ctx.email or '(pas encore réglé)'}")
        print(f"  Pseudo   : {ctx.pseudo or '-'}")
        print(f"  Nom      : {'-' if ctx.nom == '[Ton nom]' else ctx.nom}\n")
        barre("MENU")
        print("   1)  Lancer le grand ménage complet")
        print("   2)  Choisir les outils à lancer")
        print("   3)  Régler mon courriel, mon pseudo et mon nom")
        print("   4)  Voir le dernier résultat final")
        print("   5)  Ouvrir le dossier des résultats")
        print("   6)  Vérifier / installer les outils")
        print("   q)  Quitter")
        filet()
        print()
        choix = input("  Ton choix : ").strip().lower()
        print()

        if choix in ("q", "0"):
            print("  À la prochaine !")
            return
        elif choix in ("1", "2"):
            if not ctx.email:
                print("  Règle d'abord ton courriel (option 3).")
            else:
                outils = outils_base if choix == "1" else choisir_outils(outils_base)
                if outils:
                    faire_le_menage(ctx, outils, sortie)
        elif choix == "3":
            regler_identite(ctx, sortie)
        elif choix == "4":
            voir_dernier_resultat(sortie)
        elif choix == "5":
            ouvrir_dossier(sortie)
        elif choix == "6":
            verifier_installation()
        else:
            continue
        input("\n  Appuie sur Entrée pour revenir au menu...")


# ====================================================================== programme principal
def main():
    preparer_terminal()
    p = argparse.ArgumentParser(description="Grand Ménage : lance tous les outils de traces web, un par un, "
                                            "et fusionne le résultat. Sans courriel, un menu s'ouvre.")
    p.add_argument("email", nargs="?", help="TON adresse courriel (sans elle : le menu s'ouvre)")
    p.add_argument("--pseudo", help="pseudo à chercher (défaut : la partie avant le @)")
    p.add_argument("--nom", default="[Ton nom]", help="ton nom, pour les lettres de suppression")
    p.add_argument("--sortie", default=os.path.expanduser("~/grand-menage"),
                   help="dossier des résultats (défaut : ~/grand-menage)")
    p.add_argument("--sauter", default="",
                   help="outils à sauter, séparés par des virgules (" + ",".join(o[0] for o in OUTILS) + ")")
    p.add_argument("--max-archives", type=int, default=15, help="nombre max de profils vérifiés dans Wayback")
    p.add_argument("--oui", action="store_true", help="sauter la confirmation « c'est mon adresse »")
    p.add_argument("--sans-effacer", action="store_true", help="ne pas effacer l'écran au démarrage")
    p.add_argument("--ouvrir", action="store_true", help="ouvrir les liens de recherche dans le navigateur")
    a = p.parse_args()

    sauter = {s.strip() for s in a.sauter.split(",") if s.strip()}
    inconnus = sauter - {o[0] for o in OUTILS}
    if inconnus:
        sys.exit(f"Outil(s) inconnu(s) : {', '.join(sorted(inconnus))}")
    outils = [o for o in OUTILS if o[0] not in sauter]

    ctx = SimpleNamespace(email="", nom=a.nom, pseudo="", max_archives=a.max_archives, resultats=[])

    try:
        if a.email:   # mode direct : une seule commande, tout est fait
            if not re.match(EMAIL_RE, a.email):
                sys.exit("Adresse courriel invalide.")
            banniere(not a.sans_effacer)
            if not a.oui and not confirmer_adresse(a.email):
                sys.exit("  Outil réservé à tes propres adresses. Arrêt.")
            ctx.email = a.email
            ctx.pseudo = a.pseudo or a.email.split("@")[0]
            if faire_le_menage(ctx, outils, a.sortie) is None:
                sys.exit(1)
            if a.ouvrir:
                recherches = liens_recherche(ctx.email, ctx.pseudo)
                for nom, url in recherches + LIENS_NETTOYAGE:
                    rep = input(f"\n  Ouvrir « {nom.strip()} » ? (Entrée = oui, q = arrêter) ")
                    if rep.strip().lower() == "q":
                        break
                    webbrowser.open(url)
        else:         # mode menu
            if not (sys.stdin.isatty() and sys.stdout.isatty()):
                sys.exit("Donne ton courriel en argument, ou lance Grand Ménage dans un terminal pour ouvrir le menu.")
            cfg = charger_config(a.sortie)
            ctx.email = cfg.get("email", "")
            ctx.pseudo = cfg.get("pseudo", "")
            ctx.nom = cfg.get("nom") or a.nom
            menu(ctx, a.sortie, outils, a.sans_effacer)
    except (KeyboardInterrupt, EOFError):
        print("\n\n  Au revoir.")


if __name__ == "__main__":
    main()
