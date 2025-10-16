# Questions Structurées - Réunion Islam
## SOX PG-01 Classification Logic Validation

**Date:** [À compléter]  
**Durée:** 45 minutes  
**Objectif:** Valider la compréhension des règles de classification

---

## 🎯 Stratégie de Communication

### Techniques à Utiliser
1. **Montrer, ne pas dire:** Partager votre écran avec la matrice
2. **Reformuler:** "Donc si je comprends bien..."
3. **Questions fermées d'abord:** Établir une base solide
4. **Exemples concrets:** Demander des cas réels

### Points d'Attention
- Parler lentement et clairement
- Laisser du temps pour les réponses
- Confirmer votre compréhension à chaque étape
- Noter les réponses en temps réel sur la matrice

---

## 📋 Script de Questions

### INTRODUCTION (5 minutes)

**Ouverture:**
"Islam, merci pour votre temps. J'ai passé du temps sur les mémos et vidéos que vous m'avez partagés. J'ai préparé une matrice de classification pour m'assurer que j'ai bien compris la logique. Est-ce que nous pouvons la parcourir ensemble pour que vous puissiez valider ma compréhension ?"

**Transition:**
"Je vais partager mon écran pour que nous puissions regarder cela ensemble."

---

### SECTION 1: BRIDGES (15 minutes)

#### Timing Differences
**Validation:** 
"D'après le mémo, j'ai compris qu'une différence de timing se produit quand la date de posting NAV est après la fin du mois, mais la date de l'événement source est avant. Est-ce correct ?"

**Clarification si OUI:**
"Parfait. Est-ce que cette règle s'applique de la même façon pour toutes les périodes, y compris la fin d'année fiscale ?"

**Clarification si NON:**
"Pouvez-vous me corriger ? Comment identifier exactement une timing difference ?"

**Question de suivi:**
"Y a-t-il des exceptions à cette règle selon le type de transaction ou l'entité ?"

#### Accruals
**Validation:**
"Pour les accruals, j'ai noté qu'il faut chercher les mots 'ACCRUAL' ou 'ACR' dans la description du document. C'est bien ça ?"

**Clarification:**
"Y a-t-il d'autres termes ou codes spécifiques que je devrais rechercher ? Par exemple, 'PROVISION' ou 'DEFER' ?"

**Question pratique:**
"Comment faites-vous la différence entre un accrual légitime et une erreur dans les données ?"

#### Currency Revaluation
**Validation:**
"Le document mentionne que les écarts de change en dessous de 1$ sont généralement ignorés. Cette règle est-elle universelle ?"

**Clarification:**
"Ce seuil de 1$ s'applique-t-il à toutes les devises ou y a-t-il des seuils différents selon la devise ?"

**Question métier:**
"Pouvez-vous m'expliquer pourquoi ce seuil existe ? Y a-t-il un contexte réglementaire ou opérationnel ?"

---

### SECTION 2: ADJUSTMENTS (10 minutes)

#### Write-offs
**Validation:**
"Pour identifier les write-offs, quels sont les codes spécifiques que je dois rechercher dans les données ?"

**Clarification:**
"Y a-t-il une différence entre un write-off automatique et un write-off manuel dans le système ?"

**Exemple concret:**
"Pouvez-vous me donner un exemple récent d'un write-off et comment vous l'avez identifié dans les données ?"

#### Reclassifications
**Validation:**
"Une reclassification, c'est quand on transfère des montants entre comptes GL sans impact sur le P&L, c'est correct ?"

**Clarification:**
"Comment puis-je différencier systématiquement une reclassification d'un vrai mouvement opérationnel ?"

**Question pratique:**
"Y a-t-il des reclassifications qui nécessitent toujours une validation manuelle, même si elles suivent les règles ?"

---

### SECTION 3: ONE-OFF DIFFERENCES (10 minutes)

