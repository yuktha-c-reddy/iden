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

def scroll_to_load_more(page, scroll_count):
    """Scroll to load more products with better detection"""
    print(f"Scrolling to load more products (scroll {scroll_count})...")
    
    # Get current product count before scrolling
    previous_count = page.evaluate("() => document.querySelectorAll('.grid > div').length")
    
    # Scroll to the bottom of the page
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    
    # Wait for potential new content with longer timeout
    time.sleep(3)
    
    # Check if new products were loaded
    new_count = page.evaluate("() => document.querySelectorAll('.grid > div').length")
    
    print(f"Products before scroll: {previous_count}, after scroll: {new_count}")
    
    # If no new products, try scrolling again with different approach
    if new_count == previous_count:
        print("No new products detected, trying alternative scroll method...")
        
        # Try scrolling to a specific element near the bottom
        page.evaluate("""
            () => {
                const lastProduct = document.querySelectorAll('.grid > div');
                if (lastProduct.length > 0) {
                    lastProduct[lastProduct.length - 1].scrollIntoView();
                }
            }
        """)
        time.sleep(2)
        
        # Check again
        new_count = page.evaluate("() => document.querySelectorAll('.grid > div').length")
        print(f"Products after alternative scroll: {new_count}")
    
    # Return True if we should continue scrolling (we might not be at the end yet)
    return new_count < 1830  # Continue until we reach 1830 products

def extract_product_data(page):
    """Extract all product data with improved scrolling"""
    print("Extracting product data...")
    
    all_products = []
    seen_ids = set()
    scroll_count = 0
    max_scrolls = 250  # Increased for 1830 products
    consecutive_no_new_products = 0
    
    # First, let's make sure we scroll until we have exactly 1830 products
    while scroll_count < max_scrolls and len(seen_ids) < 1830:
        print(f"Scroll {scroll_count + 1}, Current products: {len(seen_ids)}/1830")
        
        # Wait for product grid
        page.wait_for_selector('.grid > div', timeout=10000)
        
        # Get all visible product cards
        product_cards = page.query_selector_all('.grid > div')
        current_count = len(product_cards)
        
        print(f"Visible products: {current_count}")
        
        # Extract data from all visible cards
        new_products_count = 0
        for i, card in enumerate(product_cards):
            try:
                # Extract product ID
                id_element = card.query_selector('p.text-xs.text-muted-foreground.font-mono')
                if not id_element:
                    id_element = card.query_selector('p.font-mono')
                
                product_id = "N/A"
                if id_element:
                    id_text = id_element.inner_text().strip()
                    if 'ID:' in id_text:
                        product_id = id_text.split('ID:')[1].strip().split()[0]
                
                # Skip if already processed or invalid ID
                if product_id in seen_ids or product_id == "N/A":
                    continue
                
                seen_ids.add(product_id)
                new_products_count += 1
                
                # Extract other product details
                name_element = card.query_selector('h3.font-semibold') or card.query_selector('h3')
                name = name_element.inner_text().strip() if name_element else "N/A"
                
                category_element = card.query_selector('.inline-flex.items-center.rounded-full.border.px-2\\.5.py-0\\.5.text-xs')
                category = category_element.inner_text().strip() if category_element else "N/A"
                
                # Extract details
                details = {"dimensions": "N/A", "color": "N/A", "price": "N/A", "brand": "N/A", "mass": "N/A"}
                
                detail_items = card.query_selector_all('dl.space-y-2.text-sm > div.flex.items-center.justify-between')
                for item in detail_items:
                    dt = item.query_selector('dt.text-muted-foreground')
                    dd = item.query_selector('dd.font-medium')
                    
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
                            details["mass"] = f"{value} kg" if value and 'kg' not in value else value
                
                # Extract updated date
                updated_element = card.query_selector('div.items-center.p-6.pt-2.border-t span')
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
                print(f"Error extracting product {i}: {e}")
                continue
        
        print(f"New products extracted: {new_products_count}")
        
        # Check if we've reached the target
        if len(seen_ids) >= 1830:
            print(f"Successfully reached target of 1830 products!")
            break
        
        # If no new products were found in this batch
        if new_products_count == 0:
            consecutive_no_new_products += 1
            print(f"No new products found ({consecutive_no_new_products}/3)")
            
            if consecutive_no_new_products >= 3:
                print("Stopping - no new products found in 3 consecutive checks")
                break
        else:
            consecutive_no_new_products = 0
        
        # Scroll to load more products
        scroll_count += 1
        should_continue = scroll_to_load_more(page, scroll_count)
        
        if not should_continue:
            print("Scroll detected we should stop")
            break
        
        # Random delay to avoid detection
        time.sleep(random.uniform(1, 2))
    
    # Final check to make sure we have all products
    print(f"Final product count: {len(all_products)}")
    
    if len(all_products) < 1830:
        print(f"Warning: Only found {len(all_products)} products out of 1830")
        print("Trying one final scroll and extraction...")
        
        # One final attempt to get remaining products
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(3)
        
        # Extract any remaining products
        product_cards = page.query_selector_all('.grid > div')
        for card in product_cards:
            try:
                id_element = card.query_selector('p.font-mono')
                if id_element:
                    id_text = id_element.inner_text().strip()
                    if 'ID:' in id_text:
                        product_id = id_text.split('ID:')[1].strip().split()[0]
                        if product_id not in seen_ids:
                            # Extract this product (simplified extraction)
                            print(f"Found additional product ID: {product_id}")
                            # You could add full extraction logic here
            except:
                pass
    
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
            products = extract_product_data(page)
            
            # Export data to JSON
            with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
                json.dump(products, f, indent=2, ensure_ascii=False)
            
            print(f"Data successfully exported to {OUTPUT_FILE}")
            print(f"Total products extracted: {len(products)}")
            
            # Show sample data
            print("\nFirst 3 products:")
            for i, product in enumerate(products[:3]):
                print(f"{i+1}. {product}")
            
            print("\nLast 3 products:")
            for i, product in enumerate(products[-3:]):
                print(f"{len(products)-2+i}. {product}")
            
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
