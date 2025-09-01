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
OUTPUT_FILE = "idenhq_products_table.json"

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
        return page.context.storage_state()

def force_table_layout(page):
    """Force the application to use table layout using multiple strategies"""
    print("Attempting to force table layout...")
    
    # Strategy 1: Modify localStorage before page loads
    page.add_init_script("""
        () => {
            localStorage.setItem('layout', 'table');
            localStorage.setItem('userLayout', 'table');
            localStorage.setItem('displayMode', 'table');
            localStorage.setItem('userConfig', JSON.stringify({layout: 'table', pathType: 'direct'}));
            
            // Set user-specific config
            localStorage.setItem('layout_ca02115b-ec7f-488c-9e47-953f6ffcd335', 'table');
            localStorage.setItem('config_ca02115b-ec7f-488c-9e47-953f6ffcd335', JSON.stringify({layout: 'table'}));
        }
    """)
    
    # Strategy 2: Intercept and modify fetch requests
    page.route("**/*", lambda route: handle_route(route))
    
    # Strategy 3: Execute scripts after page load
    page.evaluate("""
        () => {
            // Override any config loading
            const originalSetItem = localStorage.setItem;
            localStorage.setItem = function(key, value) {
                if (key === 'current_user' && value.includes('cards')) {
                    value = value.replace('"layout":"cards"', '"layout":"table"');
                    console.log('Intercepted and modified current_user to table layout');
                }
                return originalSetItem.call(this, key, value);
            };
            
            // Try to find and modify existing config objects
            for (let prop in window) {
                try {
                    if (window[prop] && typeof window[prop] === 'object' && window[prop].layout === 'cards') {
                        window[prop].layout = 'table';
                        console.log('Modified window property:', prop);
                    }
                } catch(e) {}
            }
        }
    """)

def handle_route(route):
    """Handle and modify network requests"""
    if 'config' in route.request.url or 'user' in route.request.url:
        def handle_response(response):
            try:
                body = response.body()
                if body:
                    data = json.loads(body)
                    if 'layout' in data and data['layout'] == 'cards':
                        data['layout'] = 'table'
                        modified_body = json.dumps(data).encode()
                        route.fulfill(response=response, body=modified_body)
                        return
            except:
                pass
            route.continue_()
        
        route.continue_()
    else:
        route.continue_()

def navigate_to_challenge_with_table(page):
    """Navigate to challenge and ensure table layout"""
    print("Navigating to challenge with table layout...")
    
    # First, set up the table layout interception
    force_table_layout(page)
    
    # Navigate to challenge page
    page.goto(CHALLENGE_URL)
    
    # Wait a moment for scripts to execute
    time.sleep(3)
    
    # Try multiple approaches to activate table view
    strategies = [
        # Strategy 1: Direct URL manipulation
        lambda: page.goto(f"{CHALLENGE_URL}?layout=table"),
        lambda: page.goto(f"{CHALLENGE_URL}?view=table"),
        lambda: page.goto(f"{CHALLENGE_URL}#table"),
        
        # Strategy 2: Look for UI controls
        lambda: try_click_table_control(page),
        
        # Strategy 3: Keyboard shortcuts
        lambda: page.keyboard.press('KeyT'),
        
        # Strategy 4: Force reload with modified storage
        lambda: force_reload_with_table(page),
    ]
    
    for i, strategy in enumerate(strategies):
        try:
            print(f"Trying strategy {i+1}...")
            strategy()
            time.sleep(2)
            
            # Check if we successfully got table layout
            if check_for_table_layout(page):
                print(f"✅ Table layout activated with strategy {i+1}!")
                return True
                
        except Exception as e:
            print(f"Strategy {i+1} failed: {e}")
            continue
    
    print("⚠️ Could not activate table layout, will try to extract from current view")
    return False

