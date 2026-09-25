# 🤖 powerful-claw

<div align="center">

[English](../../README.md) | [简体中文](../zh/README.md) | [Русский](../ru/README.md) | **Français**

#### ⚠️ **Statut actuel : en cours de développement / WIP, bugs connus — ne pas utiliser en production**
#### ⚠️ **GitHub est le seul dépôt principal ; les autres plateformes sont des miroirs**

**Laissez l'IA voir et piloter votre ordinateur local** — un centre de contrôle open source d'agents d'automatisation de bureau.
Il associe des grands modèles multimodaux, la perception visuelle de l'écran et l'automatisation clavier/souris ; inclut la diffusion du bureau, un éditeur vidéo simple et la planification de nœuds de calcul en réseau local.

[![Python](https://img.shields.io/badge/Python-3.13+-blue.svg?logo=python&logoColor=white)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-success.svg?logo=windows&logoColor=white)](#)
[![License](https://img.shields.io/badge/License-GPL--3.0-blue.svg)](../../LICENSE)
[![Stars](https://img.shields.io/github/stars/chen-xin-Liam/powerful-claw?style=social)](https://github.com/chen-xin-Liam/powerful-claw/stargazers)
[![bilibili](https://img.shields.io/badge/bilibili-%E6%95%B0%E7%A7%91%E6%98%9F-00A1D6.svg?logo=bilibili&logoColor=white)](https://space.bilibili.com/3493111196027162)
</div>

---

> 💡 **Vision du projet**
> La plupart des agents IA se limitent à la conversation. Ce projet construit un agent local qui **lit l'écran, comprend le contenu de l'interface et pilote le clavier/la souris pour accomplir des tâches**.
> La diffusion du bureau, le montage vidéo et le calcul en cluster LAN sont des modules d'appoint — certains encore en développement.

## ✨ Fonctionnalités clés

- 🧠 **Agent de bureau local** : connexion aux LLM multimodaux (Ollama / compatibles OpenAI / API NVIDIA), détection d'objets à l'écran avec YOLO, compréhension de captures d'écran et automatisation de la saisie. Modèle de permissions à 4 niveaux (None/View/Limited/Full) pour réduire les risques d'erreur.
- 📺 **Diffusion du bureau en temps réel** : 1–30 FPS réglables, protocoles RTMP/SRT/WebRTC. Compression par différence de trames et encodage par blocs pour réduire la bande passante. Consultable directement dans le navigateur.
- 🎬 **Éditeur vidéo web intégré (basique)** : timeline multipiste, filtres d'étalonnage, sous-titres SRT/ASS, reconnaissance vocale en sous-titres. Export MP4/MOV/GIF/WebM (1080P/2K/4K).
- 🌐 **Planification des calculs en LAN (WIP)** : découverte automatique des nœuds par UDP, collecte de charge CPU/mémoire/GPU/NPU, planification des tâches, chiffrement Fernet/RSA. Regroupez des machines inactives en cluster d'inférence.
- 🎨 **UI de bureau enfichable** : deux implémentations — légère en Python (Pillow) et haute performance en C++/OpenGL avec verre dépoli et animations de fenêtres.
- 🛠️ **Cœur en Python natif** : architecture légère facilitant la lecture du code, le développement dérivé et le débogage local.

## 📚 Pile technique

| Module | Technologies | Notes |
|--------|-------------|-------|
| Agent IA | Python 3.13+ | LLM multimodaux : Ollama/OpenAI/NVIDIA |
| Vision | Python + YOLOv8 | Capture d'écran, détection d'objets, haute DPI |
| Contrôle bureau | Python (pyautogui/keyboard) | Automatisation multiplateforme, 4 niveaux de permissions |
| Flux vidéo | Python + FFmpeg | RTMP/SRT/WebRTC, compression par différence de trames |
| UI | CustomTkinter + C++/OpenGL | Verre dépoli/lueur, deux implémentations |
| Calcul en cluster | Python + UDP/chiffrement | Découverte de nœuds, planification, Fernet/RSA |
| Journaux/erreurs | Loguru/Rich | Codes d'erreur unifiés, logs hiérarchisés, traçage |
| Moteur mathématique | C++17 + cppyy dans Python | 44 types de nœuds (arithmétique/trigonométrie/LU/statistiques), repli Python pur |

## 🚀 Implémenté

- [x] Plusieurs backends IA (Ollama, API compatible OpenAI, NVIDIA), facilement extensible
- [x] Capture d'écran + détection d'objets YOLO
- [x] Automatisation de la souris et du clavier
- [x] Diffusion du bureau RTMP/SRT/WebRTC
- [x] Découverte de nœuds LAN et surveillance matérielle
- [x] Journalisation et gestion d'erreurs unifiées
- [x] Gestion de base de l'UI fenêtrée
- [x] Point d'entrée questions-réponses

## 🐛 Problèmes connus et modules inachevés

- Écart de reconnaissance des coordonnées d'écran sur les écrans haute DPI
- Scintillement occasionnel lors du changement de résolution d'affichage
- Validation de base effectuée uniquement sur Windows 10/11
- Le changement de thème peut occasionnellement figer l'UI
- Calcul en cluster LAN : logique de planification des nœuds incomplète
- Éditeur vidéo : seule l'architecture de base est en place, fonctionnalités incomplètes

## 🛠️ Démarrage rapide

```bash
# 1. Cloner
git clone https://github.com/chen-xin-Liam/powerful-claw.git
cd powerful-claw

# 2. Installer les dépendances
pip install -r requirements.txt

# 3. Lancer
python src/main.py

# 4. Accéder à la WebUI (diffusion + édition)
# Ouvrir dans le navigateur : http://localhost:8080
```

## 📖 Documentation

**Langues** : [English](../README.md) · [简体中文](../zh/INDEX.md) · [Русский](../ru/INDEX.md) · [Français](INDEX.md)

Les documents techniques (installation, configuration, manuel utilisateur) sont actuellement disponibles en anglais et en chinois — voir l'[index de documentation](INDEX.md).

## 🧪 Tests

```bash
# Suite complète
pytest auto_tests/

# Lanceur autonome (sans pytest)
python auto_tests/run_tests.py

# Comparatifs de performance
python benchmarks/perf_bench.py compute --iters 2000
python benchmarks/perf_bench.py startup --runs 7
```

## 🔌 Import de serveurs MCP

Import des configurations MCP standard (`.mcp.json`, Claude Desktop, VS Code) :

```bash
# Lister les modèles disponibles
python -m src.services.mcp_importer --templates

# Importer depuis un fichier de configuration
python -m src.services.mcp_importer path/to/mcp.json
```

## 📦 Construction de l'exécutable

```bash
python scripts/build_exe.py
```

Sortie dans `dist/AIComputerControl/`.

## 🤝 Contribuer

Voir [CONTRIBUTING.md](CONTRIBUTING.md) pour la configuration de développement, les conventions de code et la soumission de modifications.

## 📄 Licence

Ce projet est sous licence [GNU General Public License v3.0](../../LICENSE).
