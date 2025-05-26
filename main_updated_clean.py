import requests
import json
import pandas as pd
from collections import defaultdict
from datetime import datetime
import re
import unicodedata

PERPLEXICA_API_URL = "http://localhost:3000/api/search"
PERPLEXITY_API_KEY = "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"
PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"

def normalize_brand_name(brand_name):
    """Normalise un nom de marque en retirant les espaces, majuscules et accents pour la comparaison"""
    if pd.isna(brand_name) or brand_name == '':
        return ''
    
    # Convertir en string au cas où
    brand_name = str(brand_name)
    
    # Supprimer les accents
    brand_name = unicodedata.normalize('NFD', brand_name)
    brand_name = ''.join(c for c in brand_name if unicodedata.category(c) != 'Mn')
    
    # Convertir en minuscules et supprimer les espaces et caractères spéciaux
    brand_name = re.sub(r'[^a-zA-Z0-9]', '', brand_name.lower())
    
    return brand_name

def read_holdings_csv(file_path):
    print(f"\n[DEBUG] Lecture du fichier CSV: {file_path}")
    # Lire le CSV
    df = pd.read_csv(file_path)
    print(f"[DEBUG] Nombre de lignes lues: {len(df)}")
    
    # Ajouter les nouvelles colonnes si elles n'existent pas
    if 'Statut d\'Appartenance verifié' not in df.columns:
        df['Statut d\'Appartenance verifié'] = ''
    if 'Date d\'ajout' not in df.columns:
        df['Date d\'ajout'] = ''
    if 'Secteur d\'activité' not in df.columns:
        df['Secteur d\'activité'] = ''
    if 'Département' not in df.columns:
        df['Département'] = ''
    
    # Créer un dictionnaire pour regrouper les marques par holding
    holdings_dict = defaultdict(list)
    
    # Pour chaque ligne, ajouter la marque au holding correspondant
    for _, row in df.iterrows():
        holding_name = row['Main Holding Name']
        brand_name = row['Brand Name']
        if brand_name not in holdings_dict[holding_name]:
            holdings_dict[holding_name].append(brand_name)
    
    print(f"[DEBUG] Nombre de holdings trouvés: {len(holdings_dict)}")
    return df, dict(holdings_dict)

