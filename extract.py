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
    page.wait_for_url(INSTRUCTIONS_URL, timeout=15000)
    
    print("Authentication successful")
    return page.context.storage_state()

def navigate_to_challenge(page):
    """Navigate to the challenge page"""
    print("Navigating to challenge...")
    
    # Click the launch challenge button
    launch_button = page.wait_for_selector('button:has-text("Launch Challenge")', timeout=10000)
    launch_button.click()
    print("Clicked launch challenge")
    # Wait for challenge page to load
    page.wait_for_url(CHALLENGE_URL, timeout=15000)
    page.wait_for_selector('.product-card', timeout=10000)
    
    print("Successfully navigated to challenge page")

def extract_product_data(page):
    """Extract all product data from the cards with pagination handling"""
    print("Extracting product data...")
    
    all_products = []
    page_count = 1
    
    while True:
        print(f"Processing page {page_count}...")
        
        # Wait for product cards to be visible
        page.wait_for_selector('.product-card', timeout=10000)
        
        # Get all product cards
        product_cards = page.query_selector_all('.product-card')
        
        print(f"Found {len(product_cards)} products on page {page_count}")
        
        # Extract data from each product card
        for card in product_cards:
            try:
                # Extract basic information
                name = card.query_selector('.product-name, h2, h3, h4').inner_text().strip()
                category = card.query_selector('.product-category, .category').inner_text().strip()
                
                # Extract ID - looking for text that contains "ID:"
                id_text = card.query_selector('*:has-text("ID:")').inner_text()
                product_id = id_text.split('ID:')[1].strip().split()[0] if 'ID:' in id_text else "N/A"
                
                # Initialize product data
                product_data = {
                    "id": product_id,
                    "name": name,
                    "category": category,
                    "dimensions": "N/A",
                    "color": "N/A",
                    "price": "N/A",
                    "brand": "N/A",
                    "mass": "N/A",
                    "updated": "N/A"
                }
                
                # Extract details that might be in various formats
                card_text = card.inner_text()
                
                # Extract dimensions
                if 'Dimensions:' in card_text:
                    dimensions_part = card_text.split('Dimensions:')[1].split('\n')[0].strip()
                    product_data["dimensions"] = dimensions_part
                
                # Extract color
                if 'Color:' in card_text:
                    color_part = card_text.split('Color:')[1].split('\n')[0].strip()
                    product_data["color"] = color_part
                
                # Extract price
                if 'Price:' in card_text:
                    price_part = card_text.split('Price:')[1].split('\n')[0].strip()
                    product_data["price"] = price_part
                
                # Extract brand
                if 'Brand:' in card_text:
                    brand_part = card_text.split('Brand:')[1].split('\n')[0].strip()
                    product_data["brand"] = brand_part
                
                # Extract mass
                if 'Mass' in card_text and 'kg' in card_text:
                    mass_part = card_text.split('Mass')[1].split('kg')[0].strip()
                    if ':' in mass_part:
                        mass_part = mass_part.split(':')[1].strip()
                    product_data["mass"] = f"{mass_part} kg"
                
                # Extract updated date
                if 'Updated:' in card_text:
                    updated_part = card_text.split('Updated:')[1].split('\n')[0].strip()
                    product_data["updated"] = updated_part
                
                all_products.append(product_data)
                
            except Exception as e:
                print(f"Error extracting product: {e}")
                continue
        
        # Check for pagination and navigate to next page if available
        try:
            # Look for next page button - this might need adjustment based on actual UI
            next_button = page.query_selector('button:has-text("Next"), .next-page, [aria-label="Next page"]')
            
            if next_button and not next_button.get_attribute('disabled'):
                print("Moving to next page...")
                next_button.click()
                # Wait for page to load
                time.sleep(2)  # Adjust as needed
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
        browser = p.chromium.launch(headless=True)  # Set to True for headless execution
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
            if page.url == LOGIN_URL or page.query_selector('input[name="username"]'):
                # Need to authenticate
                storage_state = authenticate(page)
                save_session(storage_state)
            
            # If we're on instructions page, navigate to challenge
            if page.url == INSTRUCTIONS_URL:
                navigate_to_challenge(page)
            
            # If we're not on challenge page yet, navigate to it
            if page.url != CHALLENGE_URL:
                page.goto(CHALLENGE_URL)
                page.wait_for_selector('.product-card', timeout=10000)
            
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
