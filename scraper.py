import os
import re
import time
import random
from typing import List, Dict, Any
from urllib.parse import urlparse, parse_qs
from playwright.sync_api import sync_playwright, Page, BrowserContext

import database

PAGES_CONFIG = [
    {
        "name": "Iniziativa Libertaria - Pordenone",
        "url": "https://www.facebook.com/iniziativalibertaria",
        "events_url": "https://www.facebook.com/iniziativalibertaria/events"
    },
    {
        "name": "Amici Zapatisti",
        "url": "https://www.facebook.com/amicizapatisti",
        "events_url": "https://www.facebook.com/amicizapatisti/events"
    },
    {
        "name": "Biblioteca Mauro Cancian",
        "url": "https://www.facebook.com/bibliomaurocancian",
        "events_url": "https://www.facebook.com/bibliomaurocancian/events"
    }
]

def human_delay(min_s: float = 1.0, max_s: float = 2.5):
    time.sleep(random.uniform(min_s, max_s))

def dismiss_overlays(page: Page):
    """Chiude banner cookie, dialoghi di accesso e overlay bloccanti."""
    cookie_btn_texts = [
        "Rifiuta cookie facoltativi",
        "Decline optional cookies",
        "Solo cookie essenziali",
        "Consenti solo cookie essenziali",
        "Only allow essential cookies"
    ]
    for text in cookie_btn_texts:
        try:
            btn = page.get_by_role("button", name=text)
            if btn.is_visible(timeout=800):
                btn.click()
                print(f"   [OK] Banner cookie gestito ({text})")
                human_delay(0.8, 1.5)
                break
        except Exception:
            pass

    try:
        page.evaluate("""() => {
            const closeButtons = document.querySelectorAll('[aria-label="Chiudi"], [aria-label="Close"], [aria-label="Annulla"]');
            closeButtons.forEach(btn => {
                if (btn && btn.offsetParent !== null) {
                    btn.click();
                }
            });

            const fixedElements = document.querySelectorAll('div');
            fixedElements.forEach(el => {
                const style = window.getComputedStyle(el);
                if (style.position === 'fixed' && el.innerText && (
                    el.innerText.includes('Accedi o iscriviti a Facebook') ||
                    el.innerText.includes('Vedi altri contenuti di')
                )) {
                    el.remove();
                }
            });
        }""")
    except Exception:
        pass

def extract_posts_from_page(page: Page, assoc_name: str, max_scrolls: int = 8) -> List[Dict[str, Any]]:
    posts_found: List[Dict[str, Any]] = []
    seen_links = set()

    print(f"   [*] Inizio estrazione comunicati in bacheca per {assoc_name}...")

    for scroll_idx in range(max_scrolls):
        dismiss_overlays(page)

        try:
            more_buttons = page.locator("text='Altro...', text='Visualizza altro'").all()
            for mb in more_buttons[:5]:
                try:
                    if mb.is_visible():
                        mb.click()
                        human_delay(0.2, 0.4)
                except Exception:
                    pass
        except Exception:
            pass

        articles = page.locator("[role=article]").all()
        for art in articles:
            try:
                full_text = art.inner_text().strip()
                if len(full_text) < 15:
                    continue

                links = art.locator("a[href*='/posts/'], a[href*='permalink.php'], a[href*='/photos/'], a[href*='/videos/'], a[href*='/events/']").all()
                permalink = ""
                for l in links:
                    href = l.get_attribute("href") or ""
                    if "comment_id=" in href or "reply_comment_id=" in href:
                        continue
                    clean_link = href.split("?")[0]
                    if any(marker in clean_link for marker in ["/posts/", "/photos/", "/videos/", "/events/"]):
                        permalink = clean_link
                        break
                    elif "permalink.php" in href:
                        permalink = href.split("&__cft__")[0]
                        break

                if not permalink:
                    for l in art.locator("a[href]").all():
                        href = l.get_attribute("href") or ""
                        txt = l.inner_text().strip()
                        if re.match(r'^(\d+\s*(?:g|h|m|min|s|d)|ieri|\d{1,2}\s+[a-z]{3})', txt, re.I):
                            permalink = href.split("?")[0]
                            break

                if not permalink or permalink in seen_links:
                    continue

                lines = [line.strip() for line in full_text.split("\n") if line.strip()]
                
                date_str = "Recente"
                for line in lines[:8]:
                    if re.match(r'^(\d+\s*(?:g|h|m|min|s|d)|ieri|\d{1,2}\s+[a-z]{3})', line, re.I):
                        date_str = line
                        break

                content_lines = []
                for line in lines:
                    if line in [assoc_name, "Condividi", "Mi piace", "Commenta", "·", "Tutte le reazioni:"]:
                        continue
                    if line.startswith("Condivisioni:") or line.startswith("Commenti:") or line == date_str:
                        continue
                    if re.match(r'^\d+$', line):
                        continue
                    content_lines.append(line)

                content_text = "\n".join(content_lines).strip()
                if not content_text:
                    content_text = full_text

                reactions = "N/D"
                for line in lines:
                    if "Tutte le reazioni:" in line or re.match(r'^\d+\s*reazion', line, re.I):
                        reactions = line

                seen_links.add(permalink)
                post_data = {
                    "association": assoc_name,
                    "author": assoc_name,
                    "content": content_text,
                    "date_str": date_str,
                    "permalink": permalink,
                    "reactions_count": reactions
                }
                posts_found.append(post_data)
                print(f"      [+] Post estratto: {content_text[:60]}... ({date_str})")

            except Exception:
                pass

        page.evaluate("window.scrollBy(0, 1200)")
        human_delay(1.5, 2.5)

    return posts_found

