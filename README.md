# Grand Ménage

**Un seul outil qui lance tous les autres, un par un, puis te donne un seul résultat final.**

Grand Ménage cherche les traces que ton adresse courriel et ton pseudo ont laissées sur le web :
fuites de données, comptes, profils publics et copies archivées. Il fusionne tout, indique à quel
point chaque résultat est fiable, puis te prépare un plan d'action et des lettres de demande de
suppression.

> **À utiliser seulement avec TON adresse courriel.** L'outil te demande de le confirmer avant de commencer.

Grand Ménage **ne supprime rien à ta place** : chaque site exige que tu te connectes ou que tu
prouves ton identité. Il te donne la liste, les liens et les lettres ; c'est toi qui fais le ménage.

---

## Ce que l'outil vérifie

| # | Outil | Ce qu'il cherche | Part de |
|---|---|---|---|
| 1 | `fuites` | Ton courriel dans les fuites de données connues ([XposedOrNot](https://xposedornot.com)) | courriel |
| 2 | `gravatar` | Un avatar public lié à ton courriel ([Gravatar](https://gravatar.com)) | courriel |
| 3 | `holehe` | Les sites où ce courriel a un compte | courriel |
| 4 | `sherlock` | Les profils qui portent ton pseudo | pseudo |
| 5 | `maigret` | Les profils qui portent ton pseudo (autre base de sites) | pseudo |
| 6 | `archives` | Les copies de ces profils dans la [Wayback Machine](https://web.archive.org) | profils trouvés |

Les outils 1, 2 et 6 n'ont rien à installer. Les outils 3, 4 et 5 sont des programmes à part
(voir [Installation pas à pas](#installation-pas-à-pas)). S'il en manque un, Grand Ménage le note « absent » et passe au suivant.

---

## Installation pas à pas

Choisis ton système et tape les commandes **dans l'ordre**, une ligne à la fois.
Les lignes qui commencent par `#` sont des explications : ne les tape pas.

- [Kali Linux](#kali-linux)
- [Ubuntu, Debian, Linux Mint](#ubuntu-debian-linux-mint)
- [Fedora](#fedora)
- [Arch Linux, Manjaro](#arch-linux-manjaro)
- [Windows 10/11](#windows-1011)
- [Android avec Termux](#android-avec-termux)

Il faut **Python 3.8 ou plus** pour Grand Ménage, et **Python 3.10 ou plus** pour l'outil maigret.

### Kali Linux

```bash
# 1. Mettre le système à jour et installer ce qu'il faut
sudo apt update
sudo apt install -y git python3 pipx sherlock maigret

# 2. Installer holehe
pipx install holehe
pipx ensurepath

# 3. FERME le terminal et ouvre-en un nouveau, puis télécharge Grand Ménage
git clone https://github.com/alexmarceauprevost812-source/Grand-menage-PY.git
cd Grand-menage-PY

# 4. Lancer Grand Ménage
python3 grand-menage.py
```

### Ubuntu, Debian, Linux Mint

```bash
# 1. Installer git, Python et pipx
sudo apt update
sudo apt install -y git python3 pipx

# 2. Installer les trois outils
pipx install holehe
pipx install sherlock-project
pipx install maigret
pipx ensurepath

# 3. FERME le terminal et ouvre-en un nouveau, puis télécharge Grand Ménage
git clone https://github.com/alexmarceauprevost812-source/Grand-menage-PY.git
cd Grand-menage-PY

# 4. Lancer Grand Ménage
python3 grand-menage.py
```

### Fedora

```bash
# 1. Installer git, Python et pipx
sudo dnf install -y git python3 pipx

# 2. Installer les trois outils
pipx install holehe
pipx install sherlock-project
pipx install maigret
pipx ensurepath

# 3. FERME le terminal et ouvre-en un nouveau, puis télécharge Grand Ménage
git clone https://github.com/alexmarceauprevost812-source/Grand-menage-PY.git
cd Grand-menage-PY

# 4. Lancer Grand Ménage
python3 grand-menage.py
```

### Arch Linux, Manjaro

```bash
# 1. Installer git, Python et pipx
sudo pacman -S --needed git python python-pipx

# 2. Installer les trois outils
pipx install holehe
pipx install sherlock-project
pipx install maigret
pipx ensurepath

# 3. FERME le terminal et ouvre-en un nouveau, puis télécharge Grand Ménage
git clone https://github.com/alexmarceauprevost812-source/Grand-menage-PY.git
cd Grand-menage-PY

# 4. Lancer Grand Ménage
python3 grand-menage.py
```

### Windows 10/11

Ouvre **PowerShell** (clic droit sur le menu Démarrer → « Terminal » ou « PowerShell »).

```powershell
# 1. Installer Python et git
winget install -e --id Python.Python.3.12
winget install -e --id Git.Git

# 2. FERME PowerShell et ouvre-le de nouveau, puis installe les trois outils
py -m pip install --user holehe sherlock-project maigret

# 3. Télécharger Grand Ménage
git clone https://github.com/alexmarceauprevost812-source/Grand-menage-PY.git
cd Grand-menage-PY

# 4. Lancer Grand Ménage
.\grand-menage
```

Pas de `winget` ? Installe Python depuis [python.org](https://www.python.org/downloads/) en cochant
**« Add Python to PATH »**. Sans git, télécharge le dossier en
[fichier ZIP](https://github.com/alexmarceauprevost812-source/Grand-menage-PY/archive/refs/heads/supabase.zip),
décompresse-le, puis dans PowerShell va dedans avec `cd` (par exemple
`cd $HOME\Downloads\Grand-menage-PY-supabase`) avant l'étape 4.

### Android avec Termux

Installe **Termux** depuis [F-Droid](https://f-droid.org/packages/com.termux/) (la version du
Play Store n'est plus à jour), ouvre-le, puis :

```bash
# 1. Mettre Termux à jour et installer git et Python
pkg update -y && pkg upgrade -y
pkg install -y git python

# 2. Télécharger Grand Ménage
git clone https://github.com/alexmarceauprevost812-source/Grand-menage-PY.git
cd Grand-menage-PY

# 3. Installer holehe (rapide)
pip install holehe

# 4. Installer sherlock (LONG : 10 à 30 minutes, il compile pandas sur le téléphone)
pkg install -y build-essential python-numpy
pip install sherlock-project

# 5. Lancer Grand Ménage, en sautant maigret
python grand-menage.py --sauter maigret
```

Sur Android, **maigret ne s'installe pas** dans la plupart des cas (une de ses bibliothèques,
`curl-cffi`, n'existe pas pour Android) : utilise `--sauter maigret`, ou décoche-le avec l'option 2
du menu. Si l'étape 4 échoue aussi, utilise `--sauter maigret,sherlock` : les fuites, Gravatar et
holehe marchent quand même.

Pour lire le rapport dans Termux : option 4 du menu, ou
`cat ~/grand-menage/*/RESULTAT_FINAL.md`.

### Ou bien : laisser Grand Ménage installer les outils

Une fois Grand Ménage téléchargé, lance-le sans argument et choisis
**6) Vérifier / installer les outils**. Il te montre ce qui manque, les commandes qu'il va lancer pour
ton système (Kali, autres Linux, Windows ou Termux), et te demande la permission avant de les lancer.

### Mettre à jour plus tard

```bash
cd Grand-menage-PY
git pull
```

Et pour mettre les outils à jour : `pipx upgrade-all` (Linux), ou
`py -m pip install -U holehe sherlock-project maigret` (Windows), ou
`pip install -U holehe sherlock-project` (Termux).

---

## Utilisation

### Avec le menu (recommandé)

```bash
python3 grand-menage.py
```

Sous Windows, dans `cmd` : `grand-menage`, ou dans PowerShell : `.\grand-menage`
(le lanceur `grand-menage.bat` choisit `py -3` ou `python` tout seul).
Dans Termux : `python grand-menage.py`.

```
   1)  Lancer le grand ménage complet
   2)  Choisir les outils à lancer
   3)  Régler mon courriel, mon pseudo et mon nom
   4)  Voir le dernier résultat final
   5)  Ouvrir le dossier des résultats
   6)  Vérifier / installer les outils
   q)  Quitter
```

La première fois, commence par **3** pour régler ton courriel, ton pseudo et ton nom (le nom sert à
signer les lettres). Ces réglages sont gardés pour les prochaines fois. Lance ensuite **1**.

### En une seule commande

```bash
python3 grand-menage.py ton.adresse@hotmail.com
python3 grand-menage.py ton.adresse@hotmail.com --pseudo tonpseudo --nom "Ton Nom"
python3 grand-menage.py ton.adresse@hotmail.com --sauter maigret,archives
```

Sous Windows, remplace `python3` par `py -3`, ou utilise `.\grand-menage` dans PowerShell.
Dans Termux, remplace `python3` par `python`.

### Options

| Option | Rôle |
|---|---|
| `--pseudo PSEUDO` | Pseudo à chercher. Par défaut : la partie avant le `@` de ton courriel. |
| `--nom "Ton Nom"` | Ton nom, pour signer les lettres de suppression. |
| `--sortie DOSSIER` | Où ranger les résultats. Par défaut : `~/grand-menage`. |
| `--sauter a,b` | Outils à ne pas lancer : `fuites`, `gravatar`, `holehe`, `sherlock`, `maigret`, `archives`. |
| `--max-archives N` | Nombre maximum de profils vérifiés dans la Wayback Machine (15 par défaut, `0` = aucun). |
| `--oui` | Ne pas demander « cette adresse est bien la tienne ? ». |
| `--sans-effacer` | Ne pas effacer l'écran au démarrage. |
| `--ouvrir` | À la fin, proposer d'ouvrir un par un les liens de recherche dans le navigateur. |

### Pendant le ménage

- Les outils passent **un par un** ; sherlock et maigret peuvent prendre plusieurs minutes.
- **Ctrl+C** arrête l'outil en cours. Ensuite, **Entrée** passe au suivant, **q** arrête tout et fait
  le rapport avec ce qui a déjà été trouvé.
- Un outil qui plante ne bloque pas les autres : il est noté « erreur » dans le rapport, avec la raison.

---

## Les résultats

Chaque lancement crée son propre dossier, par exemple `~/grand-menage/20261003_154210/` :

```
RESULTAT_FINAL.md   le rapport complet et le plan d'action à cocher
resultat.json       les mêmes données, pour d'autres programmes
lettres/            une lettre de demande de suppression par site
```

Sous Linux, ces dossiers et fichiers ne sont lisibles que par toi : ils contiennent ton courriel,
ton nom, tes fuites et tes comptes.

### Le niveau de confiance

Un site trouvé par plusieurs outils n'apparaît qu'une fois. Chaque ligne reçoit un niveau de confiance :

| Confiance | Signifie | Quoi faire |
|---|---|---|
| **forte** | Trouvé à partir de ton courriel (holehe ou Gravatar) | C'est presque sûrement à toi : supprime-le. |
| **moyenne** | Trouvé par sherlock **et** maigret avec ton pseudo | Vérifie que c'est bien toi, puis supprime-le. |
| **faible** | Trouvé par un seul outil, avec ton pseudo seulement | Probablement quelqu'un d'autre : ignore-le sauf si tu le reconnais. |

Les lettres ne sont écrites que pour les résultats **forts** et **moyens**.

### Le plan d'action

Le rapport commence par une liste à cocher adaptée à ce qui a été trouvé, par exemple :

1. Changer les mots de passe exposés par une fuite et activer la double authentification.
2. Supprimer les comptes liés à ton courriel.
3. Envoyer les lettres de `lettres/` aux sites qui n'ont pas de bouton de suppression.
4. Demander à Google de retirer tes infos des résultats : <https://g.co/resultsaboutyou>
5. Demander à archive.org de retirer les copies archivées, une fois les comptes supprimés.
6. Relancer Grand Ménage dans quelques semaines pour voir ce qui reste.

### Les lettres de suppression

Chaque lettre demande la suppression de tes renseignements personnels en citant la **Loi 25** du
Québec et, s'il y a lieu, l'**article 17 du RGPD**. Elle est adressée à `privacy@` et `dpo@` du
site : ce sont des adresses **probables**, vérifie la page « confidentialité » du site pour trouver
le bon contact avant d'envoyer.

Si un site refuse ou ne répond pas dans les 30 jours, tu peux porter plainte à la
[Commission d'accès à l'information du Québec](https://www.cai.gouv.qc.ca).

---

## Liens utiles

- [Have I Been Pwned](https://haveibeenpwned.com) : voir où ton courriel a fuité
- [JustDeleteMe](https://justdeleteme.xyz) : liens directs pour supprimer un compte
- [Google, résultats vous concernant](https://g.co/resultsaboutyou) : demander le retrait de tes infos perso
- [Commission d'accès à l'information du Québec](https://www.cai.gouv.qc.ca) : si un site refuse

---

## Problèmes fréquents

**« non installé (option 6 du menu pour l'installer) »** : l'outil n'est pas trouvé. Lance l'option 6,
ou installe-le à la main, puis ferme et rouvre le terminal.

**holehe : « la recherche n'a pas eu lieu »** : holehe a voulu se mettre à jour au lieu de chercher.
Mets-le à jour toi-même (`pipx upgrade holehe`, ou `py -m pip install -U holehe` sous Windows),
puis relance.

**« Impossible de créer le dossier des résultats »** : le dossier donné à `--sortie` n'est pas
utilisable. Choisis-en un autre ; aucun outil n'a été lancé.

**Pas de couleurs ou caractères bizarres sous Windows** : utilise Windows Terminal ou une console
Windows 10/11 à jour. Tu peux aussi désactiver les couleurs avec la variable `NO_COLOR=1`.
