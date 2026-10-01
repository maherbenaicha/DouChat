# Runbook de gestion des incidents — Équipe technique

## Niveaux de sévérité
- SEV1 : service indisponible pour tous les utilisateurs. Temps de réponse attendu : 15 minutes.
- SEV2 : fonctionnalité majeure dégradée. Temps de réponse attendu : 1 heure.
- SEV3 : problème mineur sans impact client. Traitement sous 2 jours ouvrés.

## Astreinte
L'astreinte est assurée par roulement hebdomadaire entre les ingénieurs backend. La personne d'astreinte doit être joignable 24h/24.

## Procédure
1. Accuser réception de l'alerte dans l'outil d'alerting.
2. Ouvrir un canal d'incident dédié.
3. Identifier et appliquer une mesure de contournement.
4. Rédiger un post-mortem sans reproche sous 5 jours ouvrés.
