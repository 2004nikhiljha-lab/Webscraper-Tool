import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import re
import time
import sys
import io
import json

# Fix encoding issues on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


def debug_page_structure(soup):
    """
    Debug function to see what's actually on the page
    """
    print("\n" + "="*80)
    print("DEBUG: PAGE STRUCTURE ANALYSIS")
    print("="*80)
    
    # Check all links
    all_links = soup.find_all("a", href=True)
    print(f"\n[DEBUG] Total links found: {len(all_links)}")
    print("[DEBUG] Sample links (first 20):")
    for i, link in enumerate(all_links[:20], 1):
        href = link.get('href', '')
        text = link.get_text(strip=True)
        print(f"  {i}. Text: '{text}' | Href: '{href}'")
    
    # Check headings
    print(f"\n[DEBUG] Headings found:")
    for tag in ['h1', 'h2', 'h3']:
        headings = soup.find_all(tag)
        print(f"  {tag.upper()}: {len(headings)} found")
        for h in headings[:5]:
            print(f"    - {h.get_text(strip=True)[:80]}")
    
    # Check for common class patterns
    print(f"\n[DEBUG] Looking for common patterns...")
    
    # Services
    service_elements = soup.find_all(text=re.compile(r'service|solution|offering', re.IGNORECASE))
    print(f"  Elements mentioning 'service/solution': {len(service_elements)}")
    
    # Clients
    client_elements = soup.find_all(text=re.compile(r'client|customer|trusted', re.IGNORECASE))
    print(f"  Elements mentioning 'client/customer': {len(client_elements)}")
    
    # Check images
    images = soup.find_all("img")
    print(f"\n[DEBUG] Images found: {len(images)}")
    for i, img in enumerate(images[:10], 1):
        alt = img.get('alt', 'No alt')
        src = img.get('src', 'No src')
        print(f"  {i}. Alt: '{alt}' | Src: '{src[:60]}'")
    
    print("\n" + "="*80)


