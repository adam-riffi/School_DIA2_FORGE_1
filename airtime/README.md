# AIRTIME — Optimisation de Grilles TV/Radio

Projet L2 Informatique — Programmation Logique et par Contraintes

## Objectif

Générer une grille de programmes sur **7 jours** (Lundi–Dimanche, 06h00–02h00) en **maximisant le profit** :

```
Profit = Recettes publicitaires – Coûts de diffusion
```

## Structure

```
airtime/
├── data/
│   └── programs.json          # Catalogue de 200 programmes
├── src/
│   ├── models.py              # Dataclasses : Program, Schedule, ScheduledItem
│   ├── loader.py              # Chargement + correction d'encodage JSON
│   ├── audience.py            # Modèle d'audience (tranche × jour × héritage)
│   ├── revenue.py             # Recettes pub (CPM × écrans × audience)
│   ├── constraints.py         # Validation des contraintes de diffusion
│   ├── optimizer.py           # Greedy + recherche locale (swaps)
│   ├── evaluator.py           # Métriques (profit, ROI, audience, ...)
│   └── visualizer.py          # Affichage terminal + export JSON
├── tests/
│   └── test_models.py         # 18+ tests unitaires (pytest)
├── results/                   # Grilles et métriques générées
├── main.py                    # Point d'entrée
├── requirements.txt
└── README.md
```

## Installation

```bash
pip install -r requirements.txt
```

## Utilisation

```bash
# Génération complète (greedy + optimisation locale)
python main.py

# Afficher uniquement le Lundi
python main.py --day Lundi

# Mode rapide (greedy seul, sans recherche locale)
python main.py --no-local-search
```

## Tests

```bash
pytest tests/ -v
```

## Modèle d'optimisation

### Tranches horaires

| Tranche         | Horaire       | Coeff audience | CPM (€) |
|-----------------|---------------|----------------|---------|
| Matin           | 06:00–09:00   | 0.6            | 7       |
| Matinée         | 09:00–12:00   | 0.4            | 5       |
| Midi            | 12:00–14:00   | 0.9            | 9       |
| Après-midi      | 14:00–18:00   | 0.5            | 6       |
| Access Prime    | 18:00–20:00   | 1.1            | 11      |
| Prime Time      | 20:00–22:30   | 1.3            | 15      |
| Deuxième partie | 22:30–00:30   | 0.8            | 10      |
| Nuit            | 00:30–02:00   | 0.3            | 4       |

### Formule d'audience

```
Audience_réelle = base × coeff_tranche × coeff_héritage × coeff_jour [× bonus_preferred]
```

### Recette publicitaire

```
Recette = (Audience / 1000) × CPM × nb_écrans
nb_écrans = (durée_min // 30) × 3
```

### Algorithme

1. **Greedy** : pour chaque créneau de chaque jour, sélection du programme maximisant le profit, sous contraintes.
2. **Recherche locale** : 500 tentatives de swaps aléatoires entre programmes ; un swap est accepté s'il améliore le profit total.

### Contraintes vérifiées

- Créneau interdit pour le programme (`forbidden_slots`)
- Délai minimum entre deux diffusions (`min_rerun_days`)
- Un programme diffusé au plus une fois par semaine
- Max épisodes par semaine pour les séries (`max_episodes_per_week`)
- Le programme doit tenir dans la durée restante du créneau
- Jours fixes respectés (`fixed_days`)