def get_marques_from_perplexity(groupe, marques):
    print(f"\n[DEBUG] Préparation de la requête pour le groupe: {groupe}")
    
    headers = {
        "Content-Type": "application/json"
    }
    
    # Construire le prompt pour l'API
    query = f"""Pour le groupe {groupe}, vérifie si les marques suivantes lui appartiennent bien : {', '.join(marques)}."""
    
    data = {
        "chatModel": {
            "provider": "openai",
            "name": "gpt-4o-mini"
        },
        "embeddingModel": {
            "provider": "openai",
            "name": "text-embedding-3-large"
        },
        "optimizationMode": "balanced",
        "focusMode": "webSearch",
        "query": query,
        "systemInstructions": """Tu es un expert en vérification de l'appartenance des marques commerciales à des groupes industriels ou financiers en FRANCE.

Ta mission est d'indiquer pour chaque marque si elle appartient actuellement au groupe spécifié.

Tu dois utiliser uniquement des sources officielles ou institutionnelles vérifiables (rapports annuels, sites corporate, publications légales, registres publics).

Ne tiens compte d'aucune source collaborative ou non vérifiée comme Wikipédia, forums, ou annuaires ouverts.

Pour chaque marque, retourne **une seule ligne** au format suivant :
nom_de_la_marque:score_de_certitude

Le score est un nombre entre **0** (aucune information fiable) et **1** (preuve officielle confirmée), par pas de 0.1 si nécessaire.

Exemples :
- 1 : présence explicite et actuelle dans les publications officielles du groupe
- 0.7 : source indirecte, mais fiable (filiale mentionnée, référence croisée)
- 0.3 : mention peu claire ou douteuse dans une source secondaire (PDF ancien, lien indirect)
- 0 : aucune trace fiable

Si aucune donnée pertinente n'est trouvée, indique `NaN`.

N'ajoute aucun texte, commentaire ou explication.

Respecte exactement l'ordre des marques. Ne modifie ni les noms, ni le format de sortie.""",
        "stream": False
    }
    
    print(f"[DEBUG] Structure de la requête:")
    print(f"[DEBUG] Headers: {headers}")
    print(f"[DEBUG] Data: {json.dumps(data, indent=2)}")
    
    print(f"[DEBUG] Envoi de la requête à l'API Perplexica...")
    try:
        response = requests.post(PERPLEXICA_API_URL, headers=headers, json=data)
        response.raise_for_status()
        print(f"[DEBUG] Réponse reçue avec succès (status code: {response.status_code})")
        response_data = response.json()
        print(f"[DEBUG] Contenu de la réponse: {json.dumps(response_data, indent=2)}")
        
        # Extraire le message de la réponse
        if 'message' in response_data:
            return {"choices": [{"message": {"content": response_data['message']}}]}
        else:
            print(f"[DEBUG] Format de réponse inattendu: {response_data}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"[DEBUG] Erreur lors de l'appel à l'API Perplexica: {e}")
        return None


def get_new_brand_for_holding(holding):
    print(f"\n[DEBUG] Recherche de nouvelles marques pour le holding: {holding}")
    
    headers = {
        "Content-Type": "application/json"
    }
    
    # Construire le prompt pour l'API
    query = f"""Pour le groupe {holding}, liste absolument TOUTES les marques qui lui appartiennent actuellement avec leur secteur d'activité et département."""
    
    data = {
        "chatModel": {
            "provider": "openai",
            "name": "gpt-4o-mini"
        },
        "embeddingModel": {
            "provider": "openai",
            "name": "text-embedding-3-large"
        },
        "optimizationMode": "balanced",
        "focusMode": "webSearch",
        "query": query,
        "systemInstructions": """Tu es un expert en identification et vérification de la structure de marques détenues par des groupes industriels ou financiers.

Ta tâche est de retrouver TOUTES les marques appartenant à un groupe (holding) donné, avec leur secteur d'activité et département.

Pour chaque marque que tu identifies, retourne une seule ligne au format :
nom_de_la_marque:score_de_certitude:secteur:département

Le score de certitude est un nombre compris entre **0** (aucune certitude) et **1** (certitude absolue, confirmée par source officielle).

Les secteurs d'activité peuvent être : FMCG, Technology, Automotive, Fashion, Finance, Energy, Healthcare, etc.
Les départements peuvent être : Liquides, Alimentaire, Electronics, Clothing, Banking, etc.

Exemples de format de réponse :
- Seven Up:0.9:FMCG:Liquides

Critères :
- Score **1** : la marque figure explicitement sur le site officiel du groupe ou dans ses documents financiers récents.
- Score **0.9** : la marque est mentionnée dans une source fiable proche du groupe.
- Score **0.7 ou moins** : la relation est probable mais non confirmée directement.
- Score **0.5 ou moins** : présence ancienne ou indirecte, doute raisonnable.

Règles :
- N'utilise que des **sources officielles, institutionnelles ou vérifiables** (rapports annuels, sites corporate, bases de données d'entreprises).
- Ignore Wikipédia, forums, réseaux sociaux, blogs, annuaires ouverts.
- Ne fais jamais de supposition implicite ou par similarité de nom.
- Ne modifie jamais les noms de marques.
- N'ajoute aucun commentaire, texte explicatif ou justification.
- Retourne uniquement une ligne par marque, strictement au format demandé.
- Trie les résultats par score décroissant (du plus fiable au moins sûr).
- Si le secteur ou département est inconnu, utilise "Unknown".
""",
        "stream": False
    }
    
    print(f"[DEBUG] Envoi de la requête à l'API Perplexica...")
    try:
        response = requests.post(PERPLEXICA_API_URL, headers=headers, json=data)
        response.raise_for_status()
        print(f"[DEBUG] Réponse reçue avec succès (status code: {response.status_code})")
        response_data = response.json()
        print(f"[DEBUG] Contenu de la réponse: {json.dumps(response_data, indent=2)}")
        
        # Extraire le message de la réponse
        if 'message' in response_data:
            return {"choices": [{"message": {"content": response_data['message']}}]}
        else:
            print(f"[DEBUG] Format de réponse inattendu: {response_data}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"[DEBUG] Erreur lors de l'appel à l'API Perplexica: {e}")
        return None


def get_brand_sector_and_department(brand_name):
    """Récupère le secteur d'activité et le département d'une marque"""
    print(f"\n[DEBUG] Recherche du secteur et département pour la marque: {brand_name}")
    
    headers = {
        "Content-Type": "application/json"
    }
    
    # Construire le prompt pour l'API
    query = f"""Pour la marque {brand_name}, identifie son secteur d'activité et son département."""
    
    data = {
        "chatModel": {
            "provider": "openai",
            "name": "gpt-4o-mini"
        },
        "embeddingModel": {
            "provider": "openai",
            "name": "text-embedding-3-large"
        },
        "optimizationMode": "balanced",
        "focusMode": "webSearch",
        "query": query,
        "systemInstructions": """Tu es un expert en classification des marques commerciales par secteur d'activité et département.

Ta mission est d'identifier pour une marque donnée :
1. Son secteur d'activité principal (ex: FMCG, Technology, Automotive, Fashion, etc.)
2. Son département spécifique (ex: Liquides, Alimentaire, Electronics, Clothing, etc.)

Utilise uniquement des sources officielles et fiables pour cette classification.

Retourne le résultat au format exact suivant sur une seule ligne :
secteur:département

Exemples :
- Seven Up → FMCG:Liquides
- iPhone → Technology:Electronics
- Nike Air → Fashion:Footwear

Si les informations ne sont pas disponibles ou incertaines, retourne :
Unknown:Unknown

N'ajoute aucun texte, commentaire ou explication supplémentaire.""",
        "stream": False
    }
    
    print(f"[DEBUG] Envoi de la requête à l'API Perplexica...")
    try:
        response = requests.post(PERPLEXICA_API_URL, headers=headers, json=data)
        response.raise_for_status()
        print(f"[DEBUG] Réponse reçue avec succès (status code: {response.status_code})")
        response_data = response.json()
        
        # Extraire le message de la réponse
        if 'message' in response_data:
            content = response_data['message'].strip()
            if ':' in content:
                sector, department = content.split(':', 1)
                return sector.strip(), department.strip()
            else:
                return "Unknown", "Unknown"
        else:
            print(f"[DEBUG] Format de réponse inattendu: {response_data}")
            return "Unknown", "Unknown"
            
    except requests.exceptions.RequestException as e:
        print(f"[DEBUG] Erreur lors de l'appel à l'API Perplexica: {e}")
        return "Unknown", "Unknown"


def add_new_brands_to_dataframe(df, new_brands_data):
    """Ajoute les nouvelles marques au DataFrame avec leurs informations"""
    print(f"\n[DEBUG] Ajout de {len(new_brands_data)} nouvelles marques au DataFrame")
    
    # Ajouter les nouvelles colonnes si elles n'existent pas
    new_columns = ['Date d\'ajout', 'Secteur d\'activité', 'Département']
    for col in new_columns:
        if col not in df.columns:
            df[col] = ''
    
    # Obtenir la liste des marques existantes pour éviter les doublons
    existing_brands = set()
    existing_brand_names = set()  # Ajouter un set pour les noms de marques uniquement
    existing_brand_names_normalized = set()  # Ajouter un set pour les noms normalisés
    for _, row in df.iterrows():
        holding_name = row['Main Holding Name']
        brand_name = row['Brand Name']
        brand_name_normalized = normalize_brand_name(brand_name)
        
        existing_brands.add((holding_name, brand_name))
        existing_brand_names.add(brand_name)  # Ajouter le nom de la marque seul
        existing_brand_names_normalized.add(brand_name_normalized)  # Ajouter le nom normalisé
    
    # Créer une liste pour les nouvelles lignes
    new_rows = []
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    for holding, brands in new_brands_data.items():
        print(f"\n[DEBUG] Traitement des marques pour le holding: {holding}")
        
        for brand_data in brands:
            brand_name = brand_data['name']
            brand_name_normalized = normalize_brand_name(brand_name)
            confidence = brand_data['confidence']
            sector = brand_data['sector']
            department = brand_data['department']
            
            # Vérifier si la marque n'existe pas déjà (ni par combinaison holding+marque, ni par nom seul, ni par nom normalisé)
            if (holding, brand_name) not in existing_brands and brand_name not in existing_brand_names and brand_name_normalized not in existing_brand_names_normalized:
                print(f"[DEBUG] Ajout de la nouvelle marque: {brand_name} (confiance: {confidence})")
                
                # Créer une nouvelle ligne avec toutes les colonnes du DataFrame original
                new_row = {}
                for col in df.columns:
                    new_row[col] = ''
                
                # Remplir les informations de base
                new_row['Main Holding Name'] = holding
                new_row['Brand Name'] = brand_name
                new_row['Date d\'ajout'] = current_date
                new_row['Secteur d\'activité'] = sector
                new_row['Département'] = department
                new_row['Statut d\'Appartenance verifié'] = 'OK' if confidence >= 0.7 else 'À vérifier'
                
                new_rows.append(new_row)
                existing_brands.add((holding, brand_name))
                existing_brand_names.add(brand_name)  # Ajouter aussi à la liste des noms seuls
                existing_brand_names_normalized.add(brand_name_normalized)  # Ajouter aussi le nom normalisé
            else:
                print(f"[DEBUG] Marque déjà existante ignorée: {brand_name} (normalisé: {brand_name_normalized})")
    
    # Ajouter les nouvelles lignes au DataFrame
    if new_rows:
        new_df = pd.DataFrame(new_rows)
        df = pd.concat([df, new_df], ignore_index=True)
        print(f"[DEBUG] {len(new_rows)} nouvelles marques ajoutées au DataFrame")
    else:
        print(f"[DEBUG] Aucune nouvelle marque à ajouter")
    
    return df


def discover_and_add_new_brands(df, input_data):
    """Découvre et ajoute de nouvelles marques pour chaque holding"""
    print(f"\n[DEBUG] Découverte de nouvelles marques pour {len(input_data)} holdings")
    
    # Créer un set de toutes les marques existantes dans le DataFrame
    all_existing_brands = set()
    all_existing_brands_normalized = set()
    for _, row in df.iterrows():
        brand_name = row['Brand Name']
        brand_name_normalized = normalize_brand_name(brand_name)
        all_existing_brands.add(brand_name)
        all_existing_brands_normalized.add(brand_name_normalized)
    print(f"[DEBUG] Marques existantes dans le DataFrame: {len(all_existing_brands)}")
    
    new_brands_data = {}
    
    for holding, existing_brands in input_data.items():
        print(f"\n[DEBUG] Recherche de nouvelles marques pour le holding: {holding}")
        print(f"[DEBUG] Marques existantes: {existing_brands}")
        
        try:
            # Appeler l'API pour obtenir de nouvelles marques
            response = get_new_brand_for_holding(holding)
            
            if response and 'choices' in response and len(response['choices']) > 0:
                content = response['choices'][0]['message']['content']
                print(f"[DEBUG] Contenu de la réponse: {content}")
                
                holding_new_brands = []
                
                # Parser les résultats avec le nouveau format : nom:confidence:secteur:département
                for line in content.strip().split('\n'):
                    if ':' in line:
                        line = line.strip().lstrip('-').strip()
                        try:
                            parts = line.split(':')
                            if len(parts) >= 4:  # Format complet avec secteur et département
                                brand = parts[0].strip()
                                confidence = float(parts[1].strip())
                                sector = parts[2].strip()
                                department = parts[3].strip()
                            elif len(parts) >= 2:  # Format ancien avec seulement confidence
                                brand = parts[0].strip()
                                confidence = float(parts[1].strip())
                                sector, department = "Unknown", "Unknown"
                            else:
                                continue
                            
                            # Normaliser le nom de la marque pour la comparaison
                            brand_normalized = normalize_brand_name(brand)
                            
                            # Vérifier que la marque n'est pas déjà dans les marques existantes (du holding ET du DataFrame complet)
                            # Utiliser la comparaison normalisée
                            if (brand not in existing_brands and 
                                brand not in all_existing_brands and 
                                brand_normalized not in all_existing_brands_normalized and 
                                confidence >= 0.5):  # Seuil minimum de confiance
                                
                                print(f"[DEBUG] Nouvelle marque trouvée: {brand} (normalisé: {brand_normalized}, confiance: {confidence}, secteur: {sector}, département: {department})")
                                
                                # Si secteur/département non fournis, les rechercher séparément
                                if sector == "Unknown" or department == "Unknown":
                                    sector, department = get_brand_sector_and_department(brand)
                                
                                holding_new_brands.append({
                                    'name': brand,
                                    'confidence': confidence,
                                    'sector': sector,
                                    'department': department
                                })
                                all_existing_brands.add(brand)  # Ajouter à la liste pour éviter les doublons dans la même session
                                all_existing_brands_normalized.add(brand_normalized)  # Ajouter aussi le nom normalisé
                            else:
                                if brand in existing_brands:
                                    print(f"[DEBUG] Marque ignorée (existante dans le holding): {brand}")
                                elif brand in all_existing_brands:
                                    print(f"[DEBUG] Marque ignorée (existante dans le DataFrame): {brand}")
                                elif brand_normalized in all_existing_brands_normalized:
                                    print(f"[DEBUG] Marque ignorée (existante dans le DataFrame - comparaison normalisée): {brand} (normalisé: {brand_normalized})")
                                else:
                                    print(f"[DEBUG] Marque ignorée (confiance faible): {brand} (confiance: {confidence})")
                                
                        except (ValueError, IndexError) as e:
                            print(f"[DEBUG] Erreur de parsing pour la ligne: {line} - {e}")
                
                if holding_new_brands:
                    new_brands_data[holding] = holding_new_brands
                    print(f"[DEBUG] {len(holding_new_brands)} nouvelles marques trouvées pour {holding}")
                else:
                    print(f"[DEBUG] Aucune nouvelle marque trouvée pour {holding}")
            else:
                print(f"[DEBUG] Pas de réponse valide pour le holding {holding}")
                
        except Exception as e:
            print(f"[DEBUG] Erreur lors du traitement du holding {holding}: {e}")
    
    # Ajouter les nouvelles marques au DataFrame
    if new_brands_data:
        df = add_new_brands_to_dataframe(df, new_brands_data)
    
    return df

def process_results(df, results):
    print("\n[DEBUG] Début du traitement des résultats")
    
    for holding, response in results.items():
        print(f"\n[DEBUG] Traitement du holding: {holding}")
        if response is None:
            print(f"[DEBUG] Pas de résultats pour le holding {holding} (erreur API)")
            continue
            
        # Extraire les résultats de la réponse
        if 'choices' in response and len(response['choices']) > 0:
            content = response['choices'][0]['message']['content']
            print(f"[DEBUG] Contenu de la réponse: {content}")
            
            # Parser les résultats
            for line in content.strip().split('\n'):
                if ':' in line:
                    # Nettoyer la ligne en enlevant les tirets et les espaces
                    line = line.strip().lstrip('-').strip()
                    brand, certitude = line.split(':')
                    brand = brand.strip()
                    try:
                        certitude = float(certitude.strip())
                        print(f"[DEBUG] Traitement de la marque {brand} avec certitude {certitude}")
                        
                        # Mettre à jour le statut dans le DataFrame
                        mask = (df['Main Holding Name'] == holding) & (df['Brand Name'] == brand)
                        if certitude >= 0.7:  # Seuil de certitude à 0.7 (70%)
                            df.loc[mask, 'Statut d\'Appartenance verifié'] = 'OK'
                        else:
                            df.loc[mask, 'Statut d\'Appartenance verifié'] = 'NON'
                    except ValueError:
                        print(f"[DEBUG] Erreur de parsing pour la certitude: {certitude}")
        else:
            print(f"[DEBUG] Format de réponse invalide pour le holding {holding}")
    
    return df

def verify_brands_with_perplexity(df):
    """Vérifie toutes les marques avec l'API Perplexity et ajoute la colonne À VÉRIFIER"""
    print(f"\n[DEBUG] ÉTAPE 3 : Vérification finale avec Perplexity de toutes les marques...")
    
    # Ajouter la colonne "À VÉRIFIER" si elle n'existe pas
    if 'À VÉRIFIER' not in df.columns:
        df['À VÉRIFIER'] = ''
    
    # Regrouper les marques par holding
    holdings_dict = defaultdict(list)
    for _, row in df.iterrows():
        holding_name = row['Main Holding Name']
        brand_name = row['Brand Name']
        holdings_dict[holding_name].append(brand_name)
    
    headers = {
        "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
        "Content-Type": "application/json"
    }
    
    for holding, marques in holdings_dict.items():
        print(f"\n[DEBUG] Vérification Perplexity pour le holding: {holding}")
        print(f"[DEBUG] Marques à vérifier: {marques}")
        
        # Construire le prompt pour l'API Perplexity
        query = f"""Pour le groupe {holding}, vérifie si les marques suivantes lui appartiennent bien actuellement : {', '.join(marques)}.
        
Pour chaque marque, retourne **une seule ligne** au format suivant :
nom_de_la_marque:score_de_certitude

Le score est un nombre entre **0** (aucune information fiable) et **1** (preuve officielle confirmée).

Utilise uniquement des sources officielles ou institutionnelles vérifiables (rapports annuels, sites corporate, publications légales, registres publics).

N'ajoute aucun texte, commentaire ou explication. Respecte exactement l'ordre des marques."""
        
        data = {
            "model": "sonar",
            "messages": [
                {
                    "role": "system",
                    "content": "Tu es un expert en vérification de l'appartenance des marques commerciales à des groupes industriels ou financiers. Réponds uniquement au format demandé."
                },
                {
                    "role": "user",
                    "content": query
                }
            ]
        }
        
        try:
            print(f"[DEBUG] Envoi de la requête à l'API Perplexity...")
            response = requests.post(PERPLEXITY_API_URL, headers=headers, json=data)
            response.raise_for_status()
            print(f"[DEBUG] Réponse reçue avec succès (status code: {response.status_code})")
            
            response_data = response.json()
            if 'choices' in response_data and len(response_data['choices']) > 0:
                content = response_data['choices'][0]['message']['content']
                print(f"[DEBUG] Contenu de la réponse: {content}")
                
                # Parser les résultats
                for line in content.strip().split('\n'):
                    if ':' in line:
                        # Nettoyer la ligne
                        line = line.strip().lstrip('-').strip()
                        try:
                            brand, certitude = line.split(':', 1)
                            brand = brand.strip()
                            certitude = float(certitude.strip())
                            
                            print(f"[DEBUG] Traitement de la marque {brand} avec certitude {certitude}")
                            
                            # Mettre à jour la colonne "À VÉRIFIER" dans le DataFrame
                            mask = (df['Main Holding Name'] == holding) & (df['Brand Name'] == brand)
                            if certitude < 0.7:  # Score inférieur à 0.7
                                df.loc[mask, 'À VÉRIFIER'] = 'OUI'
                                print(f"[DEBUG] Marque {brand} marquée pour vérification (score: {certitude})")
                            else:  # Score supérieur ou égal à 0.7
                                df.loc[mask, 'À VÉRIFIER'] = 'NON'
                                print(f"[DEBUG] Marque {brand} validée (score: {certitude})")
                                
                        except (ValueError, IndexError) as e:
                            print(f"[DEBUG] Erreur de parsing pour la ligne: {line} - {e}")
            else:
                print(f"[DEBUG] Format de réponse invalide pour le holding {holding}")
                
        except requests.exceptions.RequestException as e:
            print(f"[DEBUG] Erreur lors de l'appel à l'API Perplexity: {e}")
        
        # Petit délai entre les requêtes pour éviter le rate limiting
        import time
        time.sleep(2)
    
    return df

def main():
    print("\n[DEBUG] Démarrage du programme")
    # Lire le fichier CSV
    df, input_data = read_holdings_csv("Holding.csv")
    
    # ÉTAPE 1 : Vérification de l'appartenance des marques existantes
    print("\n[DEBUG] ÉTAPE 1 : Vérification des marques existantes...")
    results = {}
    for holding, marques in input_data.items():
        try:
            print(f"\n[DEBUG] Vérification des marques pour le holding: {holding}")
            marques_json = get_marques_from_perplexity(holding, marques)
            results[holding] = marques_json
        except Exception as e:
            print(f"[DEBUG] Erreur pour le holding {holding}: {e}")

    # Traiter les résultats et mettre à jour le DataFrame
    df = process_results(df, results)
      # ÉTAPE 2 : Découverte et ajout de nouvelles marques manquantes
    print("\n[DEBUG] ÉTAPE 2 : Découverte de nouvelles marques manquantes...")
    df = discover_and_add_new_brands(df, input_data)

    # ÉTAPE 3 : Vérification finale avec Perplexity
    print("\n[DEBUG] ÉTAPE 3 : Vérification finale avec Perplexity...")
    df = verify_brands_with_perplexity(df)

    # Sauvegarder les résultats dans un fichier CSV
    print("\n[DEBUG] Sauvegarde des résultats dans results_verified.csv")
    df.to_csv("results_verified.csv", index=False)
    print("\n[DEBUG] Traitement terminé. Les résultats ont été sauvegardés dans results_verified.csv")
    print(f"[DEBUG] Total des marques dans le fichier: {len(df)}")
    
    # Afficher un résumé des nouvelles marques ajoutées
    new_brands_count = len(df[df['Date d\'ajout'] != ''])
    if new_brands_count > 0:
        print(f"[DEBUG] {new_brands_count} nouvelles marques ont été ajoutées avec leurs secteurs d'activité et départements")
    else:
        print("[DEBUG] Aucune nouvelle marque n'a été ajoutée")
    
    # Afficher un résumé des marques à vérifier
    brands_to_verify = len(df[df['À VÉRIFIER'] == 'OUI'])
    brands_verified = len(df[df['À VÉRIFIER'] == 'NON'])
    print(f"[DEBUG] {brands_to_verify} marques nécessitent une vérification manuelle")
    print(f"[DEBUG] {brands_verified} marques ont été validées automatiquement")

    # ÉTAPE 3 : Vérification finale avec Perplexity
    df = verify_brands_with_perplexity(df)

    # Sauvegarder les résultats finaux dans un nouveau fichier CSV
    print("\n[DEBUG] Sauvegarde des résultats finaux dans results_final_verification.csv")
    df.to_csv("results_final_verification.csv", index=False)
    
    print("[DEBUG] Fin du traitement. Les résultats finaux ont été sauvegardés dans results_final_verification.csv")

if __name__ == "__main__":
    main()
