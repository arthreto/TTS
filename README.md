# Voix IA : synthèse vocale gratuite (français et anglais)

Vous écrivez un texte, vous choisissez la langue et une voix, et l'appli génère l'audio (WAV) que vous pouvez écouter et télécharger.

- **100 % gratuit** : aucune clé d'API, aucun abonnement, aucune limite.
- **100 % local** : tout tourne sur votre ordinateur. Votre texte ne quitte jamais votre machine.
- **Deux moteurs** :
  - **Rapide** ([Piper](https://github.com/rhasspy/piper)) : 16 voix, une phrase en moins d'une seconde, marche sur n'importe quel PC.
  - **Réaliste** ([Chatterbox Multilingual](https://github.com/resemble-ai/chatterbox), licence MIT) : voix beaucoup plus naturelles, avec intonation et émotion. Il peut aussi **imiter une voix à partir d'un enregistrement de 10 à 20 secondes**. Il demande une carte graphique NVIDIA (RTX) pour être rapide.

## Installation (une seule fois)

Rien à installer à la main, **pas besoin d'avoir Python** : l'appli télécharge elle-même son propre Python 3.12 dans son dossier (`outils/`), grâce à l'outil [uv](https://github.com/astral-sh/uv). Les Pythons déjà installés sur votre PC ne sont pas utilisés ni modifiés.

1. Dézippez le dossier où vous voulez.
2. Lancez l'appli :
   - **Windows** : double-cliquez sur `lancer-windows.bat`
   - **Mac / Linux** : dans un terminal, lancez `./lancer-mac-linux.sh`

Au premier lancement, Python et les dépendances se téléchargent (1 à 2 minutes). Ensuite la page **http://127.0.0.1:5050** s'ouvre toute seule dans votre navigateur.

### Activer le mode Réaliste

1. Mettez à jour le pilote de votre carte graphique NVIDIA (via GeForce Experience / l'application NVIDIA, ou sur nvidia.com). Il faut un pilote récent, version 570 ou plus.
2. Fermez l'appli si elle est ouverte, puis double-cliquez sur `installer-mode-realiste.bat` (Mac/Linux : `./installer-mode-realiste.sh`). Ça télécharge environ 3 Go (PyTorch et dépendances) et prend 5 à 15 minutes. À la fin, le script affiche le nom de votre carte graphique : vérifiez qu'elle est bien détectée.
3. Relancez l'appli et choisissez **Réaliste**. Au tout premier chargement, le modèle (encore environ 3 Go) se télécharge automatiquement. Les fois suivantes, il se charge en quelques secondes.

## Utilisation

1. Choisissez **Français** ou **English**, puis **Rapide** ou **Réaliste**.
2. Cliquez sur une voix. La première fois, elle se télécharge (20 à 110 Mo, une seule fois). Ensuite elle marche même sans Internet.
3. Écrivez votre texte, puis cliquez sur **Générer la voix** (ou appuyez sur Ctrl + Entrée).
   - En mode Rapide, vous pouvez régler la **vitesse**.
   - En mode Réaliste, vous pouvez régler l'**expressivité** : 0,5 donne un ton naturel, 0,8 ou plus un ton plus vivant et émotif.
4. Écoutez le résultat, puis cliquez sur **Télécharger (.wav)** pour l'enregistrer.

Pour arrêter l'appli, fermez la fenêtre noire du terminal (ou faites Ctrl + C dedans).

### Ajouter vos propres voix (mode Réaliste)

En mode Réaliste, cliquez sur **+ Ajouter une voix**, donnez-lui un nom, puis :
- **choisissez un fichier audio** (mp3, wav, m4a…), ou
- **enregistrez-vous au micro** en lisant le texte proposé.

Conseils pour un bon résultat : 10 à 20 secondes, une seule personne qui parle, sans musique ni bruit de fond, **dans la langue choisie**. Une voix enregistrée en anglais qui lit du français garde un accent anglais, et inversement.

N'utilisez que votre propre voix ou celle d'une personne qui a donné son accord.

## Voix disponibles

| Langue | Voix |
|---|---|
| Français | Siwis (femme), Jessica (femme), Tom (homme), Pierre (homme), Gilles (homme, qualité basse) |
| Anglais US | Lessac (femme, haute qualité), Amy (femme), Kristin (femme), Ryan (homme, haute qualité), Joe (homme), Norman (homme) |
| Anglais UK | Cori (femme, haute qualité), Jenny (femme), Alba (femme, accent écossais), Alan (homme), Oliver (homme, accent du nord) |

En mode Réaliste, ces voix sont imitées à partir d'un court extrait lu par la voix Piper du même nom. Une **voix intégrée** (anglais) et vos propres voix sont aussi disponibles. Pour le rendu le plus naturel, utilisez un vrai enregistrement de voix humaine.

Pour tout désinstaller, supprimez simplement le dossier de l'appli.

Les fichiers sont enregistrés dans le dossier `voices/` (vos voix dans `voices/mes-voix/`). Le modèle Réaliste est stocké dans le cache Hugging Face (`~/.cache/huggingface`, ou `C:\Users\<vous>\.cache\huggingface` sous Windows).

Pour ajouter d'autres voix Piper, il suffit d'ajouter une ligne dans la liste `CATALOG` de `app.py`. La liste complète des voix se trouve ici : https://huggingface.co/rhasspy/piper-voices

## En cas de problème

- **Une installation a échoué en cours de route** : relancez simplement `lancer-windows.bat`. Une installation incomplète est effacée et refaite automatiquement.
- **« carte graphique NVIDIA non détectée »** : mettez à jour le pilote NVIDIA, puis relancez l'appli.
- **Erreur de mémoire GPU en mode Réaliste** : fermez les jeux et autres logiciels qui utilisent la carte graphique, ou découpez le texte en plusieurs morceaux.

## Licences

- Piper et Chatterbox sont open source et gratuits, y compris pour un usage commercial (Chatterbox : licence MIT).
- Chaque voix Piper a sa propre licence (indiquée dans son fichier `MODEL_CARD` sur Hugging Face). Vérifiez-la si vous comptez publier ou vendre les fichiers audio.
- Chatterbox ajoute un tatouage numérique inaudible aux fichiers qu'il produit. Il permet de reconnaître qu'un audio a été généré par IA, et ça ne change rien à l'écoute.
