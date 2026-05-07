# ⚡ XAUUSD Riley Reversal Bot

> **Stratégie** : Riley's Reversal Strategy — 5-Step Entry Checklist  
> **Paire** : XAU/USD (Gold)  
> **Données** : 12data.com API  
> **Capital initial** : $100 USD  
> **Sortie** : Signaux Telegram  
> **Déploiement** : Railway (worker permanent)

---

## 🗂️ Structure du projet

```
xauusd-riley-reversal/
├── xauusd_riley_reversal.py   ← Bot principal
├── requirements.txt           ← Dépendances Python
├── Procfile                   ← Commande démarrage Railway
├── railway.toml               ← Config Railway
├── .env.example               ← Template variables (copier en .env)
├── .gitignore                 ← Fichiers exclus de GitHub
└── README.md                  ← Ce fichier
```

---

## 🚀 Déploiement en 3 étapes

### Étape 1 — Pousser sur GitHub

```bash
git init
git add .
git commit -m "feat: Riley Reversal Bot v1.0 — XAUUSD"
git remote add origin https://github.com/TON_USERNAME/xauusd-riley-reversal.git
git branch -M main
git push -u origin main
```

> ⚠️ Le fichier `.env` n'est **jamais** commité. Les clés restent dans Railway uniquement.

### Étape 2 — Configurer Railway

1. railway.app → **New Project** → **Deploy from GitHub repo**
2. Sélectionner `xauusd-riley-reversal`
3. **Settings → Variables** → ajouter :

| Variable | Description |
|---|---|
| `TWELVE_DATA_API_KEY` | Clé API 12data.com |
| `TELEGRAM_BOT_TOKEN` | Token du bot Telegram |
| `TELEGRAM_CHAT_ID` | ID du chat destination |

4. **Deploy** → le bot démarre en mode worker permanent

### Étape 3 — Vérifier

Onglet **Logs** Railway :
```
XAUUSD Riley Reversal Bot — Démarrage
Capital initial : $100.00 USD
```
Sur Telegram : message de démarrage reçu automatiquement.

---

## 📐 Les 5 étapes Riley

| # | Étape | Timeframe | Logique |
|---|---|---|---|
| 1 | Key Reversal Zone | 15 min | Support/résistance ≥ 2 touches |
| 2 | Current Trend Broken | 1 min | Rupture swing structure |
| 3 | Timing | UTC | Fenêtres 9h45 / 10h00 EST |
| 4 | Head & Shoulders | 1 min | H&S inverse (BUY) / classique (SELL) |
| 5 | Trade Entry | 1 min | Confirmation bougie + SL/TP |

- **Étape 1** : Pivots 50 bougies 15min, zone validée si ≥ 2 touches (±0.5%)
- **Étape 2** : Rupture = premier Higher Low (bullish) ou Lower High (bearish)
- **Étape 3** : 14h40–14h50 UTC = 9h45 EST | 14h55–15h05 UTC = 10h00 EST (indicatif)
- **Étape 4** : H&S Inverse → BUY | H&S Classique → SELL (symétrie ±0.3%)
- **Étape 5** : SL sous swing low / TP = extrémité opposée du range

---

## 💬 Format signal Telegram

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚡ SIGNAL XAUUSD — Riley Reversal
━━━━━━━━━━━━━━━━━━━━━━━━━━━

🟢 BUY  |  XAU/USD  |  07/05/2026 14:47 UTC

📌 Entrée :      3250.40
🛡 Stop Loss :   3242.50
🎯 Take Profit : 3285.00
⚖️ Risk/Reward : 1 : 4.37
📦 Lot :         0.03
💸 Risque :      $2.00

─── Checklist Riley ───────────
✅ Zone de reversal :  Support 3242.80 | Résistance 3285.00
✅ Rupture tendance :  BULLISH
✅ Timing :            9:45 AM EST
✅ Pattern :           H&S_INVERSE

─── Capital ───────────────────
📈 Capital :   $102.50  (départ : $100.00)
P&L total :    +$2.50
Trades :  ✅ 2 gagnants  |  ❌ 1 perdants
━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 💰 Gestion du capital

| Paramètre | Valeur |
|---|---|
| Capital initial | $100 USD |
| Risque par trade | 2% |
| Lot minimum | 0.01 |
| SL | Structure du marché |
| TP | Extrémité opposée du range |
| Recalcul | Automatique après chaque trade |

---

## 🔄 Mise à jour du bot

Tout push sur `main` redéploie automatiquement sur Railway :

```bash
git add .
git commit -m "fix: description de la mise a jour"
git push origin main
# Railway redémarre le worker automatiquement
```

---

## 🔮 Roadmap V6

| Version | Amélioration | Statut |
|---|---|---|
| V6.1 | Ichimoku + RSI divergence | 🔜 |
| V6.2 | TP partiel + trailing stop + filtre news | 🔜 |
| V6.3 | Commandes /status /capital /stats /stop /reset | 🔜 |
| V6.4 | Graphiques Telegram (chart bougie) | 🔜 |
| V6.5 | Drawdown 20% + lot automatique avancé | 🔜 |

---

## ⚠️ Avertissement

Ce bot est un squelette éducatif. Tester obligatoirement en compte **démo** avant tout usage réel. Le trading XAU/USD comporte des risques significatifs de perte en capital.

---

*Stratégie : Riley Coleman Trading — rileycolemantrading.com*  
*Données : twelvedata.com | Dernière mise à jour README : 07/05/2026*