#### System Errors
**Question ouverte:**
"Les mémos mentionnent des 'system errors'. Pouvez-vous me donner des exemples concrets de ce type d'erreur ?"

**Suivi:**
"Comment peut-on identifier ces erreurs de manière systématique dans les données ?"

**Validation:**
"Y a-t-il des patterns ou des indicateurs spécifiques qui signalent une erreur système ?"

#### Manual Corrections
**Question ouverte:**
"Pour les corrections manuelles, y a-t-il un processus standard ou des codes particuliers qui les identifient ?"

**Clarification:**
"Comment s'assurer qu'une correction manuelle est légitime et non une erreur ?"

**Exemple:**
"Avez-vous un exemple récent d'une correction manuelle et le processus de validation associé ?"

---

### SECTION 4: RÈGLES TRANSVERSALES (5 minutes)

#### Priorités
**Question cruciale:**
"Quand une transaction pourrait correspondre à plusieurs catégories, quelle est la logique de priorité ? Par exemple, une transaction avec 'ACCRUAL' dans la description mais qui a aussi une différence de timing ?"

#### Seuils
**Validation:**
"Y a-t-il d'autres seuils de matérialité que je dois connaître ? Par exemple, des montants en dessous desquels on ignore certaines différences ?"

#### Cas Particuliers
**Question ouverte:**
"Y a-t-il des règles spéciales pour certaines périodes (fin d'année) ou certaines entités ?"

---

## 📝 Template de Prise de Notes

### Règle Validée ✅
- **Catégorie:** [Bridge/Adjustment/One-off]
- **Sous-catégorie:** [Nom]
- **Règle confirmée:** [Description]
- **Données nécessaires:** [Champs requis]
- **Exceptions notées:** [Le cas échéant]

### Règle Modifiée 🔧
- **Catégorie:** [Bridge/Adjustment/One-off]
- **Ma compréhension initiale:** [Ce que je pensais]
- **Correction d'Islam:** [Ce qu'il a dit]
- **Nouvelle règle:** [Version corrigée]

### Nouvelle Information 💡
- **Sujet:** [Nouveau point découvert]
- **Détails:** [Explication d'Islam]
- **Impact sur l'implémentation:** [Ce que ça change]

---

## 🎬 Clôture de Réunion

### Questions de Synthèse
1. "Y a-t-il d'autres catégories de différences importantes que nous n'avons pas couvertes ?"
2. "Avez-vous des recommandations sur l'ordre de priorité pour implémenter ces règles ?"
3. "Y a-t-il des données ou des rapports existants que je pourrais utiliser pour tester ma logique ?"

### Prochaines Étapes
"Parfait, Islam. Je vais mettre à jour ma matrice avec vos clarifications et commencer l'implémentation. Puis-je revenir vers vous dans une semaine pour vous montrer les premiers résultats ?"

### Validation Finale
"Juste pour confirmer : est-ce que le processus que nous venons de discuter couvre environ 80-90% des cas que vous rencontrez habituellement ?"

---

## 📋 Checklist Post-Réunion

### Immédiatement Après (15 minutes)
- [ ] Mettre à jour la matrice de classification
- [ ] Noter les exemples concrets obtenus
- [ ] Lister les points nécessitant un suivi
- [ ] Identifier les règles prioritaires à implémenter

### Dans les 24h
- [ ] Envoyer un email de remerciement avec le résumé
- [ ] Commencer l'implémentation des règles validées
- [ ] Préparer les tests avec des données d'exemple
- [ ] Planifier la session de validation des résultats

### Suivi Hebdomadaire
- [ ] Partager les premiers résultats avec Islam
- [ ] Affiner les règles basées sur les tests
- [ ] Documenter les cas limites découverts
- [ ] Préparer la présentation des résultats finaux

---

**🎯 Objectif de Succès:** Sortir de la réunion avec une compréhension claire de 80% des règles et un plan d'action pour les 20% restants.