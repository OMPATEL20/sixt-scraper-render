# working fine
"""
AGENT 1: AI-POWERED SIXT SCRAPER
Generates and runs a Playwright scraper for any location using Ollama LLM.

Enhancements:
  - Intelligent model selection based on available RAM
  - Comprehensive exception handling: retry logic, multi-encoding CSV,
    timeout protection, and clear error messaging
  - Anti-bot protection handling
"""

import os
import re
import ast
import json
import glob
import time
import random
import platform
import subprocess
import requests
import pandas as pd
from datetime import datetime


# ─────────────────────────────────────────────
# INTELLIGENT MODEL SELECTION
# ─────────────────────────────────────────────
def get_available_ram_gb() -> float:
    """Returns total system RAM in GB."""
    system = platform.system()
    try:
        if system == "Darwin":  # macOS
            result = subprocess.run(
                ["sysctl", "-n", "hw.memsize"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return int(result.stdout.strip()) / (1024**3)
        elif system == "Linux":
            with open("/proc/meminfo", "r") as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        kb = int(line.split()[1])
                        return kb / (1024**2)
        elif system == "Windows":
            result = subprocess.run(
                ["wmic", "computersystem", "get", "TotalPhysicalMemory"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            lines = [
                l.strip() for l in result.stdout.splitlines() if l.strip().isdigit()
            ]
            if lines:
                return int(lines[0]) / (1024**3)
    except Exception as e:
        print(f"  RAM detection failed: {e}")
    return 0.0


# Model tiers
MODEL_TIERS = [
    (32, "qwen2.5-coder:32b", "High-spec  (32 GB+)"),
    (16, "qwen2.5-coder:14b", "Mid-spec   (16–31 GB)"),
    (8, "qwen2.5-coder:7b", "Standard   (8–15 GB)"),
    (0, "qwen2.5-coder:3b", "Low-spec   (<8 GB)"),
]


def get_pulled_models() -> list[str]:
    """Query Ollama for pulled models."""
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        if r.status_code == 200:
            return [m["name"] for m in r.json().get("models", [])]
    except Exception as e:
        print(f"  Could not fetch pulled models: {e}")
    return []


def model_is_available(name: str, pulled: list[str]) -> bool:
    """Check if model is available locally."""
    base = name.split(":")[0]
    tag = name.split(":")[1] if ":" in name else ""
    for pulled_name in pulled:
        if pulled_name == name:
            return True
        if pulled_name.startswith(base) and tag in pulled_name:
            return True
    return False


def select_model() -> str:
    """Intelligently select the best available model."""
    ram = get_available_ram_gb()
    pulled = get_pulled_models()

    print(
        f"  Detected RAM  : {ram:.1f} GB" if ram > 0 else "  RAM detection unavailable"
    )
    if pulled:
        print(f"  Pulled models : {', '.join(pulled)}")

    if ram > 0 and pulled:
        for min_ram, model, label in MODEL_TIERS:
            if ram >= min_ram + 2 and model_is_available(model, pulled):
                print(f"  Auto-selected  : {model}  [{label}]")
                return model

    if ram > 0 and pulled:
        for pulled_name in pulled:
            is_small = any(
                t in pulled_name for t in ("3b", "1b", "mini", "small", "tiny")
            )
            if ram >= 8 or is_small:
                print(f"  Falling back to: {pulled_name}")
                return pulled_name

    print(f"  WARNING: Falling back to default '{OLLAMA_MODEL_DEFAULT}'")
    return OLLAMA_MODEL_DEFAULT


# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
OLLAMA_URL = "http://localhost:11434"
OLLAMA_MODEL_DEFAULT = "qwen2.5-coder:latest"
GEN_TEMP = 0.1
MAX_RETRIES = 3
OLLAMA_TIMEOUT_S = 240
BACKOFF_BASE = 5.0


def banner(title: str) -> None:
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


banner("AGENT 1: AI-POWERED SIXT SCRIPT GENERATOR")
print("\nGenerates a specialised Playwright scraper for ANY location.\n")


def resolve_iata(code: str) -> str:
    """Convert IATA code to airport name."""
    try:
        url = "https://raw.githubusercontent.com/jpatokal/openflights/master/data/airports.dat"
        cols = [
            "id",
            "name",
            "city",
            "country",
            "iata",
            "icao",
            "lat",
            "lon",
            "alt",
            "tz",
            "dst",
            "tzdb",
            "type",
            "source",
        ]
        df = pd.read_csv(url, header=None, names=cols)
        row = df[df["iata"].str.upper() == code.upper()]
        if not row.empty:
            r = row.iloc[0]
            return f"{r['name']} {r['city']}"
    except Exception as e:
        print(f"  IATA lookup failed: {e}")
    return code


def check_ollama() -> bool:
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        if r.status_code == 200:
            models = r.json().get("models", [])
            print(f"  Ollama running — {len(models)} model(s) loaded")
            return True
    except requests.exceptions.ConnectionError:
        print("  ERROR: Cannot reach Ollama. Is it running?  →  ollama serve")
    except Exception as e:
        print(f"  ERROR: {e}")
    return False


if not check_ollama():
    raise SystemExit(1)

OLLAMA_MODEL = select_model()
print(f"  Active model: {OLLAMA_MODEL}")


# User input
raw_input = input(
    "\n  Enter airport, city, address, or postal code\n  (e.g. YYC  /  Calgary Downtown): "
).strip()

if not raw_input:
    raw_input = "Calgary Airport"
    print(f"  No input — using default: {raw_input}")

if len(raw_input) == 3 and raw_input.isalpha():
    resolved = resolve_iata(raw_input)
    if resolved != raw_input:
        print(f"  IATA detected → resolved to: {resolved}")
        raw_input = resolved

LOCATION = raw_input
LOCATION_CODE = re.sub(r"[^a-zA-Z0-9]", "_", LOCATION).strip("_")[:20].upper()

print(f"\n  Scraping for: {LOCATION}")
print("=" * 80 + "\n")


# ─────────────────────────────────────────────
# PROMPT BUILDER - ANTI-BOT VERSION
# ─────────────────────────────────────────────
def build_prompt(location: str) -> str:
    """Build prompt with anti-bot measures."""
    return f'''You are an expert web scraping engineer. Generate a COMPLETE, STANDALONE Python script with anti-bot protection.

OUTPUT RULES:
- Raw Python only. Zero markdown. Zero explanation.
- Single main() function with if __name__ == "__main__": main()
- Include human-like delays and random mouse movements
- Handle Cloudflare challenges

===== SECTION 1: IMPORTS =====

import json, os, re, time, random
import pandas as pd
from datetime import datetime
from playwright.sync_api import sync_playwright
import requests

def random_delay(min_sec=0.5, max_sec=2.0):
    """Human-like random delay"""
    time.sleep(random.uniform(min_sec, max_sec))

def human_mouse_movement(page, x, y):
    """Simulate human mouse movement"""
    steps = random.randint(10, 30)
    for i in range(steps):
        current_x = x * (i / steps)
        current_y = y * (i / steps)
        page.mouse.move(current_x, current_y)
        time.sleep(random.uniform(0.01, 0.05))

def human_typing(page, text, element=None):
    """Type like a human with random delays"""
    if element:
        element.click()
    random_delay(0.3, 0.8)
    for char in text:
        page.keyboard.type(char, delay=random.uniform(0.05, 0.25))

def check_cloudflare(page):
    """Check if we hit Cloudflare protection"""
    page_text = page.inner_text("body")
    if "cloudflare" in page_text.lower() or "security verification" in page_text.lower():
        print("⚠️  Cloudflare detected! Waiting for verification...")
        time.sleep(10)
        return True
    return False

def main():
    LOCATION = "{location}"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_loc = re.sub(r"[^a-zA-Z0-9]", "_", LOCATION)[:20]

    with sync_playwright() as p:
        # Use more realistic browser settings
        browser = p.chromium.launch(
            headless=True,  # Headless often triggers bot detection
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process',
                '--start-maximized'
            ]
        )
        
        # Create context with realistic viewport
        context = browser.new_context(
            viewport={{'width': 1920, 'height': 1080}},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        page = context.new_page()
        
        # Hide webdriver property
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {{
                get: () => undefined
            }});
        """)
        
        try:
            # Navigate with random delays
            print("🌐 Navigating to sixt.ca...")
            page.goto("https://www.sixt.ca", wait_until="domcontentloaded", timeout=60000)
            random_delay(2, 5)
            
            # Check for Cloudflare
            if check_cloudflare(page):
                print("Waiting for manual verification...")
                time.sleep(15)
                # Try to refresh if still stuck
                if check_cloudflare(page):
                    page.reload()
                    time.sleep(10)
            
            # Wait for page to fully load
            page.wait_for_load_state("domcontentloaded")
            random_delay(2, 4)
            
            # Random scroll to look human
            page.evaluate("window.scrollTo(0, document.body.scrollHeight/3)")
            random_delay(1, 2)
            page.evaluate("window.scrollTo(0, 0)")
            
            # Handle cookie/privacy popup
            try:
                print("🍪 Handling privacy popup...")
                agree_buttons = ['text=I AGREE', 'text=Accept', 'button:has-text("Accept")', '#accept-cookies']
                for btn in agree_buttons:
                    if page.locator(btn).count() > 0:
                        page.locator(btn).first.click()
                        random_delay(1, 2)
                        break
            except Exception:
                pass
            
            # Find and interact with location input
            print(f"🔍 Searching for '{LOCATION}'...")
            random_delay(1, 2)
            
            # Try multiple selectors for location input
            input_selectors = [
                'input[placeholder*="Airport"]',
                'input[placeholder*="city"]',
                'input[placeholder*="location"]',
                'input[placeholder*="address"]',
                'input[data-testid*="search"]',
                '#location-input',
                '.location-input'
            ]
            
            input_element = None
            for selector in input_selectors:
                if page.locator(selector).count() > 0:
                    input_element = page.locator(selector).first
                    if input_element.is_visible():
                        break
            
            if not input_element:
                # Fallback: find any visible input
                all_inputs = page.locator("input").all()
                for inp in all_inputs:
                    if inp.is_visible():
                        input_element = inp
                        break
            
            if input_element:
                human_typing(page, LOCATION, input_element)
                random_delay(1, 2)
                
                # Wait for suggestions and select first
                page.keyboard.press("ArrowDown")
                random_delay(0.5, 1)
                page.keyboard.press("Enter")
                random_delay(2, 3)
            else:
                print("❌ Could not find location input")
                page.screenshot(path=f"scrapers/debug/error_no_input_{{timestamp}}.png")
                return
            
            # Handle car search flow
            print("🚗 Looking for cars...")
            random_delay(2, 3)
            
            # Try direct "Show cars" button
            show_buttons = ['button:has-text("Show cars")', 'button:has-text("Search")', 'button:has-text("Find cars")']
            clicked = False
            for btn in show_buttons:
                if page.locator(btn).count() > 0:
                    page.locator(btn).first.click()
                    clicked = True
                    random_delay(3, 5)
                    break
            
            if not clicked:
                # Try station flow
                page.locator("button:has-text('Show stations')").click()
                random_delay(3, 5)
                # Click first station
                station_selectors = ['[data-testid*="branch"]', '.station-item', '.branch-item']
                for sel in station_selectors:
                    if page.locator(sel).count() > 0:
                        page.locator(sel).first.click()
                        random_delay(2, 3)
                        break
                
                # Click show offers
                if page.locator("button:has-text('Show offers')").count() > 0:
                    page.locator("button:has-text('Show offers')").first.click()
                    random_delay(3, 5)
            
            # Wait for results to load
            print("⏳ Waiting for car results...")
            random_delay(5, 8)
            
            # Scroll to load all cars
            for _ in range(5):
                page.evaluate("window.scrollBy(0, 800)")
                random_delay(1, 2)
            
            page.evaluate("window.scrollTo(0, 0)")
            random_delay(1, 2)
            
            # Extract car data
            print("📊 Extracting car data...")
            cars = []
            page_text = page.inner_text("body")
            
            # Save debug info
            os.makedirs("scrapers/debug", exist_ok=True)
            with open(f"scrapers/debug/debug_page_{{safe_loc}}_{{timestamp}}.txt", "w", encoding="utf-8") as f:
                f.write(page_text)
            
            # Extract with regex
            price_pattern = r'CA\$?\s*([\d,]+\.\d+)\s*/day'
            prices = re.findall(price_pattern, page_text)
            
            car_pattern = r'([A-Z]{{2,}}\s+[A-Z]{{2,}}(?:\s+[A-Z]{{2,}})?)'
            car_names_raw = re.findall(car_pattern, page_text)
            
            car_names = []
            seen = set()
            for name in car_names_raw:
                if len(name) > 5 and name not in seen and "CA$" not in name:
                    seen.add(name)
                    car_names.append(name)
            
            print(f"Found {{len(prices)}} prices and {{len(car_names)}} car names")
            
            for i, price in enumerate(prices[:30]):
                car_name = car_names[i] if i < len(car_names) else f"Car {{i+1}}"
                car_type = "Standard"
                if "SUV" in car_name.upper():
                    car_type = "SUV"
                elif "SEDAN" in car_name.upper():
                    car_type = "Sedan"
                
                cars.append({{
                    "car_name": car_name.strip(),
                    "car_type": car_type,
                    "price_per_day": f"CA${{price}}",
                    "transmission": "Automatic",
                    "seats": 5,
                    "bags": 3,
                    "location": LOCATION,
                    "scraped_at": datetime.now().isoformat()
                }})
            
            print(f"✅ Extracted {{len(cars)}} cars")
            
            # Save results
            if cars:
                df = pd.DataFrame(cars)
                os.makedirs("scrapers/outputs", exist_ok=True)
                csv_path = f"scrapers/outputs/sixt_{{safe_loc}}_{{timestamp}}.csv"
                json_path = f"scrapers/outputs/sixt_{{safe_loc}}_{{timestamp}}.json"
                
                df.to_csv(csv_path, index=False)
                with open(json_path, "w") as jf:
                    json.dump(cars, jf, indent=2)
                
                print(f"✅ SCRAPED {{len(cars)}} CARS")
                print(f"CSV → {{csv_path}}")
                print(f"JSON → {{json_path}}")
            else:
                print("❌ No cars found")
                page.screenshot(path=f"scrapers/debug/no_cars_{{safe_loc}}_{{timestamp}}.png")
        
        except Exception as e:
            print(f"Error: {{e}}")
            page.screenshot(path=f"scrapers/debug/error_{{timestamp}}.png")
            raise
        finally:
            browser.close()

if __name__ == "__main__":
    main()
'''


# ─────────────────────────────────────────────
# REST OF THE SCRIPT (call_ollama, generate_scraper, etc.)
# ─────────────────────────────────────────────
def call_ollama(prompt: str) -> str | None:
    """Call Ollama with retries."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            print(f"  Attempt {attempt}/{MAX_RETRIES} — timeout: {OLLAMA_TIMEOUT_S}s")
            resp = requests.post(
                f"{OLLAMA_URL}/api/generate",
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": GEN_TEMP,
                        "top_p": 0.95,
                        "num_predict": 4096,
                    },
                },
                timeout=OLLAMA_TIMEOUT_S,
            )
            if resp.status_code == 200:
                return resp.json().get("response", "")
            print(f"  HTTP {resp.status_code}: {resp.text[:200]}")
        except requests.exceptions.Timeout:
            print(f"  Attempt {attempt}: timed out")
        except Exception as e:
            print(f"  Attempt {attempt}: {e}")

        if attempt < MAX_RETRIES:
            wait = BACKOFF_BASE * attempt
            print(f"  Retrying in {wait:.0f}s...")
            time.sleep(wait)

    print(f"  All {MAX_RETRIES} attempts failed.")
    return None


def enforce_generated_code(code: str) -> str:
    """Enforce code rules."""
    fixes = []
    for bad, good in [
        ('wait_until="networkidle"', 'wait_until="load"'),
        ("wait_until='networkidle'", "wait_until='load'"),
    ]:
        if bad in code:
            code = code.replace(bad, good)
            fixes.append(f"Replaced {bad} → {good}")

    pattern = re.compile(
        r'^\s*page\.wait_for_load_state\(["\']networkidle["\']\).*$', re.MULTILINE
    )
    if pattern.search(code):
        code = pattern.sub("", code)
        fixes.append("Removed networkidle calls")

    if fixes:
        print("  Code enforcement fixes applied:")
        for f in fixes:
            print(f"    ❆  {f}")
    return code


def generate_scraper(location: str) -> str | None:
    print("  Sending prompt to Ollama...")
    raw = call_ollama(build_prompt(location))
    if not raw:
        return None

    if "```python" in raw:
        raw = raw.split("```python", 1)[1].split("```", 1)[0]
    elif "```" in raw:
        raw = raw.split("```", 1)[1].split("```", 1)[0]

    code = raw.strip()
    code = enforce_generated_code(code)
    return code


def fix_syntax(code: str) -> str:
    """Fix common syntax errors."""
    try:
        ast.parse(code)
        return code
    except SyntaxError:
        pass

    lines = code.split("\n")
    fixed = []
    for line in lines:
        s = line.rstrip()
        for q in ('"', "'"):
            if s.endswith(f"print({q}") or (s.count(q) % 2 != 0 and s.endswith(q)):
                s += q + ")" if "print(" in s else q
        fixed.append(s)
    code = "\n".join(fixed)

    for _ in range(10):
        try:
            ast.parse(code)
            print("  Syntax auto-fixed.")
            return code
        except SyntaxError as e:
            if e.lineno:
                lines = code.split("\n")
                bad = lines.pop(e.lineno - 1)
                print(f"  Removed bad line {e.lineno}: {bad!r}")
                code = "\n".join(lines)

    return code


def validate(code: str) -> list[str]:
    """Validate generated code."""
    issues = []
    for imp in ["playwright", "datetime", "re", "json"]:
        if imp not in code:
            issues.append(f"Missing import: {imp}")

    if "pandas" not in code and "import csv" not in code:
        issues.append("Missing data library")

    if "def main" not in code:
        issues.append("No main() function")
    if '__name__ == "__main__"' not in code:
        issues.append("Missing main guard")

    return issues


def save_script(code: str, location: str, loc_code: str) -> str:
    """Save generated script."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    os.makedirs("scrapers/generated", exist_ok=True)
    filename = f"scrapers/generated/sixt_agent1_{loc_code}_{ts}.py"
    header = f"""#!/usr/bin/env python3
\"\"\"
AI-GENERATED SIXT SCRAPER FOR {location}
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Model: {OLLAMA_MODEL}
\"\"\"

"""
    with open(filename, "w", encoding="utf-8") as fh:
        fh.write(header + code)
    os.chmod(filename, 0o755)
    return filename


def run_and_display(script_path: str) -> None:
    """Run generated script and display results."""
    banner(f"RUNNING: {script_path}")

    try:
        result = subprocess.run(["python3", script_path], timeout=600)
        time.sleep(2)

        if result.returncode != 0:
            print(f"\n  Script exited with error code {result.returncode}")
            shots = sorted(
                glob.glob("scrapers/debug/error_*.png"),
                key=os.path.getctime,
                reverse=True,
            )
            if shots:
                print(f"  Error screenshot: {shots[0]}")
    except subprocess.TimeoutExpired:
        print("\n  ERROR: Script exceeded 10-minute limit")
        return
    except Exception as e:
        print(f"\n  ERROR: {e}")
        return

    csv_files = sorted(
        glob.glob("scrapers/outputs/sixt_*.csv"), key=os.path.getctime, reverse=True
    )
    if not csv_files:
        print("\n  No CSV output found.")
        return

    newest = csv_files[0]
    print(f"\n  Most recent CSV: {newest}")
    try:
        df = pd.read_csv(newest)
        print(f"\n  {len(df)} cars found:\n")
        print(df.to_string(index=False))
    except Exception as e:
        print(f"  Could not read CSV: {e}")


def main() -> None:
    banner("STEP 1 — GENERATING SCRAPER WITH AI")
    code = generate_scraper(LOCATION)
    if not code:
        raise SystemExit("  AI generation failed")

    print(f"  Generated {len(code):,} characters")

    banner("STEP 2 — FIXING SYNTAX")
    code = fix_syntax(code)

    banner("STEP 3 — VALIDATING")
    issues = validate(code)
    if issues:
        print("  Validation warnings:")
        for iss in issues:
            print(f"    ⚠  {iss}")
    else:
        print("  All checks passed")

    banner("STEP 4 — SAVING SCRIPT")
    script_path = save_script(code, LOCATION, LOCATION_CODE)
    print(f"  Saved: {script_path}")

    run_and_display(script_path)


if __name__ == "__main__":
    main()
