import json
import os
import time
import random
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# Configuration
CREDENTIALS = {
    "username": "c.yuktha@campusuvce.in",  
    "password": "R5yS3PJD"   
}
SESSION_FILE = "idenhq_session.json"
BASE_URL = "https://hiring.idenhq.com"
LOGIN_URL = f"{BASE_URL}/"
INSTRUCTIONS_URL = f"{BASE_URL}/instructions"
CHALLENGE_URL = f"{BASE_URL}/challenge"
OUTPUT_FILE = "idenhq_products.json"

def save_session(storage_state):
    """Save session data to a file"""
    with open(SESSION_FILE, 'w') as f:
        json.dump(storage_state, f)

def load_session():
    """Load session data from file if exists"""
    if os.path.exists(SESSION_FILE):
        with open(SESSION_FILE, 'r') as f:
            return json.load(f)
    return None

def authenticate(page):
    """Authenticate with the IdenHQ application"""
    print("Authenticating...")
    
    # Navigate to login page
    page.goto(LOGIN_URL)
    
    # Wait for login form to load
    page.wait_for_selector('input[type="email"]', timeout=10000)
    
    # Fill in credentials
    page.fill('input[type="email"]', CREDENTIALS["username"])
    print("entered email")
    page.fill('input[type="password"]', CREDENTIALS["password"])
    print("entered password")
    # Click login button
    page.click('button[type="submit"]')
    
    # Wait for navigation to instructions page
    try:
        page.wait_for_url(INSTRUCTIONS_URL, timeout=15000)
        print("Authentication successful")
        return page.context.storage_state()
    except PlaywrightTimeoutError:
        print("Authentication might have succeeded but didn't navigate to instructions")
        # Check if we're on a different page that indicates success
        return page.context.storage_state()

def navigate_to_challenge(page):
    """Navigate to the challenge page"""
    print("Navigating to challenge...")
    
    # Click the launch challenge button
    try:
        launch_button = page.wait_for_selector('button:has-text("Launch Challenge")', timeout=10000)
        launch_button.click()
        print("Clicked launch challenge")
        
        # Wait for challenge page to load
        page.wait_for_url(CHALLENGE_URL, timeout=15000)
        print("Successfully navigated to challenge page")
        return True
    except PlaywrightTimeoutError:
        print("Could not find launch button or navigate to challenge")
        # Try direct navigation
        page.goto(CHALLENGE_URL)
        try:
            page.wait_for_selector('.grid > div', timeout=10000)
            print("Direct navigation to challenge succeeded")
            return True
        except PlaywrightTimeoutError:
            print("Direct navigation also failed")
            return False

def scroll_and_extract_products(page):
    """Scroll through all pages and extract products with better detection"""
    print("Starting to scroll and extract products...")
    
    all_products = []
    seen_ids = set()
    scroll_attempts = 0
    max_scroll_attempts = 100
    no_new_products_count = 0
    
    # First, let's extract the initial products
    product_cards = page.query_selector_all('.grid > div')
    print(f"Initial products found: {len(product_cards)}")
    
    while scroll_attempts < max_scroll_attempts:
        # Extract products from current view
        product_cards = page.query_selector_all('.grid > div')
        new_products = 0
        
        for card in product_cards:
            try:
                # Extract product ID
                id_element = card.query_selector('p.font-mono')
                product_id = "N/A"
                if id_element:
                    id_text = id_element.inner_text().strip()
                    if 'ID:' in id_text:
                        product_id = id_text.split('ID:')[1].strip().split()[0]
                
                # Skip if already processed
                if product_id in seen_ids or product_id == "N/A":
                    continue
                
                seen_ids.add(product_id)
                new_products += 1
                
                # Extract product details
                name_element = card.query_selector('h3')
                name = name_element.inner_text().strip() if name_element else "N/A"
                
                category_element = card.query_selector('[class*="rounded-full"][class*="border"]')
                category = category_element.inner_text().strip() if category_element else "N/A"
                
                # Extract details
                details = {"dimensions": "N/A", "color": "N/A", "price": "N/A", "brand": "N/A", "mass": "N/A"}
                
                detail_items = card.query_selector_all('dl > div')
                for item in detail_items:
                    dt = item.query_selector('dt')
                    dd = item.query_selector('dd')
                    
                    if dt and dd:
                        label = dt.inner_text().strip().lower()
                        value = dd.inner_text().strip()
                        
                        if 'dimensions' in label:
                            details["dimensions"] = value
                        elif 'color' in label:
                            details["color"] = value
                        elif 'price' in label:
                            details["price"] = value
                        elif 'brand' in label:
                            details["brand"] = value
                        elif 'mass' in label:
                            details["mass"] = f"{value} kg"
                
                # Extract updated date
                updated_element = card.query_selector('span:has-text("Updated:")')
                updated = "N/A"
                if updated_element:
                    updated_text = updated_element.inner_text().strip()
                    if 'Updated:' in updated_text:
                        updated = updated_text.split('Updated:')[1].strip()
                
                # Create product data
                product_data = {
                    "id": product_id,
                    "name": name,
                    "category": category,
                    "dimensions": details["dimensions"],
                    "color": details["color"],
                    "price": details["price"],
                    "brand": details["brand"],
                    "mass": details["mass"],
                    "updated": updated
                }
                
                all_products.append(product_data)
                
            except Exception as e:
                print(f"Error extracting product: {e}")
                continue
        
        print(f"Found {new_products} new products in this batch. Total: {len(all_products)}")
        
        # Check if we've reached the target
        if len(all_products) >= 1830:
            print(f"Reached target of {len(all_products)} products!")
            break
        
        # If no new products, increment counter
        if new_products == 0:
            no_new_products_count += 1
            if no_new_products_count >= 5:
                print("No new products found after 5 attempts. Stopping.")
                break
        else:
            no_new_products_count = 0
        
        # Scroll to load more products
        scroll_attempts += 1
        print(f"Scroll attempt {scroll_attempts}")
        
        # Scroll to bottom
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        
        # Wait for new content to load
        time.sleep(2)
        
        # Check if we can scroll further
        can_scroll_more = page.evaluate("""
            () => {
                return window.innerHeight + window.scrollY < document.body.scrollHeight - 100;
            }
        """)
        
        if not can_scroll_more:
            print("Cannot scroll further. Reached bottom of page.")
            break
    
    print(f"Finished scrolling. Total products extracted: {len(all_products)}")
    return all_products

