#!/usr/bin/env python3
"""
Script dimostrativo di test per edgarpulse.
Testa i 3 moduli operativi:
1. Streaming Feed Atom real-time (filtrato su Form 8-K e Form 4)
2. Insider Trading Engine (parsing Form 4 per NVDA)
3. Events & M&A Engine (parsing 8-K Items per NVDA)
Salva i risultati strutturati in output.json per verifica.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from edgarpulse import SECClient, SECFeed, SECInsider, SECEventManager

def run_demo():
    print("=" * 70)
    print("EDGARPULSE ENGINE: VALIDAZIONE FUNZIONALITÀ")
    print("=" * 70)
    
    client = SECClient(user_agent="SecResearchApp test-bot@secresearchapp.com")
    output_summary = {}

    # -------------------------------------------------------------
    # Test Modulo 1: Real-Time Atom Feed
    # -------------------------------------------------------------
    print("\n[MODULO 1] Controllo ultimi filing live dall'Atom Feed SEC...")
    feed = SECFeed(client=client)
    # Filtriamo solo Form 8-K (comunicati) e Form 4 (insider)
    live_filings = feed.get_latest_filings(target_forms=["8-K", "4"], count=50)
    print(f" -> Trovati {len(live_filings)} filing ad alto valore (8-K / Form 4) negli ultimi minuti:")
    for f in live_filings[:5]:
        print(f"    • [{f.form}] {f.company_name} (CIK: {f.cik}) - {f.updated}")
    
    output_summary["live_feed_sample"] = [f.to_dict() for f in live_filings[:5]]

    # -------------------------------------------------------------
    # Test Modulo 2: Insider Trading (Form 4 XML)
    # -------------------------------------------------------------
    ticker = "NVDA"
    print(f"\n[MODULO 2] Estrazione transazioni Insider Trading per {ticker} (Form 4)...")
    insider = SECInsider(client=client)
    insider_reports = insider.get_latest_insider_trades(ticker, limit=3)
    
    for report in insider_reports:
        role = report.officer_title or ("Director" if report.is_director else "10% Owner")
        print(f"\n  👤 Insider: {report.owner_name} | Ruolo: {role} | Data: {report.period_of_report}")
        print(f"     Totale Venduto: {report.total_shares_sold:,.0f} azioni (${report.total_usd_sold:,.2f})")
        print(f"     Totale Acquistato: {report.total_shares_bought:,.0f} azioni (${report.total_usd_bought:,.2f})")
        for tx in report.transactions[:3]:
            action_desc = "ACQUISTO" if tx.acquired_disposed_code == 'A' else "VENDITA"
            price_str = f"${tx.price_per_share:,.2f}" if tx.price_per_share else "N/A"
            print(f"       -> {tx.transaction_date} | {action_desc} di {tx.shares:,.0f} quote a {price_str} ({tx.security_title})")

    output_summary["insider_trades"] = [r.to_dict() for r in insider_reports]

    # -------------------------------------------------------------
    # Test Modulo 3: Eventi Straordinari & M&A (Form 8-K)
    # -------------------------------------------------------------
    print(f"\n[MODULO 3] Estrazione comunicati ed eventi 8-K per {ticker}...")
    events_mgr = SECEventManager(client=client)
    events = events_mgr.get_latest_material_events(ticker, limit=2)
    
    for ev in events:
        print(f"\n  📑 Filing {ev.form} del {ev.filing_date} (Acc: {ev.accession_number})")
        print(f"     Items dichiarati: {', '.join(ev.items_detected) if ev.items_detected else 'Nessuno'}")
        print(f"     Rilevanza M&A deal: {'SÌ' if ev.is_ma_deal else 'NO'}")
        for item in ev.parsed_items:
            print(f"     └─ [Item {item.item_code}] {item.item_title}")
            print(f"        Anteprima testo pulito: {item.content_preview[:200]}...")

    output_summary["material_events"] = [e.to_dict() for e in events]

    # -------------------------------------------------------------
    # Salvataggio JSON di output
    # -------------------------------------------------------------
    json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(output_summary, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 70)
    print(f"✅ TEST COMPLETATO CON SUCCESSO! Dati esportati in: {json_path}")
    print("=" * 70)

if __name__ == "__main__":
    run_demo()
