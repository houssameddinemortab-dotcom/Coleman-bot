"""
╔══════════════════════════════════════════════════════════════════╗
║   XAUUSD RILEY REVERSAL BOT — Squelette de signaux Telegram     ║
║   Basé sur : Riley's Reversal Strategy 5-Step Entry Checklist   ║
║   Données  : 12data.com API                                      ║
║   Capital initial : 100 USD                                      ║
╚══════════════════════════════════════════════════════════════════╝
"""

import os
import requests
import time
import json
from datetime import datetime, timezone

# ─────────────────────────────────────────────
#  CONFIGURATION — Variables d'environnement
#  Railway : Settings > Variables
#  Local   : fichier .env (non commité)
# ─────────────────────────────────────────────

TWELVE_DATA_API_KEY = os.environ.get("TWELVE_DATA_API_KEY", "1a6449e9febd41c08736d0340aedc75a")
TELEGRAM_BOT_TOKEN  = os.environ.get("TELEGRAM_BOT_TOKEN",  "8675193878:AAEKJoJDyDKkVGuSOO7qNAKNHP5ZissLTqE")
TELEGRAM_CHAT_ID    = os.environ.get("TELEGRAM_CHAT_ID",    "6387333974")

SYMBOL       = "XAU/USD"
INTERVAL_15M = "15min"
INTERVAL_1M  = "1min"

# ─────────────────────────────────────────────
#  BUDGET API 12DATA (plan gratuit = 800/jour)
#  Scan toutes les 5 min = 2 appels × 288 = 576/jour ✅
#  NE PAS descendre en dessous de 300s
# ─────────────────────────────────────────────
SCAN_INTERVAL_SEC = 300   # 5 minutes
API_RETRY_MAX     = 3     # tentatives avant abandon
API_RETRY_DELAY   = 10    # secondes entre chaque retry

# ─────────────────────────────────────────────
#  GESTION DU CAPITAL
# ─────────────────────────────────────────────

CAPITAL_INITIAL = 100.0   # USD
RISK_PER_TRADE  = 0.02    # 2% du capital par trade

capital_state = {
    "capital":      CAPITAL_INITIAL,
    "trades_total": 0,
    "trades_win":   0,
    "trades_loss":  0,
    "pnl_total":    0.0,
}


def calculer_position_size(capital: float, stop_distance_pct: float) -> float:
    """Calcule le lot en fonction du risque 2% et de la distance du stop."""
    risque_usd = capital * RISK_PER_TRADE
    if stop_distance_pct <= 0:
        return 0.01
    lot = round(risque_usd / stop_distance_pct, 2)
    return max(lot, 0.01)


def mettre_a_jour_capital(pnl: float):
    """Met à jour le capital et les statistiques après un trade."""
    capital_state["capital"]    += pnl
    capital_state["pnl_total"]  += pnl
    capital_state["trades_total"] += 1
    if pnl > 0:
        capital_state["trades_win"] += 1
    else:
        capital_state["trades_loss"] += 1


# ─────────────────────────────────────────────
#  RÉCUPÉRATION DES DONNÉES — 12data.com
# ─────────────────────────────────────────────

BASE_URL = "https://api.twelvedata.com"


