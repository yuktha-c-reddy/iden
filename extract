import json
import os
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# Configuration
CREDENTIALS = {
    "username": "username",  
    "password": "password"   
}
SESSION_FILE = "session.json"
BASE_URL = "https://example.com"  
OUTPUT_FILE = "products.json"

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
    """Authenticate with the application"""
    print("Authenticating...")
    
    # Navigate to login page (update selectors as needed)
    page.goto(f"{BASE_URL}/login")
    
    # Fill in credentials (update selectors as needed)
    page.fill('input[name="username"]', CREDENTIALS["username"])
    page.fill('input[name="password"]', CREDENTIALS["password"])
    
    # Click login button (update selector as needed)
    page.click('button[type="submit"]')
    
    # Wait for navigation to complete
    page.wait_for_url("**/dashboard**")  # Update pattern as needed
    
    print("Authentication successful")
    return page.context.storage_state()

def navigate_to_products(page):
    """Navigate through the hidden path to the product table"""
    print("Navigating to product table...")
    
    # These selectors and steps need to be customized based on the actual application
    # Example navigation flow:
    
    # Step 1: Click on main menu
    page.click('button:has-text("Menu")')
    
    # Step 2: Click on products section
    page.click('a:has-text("Products")')
    
    # Step 3: Wait for products page to load
    page.wait_for_selector('h1:has-text("Products")')
    
    # Step 4: Click on advanced view
    page.click('button:has-text("Advanced View")')
    
    # Step 5: Wait for table to load
    page.wait_for_selector('table.product-table')
    
    print("Successfully navigated to product table")

def extract_table_data(page):
    """Extract all data from the product table with pagination handling"""
    print("Extracting product data...")
    
    all_products = []
    page_num = 1
    
    while True:
        print(f"Processing page {page_num}...")
        
        # Wait for table to be fully loaded
        page.wait_for_selector('table.product-table tbody tr')
        
        # Extract table headers if first page
        if page_num == 1:
            headers = []
            header_elements = page.query_selector_all('table.product-table thead th')
            for header in header_elements:
                headers.append(header.inner_text().strip().lower().replace(' ', '_'))
        
        # Extract table rows
        rows = page.query_selector_all('table.product-table tbody tr')
        
        for row in rows:
            cells = row.query_selector_all('td')
            product_data = {}
            
            for i, cell in enumerate(cells):
                if i < len(headers):
                    product_data[headers[i]] = cell.inner_text().strip()
            
            all_products.append(product_data)
        
        # Check for and click next page button if available
        next_button = page.query_selector('button.next-page:not([disabled])')
        if next_button:
            next_button.click()
            # Wait for next page to load
            page.wait_for_function("""
                () => {
                    const currentPage = document.querySelector('.pagination .active');
                    return currentPage && parseInt(currentPage.textContent) > """ + str(page_num) + """;
                }
            """, timeout=10000)
            page_num += 1
        else:
            break
    
    print(f"Extracted {len(all_products)} products")
    return all_products

def main():
    with sync_playwright() as p:
        # Launch browser
        browser = p.chromium.launch(headless=False)  # Set headless=True for production
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
        
        # Set default timeout
        page.set_default_timeout(30000)
        
        try:
            # Navigate to base URL to check if already authenticated
            page.goto(BASE_URL)
            
            # Check if we're on login page or already logged in
            if page.url.endswith('/login') or page.query_selector('input[name="username"]'):
                # Need to authenticate
                storage_state = authenticate(page)
                save_session(storage_state)
            
            # Navigate to products table
            navigate_to_products(page)
            
            # Extract data from table
            products = extract_table_data(page)
            
            # Export data to JSON
            with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
                json.dump(products, f, indent=2, ensure_ascii=False)
            
            print(f"Data successfully exported to {OUTPUT_FILE}")
            
        except PlaywrightTimeoutError as e:
            print(f"Timeout error: {e}")
        except Exception as e:
            print(f"An error occurred: {e}")
        finally:
            # Close browser
            browser.close()

if __name__ == "__main__":
    main()
