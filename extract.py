import json
import os
import time
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# Configuration
CREDENTIALS = {
    "username": "c.yuktha@campusuvce.in",  
    "password": "password"   
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

def debug_page_content(page, filename="debug_page.html"):
    """Save page content for debugging"""
    content = page.content()
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Page content saved to {filename}")

def take_screenshot(page, filename="debug_screenshot.png"):
    """Take screenshot for debugging"""
    page.screenshot(path=filename)
    print(f"Screenshot saved to {filename}")

def authenticate(page):
    """Authenticate with the IdenHQ application"""
    print("Authenticating...")
    
    # Navigate to login page
    page.goto(LOGIN_URL)
    
    # Wait for login form to load
    try:
        page.wait_for_selector('input[type="email"]', timeout=15000)
        print("Found email input field")
        
        # Fill in credentials
        page.fill('input[type="email"]', CREDENTIALS["username"])
        print("Filled email/username")
        
        # Find and fill password field
        page.fill('input[type="password"]', CREDENTIALS["password"])
        print("Filled password")
        
        # Click login button
        login_button = page.query_selector('button[type="submit"]')
        if login_button:
            login_button.click()
            print("Clicked login button")
        else:
            # Try pressing Enter as fallback
            page.keyboard.press('Enter')
            print("Pressed Enter to submit form")
        
        # Wait for navigation to instructions page
        try:
            page.wait_for_url(INSTRUCTIONS_URL, timeout=20000)
            print("Authentication successful - reached instructions page")
            return page.context.storage_state()
        except PlaywrightTimeoutError:
            # Check if we're on a different page
            print(f"Timeout waiting for instructions page. Current URL: {page.url}")
            if "challenge" in page.url:
                print("Already on challenge page - authentication successful")
                return page.context.storage_state()
            else:
                debug_page_content(page, "post_login_page.html")
                take_screenshot(page, "post_login.png")
                return None
                
    except PlaywrightTimeoutError as e:
        print(f"Timeout waiting for login form: {e}")
        debug_page_content(page, "login_page.html")
        take_screenshot(page, "login_page.png")
        return None
    except Exception as e:
        print(f"Error during authentication: {e}")
        debug_page_content(page, "auth_error_page.html")
        take_screenshot(page, "auth_error.png")
        return None

def navigate_to_challenge(page):
    """Navigate to the challenge page"""
    print("Navigating to challenge...")
    
    # Try to find and click the launch challenge button
    try:
        launch_button = page.wait_for_selector('button:has-text("Launch Challenge")', timeout=10000)
        launch_button.click()
        print("Clicked Launch Challenge button")
        
        # Wait for challenge page to load
        try:
            page.wait_for_url(CHALLENGE_URL, timeout=15000)
            print("Successfully navigated to challenge page")
            return True
        except PlaywrightTimeoutError:
            print(f"Timeout waiting for challenge page. Current URL: {page.url}")
            # Check if we're already on the challenge page
            if "challenge" in page.url:
                print("Already on challenge page")
                return True
            return False
            
    except Exception as e:
        print(f"Error clicking launch button: {e}")
        return False

def extract_product_data(page):
    """Extract all product data from the cards with pagination handling"""
    print("Extracting product data...")
    
    # Wait for products to load
    try:
        page.wait_for_selector('.product-card, .card, [data-product]', timeout=10000)
    except:
        print("No product cards found initially")
        debug_page_content(page, "products_page.html")
        take_screenshot(page, "products_page.png")
        return []
    
    all_products = []
    page_count = 1
    max_pages = 10  # Safety limit to prevent infinite loops
    
    while page_count <= max_pages:
        print(f"Processing page {page_count}...")
        
        # Wait for product cards to be visible
        try:
            page.wait_for_selector('.product-card, .card, [data-product]', timeout=10000)
        except:
            print("No product cards found on this page")
            break
        
        # Get all product cards
        product_cards = page.query_selector_all('.product-card, .card, [data-product]')
        
        print(f"Found {len(product_cards)} products on page {page_count}")
        
        if len(product_cards) == 0:
            print("No products found, stopping extraction")
            break
        
        # Extract data from each product card
        for i, card in enumerate(product_cards):
            try:
                # Get all text content
                card_text = card.inner_text()
                
                # Extract ID
                product_id = "N/A"
                if 'ID:' in card_text:
                    id_part = card_text.split('ID:')[1].strip()
                    product_id = id_part.split()[0] if id_part else "N/A"
                
                # Extract name - try to find a heading element
                name = "N/A"
                heading_selectors = ['h2', 'h3', 'h4', '.product-name', '.name', '.title']
                for selector in heading_selectors:
                    try:
                        heading = card.query_selector(selector)
                        if heading:
                            name = heading.inner_text().strip()
                            break
                    except:
                        continue
                
                if name == "N/A":
                    # Try to extract name from text
                    lines = card_text.split('\n')
                    if lines:
                        name = lines[0].strip()
                
                # Extract category
                category = "N/A"
                category_indicators = {
                    'Clothing': 'Clothing',
                    'Electronics': 'Electronics', 
                    'Health': 'Health',
                    'Office': 'Office',
                    'Sports': 'Sports'
                }
                
                for indicator, cat in category_indicators.items():
                    if indicator in card_text:
                        category = cat
                        break
                
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
                
                # Extract details from text
                if 'Dimensions:' in card_text:
                    dimensions_part = card_text.split('Dimensions:')[1].split('\n')[0].strip()
                    product_data["dimensions"] = dimensions_part
                
                if 'Color:' in card_text:
                    color_part = card_text.split('Color:')[1].split('\n')[0].strip()
                    product_data["color"] = color_part
                
                if 'Price:' in card_text:
                    price_part = card_text.split('Price:')[1].split('\n')[0].strip()
                    product_data["price"] = price_part
                
                if 'Brand:' in card_text:
                    brand_part = card_text.split('Brand:')[1].split('\n')[0].strip()
                    product_data["brand"] = brand_part
                
                if 'Mass' in card_text and 'kg' in card_text:
                    mass_text = card_text.split('Mass')[1].split('kg')[0].strip()
                    if ':' in mass_text:
                        mass_text = mass_text.split(':')[1].strip()
                    product_data["mass"] = f"{mass_text} kg"
                
                if 'Updated:' in card_text:
                    updated_part = card_text.split('Updated:')[1].split('\n')[0].strip()
                    product_data["updated"] = updated_part
                
                all_products.append(product_data)
                
            except Exception as e:
                print(f"Error extracting product {i}: {e}")
                continue
        
        # Check for pagination
        try:
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
            print(f"Error with pagination: {e}")
            break
    
    print(f"Extracted {len(all_products)} products in total")
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
            # Navigate to base URL
            print(f"Navigating to {BASE_URL}")
            page.goto(BASE_URL)
            
            # Check if we need to login
            if page.url == LOGIN_URL or "login" in page.url.lower() or page.query_selector('input[type="email"]'):
                print("Login page detected")
                storage_state = authenticate(page)
                if storage_state:
                    save_session(storage_state)
                    print("Authentication successful, session saved")
                else:
                    print("Authentication failed")
                    return
            
            # Check if we're on instructions page
            if page.url == INSTRUCTIONS_URL or "instructions" in page.url.lower():
                print("On instructions page")
                if navigate_to_challenge(page):
                    print("Navigated to challenge successfully")
                else:
                    print("Failed to navigate to challenge")
                    # Try direct navigation
                    page.goto(CHALLENGE_URL)
            
            # Make sure we're on challenge page
            if "challenge" not in page.url:
                print(f"Not on challenge page, current URL: {page.url}")
                page.goto(CHALLENGE_URL)
            
            # Wait for challenge page to load
            try:
                page.wait_for_selector('.product-card, .card, [data-product]', timeout=10000)
                print("Challenge page loaded successfully")
            except:
                print("Challenge page elements not found")
                debug_page_content(page, "challenge_debug.html")
                take_screenshot(page, "challenge_debug.png")
            
            # Extract product data
            products = extract_product_data(page)
            
            # Export data to JSON
            with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
                json.dump(products, f, indent=2, ensure_ascii=False)
            
            print(f"Data successfully exported to {OUTPUT_FILE}")
            
        except PlaywrightTimeoutError as e:
            print(f"Timeout error: {e}")
        except Exception as e:
            print(f"An error occurred: {e}")
            debug_page_content(page, "error_page.html")
            take_screenshot(page, "error_screenshot.png")
        finally:
            # Close browser
            browser.close()

if __name__ == "__main__":
    main()
