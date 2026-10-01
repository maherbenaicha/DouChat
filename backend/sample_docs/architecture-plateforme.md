# Architecture de la plateforme — Équipe technique

## Vue d'ensemble
La plateforme interne repose sur une architecture microservices déployée sur Kubernetes. Chaque service expose une API REST documentée avec OpenAPI.

## Base de données
Les services utilisent PostgreSQL 16. Les sauvegardes complètes sont réalisées chaque nuit à 2h00 et conservées 30 jours.

## Intégration et déploiement continus
Chaque merge request déclenche un pipeline CI : lint, tests unitaires, tests d'intégration et construction des images Docker. Le déploiement en production est automatique après validation sur l'environnement de staging.

## Observabilité
Les métriques sont collectées avec Prometheus et visualisées dans Grafana. Les logs sont centralisés et conservés 14 jours.
