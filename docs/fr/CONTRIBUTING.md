# Contribuer à powerful-claw

[English](../../CONTRIBUTING.md) | [简体中文](../zh/CONTRIBUTING.md) | [Русский](../ru/CONTRIBUTING.md) | **Français**

Merci de votre intérêt pour le projet ! Ce guide explique comment configurer un environnement de développement, lancer les tests et soumettre des modifications.

---

## Prérequis

| Prérequis | Version minimale | Notes |
|-----------|------------------|-------|
| Python | 3.13 | Testé sur Windows 10/11 |
| MinGW (gcc/g++) | 13.x | Uniquement pour le backend natif C++ |
| Git | 2.40+ | Gestion de versions |

---

## Configuration de l'environnement de développement

```bash
# 1. Cloner le dépôt
git clone https://github.com/chen-xin-Liam/powerful-claw.git
cd powerful-claw

# 2. Créer et activer un environnement virtuel
python -m venv venv
venv\Scripts\activate          # Windows PowerShell

# 3. Installer les dépendances
pip install -r requirements.txt
pip install pytest             # Exécution des tests
```

**Optionnel — Compiler le backend natif C++** (nécessaire pour les comparatifs) :

```bash
python src/core/native/build_native.py
```

Produit `src/core/native/build/nodecalc_native.dll`. Si la DLL est absente, le backend bascule automatiquement en Python pur.

---

## Lancement de l'application

```bash
python src/main.py
```

Au premier lancement, les répertoires `config/` et `logs/` sont créés et la fenêtre principale s'ouvre.

---

## Exécution des tests

### Test de fumée rapide (lanceur autonome, sans pytest)

```bash
python auto_tests/run_tests.py
```

### Suite complète

```bash
pytest auto_tests/
```

Les tests couvrent :
- Le moteur d'expressions (les 44 types de nœuds)
- La parité entre backends natif et Python
- Les régressions de performance (comparaison avec `benchmarks/results_native_compute.json`)
- La vérification de connectivité des API
- L'import des configurations MCP

---

## Construction de l'exécutable

```bash
python scripts/build_exe.py
```

La sortie va dans `dist/AIComputerControl/`. La construction utilise PyInstaller avec le fichier spec `AIComputerControl.spec`.

Essai à blanc (inspecter le contenu sans créer de fichiers) :

```bash
python scripts/build_exe.py --dry-run
```

---

## Structure du code

```
src/
├── core/                  # Moteur d'expressions (Python pur + backend natif C++)
│   ├── node_engine.py     # 44 types de nœuds
│   ├── expression_parser.py
│   └── native/            # Sources C++, script de build, pont cffi
├── services/              # Services d'arrière-plan (WebSocket, API, IA, MCP, etc.)
├── ui/                    # Fenêtre principale CustomTkinter + réglages PySide6
├── config/                # Paramètres, thèmes, configurations d'extensions
└── system/                # Interaction matérielle, dialogues de confirmation

auto_tests/                # Suite de tests automatisés (pytest)
benchmarks/                # JSON de référence de performance
docs/                      # Documentation (en/zh/ru/fr)
scripts/                   # Scripts de build et de maintenance
```

---

## Conventions de code

- **Langage** : Python 3.13 (annotations de type recommandées)
- **UI** : CustomTkinter pour la fenêtre principale, PySide6 pour le dialogue de réglages
- **Imports** : les modules tiers lourds (openai, PIL, pyautogui, etc.) doivent être importés tardivement à l'intérieur des fonctions, et non au niveau du module. Cela maintient le démarrage à froid sous 1 seconde.
- **Repli de backend** : les modules de calcul doivent fonctionner en Python pur lorsque la DLL native est absente.
- **Commentaires** : écrivez les commentaires en chinois, par cohérence avec la base de code existante.
- **Docstrings** : docstrings de module obligatoires ; docstrings de fonction pour les API publiques.

---

## Ajouter un serveur MCP

Utilisez l'importeur intégré :

```python
from src.services.mcp_importer import add_from_template
add_from_template("github", env={"GITHUB_TOKEN": "your_token"})
```

Ou importez depuis un fichier `.mcp.json` standard :

```python
from src.services.mcp_importer import import_mcp_config
report = import_mcp_config("path/to/mcp.json")
```

Modèles disponibles : `filesystem`, `github`, `fetch`, `memory`, `sqlite`, `puppeteer`.

---

## Vérifier la connectivité des API

Avant de committer des modifications touchant au code des fournisseurs IA, vérifiez la connectivité :

```bash
python -m src.services.api_connectivity
```

Vérifie tous les fournisseurs configurés et affiche un rapport de synthèse.

---

## Soumettre des modifications

1. **Forkez** le dépôt et créez une branche de fonctionnalité :
   ```bash
   git checkout -b feat/your-feature-name
   ```

2. **Effectuez vos modifications** et ajoutez des tests dans `auto_tests/` le cas échéant.

3. **Lancez la suite complète** :
   ```bash
   pytest auto_tests/
   ```

4. **Commitez** avec un message descriptif dans le style existant (sujet court à l'impératif, corps optionnel) :
   ```bash
   git commit -m "Add GPU temperature monitoring to system info"
   ```

5. **Poussez** et ouvrez une Pull Request vers `main`.

---

## Signaler des problèmes

Ouvrez une issue sur GitHub avec :
- Une description claire du problème
- Les étapes de reproduction
- Le comportement attendu vs réel
- Les détails d'environnement (OS, version Python)
- Les journaux pertinents de `logs/`

---

## Licence

En contribuant, vous acceptez que vos contributions soient sous licence [GNU General Public License v3.0](../../LICENSE).
