# Matrice de Classification SOX PG-01
## Préparation Réunion Islam - $(date '+%Y-%m-%d')

### 🎯 Objectif de la Réunion
**VALIDER et CLARIFIER** la logique de classification basée sur l'analyse des mémos et vidéos.
**Durée cible:** 45 minutes maximum

---

## 📋 Matrice de Classification (À compléter avec les mémos)

| Catégorie | Sous-catégorie | Logique d'Identification | Données Requises | Questions de Validation | Questions de Clarification |
|-----------|----------------|---------------------------|------------------|------------------------|---------------------------|
| **Bridge** | Timing Difference | `nav_posting_date` > fin mois ET `source_event_date` < fin mois | `nav_posting_date`, `source_event_date`, `cut_off_date` | ✅ "Cette règle s'applique-t-elle aussi aux transactions de fin d'année ?" | ❓ "Y a-t-il des exceptions à cette règle selon le type de transaction ?" |
| **Bridge** | Timing Difference (Technique) | Un bon de commande est identifié où `vouchers_df.order_month` est Septembre ET le `usage_df.delivery_month` ou `usage_df.cancellation_month` correspondant est Octobre. | `vouchers_df`, `usage_df`, `order_date`, `delivery_date`, `cancellation_date` | "Cette logique est-elle correcte ? Y a-t-il d'autres statuts finaux à considérer ?" |
| **Bridge** | Accruals | `Document Description` contient "ACCRUAL", "ACR", "PROVISION" | `Document Description`, `Source Code` | ✅ "Y a-t-il d'autres mots-clés spécifiques à rechercher ?" | ❓ "Comment distinguer un accrual légitime d'une erreur ?" |
| **Bridge** | Currency Revaluation | Écarts de change < seuil défini (ex: 1$) | `Currency Code`, `Amount`, `Amount_LCY`, montant en devise locale | ✅ "Le seuil de 1$ est-il fixe ou variable selon la devise ?" | ❓ "Pourquoi ce seuil spécifique ? Y a-t-il un contexte réglementaire ?" |
| **Adjustment** | Write-offs | Process spécifique de "write-off" + codes particuliers | `Reason Code`, `Source Code`, `Document Type` | ✅ "Quels sont les codes spécifiques qui identifient un write-off ?" | ❓ "Avez-vous un exemple récent de write-off et comment l'identifier ?" |
| **Adjustment** | Reclassifications | Transfert entre comptes GL sans impact P&L | `GL Account No`, `Bal Account No`, `Account Category` | ✅ "Comment différencier une reclassification d'un vrai mouvement ?" | ❓ "Y a-t-il des reclassifications qui nécessitent une validation manuelle ?" |
| **One-off** | System Errors | [À compléter d'après les mémos] | [À identifier] | ✅ "Comment identifier de manière systématique ces erreurs ?" | ❓ "Pouvez-vous partager un exemple récent d'erreur système ?" |
| **One-off** | Manual Corrections | [À compléter d'après les mémos] | [À identifier] | ✅ "Y a-t-il un processus standard pour ces corrections ?" | ❓ "Comment s'assurer qu'une correction manuelle est légitime ?" |

---

## 🔍 Points Spécifiques à Clarifier

### 1. Règles de Priorité
- **Question:** "Quand une transaction pourrait correspondre à plusieurs catégories, quelle est la logique de priorité ?"
- **Exemple:** Une transaction avec "ACCRUAL" dans la description mais qui a aussi une différence de timing

### 2. Seuils et Limites
- **Montants:** Y a-t-il des seuils en dessous desquels on ignore certaines différences ?
- **Pourcentages:** Existe-t-il des règles basées sur des % du total ?

### 3. Exceptions et Cas Particuliers
- **Fin d'année:** Les règles changent-elles en décembre/janvier ?
- **Devises:** Traitement spécial pour certaines devises ?
- **Entités:** Règles différentes selon les filiales ?

---

## 📈 Plan de Réunion (45 minutes)

### Introduction (5 min)
- "Islam, j'ai analysé les mémos et vidéos. Je voudrais valider ma compréhension avec vous."
- **Montrer la matrice à l'écran**

### Validation des Règles (25 min)
- Parcourir chaque ligne de la matrice
- **Technique:** "D'après le mémo X, j'ai compris que... Est-ce correct ?"
- Laisser Islam compléter/corriger

### Clarifications (10 min)
- Questions ouvertes sur les "pourquoi" et exemples concrets
- **Focus:** Cas limites et exceptions

### Synthèse et Prochaines Étapes (5 min)
- Récapituler les points validés et les ajustements
- Définir le plan pour l'implémentation

---

## 🎤 Scripts de Questions Préparées

### Questions de Validation (Fermées)
1. "D'après ce document, une différence de timing se produit quand nav_date > cutoff et source_date < cutoff. C'est bien ça ?"
2. "Pour les accruals, je dois chercher 'ACCRUAL' dans Document Description. Y a-t-il d'autres termes ?"
3. "Les écarts de change en dessous de 1$ sont ignorés selon ce mémo. Cette règle est-elle universelle ?"

### Questions de Clarification (Ouvertes)
1. "Pouvez-vous m'expliquer pourquoi cette règle des 1$ existe ? Y a-t-il un contexte réglementaire ?"
2. "Avez-vous un exemple récent d'une 'one-off difference' et comment vous l'avez identifiée ?"
3. "Comment gérez-vous les cas où une transaction pourrait être classée dans plusieurs catégories ?"

---

## 🔧 Notes Techniques pour l'Implémentation

### Structure de Données Cible
```python
classification_result = {
    'transaction_id': '12345',
    'category': 'Bridge',
    'subcategory': 'Timing Difference',
    'confidence_score': 0.95,
    'applied_rules': ['nav_date_check', 'source_date_check'],
    'explanation': 'NAV posting date (2024-05-01) après cutoff, source date (2024-04-30) avant cutoff'
}
```

### Points d'Attention pour le Code
- **Ordre d'évaluation:** Implémenter la logique de priorité
- **Logging:** Tracer chaque règle appliquée pour l'audit
- **Performance:** Optimiser pour traiter des volumes importants
- **Flexibilité:** Configuration externe pour ajuster les règles facilement

---

## ✅ Checklist Post-Réunion

- [ ] Mettre à jour la matrice avec les clarifications d'Islam
- [ ] Documenter les exemples concrets obtenus
- [ ] Lister les zones grises nécessitant une validation métier
- [ ] Prioriser l'implémentation des règles par ordre de complexité
- [ ] Planifier les tests avec des données historiques

---

**Rappel Stratégique:** L'objectif n'est pas de tout comprendre parfaitement, mais d'avoir une base solide pour implémenter une V1 fonctionnelle qui pourra être affinée itérativement.