
# Iden Product Scraper

A Python automation script using **Playwright** to scrape product data from [IdenHQ](https://hiring.idenhq.com) challenges. The script logs in, navigates to the challenge page, scrolls through products, and exports the data to a JSON file.


---

## Features

* Automatic login using credentials.
* Session persistence using a JSON `storage_state` file.
* Navigate to instructions and challenge pages automatically.
* Scroll through product listings and extract all details:

  * Product ID, name, category, dimensions, color, price, brand, mass, updated date.
* Handles dynamic loading with retries and scroll attempts.
* Exports data to `idenhq_products.json`.
* Optional screenshots for errors or page issues.

---

## Output
<img width="1261" height="942" alt="image" src="https://github.com/user-attachments/assets/32480c5c-829e-4331-9700-7fbbb38c4f13" />

<br/><br/>

<img width="1786" height="2053" alt="image" src="https://github.com/user-attachments/assets/65e985e0-25ef-4443-bf7b-bda14405dbd9" />

---
## Requirements

* Python 3.9+
* [Playwright](https://playwright.dev/python/docs/intro)

Install dependencies:

```bash
pip install playwright
playwright install
```

---

## Configuration

Update `CREDENTIALS` in the script with your IdenHQ email and password:

```python
CREDENTIALS = {
    "username": "email@example.com",
    "password": "password"
}
```

Optional: adjust `SESSION_FILE` and `OUTPUT_FILE` names if needed.

---

## Usage

Run the scraper:

```bash
python extract.py
```

* The script will try to use an existing session (`idenhq_session.json`) if available.
* If not, it will log in and save the session for future runs.
* Extracted product data will be saved to `idenhq_products.json`.

---

## Notes / Tips

* For faster execution, enable headless mode in the script:

```python
browser = p.chromium.launch(headless=True)
```

* If the challenge page doesn’t load, a screenshot will be saved as `challenge_page.png`.
* We can adjust scroll attempts or wait times in the script for performance tuning.

---
## Table attempt:
I was able to comprehend that layout:table for table view instead of layout: cards beside assessment id but my methods to switch to table was not successful like expected.
<br/> One issue faced sometimes 
<img width="1649" height="269" alt="image" src="https://github.com/user-attachments/assets/daedab01-a782-4a47-aa2c-ec8e5f243a82" />
