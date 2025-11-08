"""
Flask API wrapper for Medicine Price Scraper
Lightweight version without Selenium - uses HTTP requests only
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import re
import time

app = Flask(__name__)
CORS(app)

# Headers to avoid being blocked
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def clean_price(text):
    """Extract price from text"""
    if not text:
        return None
    text = text.replace(',', '').replace('₹', '').replace('Rs', '').strip()
    match = re.search(r'\d+\.?\d*', text)
    return float(match.group()) if match else None

def scrape_netmeds(medicine):
    """Scrape Netmeds with HTTP requests"""
    try:
        url = f"https://www.netmeds.com/catalogsearch/result/{medicine.replace(' ', '-')}/all"
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find product container
        product = soup.find('div', {'class': re.compile(r'product|item')})
        if product:
            price_text = product.find('span', {'class': re.compile(r'price|cost')})
            name_text = product.find('a', {'class': re.compile(r'title|name')})
            
            if price_text and name_text:
                price = clean_price(price_text.get_text())
                name = name_text.get_text().strip()[:80]
                
                if price:
                    return {
                        'pharmacy': 'Netmeds',
                        'medicine': name,
                        'price': price,
                        'url': url
                    }
        return None
    except Exception as e:
        print(f"[Netmeds Error] {str(e)[:50]}")
        return None

def scrape_apollo(medicine):
    """Scrape Apollo Pharmacy with HTTP requests"""
    try:
        url = f"https://www.apollopharmacy.in/search-medicines/{medicine.replace(' ', '%20')}"
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find product container
        product = soup.find('div', {'class': re.compile(r'ProductCard|product-card')})
        if product:
            price_text = product.find('span', {'class': re.compile(r'price|cost|amount')})
            name_text = product.find(['a', 'span'], {'class': re.compile(r'title|name|product-title')})
            
            if price_text and name_text:
                price = clean_price(price_text.get_text())
                name = name_text.get_text().strip()[:80]
                
                if price:
                    link = product.find('a')
                    link_url = link.get('href', url) if link else url
                    
                    return {
                        'pharmacy': 'Apollo Pharmacy',
                        'medicine': name,
                        'price': price,
                        'url': link_url
                    }
        return None
    except Exception as e:
        print(f"[Apollo Error] {str(e)[:50]}")
        return None

def scrape_pharmeasy(medicine):
    """Scrape PharmEasy with HTTP requests"""
    try:
        url = f"https://pharmeasy.in/search/all?name={medicine.replace(' ', '%20')}"
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find product container
        product = soup.find('div', {'class': re.compile(r'ProductCard|product-card|medicine-item')})
        if product:
            price_text = product.find('span', {'class': re.compile(r'price|cost|amount')})
            name_text = product.find(['a', 'span'], {'class': re.compile(r'title|name|product-name')})
            
            if price_text and name_text:
                price = clean_price(price_text.get_text())
                name = name_text.get_text().strip()[:80]
                
                if price:
                    link = product.find('a')
                    link_url = link.get('href', url) if link else url
                    
                    return {
                        'pharmacy': 'PharmEasy',
                        'medicine': name,
                        'price': price,
                        'url': link_url
                    }
        return None
    except Exception as e:
        print(f"[PharmEasy Error] {str(e)[:50]}")
        return None

def scrape_1mg(medicine):
    """Scrape 1mg with HTTP requests"""
    try:
        url = f"https://www.1mg.com/search/all?name={medicine.replace(' ', '%20')}"
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find product containers
        products = soup.find_all('a', {'class': re.compile(r'product|medicine|item')}, limit=20)
        
        for product in products:
            price_text = product.find('span', {'class': re.compile(r'price|cost')})
            if price_text:
                price = clean_price(price_text.get_text())
                name = product.get_text().strip().split('\n')[0][:80]
                link_url = product.get('href', url)
                
                if price and name and len(name) > 3:
                    return {
                        'pharmacy': '1mg',
                        'medicine': name,
                        'price': price,
                        'url': link_url
                    }
        return None
    except Exception as e:
        print(f"[1mg Error] {str(e)[:50]}")
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
        
        if not medicine or len(medicine) < 2:
            return jsonify({'error': 'Please enter a medicine name'}), 400
        
        results = []
        
        scrapers = [
            scrape_1mg,
            scrape_netmeds,
            scrape_apollo,
            scrape_pharmeasy,
        ]
        
        for scraper_func in scrapers:
            try:
                result = scraper_func(medicine)
                if result and result.get('price'):
                    results.append(result)
                    time.sleep(0.5)  # Small delay to avoid rate limiting
            except Exception as e:
                print(f"Scraper error: {str(e)[:50]}")
                pass
        
        # Sort by price
        results.sort(key=lambda x: x['price'] if x['price'] else float('inf'))
        
        if not results:
            return jsonify({'error': 'No results found. Try searching with generic name like "paracetamol"'}), 404
        
        # Calculate savings
        savings = None
        savings_percentage = None
        if len(results) > 1:
            savings = results[-1]['price'] - results[0]['price']
            savings_percentage = (savings / results[-1]['price']) * 100 if results[-1]['price'] > 0 else 0
        
        return jsonify({
            'medicine': medicine,
            'results': results,
            'bestPrice': results[0]['price'],
            'savings': savings,
            'savingsPercentage': savings_percentage,
            'count': len(results)
        }), 200
    except Exception as e:
        print(f"Search error: {str(e)}")
        return jsonify({'error': f'Server error: {str(e)[:100]}'}), 500

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