def try_click_table_control(page):
    """Try to find and click table layout controls"""
    selectors = [
        "button[data-layout='table']",
        "button:has-text('Table')",
        "[data-view='table']",
        ".layout-toggle",
        ".table-view",
        ".view-table",
        "button[aria-label*='table' i]"
    ]
    
    for selector in selectors:
        try:
            element = page.wait_for_selector(selector, timeout=3000)
            if element:
                element.click()
                print(f"Clicked table control: {selector}")
                return True
        except:
            continue
    return False

def force_reload_with_table(page):
    """Force reload with table configuration"""
    page.evaluate("""
        () => {
            // Clear any existing layout config
            localStorage.removeItem('current_user');
            
            // Set up clean table config
            const tableConfig = {
                layout: 'table',
                pathType: 'direct'
            };
            localStorage.setItem('userConfig', JSON.stringify(tableConfig));
            localStorage.setItem('layout', 'table');
        }
    """)
    page.reload()

def check_for_table_layout(page):
    """Check if we're currently in table layout"""
    table_indicators = [
        "table",
        "thead",
        "tbody", 
        ".data-table",
        "[role='grid']",
        ".table-container",
        "tr:not(:first-child)"  # Table rows (not header)
    ]
    
    for selector in table_indicators:
        if page.query_selector(selector):
            print(f"Table layout detected with: {selector}")
            return True
    
    return False

def extract_from_table(page):
    """Extract data from table layout"""
    print("Extracting data from table layout...")
    
    all_products = []
    
    try:
        # Wait for table to load
        page.wait_for_selector("table, [role='grid']", timeout=10000)
        
        # Extract headers
        headers = []
        header_elements = page.query_selector_all("th, .table-header, [role='columnheader']")
        for header in header_elements:
            headers.append(header.inner_text().strip())
        
        print(f"Table headers: {headers}")
        
        # Handle pagination in table view
        page_num = 1
        while True:
            print(f"Processing table page {page_num}...")
            
            # Extract rows from current page
            rows = page.query_selector_all("tbody tr, .table-row, [role='row']:not([role='row']:has([role='columnheader']))")
            
            page_products = []
            for row in rows:
                cells = row.query_selector_all("td, .cell, .table-cell")
                if len(cells) >= len(headers):
                    product = {}
                    for i, header in enumerate(headers):
                        if i < len(cells):
                            product[header.lower()] = cells[i].inner_text().strip()
                    
                    if product:  # Only add non-empty products
                        page_products.append(product)
            
            all_products.extend(page_products)
            print(f"Extracted {len(page_products)} products from page {page_num}. Total: {len(all_products)}")
            
            # Look for next page button
            next_button = None
            next_selectors = [
                "button:has-text('Next')",
                ".pagination-next",
                "[aria-label='Next page']",
                "button[data-action='next']"
            ]
            
            for selector in next_selectors:
                try:
                    btn = page.query_selector(selector)
                    if btn and btn.is_enabled() and btn.is_visible():
                        next_button = btn
                        break
                except:
                    continue
            
            if next_button:
                next_button.click()
                time.sleep(3)
                page_num += 1
                
                # Wait for new data to load
                page.wait_for_timeout(2000)
            else:
                print("No more pages in table view")
                break
                
            # Safety check
            if page_num > 50:
                print("Reached maximum pages limit")
                break
        
        return all_products
        
    except Exception as e:
        print(f"Error extracting from table: {e}")
        return []

