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
    """Scroll to load more products"""
    print(f"Scrolling to load more products (scroll {scroll_count})...")
    
    # Scroll to the bottom of the page
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    
    # Wait for new content to load
    time.sleep(2)
    
    # Check if there's a loading indicator or if more products appear
    try:
        page.wait_for_function("""
            () => {
                const loadingIndicator = document.querySelector('.loading, .spinner, [aria-busy="true"]');
                return loadingIndicator === null;
            }
        """, timeout=5000)
    except:
        time.sleep(1)
    
    # Check if we've reached the end
    end_of_content = page.evaluate("""
        () => {
            return document.body.textContent.includes('No more') || 
                   document.body.textContent.includes('End of') ||
                   document.body.textContent.includes('All products loaded') ||
                   document.querySelector('[data-end-of-list]') !== null;
        }
    """)
    
    return not end_of_content

def extract_product_data(page):
    """Extract all product data with scrolling to load more products"""
    print("Extracting product data...")
    
    all_products = []
    seen_ids = set()
    scroll_count = 0
    max_scrolls = 200  # Increased for 1800 products
    no_new_products_count = 0
    previous_product_count = 0
    
    while scroll_count < max_scrolls:
        print(f"Processing after {scroll_count} scrolls...")
        
        # Wait for product grid to be visible
        page.wait_for_selector('.grid > div', timeout=10000)
        
        # Get all product cards
        product_cards = page.query_selector_all('.grid > div')
        current_product_count = len(product_cards)
        print(f"Found {current_product_count} total products so far")
        
        # If no new products were loaded, check if we're done
        if current_product_count == previous_product_count:
            no_new_products_count += 1
            if no_new_products_count >= 3:
                print("No new products loaded in consecutive scrolls. Assuming all products loaded.")
                break
        else:
            no_new_products_count = 0
            previous_product_count = current_product_count
        
        # Extract data from each product card
        new_products_count = 0
        for i, card in enumerate(product_cards):
            try:
                # Get the visible text content first for debugging
                card_text = card.inner_text()
                
                # Extract product ID - more precise method
                id_element = card.query_selector('p.text-xs.text-muted-foreground.font-mono')
                if not id_element:
                    id_element = card.query_selector('p.font-mono')
                
                product_id = "N/A"
                if id_element:
                    id_text = id_element.inner_text().strip()
                    if 'ID:' in id_text:
                        product_id = id_text.split('ID:')[1].strip().split()[0]  # Get only the ID number
                
                # Skip if we've already processed this product or no ID found
                if product_id in seen_ids or product_id == "N/A":
                    continue
                
                seen_ids.add(product_id)
                new_products_count += 1
                
                # Extract product name - more precise selector
                name_element = card.query_selector('h3.font-semibold')
                if not name_element:
                    name_element = card.query_selector('h3')
                name = name_element.inner_text().strip() if name_element else "N/A"
                
                # Extract category - look for the badge with specific classes
                category_element = card.query_selector('.inline-flex.items-center.rounded-full.border.px-2\\.5.py-0\\.5.text-xs')
                if not category_element:
                    category_element = card.query_selector('[class*="rounded-full"][class*="border"][class*="px-2.5"][class*="py-0.5"][class*="text-xs"]')
                category = category_element.inner_text().strip() if category_element else "N/A"
                
                # Extract details using more precise selectors
                details = {
                    "dimensions": "N/A",
                    "color": "N/A",
                    "price": "N/A",
                    "brand": "N/A",
                    "mass": "N/A"
                }
                
                # Get all detail items using the specific structure
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
                
                # Extract updated date - more precise selector
                updated_element = card.query_selector('div.items-center.p-6.pt-2.border-t span')
                updated = "N/A"
                if updated_element:
                    updated_text = updated_element.inner_text().strip()
                    if 'Updated:' in updated_text:
                        updated = updated_text.split('Updated:')[1].strip()
                
                # Create product data object
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
                
                # Print sample for verification
                if len(all_products) % 100 == 0:
                    print(f"Sample product {len(all_products)}: {product_data['name']} (ID: {product_data['id']})")
                
            except Exception as e:
                print(f"Error extracting product {i}: {e}")
                continue
        
        print(f"Added {new_products_count} new products in this batch")
        
        # If we've found 1800+ products, we're probably done
        if len(all_products) >= 1800:
            print(f"Reached target of {len(all_products)} products")
            break
        
        # Scroll to load more products
        scroll_count += 1
        has_more_content = scroll_to_load_more(page, scroll_count)
        
        if not has_more_content:
            print("Reached end of content")
            break
        
        # Add a small random delay
        time.sleep(random.uniform(0.5, 1.5))
    
    print(f"Extracted {len(all_products)} products in total after {scroll_count} scrolls")
    
    # Verify we have the expected number
    if len(all_products) < 1830:
        print(f"Warning: Expected 1830 products but only found {len(all_products)}")
    
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
            
            # Print a sample of the extracted data for verification
            print("\nSample of extracted data:")
            for i, product in enumerate(products[:3]):
                print(f"Product {i+1}: {product}")
            
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