def scrape_company_profile(url, debug_mode=True):
    """
    Enhanced scraper with better detection and debug mode
    """
    profile = {
        "company_name": None,
        "website": url,
        "about_us": {
            "description": None,
            "page_url": None
        },
        "services": [],
        "clients": [],
        "process": [],
        "articles": [],
        "contact_info": {
            "contact_page": None,
            "email": None,
            "phone": None,
            "address": None
        },
        "careers": {
            "page_url": None
        },
        "policies": {
            "privacy_policy": None,
            "returns_policy": None,
            "terms_of_service": None
        }
    }

    # Headers to mimic a real browser
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive',
    }

    try:
        print(f"\n[*] Fetching main page: {url}")
        response = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
        response.raise_for_status()
        print(f"[+] Status Code: {response.status_code}")
        print(f"[+] Final URL: {response.url}")
        print(f"[+] Content Length: {len(response.text)} characters")
    except requests.exceptions.RequestException as e:
        print(f"[!] Failed to fetch website: {e}")
        return profile

    soup = BeautifulSoup(response.text, "html.parser")
    
    # Save HTML for inspection
    if debug_mode:
        with open("page_source.html", "w", encoding="utf-8") as f:
            f.write(soup.prettify())
        print(f"[+] HTML saved to page_source.html for inspection")
    
    # Run debug analysis
    if debug_mode:
        debug_page_structure(soup)

    # ===== EXTRACT COMPANY NAME =====
    print("\n[*] Extracting company name...")
    
    # Try multiple methods
    if soup.title:
        title_text = soup.title.text.strip()
        profile["company_name"] = title_text.split('|')[0].split('-')[0].split('–')[0].strip()
        print(f"[+] From title: {profile['company_name']}")
    
    og_site_name = soup.find("meta", property="og:site_name")
    if og_site_name and og_site_name.get("content"):
        profile["company_name"] = og_site_name["content"].strip()
        print(f"[+] From og:site_name: {profile['company_name']}")
    
    # Try logo alt text
    logo = soup.find("img", alt=re.compile(r"logo", re.IGNORECASE))
    if logo and logo.get("alt"):
        profile["company_name"] = logo["alt"].replace("logo", "").replace("Logo", "").strip()
        print(f"[+] From logo alt: {profile['company_name']}")

    # ===== COLLECT ALL LINKS =====
    print("\n[*] Collecting all links...")
    all_links = []
    
    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = a.get_text(strip=True)
        full_url = urljoin(response.url, href)
        
        # Only include links from same domain
        if urlparse(full_url).netloc == urlparse(response.url).netloc or not urlparse(href).netloc:
            all_links.append({
                "url": full_url,
                "text": text.lower(),
                "href": href.lower()
            })
    
    print(f"[+] Collected {len(all_links)} links")

    # ===== FIND KEY PAGES =====
    print("\n[*] Identifying key pages...")
    
    # About Us
    for link in all_links:
        if "about" in link["href"] or "about" in link["text"]:
            if not profile["about_us"]["page_url"] or len(link["href"]) < len(urlparse(profile["about_us"]["page_url"] or "").path):
                profile["about_us"]["page_url"] = link["url"]
    
    if profile["about_us"]["page_url"]:
        print(f"[+] About Us: {profile['about_us']['page_url']}")

    # Contact
    for link in all_links:
        if "contact" in link["href"] or "contact" in link["text"]:
            profile["contact_info"]["contact_page"] = link["url"]
            break
    
    if profile["contact_info"]["contact_page"]:
        print(f"[+] Contact: {profile['contact_info']['contact_page']}")

    # Careers
    for link in all_links:
        if any(word in link["href"] or word in link["text"] for word in ["career", "job", "hiring", "join"]):
            profile["careers"]["page_url"] = link["url"]
            break
    
    if profile["careers"]["page_url"]:
        print(f"[+] Careers: {profile['careers']['page_url']}")

    # Privacy Policy
    for link in all_links:
        if "privacy" in link["href"] or "privacy" in link["text"]:
            profile["policies"]["privacy_policy"] = link["url"]
            break
    
    if profile["policies"]["privacy_policy"]:
        print(f"[+] Privacy Policy: {profile['policies']['privacy_policy']}")

    # Returns Policy
    for link in all_links:
        if "return" in link["href"] or "refund" in link["href"] or "return" in link["text"]:
            profile["policies"]["returns_policy"] = link["url"]
            break
    
    if profile["policies"]["returns_policy"]:
        print(f"[+] Returns Policy: {profile['policies']['returns_policy']}")

    # Terms of Service
    for link in all_links:
        if any(term in link["href"] or term in link["text"] for term in ["term", "condition", "tos"]):
            profile["policies"]["terms_of_service"] = link["url"]
            break
    
    if profile["policies"]["terms_of_service"]:
        print(f"[+] Terms of Service: {profile['policies']['terms_of_service']}")

    # ===== SCRAPE SERVICES =====
    print("\n[*] Extracting services...")
    
    # Method 1: Look for service-related headings
    service_keywords = ["service", "solution", "offer", "product", "expertise", "specialization"]
    
    for heading in soup.find_all(["h1", "h2", "h3", "h4", "h5"]):
        heading_text = heading.get_text(strip=True).lower()
        
        if any(keyword in heading_text for keyword in service_keywords):
            print(f"[+] Found service section: {heading.get_text(strip=True)}")
            
            # Get next siblings or parent container
            parent = heading.find_parent(['div', 'section', 'article', 'main'])
            if parent:
                # Look for lists
                for ul in parent.find_all(['ul', 'ol'], limit=5):
                    for li in ul.find_all("li"):
                        service = li.get_text(strip=True)
                        if service and 3 < len(service) < 200:
                            if service not in profile["services"]:
                                profile["services"].append(service)
                                print(f"  - {service[:80]}")
                
                # Look for div cards
                for div in parent.find_all('div', class_=True, limit=20):
                    # Check if div has substantial text
                    text = div.get_text(strip=True)
                    if 10 < len(text) < 300:
                        # Check if it's likely a service card (has a heading inside)
                        inner_heading = div.find(['h3', 'h4', 'h5'])
                        if inner_heading:
                            service = inner_heading.get_text(strip=True)
                            if service not in profile["services"] and len(service) > 3:
                                profile["services"].append(service)
                                print(f"  - {service[:80]}")

    # Method 2: Look for common service patterns
    body_text = soup.get_text()
    service_pattern = r'We (offer|provide|deliver|specialize in) ([^.!?]{10,100})'
    matches = re.findall(service_pattern, body_text, re.IGNORECASE)
    for match in matches:
        service = match[1].strip()
        if service not in profile["services"] and len(service) > 10:
            profile["services"].append(service)

    print(f"[+] Total services found: {len(profile['services'])}")

    # ===== SCRAPE CLIENTS =====
    print("\n[*] Extracting clients...")
    
    # Look for client sections
    client_keywords = ["client", "customer", "partner", "trust", "work with", "portfolio"]
    
    for heading in soup.find_all(["h1", "h2", "h3", "h4", "h5"]):
        heading_text = heading.get_text(strip=True).lower()
        
        if any(keyword in heading_text for keyword in client_keywords):
            print(f"[+] Found client section: {heading.get_text(strip=True)}")
            
            parent = heading.find_parent(['div', 'section', 'article', 'main'])
            if parent:
                # Look for images (often client logos)
                for img in parent.find_all("img"):
                    alt = img.get("alt", "").strip()
                    title = img.get("title", "").strip()
                    
                    client_name = alt or title
                    if client_name and len(client_name) > 1 and len(client_name) < 100:
                        # Clean up common suffixes
                        client_name = re.sub(r'\s+(logo|icon|image)$', '', client_name, flags=re.IGNORECASE)
                        if client_name not in profile["clients"]:
                            profile["clients"].append(client_name)
                            print(f"  - {client_name}")
                
                # Look for text mentions
                for elem in parent.find_all(['li', 'span', 'p', 'div']):
                    text = elem.get_text(strip=True)
                    # Only add if it's short (likely a company name)
                    if 2 < len(text) < 50 and text not in profile["clients"]:
                        profile["clients"].append(text)
                        print(f"  - {text}")

    print(f"[+] Total clients found: {len(profile['clients'])}")

    # ===== SCRAPE PROCESS =====
    print("\n[*] Extracting process/methodology...")
    
    process_keywords = ["process", "methodology", "approach", "how we", "workflow", "step"]
    
    for heading in soup.find_all(["h1", "h2", "h3", "h4", "h5"]):
        heading_text = heading.get_text(strip=True).lower()
        
        if any(keyword in heading_text for keyword in process_keywords):
            print(f"[+] Found process section: {heading.get_text(strip=True)}")
            
            parent = heading.find_parent(['div', 'section', 'article', 'main'])
            if parent:
                # Look for ordered lists
                for ol in parent.find_all('ol'):
                    for i, li in enumerate(ol.find_all("li"), 1):
                        step_text = li.get_text(strip=True)
                        if step_text and len(step_text) > 5:
                            profile["process"].append({
                                "step": i,
                                "description": step_text
                            })
                            print(f"  Step {i}: {step_text[:60]}...")
                
                # Look for numbered divs or steps
                step_divs = parent.find_all(['div', 'article'], class_=True, limit=10)
                for i, div in enumerate(step_divs, len(profile["process"]) + 1):
                    text = div.get_text(strip=True)
                    if 10 < len(text) < 500:
                        # Check if it looks like a step (contains number or has heading)
                        if re.search(r'\b\d+\b', text[:50]) or div.find(['h3', 'h4', 'h5']):
                            profile["process"].append({
                                "step": i,
                                "description": text[:300]
                            })
                            print(f"  Step {i}: {text[:60]}...")

    print(f"[+] Total process steps found: {len(profile['process'])}")

    # ===== SCRAPE ARTICLES/BLOG =====
    print("\n[*] Extracting articles/blog posts...")
    
    # Look for blog/article links
    blog_urls = []
    for link in all_links:
        if any(keyword in link["href"] or keyword in link["text"] 
               for keyword in ["blog", "article", "news", "insight", "resource", "post"]):
            blog_urls.append(link["url"])
    
    if blog_urls:
        # Visit first blog page
        try:
            print(f"[+] Scraping blog page: {blog_urls[0]}")
            blog_response = requests.get(blog_urls[0], headers=headers, timeout=10)
            blog_soup = BeautifulSoup(blog_response.text, "html.parser")
            
            # Look for article elements
            for article in blog_soup.find_all(['article', 'div'], class_=True, limit=15):
                # Find title
                title_elem = article.find(['h1', 'h2', 'h3', 'h4', 'a'])
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    link = title_elem.get('href') if title_elem.name == 'a' else None
                    
                    if title and 5 < len(title) < 200:
                        article_data = {
                            "title": title,
                            "url": urljoin(blog_urls[0], link) if link else None
                        }
                        if article_data not in profile["articles"]:
                            profile["articles"].append(article_data)
                            print(f"  - {title}")
        except Exception as e:
            print(f"[!] Could not scrape blog: {e}")
    
    print(f"[+] Total articles found: {len(profile['articles'])}")

    # ===== EXTRACT CONTACT INFO =====
    print("\n[*] Extracting contact information...")
    
    body_text = soup.get_text()
    
    # Email
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    emails = re.findall(email_pattern, body_text)
    # Filter out common false positives
    emails = [e for e in emails if not any(x in e.lower() for x in ['example.com', 'domain.com', 'email.com'])]
    if emails:
        profile["contact_info"]["email"] = emails[0]
        print(f"[+] Email: {emails[0]}")
    
    # Phone - more flexible pattern
    phone_pattern = r'(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})'
    phones = re.findall(phone_pattern, body_text)
    if phones:
        formatted_phone = f"{phones[0][0]}-{phones[0][1]}-{phones[0][2]}"
        profile["contact_info"]["phone"] = formatted_phone
        print(f"[+] Phone: {formatted_phone}")

    # ===== SCRAPE ABOUT US PAGE =====
    if profile["about_us"]["page_url"]:
        print(f"\n[*] Scraping About Us page...")
        try:
            about_response = requests.get(profile["about_us"]["page_url"], headers=headers, timeout=10)
            about_soup = BeautifulSoup(about_response.text, "html.parser")
            
            # Remove script and style elements
            for script in about_soup(["script", "style", "nav", "footer", "header"]):
                script.decompose()
            
            # Get meaningful paragraphs
            paragraphs = []
            for p in about_soup.find_all("p"):
                text = p.get_text(strip=True)
                if len(text) > 50:
                    paragraphs.append(text)
                    if len(paragraphs) >= 3:
                        break
            
            if paragraphs:
                profile["about_us"]["description"] = " ".join(paragraphs)
                print(f"[+] About Us description extracted ({len(profile['about_us']['description'])} chars)")
        except Exception as e:
            print(f"[!] Could not scrape About Us page: {e}")

    return profile