def parse_event_card_info(raw_text: str, default_status: str, assoc_name: str, event_url: str) -> Dict[str, Any]:
    lines = [l.strip() for l in raw_text.split("\n") if l.strip() and l.strip() != "·"]
    
    date_str = ""
    title_str = ""
    location_str = ""
    status = default_status
    participants_str = "N/D"

    day_keywords = ["lun", "mar", "mer", "gio", "ven", "sab", "dom", "gen", "feb", "mar", "apr", "mag", "giu", "lug", "ago", "set", "ott", "nov", "dic"]
    
    date_idx = -1
    for i, line in enumerate(lines):
        line_lower = line.lower()
        if any(dk in line_lower for dk in day_keywords) and len(line) < 40 and not line.startswith("Evento di"):
            date_str = line
            date_idx = i
            break
            
    title_candidates = []
    for i, line in enumerate(lines):
        if i == date_idx:
            continue
        if line.startswith("Evento di ") or "interessat" in line.lower() or "partecipant" in line.lower():
            continue
        title_candidates.append(line)
        
    if title_candidates:
        title_str = title_candidates[0]
        if len(title_candidates) > 1:
            loc_candidate = title_candidates[1]
            if not loc_candidate.startswith("Evento di"):
                location_str = loc_candidate

    for line in lines:
        line_lower = line.lower()
        if "interessat" in line_lower or "partecipant" in line_lower:
            participants_str = line
        if any(marker in line_lower for marker in ["via ", "piazza ", "piazzetta ", "viale ", "corso ", "online", "stazione "]):
            location_str = line

    if not title_str and lines:
        title_str = lines[0]

    return {
        "association": assoc_name,
        "title": title_str,
        "date_str": date_str if date_str else "N/D",
        "location": location_str if location_str else "Non specificato",
        "status": status,
        "participants": participants_str,
        "permalink": event_url
    }

