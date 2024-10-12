from flask import Flask, jsonify, Response
from playwright.sync_api import sync_playwright
import validators
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup

app = Flask(__name__)

def make_absolute_urls(html_content, base_url):
    """
    Convert all relative URLs in the HTML content to absolute URLs based on the base_url.
    """
    soup = BeautifulSoup(html_content, 'html.parser')

    # Tags and their attributes that contain URLs
    tags_attrs = {
        'a': 'href',
        'img': 'src',
        'link': 'href',
        'script': 'src',
        'iframe': 'src',
        'source': 'src',
        'video': 'src',
        'audio': 'src',
        'embed': 'src',
        'object': 'data',
    }

    for tag, attr in tags_attrs.items():
        for element in soup.find_all(tag):
            url = element.get(attr)
            if url:
                # Convert relative URL to absolute
                absolute_url = urljoin(base_url, url)
                element[attr] = absolute_url

    # Handle inline CSS with URLs, e.g., background-image
    for element in soup.find_all(style=True):
        style = element['style']
        new_style = ''
        for part in style.split(';'):
            if 'url(' in part:
                start = part.find('url(') + 4
                end = part.find(')', start)
                if end > start:
                    resource_url = part[start:end].strip('\'"')
                    absolute_resource_url = urljoin(base_url, resource_url)
                    part = f"url('{absolute_resource_url}')"
            new_style += part + ';'
        element['style'] = new_style

    return str(soup)

@app.route('/api/<path:url>', methods=['GET'])
def fetch_html(url):
    """
    API endpoint to fetch HTML content of a given URL using Playwright.
    
    Example:
        GET /api/www.google.com
    """
    # Prepend scheme if missing
    if not url.startswith(('http://', 'https://')):
        url = 'http://' + url  # Default to HTTP. You can change to HTTPS if preferred.

    # Validate the URL
    if not validators.url(url):
        return jsonify({'error': 'Invalid URL provided.'}), 400

    try:
        with sync_playwright() as p:
            # Launch the browser in headless mode
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            # Navigate to the URL with a timeout of 15 seconds
            page.goto(url, timeout=15000)

            # Wait until the network is idle to ensure the page is fully loaded
            page.wait_for_load_state('networkidle')

            # Get the page content
            content = page.content()

            # Close the browser
            browser.close()

        # Convert relative URLs to absolute URLs
        absolute_content = make_absolute_urls(content, url)

        # Return the modified HTML content with appropriate MIME type
        return Response(absolute_content, mimetype='text/html')

    except Exception as e:
        # Handle exceptions and return error message
        return jsonify({'error': str(e)}), 500

@app.route('/', methods=['GET'])
def index():
    """
    Simple index route to provide usage information.
    """
    return jsonify({
        'message': 'Welcome to the Playwright-Flask HTML Fetcher API!',
        'usage': '/api/<url>'
    })

if __name__ == '__main__':
    # Run the Flask app on port 5000
    app.run(host='0.0.0.0', port=5000, debug=True)
