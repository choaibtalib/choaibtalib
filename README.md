# Bot de Protection LINE

Ce bot a été développé pour aider à gérer et protéger les groupes LINE. Il offre plusieurs fonctionnalités de protection et de suivi des membres.

## Fonctionnalités

- Suivi des utilisateurs connectés au groupe
- Commande `.r` pour afficher qui a lu le dernier message
- Protection du propriétaire du groupe contre l'expulsion
- Gestion des membres qui enfreignent les règles du groupe

## Commandes disponibles

- `.r` - Afficher les lecteurs du dernier message
- `.setowner` - Définir l'utilisateur actuel comme propriétaire (admin uniquement)
- `.help` - Afficher le message d'aide

## Configuration

Le bot utilise les variables d'environnement suivantes:

- `CHANNEL_ACCESS_TOKEN` - Token d'accès pour l'API LINE
- `CHANNEL_SECRET` - Secret du canal LINE
- `USER_ID` - ID de l'utilisateur administrateur
- `WEBHOOK_URL` - URL du webhook pour les callbacks LINE

## Déploiement

Ce bot est conçu pour être déployé sur Render. Assurez-vous de configurer les variables d'environnement dans les paramètres de votre service Render.

## Développement local

Pour exécuter le bot localement:

```bash
python app.py
```

Le serveur démarrera sur le port 5000 par défaut.
