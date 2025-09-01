import json
import os
import time
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

def extract_product_data(page):
    """Extract all product data from the grid with pagination handling"""
    print("Extracting product data...")
    
    all_products = []
    page_count = 1
    
    while True:
        print(f"Processing page {page_count}...")
        
        # Wait for product grid to be visible
        page.wait_for_selector('.grid > div', timeout=10000)
        
        # Get all product cards (each div in the grid)
        product_cards = page.query_selector_all('.grid > div')
        
        print(f"Found {len(product_cards)} products on page {page_count}")
        
        # Extract data from each product card
        for card in product_cards:
            try:
                # Extract product name
                name_element = card.query_selector('h3')
                name = name_element.inner_text().strip() if name_element else "N/A"
                
                # Extract category from the badge
                category_element = card.query_selector('[class*="rounded-full"][class*="border"][class*="px-2.5"][class*="py-0.5"][class*="text-xs"]')
                category = category_element.inner_text().strip() if category_element else "N/A"
                
                # Extract ID from the monospace text
                id_element = card.query_selector('p.font-mono')
                product_id = "N/A"
                if id_element:
                    id_text = id_element.inner_text().strip()
                    if 'ID:' in id_text:
                        product_id = id_text.split('ID:')[1].strip()
                
                # Extract details from the description list
                details = {
                    "dimensions": "N/A",
                    "color": "N/A",
                    "price": "N/A",
                    "brand": "N/A",
                    "mass": "N/A"
                }
                
                # Get all detail items
                detail_items = card.query_selector_all('dl.text-sm > div')
                for item in detail_items:
                    dt = item.query_selector('dt')
                    dd = item.query_selector('dd')
                    if dt and dd:
                        key = dt.inner_text().strip().lower().replace(':', '').replace(' (kg)', '').replace(' ', '_')
                        value = dd.inner_text().strip()
                        
                        if 'mass' in key:
                            details['mass'] = f"{value} kg"
                        elif 'dimensions' in key:
                            details['dimensions'] = value
                        elif 'color' in key:
                            details['color'] = value
                        elif 'price' in key:
                            details['price'] = value
                        elif 'brand' in key:
                            details['brand'] = value
                
                # Extract updated date
                updated_element = card.query_selector('span:has-text("Updated:")')
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
                
            except Exception as e:
                print(f"Error extracting product: {e}")
                continue
        
        # Check for pagination and navigate to next page if available
        try:
            # Look for next page button
            next_button = page.query_selector('button:has-text("Next"), [aria-label="Next page"]')
            
            if next_button and not next_button.get_attribute('disabled'):
                print("Moving to next page...")
                next_button.click()
                # Wait for page to load
                time.sleep(2)
                page_count += 1
            else:
                print("No more pages available")
                break
                
        except Exception as e:
            print(f"Error navigating to next page: {e}")
            break
    
    print(f"Extracted {len(all_products)} products in total")
    return all_products

def main():
    with sync_playwright() as p:
        # Launch browser
        browser = p.chromium.launch(headless=False)  # Set to False to see what's happening
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
            
            # Extract data from product cards
            products = extract_product_data(page)
            
            # Export data to JSON
            with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
                json.dump(products, f, indent=2, ensure_ascii=False)
            
            print(f"Data successfully exported to {OUTPUT_FILE}")
            
        except PlaywrightTimeoutError as e:
            print(f"Timeout error: {e}")
        except Exception as e:
            print(f"An error occurred: {e}")
            # Take screenshot for debugging
            page.screenshot(path="error_screenshot.png")
            print("Screenshot saved as error_screenshot.png")
        finally:
            # Close browser
            browser.close()

if __name__ == "__main__":
    main()