def get_candles(interval: str, outputsize: int = 100) -> list[dict]:
    """
    Récupère les bougies OHLCV pour XAU/USD depuis 12data.
    Retry automatique jusqu'à API_RETRY_MAX fois en cas d'erreur.
    Retourne une liste de dicts : {datetime, open, high, low, close, volume}
    """
    url = f"{BASE_URL}/time_series"
    params = {
        "symbol":     SYMBOL,
        "interval":   interval,
        "outputsize": outputsize,
        "apikey":     TWELVE_DATA_API_KEY,
        "format":     "JSON",
    }
    last_error = None
    for tentative in range(1, API_RETRY_MAX + 1):
        try:
            resp = requests.get(url, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            if "values" not in data:
                raise ValueError(f"Erreur 12data: {data.get('message', 'Réponse invalide')}")
            candles = []
            for v in reversed(data["values"]):   # ordre chronologique
                candles.append({
                    "datetime": v["datetime"],
                    "open":     float(v["open"]),
                    "high":     float(v["high"]),
                    "low":      float(v["low"]),
                    "close":    float(v["close"]),
                    "volume":   float(v.get("volume", 0)),
                })
            return candles
        except Exception as e:
            last_error = e
            print(f"  ⚠ 12data tentative {tentative}/{API_RETRY_MAX} échouée : {e}")
            if tentative < API_RETRY_MAX:
                time.sleep(API_RETRY_DELAY)
    raise last_error


# ─────────────────────────────────────────────
#  ÉTAPE 1 — KEY REVERSAL ZONE (15 min)
#  Identifier support/résistance + trendlines
# ─────────────────────────────────────────────

def identifier_zones_reversal(candles_15m: list[dict]) -> dict:
    """
    Étape 1 : Détecte les zones clés de support/résistance sur 15min.
    Règle : au moins 2 touches pour valider une zone.
    Retourne un dict avec 'support' et 'resistance'.
    """
    highs  = [c["high"]  for c in candles_15m]
    lows   = [c["low"]   for c in candles_15m]
    closes = [c["close"] for c in candles_15m]

    prix_actuel = closes[-1]

    # Zones simples : pivots récents sur les 50 dernières bougies
    periode = candles_15m[-50:]
    pivot_high = max(c["high"] for c in periode)
    pivot_low  = min(c["low"]  for c in periode)

    # Vérification du nombre de touches (au moins 2)
    tolerance = (pivot_high - pivot_low) * 0.005   # 0.5% de tolérance

    touches_support    = sum(1 for c in periode if abs(c["low"]  - pivot_low)  < tolerance)
    touches_resistance = sum(1 for c in periode if abs(c["high"] - pivot_high) < tolerance)

    return {
        "support":            pivot_low,
        "resistance":         pivot_high,
        "prix_actuel":        prix_actuel,
        "touches_support":    touches_support,
        "touches_resistance": touches_resistance,
        "zone_valide":        touches_support >= 2 or touches_resistance >= 2,
        "pres_support":       abs(prix_actuel - pivot_low)  / pivot_low  < 0.005,
        "pres_resistance":    abs(prix_actuel - pivot_high) / pivot_high < 0.005,
    }


# ─────────────────────────────────────────────
#  ÉTAPE 2 — TREND BREAK (1 min)
#  Détecter la rupture de tendance en cours
# ─────────────────────────────────────────────

def detecter_rupture_tendance(candles_1m: list[dict]) -> dict:
    """
    Étape 2 : Analyse la structure swing sur 1min.
    Downtrend = lower lows + lower highs.
    Uptrend   = higher highs + higher lows.
    Rupture   = séquence cassée.
    """
    recentes = candles_1m[-20:]   # 20 dernières bougies 1min

    swings_highs = [c["high"] for c in recentes]
    swings_lows  = [c["low"]  for c in recentes]

    # Détection de la tendance actuelle
    dernier_haut  = max(swings_highs[-5:])
    precedent_haut = max(swings_highs[-10:-5])
    dernier_bas   = min(swings_lows[-5:])
    precedent_bas  = min(swings_lows[-10:-5])

    tendance_down   = dernier_haut < precedent_haut and dernier_bas < precedent_bas
    tendance_up     = dernier_haut > precedent_haut and dernier_bas > precedent_bas
    rupture_down    = tendance_down and dernier_bas > precedent_bas   # HL formé
    rupture_up      = tendance_up   and dernier_haut < precedent_haut # LH formé

    return {
        "tendance":        "DOWN" if tendance_down else ("UP" if tendance_up else "NEUTRE"),
        "rupture_detectee": rupture_down or rupture_up,
        "type_rupture":    "BULLISH" if rupture_down else ("BEARISH" if rupture_up else "AUCUNE"),
        "dernier_haut":    dernier_haut,
        "dernier_bas":     dernier_bas,
    }


# ─────────────────────────────────────────────
#  ÉTAPE 3 — TIMING (9h45 / 10h00 EST)
# ─────────────────────────────────────────────

def verifier_timing() -> dict:
    """
    Étape 3 : Vérifie si l'heure actuelle est dans une fenêtre de timing.
    Windows clés : 9h45 EST et 10h00 EST (= 14h45 / 15h00 UTC).
    """
    now_utc  = datetime.now(timezone.utc)
    heure    = now_utc.hour
    minute   = now_utc.minute

    # Fenêtre ±5 minutes autour de 14h45 et 15h00 UTC
    fenetres = [(14, 40, 14, 50), (14, 55, 15, 5)]
    dans_fenetre = False
    fenetre_nom  = ""

    for h_start, m_start, h_end, m_end in fenetres:
        debut = h_start * 60 + m_start
        fin   = h_end   * 60 + m_end
        actuel = heure  * 60 + minute
        if debut <= actuel <= fin:
            dans_fenetre = True
            fenetre_nom  = "9:45 AM EST" if h_start == 14 else "10:00 AM EST"
            break

    return {
        "heure_utc":     now_utc.strftime("%H:%M UTC"),
        "dans_fenetre":  dans_fenetre,
        "fenetre_nom":   fenetre_nom,
    }


# ─────────────────────────────────────────────
#  ÉTAPE 4 — HEAD & SHOULDERS PATTERN (1 min)
# ─────────────────────────────────────────────

def detecter_head_and_shoulders(candles_1m: list[dict]) -> dict:
    """
    Étape 4 : Détecte un pattern tête & épaules (inverse ou classique).
    Logique simplifiée : 3 creux/sommets avec le central plus prononcé.
    """
    recentes = candles_1m[-30:]
    lows     = [c["low"]  for c in recentes]
    highs    = [c["high"] for c in recentes]

    # H&S inverse (bullish reversal) : 3 creux, celui du milieu plus bas
    tiers   = len(lows) // 3
    bas_g   = min(lows[:tiers])
    bas_c   = min(lows[tiers:2*tiers])
    bas_d   = min(lows[2*tiers:])
    hs_inv  = bas_c < bas_g and bas_c < bas_d and abs(bas_g - bas_d) / bas_g < 0.003

    # H&S classique (bearish reversal) : 3 sommets, celui du milieu plus haut
    haut_g  = max(highs[:tiers])
    haut_c  = max(highs[tiers:2*tiers])
    haut_d  = max(highs[2*tiers:])
    hs_std  = haut_c > haut_g and haut_c > haut_d and abs(haut_g - haut_d) / haut_g < 0.003

    pattern = "H&S_INVERSE" if hs_inv else ("H&S_CLASSIQUE" if hs_std else "AUCUN")

    return {
        "pattern_detecte": hs_inv or hs_std,
        "type_pattern":    pattern,
        "signal":          "BUY" if hs_inv else ("SELL" if hs_std else "AUCUN"),
    }


# ─────────────────────────────────────────────
#  ÉTAPE 5 — TRADE ENTRY
#  Confirmation bougie + calcul SL/TP
# ─────────────────────────────────────────────

def calculer_trade(
    signal: str,
    prix_actuel: float,
    support: float,
    resistance: float,
    capital: float,
) -> dict:
    """
    Étape 5 : Calcule l'entrée, le stop-loss et le take-profit.
    SL : sous le swing low récent (BUY) ou au-dessus du swing high (SELL).
    TP : extrémité opposée du range.
    """
    if signal == "BUY":
        entree = prix_actuel
        sl     = round(support  * 0.9985, 2)   # légèrement sous le support
        tp     = round(resistance, 2)
    elif signal == "SELL":
        entree = prix_actuel
        sl     = round(resistance * 1.0015, 2)  # légèrement au-dessus résistance
        tp     = round(support, 2)
    else:
        return {}

    stop_dist_pct = abs(entree - sl) / entree * 100
    lot           = calculer_position_size(capital, abs(entree - sl))
    rr_ratio      = round(abs(tp - entree) / abs(sl - entree), 2) if sl != entree else 0

    return {
        "signal":    signal,
        "entree":    entree,
        "sl":        sl,
        "tp":        tp,
        "lot":       lot,
        "rr_ratio":  rr_ratio,
        "risque_usd": round(capital * RISK_PER_TRADE, 2),
    }


# ─────────────────────────────────────────────
#  ENVOI TELEGRAM
# ─────────────────────────────────────────────

def envoyer_telegram(message: str):
    """Envoie un message formaté sur Telegram."""
    url     = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id":    TELEGRAM_CHAT_ID,
        "text":       message,
        "parse_mode": "HTML",
    }
    resp = requests.post(url, json=payload, timeout=10)
    resp.raise_for_status()
    return resp.json()


