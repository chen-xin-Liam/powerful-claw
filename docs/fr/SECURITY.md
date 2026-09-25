# Politique de sécurité

[English](../../SECURITY.md) | [简体中文](../zh/SECURITY.md) | [Русский](../ru/SECURITY.md) | **Français**

## Versions prises en charge

| Version | Support |
|---------|---------|
| Dernier commit sur `main` | ✅ |

Nous ne maintenons pas de branches de publication distinctes. Les correctifs de sécurité sont appliqués directement sur `main`.

---

## Signaler une vulnérabilité

**N'ouvrez PAS d'issue GitHub publique pour les vulnérabilités de sécurité.**

Signalez-les en privé via l'un des canaux suivants :

- **GitHub Security Advisories** : [Signaler une vulnérabilité](https://github.com/chen-xin-Liam/powerful-claw/security/advisories/new)
- **Email** : ouvrez une discussion privée sur le dépôt avec le label `security`

### Éléments à fournir

1. **Description** — ce qu'est la vulnérabilité et comment elle peut être exploitée
2. **Impact** — ce qu'un attaquant pourrait obtenir (fuite de données, exécution de code, élévation de privilèges, etc.)
3. **Étapes de reproduction** — étapes minimales ou code de preuve de concept
4. **Environnement** — OS, version Python, modules affectés (service IA, serveur WebSocket, MCP, etc.)
5. **Correctif suggéré** (optionnel) — si vous avez un patch ou une idée d'atténuation

### À quoi s'attendre

| Étape | Délai |
|-------|-------|
| Accusé de réception | Sous 72 heures |
| Évaluation initiale | Sous 7 jours |
| Correctif ou atténuation | Selon la gravité (problèmes critiques prioritaires) |
| Divulgation publique | Après fusion du correctif, avec crédit du rapporteur (sauf demande d'anonymat) |

---

## Modèle de sécurité

### Niveaux de permission

L'application applique un **modèle de permissions à 4 niveaux** pour les opérations de l'agent IA :

| Niveau | Capacités |
|--------|-----------|
| **None** | Pas d'accès à l'écran, pas de simulation de saisie |
| **View** | Capture d'écran uniquement, lecture seule |
| **Limited** | Capture d'écran + clavier/souris restreints (zones critiques système exclues) |
| **Full** | Accès complet à l'écran + clavier/souris sans restriction |

**Par défaut** : `None` — aucune opération de l'agent n'est autorisée tant que l'utilisateur ne l'a pas explicitement activée.

### Traitement des données

- **Clés API** stockées localement dans `.env` ou `config/settings.ini` — jamais transmises à des tiers
- **Captures d'écran** traitées localement ; elles ne sont envoyées au fournisseur IA configuré que lorsque l'utilisateur déclenche une requête IA
- **Historique des conversations** stocké localement dans `conversations.json` — exclu du contrôle de version
- **Communication du cluster LAN** : chiffrement symétrique Fernet (AES-128-CBC) avec échange de clés RSA

### Services réseau

| Port | Service | Exposition |
|------|---------|------------|
| 15000 | WebSocket (principal) | `0.0.0.0` — accessible en LAN |
| 15001 | WebSocket (secondaire) | `0.0.0.0` |
| 15002 | Serveur API HTTP | `0.0.0.0` |
| 15003 | WebSocket (API) | `0.0.0.0` |
| 15004 | Moniteur d'écran | `0.0.0.0` |
| 15010 | Éditeur vidéo | `0.0.0.0` |
| 15012 | WebSocket éditeur vidéo | `0.0.0.0` |

**Note** : ces services sont liés à `0.0.0.0` par défaut pour les fonctionnalités LAN. Si vous n'avez pas besoin d'accès distant, limitez-les via des règles de pare-feu.

### Serveurs MCP

Les serveurs MCP sont lancés comme **sous-processus locaux** en transport stdio. Ils héritent des variables d'environnement de l'application, y compris des clés API. N'importez des configurations MCP qu'à partir de sources de confiance.

---

## Considérations de sécurité connues

- **Automatisation du bureau** : l'agent peut simuler la saisie clavier/souris. Des invites malveillantes ou un fournisseur IA compromis pourraient déclencher des actions non désirées. Utilisez le niveau `Limited` quand c'est possible.
- **Capture d'écran** : les captures peuvent contenir des informations sensibles (mots de passe, données personnelles). L'application ne filtre pas le contenu sensible avant l'envoi aux fournisseurs IA.
- **Serveurs MCP non vérifiés** : les serveurs importés s'exécutent avec les mêmes privilèges que l'application principale. Examinez les configurations avant import.
- **Pas de bac à sable** : l'application s'exécute avec les privilèges OS complets de l'utilisateur. Soyez prudent en mode `Full`.

---

## Bonnes pratiques pour les utilisateurs

1. **Utilisez les permissions `View` ou `Limited`** sauf automatisation complète nécessaire
2. **N'exposez pas les ports 15000–15012 sur l'internet public** — limitez au LAN via le pare-feu
3. **Gardez les clés API hors du contrôle de version** — utilisez des fichiers `.env` (déjà dans `.gitignore`)
4. **Examinez les configurations MCP** avant import depuis des sources externes
5. **Mettez régulièrement à jour les dépendances** — `pip install -U -r requirements.txt` pour les correctifs de sécurité

---

## Périmètre

Sont **dans le périmètre** des rapports :

- Contournement d'authentification/autorisation dans le modèle de permissions
- Exécution de code à distance via les services réseau
- Fuite de clés API dans les journaux ou le trafic réseau
- Élévation de privilèges dans la gestion des serveurs MCP
- Exposition de données (captures d'écran, historique de conversation, clés API) à des tiers non autorisés

Sont **hors périmètre** :

- Vulnérabilités des dépendances tierces (signalez-les au projet amont)
- Attaques par ingénierie sociale
- Accès physique à la machine
- Problèmes nécessitant la désactivation des protections par l'utilisateur (par ex. permission `Full`)
