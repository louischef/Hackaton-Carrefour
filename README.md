# 🏢 Brand Holdings Verification & Discovery System

Un système automatisé pour vérifier l'appartenance des marques à leurs holdings et découvrir de nouvelles marques manquantes, avec classification par secteur d'activité et département.

## 📋 Table des matières

- [Vue d'ensemble](#vue-densemble)
- [Fonctionnalités](#fonctionnalités)
- [Prérequis](#prérequis)
- [Installation](#installation)
- [Configuration](#configuration)
- [Utilisation](#utilisation)
- [Workflow](#workflow)
- [Format des données](#format-des-données)
- [API utilisées](#api-utilisées)
- [Troubleshooting](#troubleshooting)
- [Contribution](#contribution)

## 🎯 Vue d'ensemble

Ce projet automatise la vérification et la découverte de marques appartenant à des holdings/groupes industriels. Il combine trois étapes de traitement :

1. **Vérification initiale** : Validation des marques existantes via Perplexica
2. **Découverte** : Identification de nouvelles marques manquantes avec secteur/département
3. **Validation finale** : Vérification complète via l'API Perplexity avec scoring de confiance

## ✨ Fonctionnalités

- 🔍 **Vérification automatique** des marques existantes
- 🆕 **Découverte de nouvelles marques** pour chaque holding
- 🏭 **Classification automatique** par secteur d'activité et département
- 🎯 **Scoring de confiance** de 0 à 1 pour chaque marque
- 🚫 **Détection de doublons** intelligente (gestion des accents, espaces, casse)
- 📊 **Export CSV** avec toutes les métadonnées
- 🕒 **Horodatage** des ajouts
- ⚠️ **Marquage** des marques nécessitant une vérification manuelle

## 🔧 Prérequis

- **Python 3.8+**
- **Docker** et **Docker Compose**
- **Clé API Perplexity** (pour la vérification finale)
- **Accès internet** pour les API

## 🚀 Installation

### 1. Cloner le repository

```bash
git clone https://github.com/votre-username/brand-holdings-verification.git
cd brand-holdings-verification/Complexity
```

### 2. Démarrer Perplexica

Perplexica doit être lancé en premier pour fournir l'API locale de recherche.

```bash
cd Perplexica
docker compose up -d
```

> ⚠️ **Important** : Attendez que tous les services Perplexica soient opérationnels avant de continuer. Vérifiez avec `docker ps` que les conteneurs sont en statut "healthy".

### 3. Installer les dépendances Python

Retournez dans le dossier principal et installez les requirements :

```bash
cd ..
pip install -r requirements.txt
```

## ⚙️ Configuration

### 1. Préparer vos données

Placez votre fichier CSV d'entrée nommé `Holding.csv` dans le dossier `Complexity/`. Le fichier doit contenir au minimum les colonnes :

- `Main Holding Name` : Nom du holding/groupe
- `Brand Name` : Nom de la marque

### 2. Configurer la clé API Perplexity

Éditez le fichier `main_updated_clean.py` et remplacez la clé API :

```python
PERPLEXITY_API_KEY = "votre-clé-api-perplexity"
```

## 🎮 Utilisation

### Lancement du script principal

```bash
python main_updated_clean.py
```

### Workflow d'exécution

Le script suit automatiquement ces étapes :

#### **ÉTAPE 1 : Vérification des marques existantes**
- Utilise Perplexica pour vérifier chaque marque
- Met à jour la colonne `Statut d'Appartenance verifié`
- Score ≥ 0.7 → "OK", Score < 0.7 → "NON"

#### **ÉTAPE 2 : Découverte de nouvelles marques**
- Recherche toutes les marques du holding via Perplexica
- Filtre les marques déjà présentes (détection de doublons)
- Classifie chaque nouvelle marque par secteur/département
- Ajoute les métadonnées : date, secteur, département

#### **ÉTAPE 3 : Validation finale avec Perplexity**
- Vérifie TOUTES les marques (existantes + nouvelles) via l'API Perplexity
- Ajoute la colonne `À VÉRIFIER`
- Score < 0.7 → "OUI" (nécessite vérification manuelle)
- Score ≥ 0.7 → "NON" (validé automatiquement)

## 📊 Format des données

### Fichier d'entrée (`Holding.csv`)

```csv
Main Holding Name,Brand Name
Unilever,Dove
Unilever,Knorr
Nestlé,Nescafé
...
```

### Fichier de sortie (`results_verified.csv`)

Le fichier généré contient toutes les colonnes originales plus :

| Colonne | Description | Valeurs possibles |
|---------|-------------|-------------------|
| `Statut d'Appartenance verifié` | Résultat vérification initiale | "OK", "NON", "À vérifier" |
| `Date d'ajout` | Date d'ajout (nouvelles marques) | YYYY-MM-DD ou vide |
| `Secteur d'activité` | Secteur de la marque | FMCG, Technology, etc. |
| `Département` | Département spécifique | Liquides, Electronics, etc. |
| `À VÉRIFIER` | Validation finale Perplexity | "OUI", "NON" |

## 🔌 API utilisées

### **Perplexica (Local)**
- **URL** : `http://localhost:3000/api/search`
- **Usage** : Vérification initiale et découverte de marques
- **Modèle** : GPT-4o-mini via OpenAI

### **Perplexity AI (Cloud)**
- **URL** : `https://api.perplexity.ai/chat/completions`
- **Usage** : Validation finale avec scoring
- **Modèle** : Sonar

## 🐛 Troubleshooting

### Perplexica ne répond pas
```bash
# Vérifier le statut des conteneurs
docker ps

# Redémarrer si nécessaire
cd Perplexica
docker compose down
docker compose up -d
```

### Erreur de clé API Perplexity
- Vérifiez que votre clé API est valide
- Contrôlez vos quotas sur le dashboard Perplexity

### Problèmes de doublons
Le système gère automatiquement :
- Les variations de casse (`NUII` vs `nuii`)
- Les accents (`café` vs `cafe`)
- Les espaces (`Air France` vs `AirFrance`)

### Fichier CSV corrompu
- Vérifiez l'encodage (UTF-8 recommandé)
- Assurez-vous que les colonnes requises sont présentes

## 📈 Statistiques d'exécution

À la fin de l'exécution, le script affiche :

```
[DEBUG] Total des marques dans le fichier: 1250
[DEBUG] 45 nouvelles marques ont été ajoutées avec leurs secteurs d'activité et départements
[DEBUG] 12 marques nécessitent une vérification manuelle
[DEBUG] 1238 marques ont été validées automatiquement
```

## 🤝 Contribution

1. Fork le projet
2. Créez votre branche (`git checkout -b feature/amazing-feature`)
3. Committez vos changements (`git commit -m 'Add amazing feature'`)
4. Push vers la branche (`git push origin feature/amazing-feature`)
5. Ouvrez une Pull Request

## 📝 Licence

Ce projet est sous licence MIT. Voir le fichier `LICENSE` pour plus de détails.

## 🆘 Support

Pour toute question ou problème :
- Ouvrez une [issue](https://github.com/votre-username/brand-holdings-verification/issues)
- Consultez la documentation des API utilisées
- Vérifiez les logs de debug dans la console

---

**Développé avec ❤️ pour automatiser la vérification des marques et holdings**
