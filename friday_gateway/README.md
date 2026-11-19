# FRIDAY pour LunarNX FR+ — pilote

Cette version garde l'interface principale de LunarNX et ses moteurs Remote Play inchangés. Seules des lignes ont été ajoutées à la section de paramètres LunarNX FR+.

## Fonctionnement immédiat hors ligne
- Option « FRIDAY anti-lag » : détecte les pertes de paquets PS5 supérieures à 3,5 % ou un RTT supérieur à 140 ms sur plusieurs mesures consécutives. Affiche un conseil au maximum une fois par 90 secondes. Elle ne modifie PAS le flux vidéo en direct.
- « FRIDAY Chat » : conseils locaux préprogrammés sur Wi-Fi, lag, FPS, image, PS5, autonomie. **Ce mode local n'est pas une IA générative.**

## Activer la véritable IA (facultatif)
Une passerelle Python sert d'intermédiaire entre la Switch et l'API d'un modèle IA. **Ne mets jamais la clé OpenAI sur la Switch, ni dans le code GitHub.**

1. Sur une machine ou un hébergement serveur ayant Python 3, installer le module OpenAI : pip install openai.
2. Définir les variables d'environnement :
   - OPENAI_API_KEY : clé privée API OpenAI, conservée uniquement sur le serveur.
   - FRIDAY_SHARED_TOKEN : un secret aléatoire de 16 caractères minimum (générateur Python : import secrets; print(secrets.token_urlsafe(24))).
   - FRIDAY_MODEL : modèle textuel accessible avec le compte API ; la valeur par défaut du script est gpt-4.1-mini.
3. Lancer : python3 server.py. Le serveur écoute **uniquement localhost:8765**, par sécurité.
4. Publier le point d'accès /ask au travers d'un reverse proxy HTTPS avec un certificat TLS valide et un nom de domaine que tu contrôles. Le port HTTP local ne doit **pas** être exposé directement. Exemple : un proxy Caddy pourrait acheminer https://ton-domaine.fr/ask vers 127.0.0.1:8765 (le domaine est illustratif et non disponible).
5. Dans LunarNX, PlayStation > Paramètres > LunarNX FR+ :
   - « Serveur FRIDAY (HTTPS) » : adresse complète https://ton-domaine.fr/ask.
   - « Code FRIDAY » : FRIDAY_SHARED_TOKEN. **Jamais la clé OpenAI.**
   - Refermer les paramètres pour enregistrer, puis ouvrir FRIDAY Chat.

Aucun serveur ou compte IA n'est fourni automatiquement. La connexion HTTPS dépend aussi de la compatibilité TLS/certificats de la Switch : **à tester sur matériel réel**. La consommation de l'API peut entraîner une facturation indépendante d'un éventuel abonnement ChatGPT.

## Confidentialité et robustesse
- Question envoyée au serveur uniquement après validation explicite de l'utilisateur. Pas de capture d'écran, vidéo, identifiants PSN ni données du compte.
- TLS avec vérification de certificat, aucune redirection, délais réseau limités.
- Le code d'accès de la **passerelle** est sauvegardé dans la configuration locale de LunarNX. Ne pas partager le dossier de configuration de la Switch.
- Le serveur impose le secret partagé, des limites de taille et de fréquence ; ne journalise pas les questions et passe l'option store=False.
- L'IA ou le serveur peuvent tomber en panne **sans interrompre le Remote Play**.
- Les fonctions FRIDAY Voice, Vision et adaptation réelle du débit pendant la session ne sont **pas** implémentées dans cette phase.

## Code source et licence
Le workflow GitHub applique la traduction française, les six fonctions FR+, puis le correctif FRIDAY, avant compilation. Les correctifs, ce serveur et les notices du projet original sont publiés avec l'artefact. Les obligations de licence AGPL-3.0 de chiaki-ng restent applicables. La réussite de GitHub Actions ne garantit pas le fonctionnement sur Switch Lite et PS5.
