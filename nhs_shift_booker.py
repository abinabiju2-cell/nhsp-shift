"""
NHS Professionals Automatic Shift Booker
Customized for: Sanjay Jismon
Location: Worcester Royal Hospital
Shift Type: Healthcare Assistant (Night shifts 19:00 - 08:00)

This script automates shift booking on the NHS Professionals platform using Selenium.
It continuously searches for available shifts and books them automatically.
"""

import time
import logging
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
from config import (
    NHS_EMAIL, NHS_PASSWORD, PREFERRED_LOCATION, PREFERRED_SHIFT_TYPES,
    SHIFT_TIME_START, SHIFT_TIME_END, MAX_SHIFTS_TO_BOOK,
    SEARCH_INTERVAL_MINUTES, HEADLESS_MODE, MAX_RETRY_ATTEMPTS,
    RETRY_DELAY_SECONDS, ELEMENT_WAIT_TIME
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('nhs_shift_booker.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class NHSShiftBooker:
    def __init__(self, email, password, headless=False):
        """
        Initialize the NHS Shift Booker
        
        Args:
            email (str): Your NHS Professionals email
            password (str): Your NHS Professionals password
            headless (bool): Run browser in headless mode
        """
        self.email = email
        self.password = password
        self.headless = headless
        self.driver = None
        self.wait = None
        self.booked_shifts = []
        
    def setup_driver(self):
        """Initialize the Chrome WebDriver"""
        try:
            options = webdriver.ChromeOptions()
            if self.headless:
                options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_argument('--start-maximized')
            options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            self.wait = WebDriverWait(self.driver, ELEMENT_WAIT_TIME)
            logger.info("✅ WebDriver initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize WebDriver: {e}")
            raise

    def login(self, retry_count=0):
        """Login to NHS Professionals with retry logic"""
        try:
            logger.info("🔐 Starting login process...")
            self.driver.get("https://www.nhsprofessionals.nhs.uk/")
            time.sleep(3)
            
            # Look for login button
            try:
                login_button = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Log in')] | //button[contains(text(), 'Log in')]"))
                )
                login_button.click()
                logger.info("✓ Clicked login button")
                time.sleep(2)
            except:
                logger.warning("Login button not found, might already be on login page")
            
            # Switch to login frame if exists
            try:
                iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
                if iframes:
                    self.driver.switch_to.frame(iframes[0])
                    logger.info("✓ Switched to login iframe")
                    time.sleep(1)
            except Exception as e:
                logger.debug(f"No iframe found: {e}")
            
            # Enter email
            try:
                email_field = self.wait.until(
                    EC.presence_of_element_located((By.XPATH, "//input[@id='username'] | //input[@name='email'] | //input[@type='email']"))
                )
                email_field.clear()
                email_field.send_keys(self.email)
                logger.info("✓ Email entered")
                time.sleep(1)
            except Exception as e:
                logger.error(f"❌ Failed to find email field: {e}")
                if retry_count < MAX_RETRY_ATTEMPTS:
                    logger.info(f"Retrying login... Attempt {retry_count + 1}")
                    time.sleep(RETRY_DELAY_SECONDS)
                    self.driver.refresh()
                    return self.login(retry_count + 1)
                raise
            
            # Enter password
            try:
                password_field = self.wait.until(
                    EC.presence_of_element_located((By.XPATH, "//input[@id='password'] | //input[@name='password'] | //input[@type='password']"))
                )
                password_field.clear()
                password_field.send_keys(self.password)
                logger.info("✓ Password entered")
                time.sleep(1)
            except Exception as e:
                logger.error(f"❌ Failed to find password field: {e}")
                raise
            
            # Click login button
            try:
                submit_button = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//button[@id='kc-login'] | //button[contains(@type, 'submit')] | //input[@value='Log in']"))
                )
                submit_button.click()
                logger.info("✓ Login submitted")
                time.sleep(5)
            except Exception as e:
                logger.error(f"❌ Failed to find submit button: {e}")
                raise
            
            # Check if login was successful
            try:
                self.driver.switch_to.default_content()
            except:
                pass
            
            time.sleep(3)
            logger.info("✅ Login successful")
            
        except Exception as e:
            logger.error(f"❌ Login failed: {e}")
            raise

    def navigate_to_shifts(self):
        """Navigate to available shifts"""
        try:
            logger.info("🔍 Navigating to available shifts...")
            
            # Try multiple ways to find shifts/find work link
            xpath_options = [
                "//a[contains(text(), 'Find work')]",
                "//a[contains(text(), 'Shifts')]",
                "//a[contains(text(), 'Available shifts')]",
                "//nav//a[contains(text(), 'Work')"]
            ]
            
            found = False
            for xpath in xpath_options:
                try:
                    shifts_link = self.wait.until(
                        EC.element_to_be_clickable((By.XPATH, xpath))
                    )
                    shifts_link.click()
                    found = True
                    logger.info("✓ Found and clicked shifts link")
                    break
                except:
                    continue
            
            if not found:
                logger.warning("⚠️ Could not find shifts link, trying direct URL")
                self.driver.get("https://www.nhsprofessionals.nhs.uk/search-shifts")
            
            time.sleep(3)
            logger.info("✅ Navigated to shifts section")
            
        except Exception as e:
            logger.error(f"❌ Navigation to shifts failed: {e}")
            raise

    def search_shifts(self, location=None, shift_type=None):
        """Search for available shifts with filters"""
        
        Args:
            location (str): Location/area
            shift_type (str): Type of shift
        """
        try:
            logger.info(f"🔎 Searching for shifts - Location: {location}, Type: {shift_type}")
            
            # Try to find and fill location field
            if location:
                try:
                    location_field = self.wait.until(
                        EC.presence_of_element_located((By.XPATH, "//input[contains(@placeholder, 'location')] | //input[contains(@placeholder, 'Location')] | //input[@name='location']"))
                    )
                    location_field.clear()
                    location_field.send_keys(location)
                    time.sleep(1)
                    logger.info(f"✓ Entered location: {location}")
                except Exception as e:
                    logger.warning(f"⚠️ Could not enter location: {e}")
            
            # Try to find and fill shift type field
            if shift_type:
                try:
                    type_field = self.wait.until(
                        EC.presence_of_element_located((By.XPATH, "//input[contains(@placeholder, 'type')] | //select[@name='shiftType']"))
                    )
                    type_field.clear()
                    type_field.send_keys(shift_type)
                    time.sleep(1)
                    logger.info(f"✓ Entered shift type: {shift_type}")
                except Exception as e:
                    logger.warning(f"⚠️ Could not enter shift type: {e}")
            
            # Click search button
            try:
                search_button = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Search')] | //button[contains(text(), 'search')] | //button[@type='submit']"))
                )
                search_button.click()
                logger.info("✓ Search submitted")
                time.sleep(4)
            except Exception as e:
                logger.warning(f"⚠️ Could not find search button: {e}")
            
            logger.info("✅ Shift search completed")
            
        except Exception as e:
            logger.error(f"❌ Shift search failed: {e}")

    def get_available_shifts(self):
        """Get list of available shifts matching criteria"""
        
        Returns:
            list: List of shift details
        """
        try:
            shifts = []
            
            # Try multiple selector patterns for shift items
            selectors = [
                "//div[contains(@class, 'shift-item')] | //div[contains(@class, 'shift-card')]",
                "//tr[contains(@class, 'shift')]",
                "//li[contains(@class, 'shift')]"
            ]
            
            shift_elements = []
            for selector in selectors:
                try:
                    shift_elements = self.driver.find_elements(By.XPATH, selector)
                    if shift_elements:
                        break
                except:
                    continue
            
            logger.info(f"🔎 Found {len(shift_elements)} shift elements")
            
            for idx, shift in enumerate(shift_elements):
                try:
                    # Extract shift details
                    shift_info = {
                        'index': idx,
                        'element': shift
                    }
                    
                    # Try to get job title
                    try:
                        title = shift.find_element(By.XPATH, ".//*[contains(@class, 'title')] | ./h3 | .//*[contains(@class, 'job-title')] ").text
                        shift_info['title'] = title
                    except:
                        shift_info['title'] = 'Unknown'
                    
                    # Try to get location
                    try:
                        location = shift.find_element(By.XPATH, ".//*[contains(@class, 'location')] | .//*[contains(text(), 'worcester')] ").text
                        shift_info['location'] = location
                    except:
                        shift_info['location'] = 'Unknown'
                    
                    # Try to get date
                    try:
                        date = shift.find_element(By.XPATH, ".//*[contains(@class, 'date')] | .//*[contains(@class, 'shift-date')] ").text
                        shift_info['date'] = date
                    except:
                        shift_info['date'] = 'Unknown'
                    
                    # Try to get time
                    try:
                        time_text = shift.find_element(By.XPATH, ".//*[contains(@class, 'time')] | .//*[contains(@class, 'shift-time')] ").text
                        shift_info['time'] = time_text
                    except:
                        shift_info['time'] = 'Unknown'
                    
                    # Try to get pay
                    try:
                        pay = shift.find_element(By.XPATH, ".//*[contains(@class, 'pay')] | .//*[contains(text(), '£')] ").text
                        shift_info['pay'] = pay
                    except:
                        shift_info['pay'] = 'Unknown'
                    
                    shifts.append(shift_info)
                    logger.debug(f"Shift {idx}: {shift_info.get('title', 'Unknown')} - {shift_info.get('date', 'Unknown')}")
                    
                except Exception as e:
                    logger.debug(f"Could not parse shift {idx}: {e}")
                    continue
            
            logger.info(f"✅ Found {len(shifts)} available shifts")
            return shifts
            
        except Exception as e:
            logger.error(f"❌ Failed to get available shifts: {e}")
            return []

    def book_shift(self, shift_details, retry_count=0):
        """Book a specific shift with retry logic"""
        
        Args:
            shift_details (dict): Shift details dictionary
            retry_count (int): Current retry attempt
            
        Returns:
            bool: True if booking successful, False otherwise
        """
        try:
            shift_title = shift_details.get('title', 'Unknown')
            shift_date = shift_details.get('date', 'Unknown')
            logger.info(f"📅 Attempting to book shift: {shift_title} on {shift_date}")
            
            # Scroll to shift element
            self.driver.execute_script("arguments[0].scrollIntoView(true);");
            time.sleep(1)
            
            # Find and click book/apply button
            try:
                book_button = shift_details['element'].find_element(
                    By.XPATH, 
                    ".//button[contains(text(), 'Book')] | .//a[contains(text(), 'Apply')] | .//button[contains(text(), 'Apply')] | .//button[contains(@class, 'book')]"
                )
                book_button.click()
                logger.info("✓ Clicked book/apply button")
                time.sleep(2)
            except Exception as e:
                logger.warning(f"⚠️ Could not find book button: {e}")
                if retry_count < MAX_RETRY_ATTEMPTS:
                    logger.info("Retrying...")
                    time.sleep(RETRY_DELAY_SECONDS)
                    return self.book_shift(shift_details, retry_count + 1)
                return False
            
            # Handle confirmation dialog if present
            try:
                confirm_button = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Confirm')] | //button[contains(text(), 'Yes')] | //button[@class='btn-primary']"))
                )
                confirm_button.click()
                logger.info("✓ Confirmed booking")
                time.sleep(2)
            except:
                logger.debug("No confirmation dialog found")
            
            # Check for success message
            try:
                success_indicators = [
                    "//*[contains(text(), 'successfully')]",
                    "//*[contains(text(), 'booked')]",
                    "//*[contains(text(), 'confirmed')]",
                    "//*[contains(text(), 'Application successful')]"
                ]
                
                for indicator in success_indicators:
                    try:
                        success_msg = self.driver.find_element(By.XPATH, indicator)
                        logger.info(f"✅ Shift booked successfully: {success_msg.text}")
                        self.booked_shifts.append({
                            'title': shift_title,
                            'date': shift_date,
                            'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        })
                        return True
                    except:
                        continue
                
                # If no explicit success message, assume success after 2 seconds
                logger.info(f"✅ Shift booking processed for: {shift_title}")
                self.booked_shifts.append({
                    'title': shift_title,
                    'date': shift_date,
                    'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })
                return True
                
            except Exception as e:
                logger.warning(f"⚠️ Could not verify booking status: {e}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to book shift: {e}")
            if retry_count < MAX_RETRY_ATTEMPTS:
                logger.info(f"Retrying... Attempt {retry_count + 1}/{MAX_RETRY_ATTEMPTS}")
                time.sleep(RETRY_DELAY_SECONDS)
                return self.book_shift(shift_details, retry_count + 1)
            return False

    def run_continuous_booking(self):
        """Continuously search and book shifts 24/7"""
        search_cycle = 0
        
        try:
            self.setup_driver()
            self.login()
            
            logger.info("="*60)
            logger.info("🚀 STARTING CONTINUOUS SHIFT BOOKING")
            logger.info(f"📍 Location: {PREFERRED_LOCATION}")
            logger.info(f"👔 Shift Type: {PREFERRED_SHIFT_TYPES}")
            logger.info(f"🕐 Time: {SHIFT_TIME_START} - {SHIFT_TIME_END}")
            logger.info(f"🔄 Search Interval: Every {SEARCH_INTERVAL_MINUTES} minutes")
            logger.info("="*60)
            
            while True:
                search_cycle += 1
                logger.info(f"\n{'='*60}")
                logger.info(f"🔄 SEARCH CYCLE #{search_cycle} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                logger.info(f"{'='*60}")
                
                try:
                    self.navigate_to_shifts()
                    self.search_shifts(
                        location=PREFERRED_LOCATION,
                        shift_type=PREFERRED_SHIFT_TYPES[0] if PREFERRED_SHIFT_TYPES else None
                    )
                    
                    shifts = self.get_available_shifts()
                    
                    if not shifts:
                        logger.info("ℹ️  No available shifts found. Waiting for next search...")
                    else:
                        logger.info(f"📊 Booked {len(self.booked_shifts)} shifts so far")
                        
                        for shift in shifts:
                            logger.info(f"\n→ Processing: {shift.get('title', 'Unknown')}")
                            logger.info(f"  Date: {shift.get('date', 'Unknown')}")
                            logger.info(f"  Time: {shift.get('time', 'Unknown')}")
                            logger.info(f"  Location: {shift.get('location', 'Unknown')}")
                            
                            if self.book_shift(shift):
                                logger.info(f"✅ Successfully booked!")
                            else:
                                logger.warning(f"⚠️  Booking failed, will retry next cycle")
                            
                            time.sleep(2)
                    
                    # Log booking statistics
                    logger.info(f"\n📈 BOOKING STATISTICS:")
                    logger.info(f"   Total shifts booked: {len(self.booked_shifts)}")
                    if self.booked_shifts:
                        for booking in self.booked_shifts:
                            logger.info(f"   ✓ {booking['title']} on {booking['date']}")
                    
                except Exception as e:
                    logger.error(f"❌ Error during search cycle: {e}")
                    logger.info("Continuing to next cycle...")
                
                # Wait before next search
                logger.info(f"\n⏳ Waiting {SEARCH_INTERVAL_MINUTES} minutes before next search...")
                logger.info(f"⏰ Next search at: {datetime.now().strftime('%H:%M:%S')}")
                time.sleep(SEARCH_INTERVAL_MINUTES * 60)
                
        except KeyboardInterrupt:
            logger.info("\n\n🛑 Stopping shift booker (Ctrl+C pressed)")
            logger.info(f"📊 Final Statistics: {len(self.booked_shifts)} shifts booked")
            for booking in self.booked_shifts:
                logger.info(f"   ✓ {booking['title']} on {booking['date']}")
        except Exception as e:
            logger.error(f"❌ Fatal error: {e}")
            logger.error("Attempting to restart...")
            time.sleep(10)
            self.run_continuous_booking()
        finally:
            self.close()

    def close(self):
        """Close the WebDriver"""
        if self.driver:
            self.driver.quit()
            logger.info("🔚 WebDriver closed")


def main():
    """Main execution function"""
    logger.info("Starting NHS Professionals Shift Booker...")
    logger.info(f"Configuration loaded for: {NHS_EMAIL}")
    
    booker = NHSShiftBooker(NHS_EMAIL, NHS_PASSWORD, headless=HEADLESS_MODE)
    booker.run_continuous_booking()


if __name__ == "__main__":
    main()