def formater_signal(trade: dict, zones: dict, timing: dict, rupture: dict, pattern: dict) -> str:
    """
    Formate le message de signal Telegram — clair et lisible.
    """
    cap  = capital_state["capital"]
    win  = capital_state["trades_win"]
    loss = capital_state["trades_loss"]
    pnl  = capital_state["pnl_total"]
    emoji_signal = "🟢 BUY" if trade["signal"] == "BUY" else "🔴 SELL"
    emoji_pnl    = "📈" if pnl >= 0 else "📉"

    msg = f"""
<b>━━━━━━━━━━━━━━━━━━━━━━━━━━━</b>
<b>⚡ SIGNAL XAUUSD — Riley Reversal</b>
<b>━━━━━━━━━━━━━━━━━━━━━━━━━━━</b>

<b>{emoji_signal}</b>  |  <b>XAU/USD</b>  |  {datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")}

<b>📌 Entrée :</b>  <code>{trade['entree']:.2f}</code>
<b>🛡 Stop Loss :</b> <code>{trade['sl']:.2f}</code>
<b>🎯 Take Profit :</b> <code>{trade['tp']:.2f}</code>
<b>⚖️ Risk/Reward :</b> <code>1 : {trade['rr_ratio']}</code>
<b>📦 Lot :</b>  <code>{trade['lot']}</code>
<b>💸 Risque :</b>  <code>${trade['risque_usd']}</code>

<b>─── Checklist Riley ───────────</b>
✅ Zone de reversal :  Support <code>{zones['support']:.2f}</code> | Résistance <code>{zones['resistance']:.2f}</code>
✅ Rupture tendance :  <code>{rupture['type_rupture']}</code>
✅ Timing :            <code>{timing['fenetre_nom'] if timing['dans_fenetre'] else 'Hors fenêtre'}</code>
✅ Pattern :           <code>{pattern['type_pattern']}</code>

<b>─── Capital ───────────────────</b>
{emoji_pnl} <b>Capital :</b>  <code>${cap:.2f}</code>  (départ : $100.00)
<b>P&L total :</b>  <code>${pnl:+.2f}</code>
<b>Trades :</b>  ✅ {win} gagnants  |  ❌ {loss} perdants

<b>━━━━━━━━━━━━━━━━━━━━━━━━━━━</b>
"""
    return msg.strip()


