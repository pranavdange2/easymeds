"""
Flask API wrapper for Medicine Price Scraper
Deploys on Railway.app
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import sys
import os
import time
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

app = Flask(__name__)
CORS(app)

def get_driver():
    """Setup Selenium driver with auto-managed ChromeDriver"""
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)

def clean_price(text):
    """Extract price from text"""
    if not text:
        return None
    text = text.replace(',', '').replace('₹', '').replace('Rs', '').strip()
    match = re.search(r'\d+\.?\d*', text)
    return float(match.group()) if match else None

def scrape_netmeds(medicine):
    """Scrape Netmeds"""
    try:
        driver = get_driver()
        url = f"https://www.netmeds.com/catalogsearch/result/{medicine.replace(' ', '-')}/all"
        driver.get(url)
        time.sleep(4)
        
        soup_source = driver.page_source
        
        try:
            product_elem = driver.find_element(By.CSS_SELECTOR, "div[class*='product'], div[class*='cat-'], div[class*='item']")
            product_text = product_elem.text
            
            price_match = re.search(r'₹\s*(\d+\.?\d*)', product_text)
            if price_match:
                price = float(price_match.group(1))
                name = product_text.split('\n')[0][:80]
                
                driver.quit()
                return {
                    'pharmacy': 'Netmeds',
                    'medicine': name,
                    'price': price,
                    'url': url
                }
        except:
            pass
        
        driver.quit()
        return None
    except Exception as e:
        if 'driver' in locals():
            driver.quit()
        return None

def scrape_apollo(medicine):
    """Scrape Apollo Pharmacy"""
    try:
        driver = get_driver()
        url = f"https://www.apollopharmacy.in/search-medicines/{medicine.replace(' ', '%20')}"
        driver.get(url)
        time.sleep(4)
        
        try:
            product = driver.find_element(By.CSS_SELECTOR, "div[class*='ProductCard']")
            product_text = product.text
            
            price_match = re.search(r'₹\s*(\d+(?:,\d+)*(?:\.\d+)?)', product_text)
            price = clean_price(price_match.group(1)) if price_match else None
            
            name = product_text.split('\n')[0][:80] if product_text else medicine
            
            try:
                link_elem = product.find_element(By.TAG_NAME, 'a')
                link = link_elem.get_attribute('href')
            except:
                link = url
            
            driver.quit()
            
            if price:
                return {
                    'pharmacy': 'Apollo Pharmacy',
                    'medicine': name,
                    'price': price,
                    'url': link
                }
        except:
            pass
        
        driver.quit()
        return None
    except Exception as e:
        if 'driver' in locals():
            driver.quit()
        return None

def scrape_pharmeasy(medicine):
    """Scrape PharmEasy"""
    try:
        driver = get_driver()
        url = f"https://pharmeasy.in/search/all?name={medicine.replace(' ', '%20')}"
        driver.get(url)
        time.sleep(5)
        
        try:
            product = driver.find_element(By.CSS_SELECTOR, "div[class*='ProductCard']")
            product_text = product.text
            
            price_match = re.search(r'₹\s*(\d+(?:,\d+)*(?:\.\d+)?)', product_text)
            price = clean_price(price_match.group(1)) if price_match else None
            
            name = product_text.split('\n')[0][:80] if product_text else medicine
            
            try:
                link_elem = product.find_element(By.TAG_NAME, 'a')
                link = link_elem.get_attribute('href')
            except:
                link = url
            
            driver.quit()
            
            if price:
                return {
                    'pharmacy': 'PharmEasy',
                    'medicine': name,
                    'price': price,
                    'url': link
                }
        except:
            pass
        
        driver.quit()
        return None
    except Exception as e:
        if 'driver' in locals():
            driver.quit()
        return None

def scrape_1mg(medicine):
    """Scrape 1mg"""
    try:
        driver = get_driver()
        url = f"https://www.1mg.com/search/all?name={medicine.replace(' ', '%20')}"
        driver.get(url)
        time.sleep(5)
        
        driver.execute_script("window.scrollTo(0, 500);")
        time.sleep(2)
        
        try:
            all_links = driver.find_elements(By.TAG_NAME, 'a')
            for link in all_links[:20]:
                link_text = link.text
                if '₹' in link_text and len(link_text) > 10:
                    price_match = re.search(r'₹\s*(\d+\.?\d*)', link_text)
                    if price_match:
                        price = float(price_match.group(1))
                        name = link_text.split('\n')[0][:80]
                        link_url = link.get_attribute('href')
                        
                        driver.quit()
                        return {
                            'pharmacy': '1mg',
                            'medicine': name,
                            'price': price,
                            'url': link_url if link_url else url
                        }
        except:
            pass
        
        driver.quit()
        return None
    except Exception as e:
        if 'driver' in locals():
            driver.quit()
        return None

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'ok'}), 200

@app.route('/api/search', methods=['POST'])
def search():
    """Search for medicine prices"""
    try:
        data = request.json
        medicine = data.get('medicine', '').strip()
        
        if not medicine:
            return jsonify({'error': 'Please enter a medicine name'}), 400
        
        results = []
        
        scrapers = [
            scrape_netmeds,
            scrape_1mg,
            scrape_apollo,
            scrape_pharmeasy,
        ]
        
        for scraper_func in scrapers:
            try:
                result = scraper_func(medicine)
                if result and result.get('price'):
                    results.append(result)
            except:
                pass
            
            time.sleep(2)
        
        # Sort by price
        results.sort(key=lambda x: x['price'] if x['price'] else float('inf'))
        
        if not results:
            return jsonify({'error': 'No results found. Try searching with generic name like "paracetamol"'}), 404
        
        # Calculate savings
        savings = None
        savings_percentage = None
        if len(results) > 1:
            savings = results[-1]['price'] - results[0]['price']
            savings_percentage = (savings / results[-1]['price']) * 100
        
        return jsonify({
            'medicine': medicine,
            'results': results,
            'bestPrice': results[0]['price'],
            'savings': savings,
            'savingsPercentage': savings_percentage,
            'count': len(results)
        }), 200
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)[:100]}'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