def extract_from_cards_with_table_attempt(page):
    """Fallback: Extract from cards but try to get table data structure"""
    print("Extracting from cards layout with table structure mapping...")
    
    all_products = []
    seen_ids = set()
    scroll_attempts = 0
    max_scroll_attempts = 100
    no_new_products_count = 0
    
    # Expected table structure based on console logs
    table_fields = ["id", "name", "dimensions", "color", "price", "manufacturer", "weight"]
    
    while scroll_attempts < max_scroll_attempts:
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
                
                if product_id in seen_ids or product_id == "N/A":
                    continue
                
                seen_ids.add(product_id)
                new_products += 1
                
                # Map card data to table structure
                product_data = {
                    "id": product_id,
                    "name": "N/A",
                    "dimensions": "N/A", 
                    "color": "N/A",
                    "price": "N/A",
                    "manufacturer": "N/A",
                    "weight": "N/A"
                }
                
                # Extract name
                name_element = card.query_selector('h3')
                if name_element:
                    product_data["name"] = name_element.inner_text().strip()
                
                # Extract other fields from detail items
                detail_items = card.query_selector_all('dl > div')
                for item in detail_items:
                    dt = item.query_selector('dt')
                    dd = item.query_selector('dd')
                    
                    if dt and dd:
                        label = dt.inner_text().strip().lower()
                        value = dd.inner_text().strip()
                        
                        if 'dimensions' in label:
                            product_data["dimensions"] = value
                        elif 'color' in label:
                            product_data["color"] = value
                        elif 'price' in label:
                            product_data["price"] = value
                        elif 'brand' in label or 'manufacturer' in label:
                            product_data["manufacturer"] = value
                        elif 'mass' in label or 'weight' in label:
                            # Extract just the number for weight
                            weight_val = value.replace('kg', '').strip()
                            product_data["weight"] = weight_val
                
                all_products.append(product_data)
                
            except Exception as e:
                print(f"Error extracting product: {e}")
                continue
        
        print(f"Found {new_products} new products. Total: {len(all_products)}")
        
        if len(all_products) >= 1830:
            print(f"Reached target of {len(all_products)} products!")
            break
        
        if new_products == 0:
            no_new_products_count += 1
            if no_new_products_count >= 5:
                print("No new products found. Stopping.")
                break
        else:
            no_new_products_count = 0
        
        # Scroll to load more
        scroll_attempts += 1
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(2)
        
        # Check if we can scroll more
        can_scroll_more = page.evaluate("""
            () => {
                return window.innerHeight + window.scrollY < document.body.scrollHeight - 100;
            }
        """)
        
        if not can_scroll_more:
            print("Reached bottom of page.")
            break
    
    return all_products

def try_direct_table_access(page):
    """Try various methods to access table layout directly"""
    print("🔍 Attempting to access hidden table layout...")
    
    table_access_methods = [
        # Method 1: URL parameters
        lambda: page.goto(f"{CHALLENGE_URL}?layout=table"),
        lambda: page.goto(f"{CHALLENGE_URL}?view=table"), 
        lambda: page.goto(f"{CHALLENGE_URL}?display=table"),
        lambda: page.goto(f"{CHALLENGE_URL}&layout=table"),
        
        # Method 2: Hash fragments
        lambda: page.goto(f"{CHALLENGE_URL}#table"),
        lambda: page.goto(f"{CHALLENGE_URL}#view=table"),
        
        # Method 3: Subpaths
        lambda: page.goto(f"{BASE_URL}/challenge/table"),
        lambda: page.goto(f"{BASE_URL}/table"),
        lambda: page.goto(f"{BASE_URL}/products/table"),
        lambda: page.goto(f"{BASE_URL}/challenge?mode=table"),
        
        # Method 4: Force through JavaScript
        lambda: force_js_table_switch(page),
    ]
    
    for i, method in enumerate(table_access_methods):
        try:
            print(f"  Trying method {i+1}...")
            method()
            time.sleep(3)
            
            # Check if we got table layout
            if check_for_table_elements(page):
                print(f"✅ Success! Table layout found with method {i+1}")
                return True
                
        except Exception as e:
            print(f"  Method {i+1} failed: {e}")
            continue
    
    return False

