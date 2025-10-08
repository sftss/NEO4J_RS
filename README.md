# Étude de cas sur les réseaux sociaux - Neo4j

Ce projet propose une étude de cas sur la modélisation et l’analyse de réseaux sociaux à l’aide de Neo4j, une base de données orientée graphes. L’objectif est de comprendre les interactions entre utilisateurs, de détecter des communautés et d’extraire des informations pertinentes à partir des relations.

## Fonctionnalités principales

- Modélisation des utilisateurs et de leurs relations (amis, abonnements, etc.)
- Importation et visualisation des données dans Neo4j
- Requêtes Cypher pour l’analyse des réseaux (centralité, communautés, etc.)

## Prérequis

- Python 3.10+
- Un environnement virtuel Python

## Installation

1. Clonez le dépôt :
    ```bash
    git clone <url-du-repo>
    cd NEO4J_RS
    ```
2. Créez et activez l’environnement virtuel :
    ```bash
    python -m venv .venv
    source .venv/bin/activate
    ```
3. Installez les dépendances :
    ```bash
    pip install -r requirements.txt
    ```

## Utilisation

1. Lancez Neo4j et créez une base de données.
2. Importez les données du projet dans Neo4j.
3. Exécutez les scripts Python pour interagir avec la base et effectuer des analyses.

## Structure du projet

- `data/` : jeux de données d’exemple
- `generator.py` et `import.py` : scripts Python pour l’import et la génération de données
- `modele.cypher` : scripts Cypher pour la création du modèle de graphe Neo4j
- `README.md` : documentation du projet

## Ressources

- [Documentation Neo4j](https://neo4j.com/docs/)
- [Cypher Query Language](https://neo4j.com/developer/cypher/)

## Auteurs
- [Valenper](https://github.com/Valenper)
- [Sefer](https://github.com/sftss)
- [feyy7435](https://github.com/feyy7435)
