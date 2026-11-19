# LunarNX FR+ (branche \`lunarnx-fr-plus\`)

Version expérimentale de LunarNX pour Switch modifiée, basée sur la traduction française précédente. Le client PlayStation/chiaki-ng et le chemin Xbox sont conservés ; les modifications sont limitées à l'interface et à la configuration de départ des flux PS.

## Fonctions ajoutées

1. **Qualité réseau auto (au démarrage)** : profil 720p/12 Mb/s sur réseau local ou 720p/8 Mb/s via PSN. Ce n'est **pas** un débit adaptatif pendant le jeu ; changer de profil exige une nouvelle session.
2. **Alimentation PS5** : bouton dans le menu tactile du streaming qui envoie la touche PS et indique comment choisir « Alimentation > Mode repos » sur la PS5. Le réveil depuis le mode repos utilise la fonction déjà incluse dans LunarNX. **Aucune mise en repos instantanée ou extinction forcée n'a été ajoutée.**
3. **Économie de batterie** : limite le nouveau flux PS à 720p/6 Mb/s et désactive les vibrations. C'est une approche légère de réduction de charge, **sans gain d'autonomie mesuré** et sans changement automatique de luminosité/fréquence CPU.
4. **Statistiques en direct** : case à cocher pour afficher le bandeau d'informations réseau/FPS dès le lancement d'un flux PS (LunarNX possède déjà ces statistiques). Leur affichage reste pilotable avec le menu tactile.
5. **Thèmes personnalisables** : accent menthe/bleu PS/violet/rouge. Le choix est enregistré ; **redémarrer LunarNX** pour l'appliquer.
6. **Reconnexion simplifiée** : bouton « Reconnexion PS5 rapide » dans l'accueil PlayStation ; il réutilise la dernière console et la route mémorisées, relance la découverte au besoin. Il ne reconnecte jamais automatiquement en boucle après une erreur et ne contourne aucune connexion PSN ni vérification de compte.

## Réglages

Menu PlayStation > Paramètres > section « LunarNX FR+ ». Une option désactivée garde le comportement d'origine.

**Limites** : les fonctions doivent encore être vérifiées sur une vraie Switch Lite et PS5 ; un build CI réussi démontre uniquement la compilation. Les composants Remote Play existants restent les seules voies de lecture, sans cloud streaming PS5 local ou mode repos actif.

## Sources et licences

Source upstream : https://github.com/thinkzhou/LunarNX
Ce dépôt conserve les notices de tiers et les licences du code PlayStation chiaki-ng (AGPL-3.0). Pour redistribuer le NRO combiné, publier le code source correspondant, y compris les patchs locaux et dépendances applicables.

Fichier source principal des changements : \`lunarnx_fr_payload/apply_features.py\` et patch français préexistant \`lunarnx_fr_payload/01.txt\` à \`08.txt\`.