def extract_events_from_page(page: Page, events_url: str, assoc_name: str) -> List[Dict[str, Any]]:
    print(f"   [*] Inizio estrazione eventi per {assoc_name} da {events_url}...")
    events_found: List[Dict[str, Any]] = []
    seen_event_ids = set()

    try:
        page.goto(events_url, wait_until="networkidle", timeout=30000)
    except Exception:
        pass

    human_delay(2.0, 3.0)
    dismiss_overlays(page)

    tab_locators = page.locator("[role=tab], a[role=tab]").all()
    tabs_map = {}
    for t in tab_locators:
        t_text = t.inner_text().strip()
        if "In programma" in t_text or "Upcoming" in t_text:
            tabs_map["In programma"] = t
        elif "Passati" in t_text or "Past" in t_text:
            tabs_map["Passato"] = t

    sections_to_scrape = []
    if tabs_map:
        for s_name, tab_elem in tabs_map.items():
            sections_to_scrape.append((s_name, tab_elem))
    else:
        sections_to_scrape.append(("Passato", None))

    for section_name, tab_elem in sections_to_scrape:
        if tab_elem is not None:
            try:
                tab_elem.click()
                human_delay(1.5, 2.5)
                dismiss_overlays(page)
            except Exception:
                pass

        # Scroll progressivo
        prev_count = 0
        no_new = 0
        for _ in range(12):
            dismiss_overlays(page)
            page.evaluate("window.scrollBy(0, 1200)")
            human_delay(1.2, 2.0)
            cur_count = page.locator("a[href*='/events/']").count()
            if cur_count == prev_count:
                no_new += 1
                if no_new >= 2:
                    break
            else:
                no_new = 0
                prev_count = cur_count

        event_links = page.locator("a[href*='/events/']").all()
        for link in event_links:
            try:
                raw_href = link.get_attribute("href") or ""
                match = re.search(r'/events/(\d+)', raw_href)
                if not match:
                    continue
                event_id = match.group(1)
                if event_id in seen_event_ids:
                    continue
                seen_event_ids.add(event_id)
                canonical_url = f"https://www.facebook.com/events/{event_id}/"

                card_text = link.evaluate("""el => {
                    let curr = el;
                    for (let i = 0; i < 6; i++) {
                        if (!curr.parentElement) break;
                        curr = curr.parentElement;
                        const t = curr.innerText || '';
                        const lines = t.split('\\n').map(x => x.trim()).filter(x => x.length > 0);
                        if (lines.length >= 3 && lines.some(l => l.includes('Evento di') || l.length > 15)) {
                            return t;
                        }
                    }
                    return el.innerText;
                }""")

                ev_info = parse_event_card_info(
                    raw_text=card_text,
                    default_status=section_name,
                    assoc_name=assoc_name,
                    event_url=canonical_url
                )
                events_found.append(ev_info)
                print(f"      [+] Evento estratto: {ev_info['title']} ({ev_info['date_str']}) - {ev_info['status']}")
            except Exception:
                pass

    return events_found

def run_sync() -> Dict[str, Any]:
    print("==================================================")
    print("=== AVVIO AGENTE DI SINCRONIZZAZIONE FACEBOOK ===")
    database.init_db()

    total_posts_saved = 0
    total_events_saved = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--lang=it-IT",
                "--no-sandbox",
                "--disable-dev-shm-usage"
            ]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
            viewport={"width": 1366, "height": 900},
            locale="it-IT"
        )

        for cfg in PAGES_CONFIG:
            assoc_name = cfg["name"]
            page_url = cfg["url"]
            events_url = cfg["events_url"]

            print(f"\n[*] Sincronizzazione associazione: {assoc_name}")
            page = context.new_page()
            
            # 1. Scraping Bacheca Post
            try:
                page.goto(page_url, wait_until="networkidle", timeout=30000)
            except Exception:
                pass
            human_delay(2.0, 3.0)
            dismiss_overlays(page)
            
            posts = extract_posts_from_page(page, assoc_name, max_scrolls=4)
            for p_item in posts:
                if database.upsert_post(p_item):
                    total_posts_saved += 1

            # 2. Scraping Sezione Eventi
            events = extract_events_from_page(page, events_url, assoc_name)
            for e_item in events:
                if database.upsert_event(e_item):
                    total_events_saved += 1

            page.close()
            human_delay(1.5, 3.0)

        browser.close()

    status_msg = f"Sincronizzazione completata: {total_posts_saved} post salvati/aggiornati, {total_events_saved} eventi salvati/aggiornati."
    database.log_sync("SUCCESS", total_posts_saved, total_events_saved, status_msg)
    print(f"\n[OK] {status_msg}")
    return {
        "success": True,
        "posts_saved": total_posts_saved,
        "events_saved": total_events_saved,
        "message": status_msg
    }

if __name__ == "__main__":
    run_sync()
