# Impact des athlètes de haut niveau et des performances françaises sur les licences sportives

Projet de fin de semestre réalisé dans le cadre du cours *Python pour la data science* (2e année, ENSAE Paris).

## Problématique

Les grands succès sportifs français, qu'il s'agisse des Jeux Olympiques de Paris 2024 ou d'un titre collectif comme la Coupe du Monde 2018, provoquent-ils vraiment une hausse durable des inscriptions en club ?

Plutôt que de s'arrêter à un simple comptage de médailles, ce projet cherche à comprendre les mécanismes concrets qui transforment l'attention médiatique en nouvelles licences : proximité géographique avec un champion ("héros local"), identification par l'âge ou le genre, effet de nouveauté face à une figure déjà installée, contraintes matérielles ou d'infrastructures, et rôle des aides financières pour les publics modestes.

## Sources de données

L'analyse croise quatre jeux de données publics collectés par API ou téléchargement direct :

- **Recensement des licences sportives (INJEP / data.sports.gouv.fr et data.gouv.fr)** : base départementale 2016-2023 enrichie du millésime 2025, et série historique nationale 2002-2025 (`lics_histo`).
- **Athlètes des JO de Paris 2024 (data.gouv.fr)** : résultats individuels et par discipline de la délégation française (`athletes_paris_2024`).
- **API Wikimedia (Pageviews)** : volume mensuel (2023-2025) et journalier (été 2024) des consultations Wikipédia de plusieurs athlètes français comme indicateur d'attention médiatique.
- **Pass'Sport (data.gouv.fr)** : activations annuelles par département, fédération et genre sur les campagnes 2022 à 2024.