def print_profile(profile):
    """
    Pretty print the scraped profile
    """
    print("\n" + "="*80)
    print("COMPREHENSIVE COMPANY PROFILE REPORT")
    print("="*80)
    
    print(f"\n[COMPANY NAME]")
    print(f"  {profile['company_name'] or 'Not found'}")
    
    print(f"\n[ABOUT US]")
    if profile["about_us"]["description"]:
        desc = profile["about_us"]["description"][:300] + "..." if len(profile["about_us"]["description"]) > 300 else profile["about_us"]["description"]
        print(f"  {desc}")
    else:
        print(f"  Not found")
    print(f"  Page URL: {profile['about_us']['page_url'] or 'Not found'}")
    
    print(f"\n[SERVICES] ({len(profile['services'])} found)")
    if profile['services']:
        for i, service in enumerate(profile['services'][:15], 1):
            print(f"  {i}. {service[:150]}{'...' if len(service) > 150 else ''}")
    else:
        print("  None found")
    
    print(f"\n[CLIENTS] ({len(profile['clients'])} found)")
    if profile['clients']:
        for i, client in enumerate(profile['clients'][:20], 1):
            print(f"  {i}. {client}")
    else:
        print("  None found")
    
    print(f"\n[PROCESS/METHODOLOGY] ({len(profile['process'])} steps)")
    if profile['process']:
        for item in profile['process']:
            desc = item['description'][:150] + "..." if len(item['description']) > 150 else item['description']
            print(f"  Step {item['step']}: {desc}")
    else:
        print("  None found")
    
    print(f"\n[ARTICLES/BLOG] ({len(profile['articles'])} found)")
    if profile['articles']:
        for i, article in enumerate(profile['articles'][:10], 1):
            print(f"  {i}. {article['title']}")
            if article.get('url'):
                print(f"     URL: {article['url']}")
    else:
        print("  None found")
    
    print(f"\n[CONTACT INFORMATION]")
    print(f"  Contact Page: {profile['contact_info']['contact_page'] or 'Not found'}")
    print(f"  Email: {profile['contact_info']['email'] or 'Not found'}")
    print(f"  Phone: {profile['contact_info']['phone'] or 'Not found'}")
    
    print(f"\n[CAREERS]")
    print(f"  Careers Page: {profile['careers']['page_url'] or 'Not found'}")
    
    print(f"\n[POLICIES]")
    print(f"  Privacy Policy: {profile['policies']['privacy_policy'] or 'Not found'}")
    print(f"  Returns Policy: {profile['policies']['returns_policy'] or 'Not found'}")
    print(f"  Terms of Service: {profile['policies']['terms_of_service'] or 'Not found'}")
    
    print("\n" + "="*80)


def save_to_json(profile, filename="company_profile.json"):
    """
    Save the profile to a JSON file
    """
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(profile, f, indent=2, ensure_ascii=False)
    print(f"\n[+] Profile saved to {filename}")


# Example Usage
if __name__ == "__main__":
    # Test URL
    company_url = "https://google.com/"
    
    try:
        # Run with debug mode ON to see what's being found
        data = scrape_company_profile(company_url, debug_mode=True)
        print_profile(data)
        save_to_json(data)
        
    except Exception as e:
        print(f"\n[!] Error scraping {company_url}: {e}")
        import traceback
        traceback.print_exc()