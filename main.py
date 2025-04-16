import tkinter as tk
from tkinter import simpledialog
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import pandas as pd
import time
import re
import datetime

options = Options()
options.add_experimental_option("detach", True)
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

driver.get(f"https://www.noon.com/saudi-ar/p-105882/")
all_product = []
time.sleep(3)

current_page = 1
while current_page <= 2:
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    product_cards = soup.find_all("div", "ProductBoxLinkHandler_linkWrapper__b0qZ9")
    
    for card in product_cards:
        product_name = card.find('h2', {"data-qa": "product-name"})
        price_tag = card.find("strong", class_="Price_amount__2sXa7")
        old_price = card.find('span', class_="Price_oldPrice__ZqD8B")
        dicount_percent = card.find('span', "PriceDiscount_discount__1ViHb PriceDiscount_pBox__eWMKb")
        link = card.find('a', class_='ProductBoxLinkHandler_productBoxLink__FPhjp')
        href = link.get('href')
        image = card.find('img', class_="ProductImageCarousel_productImage__jtsOn")
        src = image.get('src')
        
        product = {
            "اسم المنتج": product_name.get('title').strip() if product_name else None,
            "السعر": price_tag.get_text(strip=True) if price_tag else None,
            "السعر قبل الخصم": old_price.get_text(strip=True) if old_price else None,
            "نسبة الخصم": dicount_percent.get_text(strip=True) if dicount_percent else None,
            "رابط المنتج": f"https://www.noon.com{href}" if href else None,  # Add the URL prefix
            "صورة المنتج": src if src else None
        }
        all_product.append(product)
    print(f"✅ Page {current_page} scraped.")
    try:
        next_button = driver.find_element(By.CSS_SELECTOR, 'a[aria-label="Next page"]')
        driver.execute_script("arguments[0].scrollIntoView(true);", next_button)
        time.sleep(1)
        next_button.click()
        current_page += 1
    except:  
        print("❌ Next button not found or can't be clicked.")
        break

driver.quit()

# ---------- 🧹 Data Cleaning ----------
df = pd.DataFrame(all_product)

# Drop duplicates
df.drop_duplicates(inplace=True)

# Drop rows with missing product name or price
df.dropna(subset=["اسم المنتج", "السعر"], inplace=True)

# Remove currency symbols and commas, convert to float
def clean_price(value):
    if value:
        cleaned = re.sub(r"[^\d.]", "", value.replace(",", ""))
        return float(cleaned) if cleaned else None
    return None

df["السعر"] = df["السعر"].apply(clean_price)
df["السعر قبل الخصم"] = df["السعر قبل الخصم"].apply(clean_price)

# Calculate Discount Amount and Discount Percentage
def calculate_discount(row):
    if row["السعر قبل الخصم"] and row["السعر"]:
        discount_amount = row["السعر قبل الخصم"] - row["السعر"]
        discount_percentage = (discount_amount / row["السعر قبل الخصم"]) * 100 if row["السعر قبل الخصم"] else 0
        return pd.Series([discount_amount, discount_percentage])
    return pd.Series([None, None])

df[["مقدار الخصم", "نسبة الخصم"]] = df.apply(calculate_discount, axis=1)

# Remove the "مقدار الخصم" column
df.drop(columns=["مقدار الخصم"], inplace=True)

# Sort by Discount Percentage (descending)
df.sort_values(by=["نسبة الخصم"], ascending=False, inplace=True)

# Reset index
df.reset_index(drop=True, inplace=True)

# ---------- 💾 Save to CSV with Unique Filename ----------
# Get the current timestamp to generate a unique filename
timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
filename = f"noon_products_{timestamp}.csv"

df.to_csv(filename, index=False, encoding='utf-8-sig')
print(f"✅ Scraping, cleaning, and sorting complete. Data saved to '{filename}'.")