def formater_alerte_no_signal(raison: str) -> str:
    """Message d'information quand les conditions ne sont pas réunies."""
    return (
        f"<b>ℹ️ XAUUSD — Aucun signal</b>\n"
        f"<code>{datetime.now(timezone.utc).strftime('%H:%M UTC')}</code>\n"
        f"Raison : {raison}"
    )


# ─────────────────────────────────────────────
#  LOGIQUE PRINCIPALE — 5 ÉTAPES RILEY
# ─────────────────────────────────────────────

def analyser_et_signaler():
    """
    Exécute les 5 étapes de la stratégie Riley sur XAU/USD
    et envoie un signal Telegram si toutes les conditions sont réunies.
    """
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Analyse en cours...")

    # ── Données ─────────────────────────────
    candles_15m = get_candles(INTERVAL_15M, outputsize=100)
    candles_1m  = get_candles(INTERVAL_1M,  outputsize=60)

    # ── Étape 1 : Zone de reversal ──────────
    zones = identifier_zones_reversal(candles_15m)
    if not zones["zone_valide"]:
        print("  ✗ Étape 1 : Aucune zone valide (< 2 touches)")
        return

    # ── Étape 2 : Rupture de tendance ───────
    rupture = detecter_rupture_tendance(candles_1m)
    if not rupture["rupture_detectee"]:
        print("  ✗ Étape 2 : Pas de rupture de tendance")
        return

    # ── Étape 3 : Timing ────────────────────
    timing = verifier_timing()
    if not timing["dans_fenetre"]:
        print(f"  ✗ Étape 3 : Hors fenêtre ({timing['heure_utc']})")
        # On continue quand même (le timing est indicatif, pas bloquant)
        timing["fenetre_nom"] = "Hors fenêtre"

    # ── Étape 4 : Pattern H&S ───────────────
    pattern = detecter_head_and_shoulders(candles_1m)
    if not pattern["pattern_detecte"]:
        print("  ✗ Étape 4 : Aucun pattern H&S détecté")
        return

    # ── Étape 5 : Calcul du trade ───────────
    signal = pattern["signal"]
    trade  = calculer_trade(
        signal        = signal,
        prix_actuel   = zones["prix_actuel"],
        support       = zones["support"],
        resistance    = zones["resistance"],
        capital       = capital_state["capital"],
    )

    if not trade:
        print("  ✗ Étape 5 : Signal invalide")
        return

    # ── Envoi Telegram ──────────────────────
    message = formater_signal(trade, zones, timing, rupture, pattern)
    envoyer_telegram(message)
    print(f"  ✓ Signal {signal} envoyé ! Entrée={trade['entree']} SL={trade['sl']} TP={trade['tp']}")


# ─────────────────────────────────────────────
#  BOUCLE PRINCIPALE
# ─────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  XAUUSD Riley Reversal Bot — Démarrage")
    print(f"  Capital initial : ${CAPITAL_INITIAL:.2f} USD")
    print("=" * 60)

    envoyer_telegram(
        f"<b>🚀 Riley Reversal Bot démarré</b>\n"
        f"Capital initial : <code>${CAPITAL_INITIAL:.2f} USD</code>\n"
        f"Paire : <b>XAU/USD</b>\n"
        f"Stratégie : Riley 5-Step Reversal\n"
        f"Scan toutes les 5 minutes (300s)\nBudget API : ~576 appels/jour (limite 800)"
    )

    while True:
        try:
            analyser_et_signaler()
        except requests.exceptions.HTTPError as e:
            print(f"  ⚠ Erreur HTTP : {e}")
        except requests.exceptions.ConnectionError:
            print("  ⚠ Erreur de connexion réseau")
        except ValueError as e:
            print(f"  ⚠ Erreur données : {e}")
        except Exception as e:
            print(f"  ⚠ Erreur inattendue : {e}")

        time.sleep(SCAN_INTERVAL_SEC)   # Scan toutes les 5 minutes (300s)


if __name__ == "__main__":
    main()