def force_js_table_switch(page):
    """Use JavaScript to force table layout"""
    page.evaluate("""
        () => {
            // Clear existing config
            localStorage.clear();
            
            // Set table config
            localStorage.setItem('layout', 'table');
            localStorage.setItem('userConfig', '{"layout":"table","pathType":"direct"}');
            
            // Set user-specific config with correct user ID
            const userId = 'ca02115b-ec7f-488c-9e47-953f6ffcd335';
            localStorage.setItem(`layout_${userId}`, 'table');
            localStorage.setItem(`config_${userId}`, '{"layout":"table"}');
            
            // Create current_user with table layout
            const currentUser = {
                id: userId,
                email: "c.yuktha@campusuvce.in", 
                role: "candidate",
                config: {
                    fields: ["id","name","dimensions","color","price","manufacturer","weight"],
                    layout: "table",
                    pathType: "direct",
                    fieldNames: {
                        id: "ID", name: "Product", dimensions: "Dimensions", 
                        color: "Color", price: "Price", manufacturer: "Brand", weight: "Mass (kg)"
                    },
                    totalItemCount: 1830,
                    fieldRenderers: {}
                }
            };
            localStorage.setItem('current_user', JSON.stringify(currentUser));
            
            // Try to trigger re-render
            if (window.location.reload) {
                window.location.reload();
            }
        }
    """)

def check_for_table_elements(page):
    """Check if table elements are present"""
    table_selectors = [
        "table",
        "thead", 
        "tbody tr",
        ".data-table",
        "[role='grid']",
        ".table-container table",
        "tr td"
    ]
    
    for selector in table_selectors:
        elements = page.query_selector_all(selector)
        if len(elements) > 0:
            print(f"✓ Table elements found: {selector} ({len(elements)} elements)")
            return True
    
    return False

def navigate_to_challenge(page):
    """Navigate to the challenge page"""
    print("Navigating to challenge...")
    
    try:
        launch_button = page.wait_for_selector('button:has-text("Launch Challenge")', timeout=10000)
        launch_button.click()
        print("Clicked launch challenge")
        
        page.wait_for_url(CHALLENGE_URL, timeout=15000)
        print("Successfully navigated to challenge page")
        return True
    except PlaywrightTimeoutError:
        print("Could not find launch button, trying direct navigation")
        page.goto(CHALLENGE_URL)
        try:
            page.wait_for_selector('.grid > div, table', timeout=10000)
            print("Direct navigation succeeded")
            return True
        except PlaywrightTimeoutError:
            print("Direct navigation also failed")
            return False

def main():
    with sync_playwright() as p:
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
        page.set_default_timeout(30000)
        page.set_viewport_size({"width": 1920, "height": 1080})
        
        try:
            # Navigate to base URL
            page.goto(BASE_URL)
            
            # Authenticate if needed
            if page.url == LOGIN_URL or page.query_selector('input[type="email"]'):
                storage_state = authenticate(page)
                save_session(storage_state)
            
            # Navigate to instructions if needed
            if page.url == INSTRUCTIONS_URL:
                if not navigate_to_challenge(page):
                    print("Failed to navigate to challenge")
                    return
            
            # Try to access table layout
            table_success = try_direct_table_access(page)
            
            products = []
            
            if table_success and check_for_table_elements(page):
                print("🎉 Table layout accessed! Extracting from table...")
                products = extract_from_table(page)
            else:
                print("⚠️ Table layout not accessible, using enhanced cards extraction...")
                # Navigate to challenge with cards layout
                page.goto(CHALLENGE_URL)
                page.wait_for_selector('.grid > div', timeout=10000)
                products = extract_from_cards_with_table_attempt(page)
            
            # Export data
            if products:
                export_data = {
                    "metadata": {
                        "total_products": len(products),
                        "extraction_method": "table" if table_success else "cards_mapped_to_table",
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "target_count": 1830
                    },
                    "products": products
                }
                
                with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, indent=2, ensure_ascii=False)
                
                print(f"Data exported to {OUTPUT_FILE}")
                print(f"Total products: {len(products)}")
                
                # Summary stats
                if len(products) >= 1830:
                    print("Successfully extracted target number of products!")
                else:
                    print(f"Got {len(products)}/1830 products")
                    
            else:
                print("No products extracted")
                
        except Exception as e:
            print(f"Critical error: {e}")
            page.screenshot(path="error_screenshot.png")
            
        finally:
            browser.close()

if __name__ == "__main__":
    main()