def main():
    with sync_playwright() as p:
        # Launch browser
        browser = p.chromium.launch(headless=False)
        context = None
        
        # Try to load existing session
        storage_state = load_session()
        if storage_state:
            print("Using existing session...")
            context = browser.new_context(storage_state=storage_state)
        else:
            print("No existing session found")
            context = browser.new_context()
        
        page = context.new_page()
        
        # Set default timeout and viewport size
        page.set_default_timeout(30000)
        page.set_viewport_size({"width": 1280, "height": 800})
        
        try:
            # Navigate to base URL to check if already authenticated
            page.goto(BASE_URL)
            
            # Check if we're on login page or already logged in
            if page.url == LOGIN_URL or page.query_selector('input[type="email"]'):
                # Need to authenticate
                storage_state = authenticate(page)
                save_session(storage_state)
            
            # If we're on instructions page, navigate to challenge
            if page.url == INSTRUCTIONS_URL:
                if not navigate_to_challenge(page):
                    print("Failed to navigate to challenge page")
                    return
            
            # If we're not on challenge page yet, navigate to it
            if page.url != CHALLENGE_URL:
                page.goto(CHALLENGE_URL)
                try:
                    page.wait_for_selector('.grid > div', timeout=10000)
                except PlaywrightTimeoutError:
                    print("Challenge page didn't load expected elements")
                    page.screenshot(path="challenge_page.png")
                    print("Screenshot saved as challenge_page.png")
            
            # Extract data from product cards with scrolling
            products = scroll_and_extract_products(page)
            
            # If we didn't get all products, try a different approach
            if len(products) < 1830:
                print(f"Only got {len(products)} products. Trying alternative approach...")
                
                # Try scrolling to specific intervals
                for i in range(10):
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    time.sleep(1)
                    
                    # Extract any new products
                    product_cards = page.query_selector_all('.grid > div')
                    for card in product_cards:
                        try:
                            id_element = card.query_selector('p.font-mono')
                            if id_element:
                                id_text = id_element.inner_text().strip()
                                if 'ID:' in id_text:
                                    product_id = id_text.split('ID:')[1].strip().split()[0]
                                    
                                    # Check if this is a new product
                                    if not any(p['id'] == product_id for p in products):
                                        print(f"Found additional product: {product_id}")
                                        # Add to products list (simplified)
                                        products.append({"id": product_id})
                        except:
                            pass
                
                print(f"After alternative approach: {len(products)} products")
            
            # Export data to JSON
            with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
                json.dump(products, f, indent=2, ensure_ascii=False)
            
            print(f"Data successfully exported to {OUTPUT_FILE}")
            print(f"Total products extracted: {len(products)}")
            
        except PlaywrightTimeoutError as e:
            print(f"Timeout error: {e}")
        except Exception as e:
            print(f"An error occurred: {e}")
            page.screenshot(path="error_screenshot.png")
            print("Screenshot saved as error_screenshot.png")
        finally:
            browser.close()

if __name__ == "__main__":
    main()
