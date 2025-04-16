import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QLineEdit, QPushButton, QTextEdit, QCheckBox, 
                             QSlider, QProgressBar, QMessageBox, QSplitter)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QTextCursor
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import re
import random
import os

class ScraperThread(QThread):
    update_signal = pyqtSignal(str)
    result_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int, int, str)
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, hashtag, scroll_count, headless_mode):
        super().__init__()
        self.hashtag = hashtag
        self.scroll_count = scroll_count
        self.headless_mode = headless_mode
        self._is_running = True
        self.driver = None

    def run(self):
        try:
            self.log_message("🚀 Запуск парсера Instagram...")
            
            self.account_manager = AccountManager(self.log_message)
            self.state = ScraperState(self.hashtag, self.log_message)
            
            options = webdriver.ChromeOptions()
            options.add_argument("--disable-notifications")
            options.add_argument("--lang=en-US") 
            if self.headless_mode:
                options.add_argument("--headless=new")
                self.log_message("👻 Режим без отображения браузера")
            
            self.driver = webdriver.Chrome(options=options)
            
            try:
                username, password = self.account_manager.get_current_account()
                if not self.login_to_instagram(username, password):
                    self.finished_signal.emit(False, "❌ Ошибка входа в аккаунт")
                    return
                
                if not self.state.post_urls:
                    self.log_message("🌐 Начало сбора по хэштегу...")
                    if not self.scrape_hashtag_posts():
                        self.finished_signal.emit(False, "❌ Ошибка сбора по хэштегу")
                        return
                    self.state.save_state()
                
                self.log_message(f"🔍 Извлечение URL профилей из постов ({self.state.processed_posts}/{len(self.state.post_urls)} обработано)...")
                for i in range(self.state.processed_posts, len(self.state.post_urls)):
                    if not self._is_running:
                        self.finished_signal.emit(False, "⏹️ Парсинг остановлен пользователем")
                        return
                    
                    post_url = self.state.post_urls[i]
                    profile_url = self.extract_profile_url(post_url)
                    if profile_url:
                        self.state.profile_urls.append(profile_url)
                    self.state.processed_posts = i + 1
                    self.state.save_state()
                    self.progress_signal.emit(i+1, len(self.state.post_urls), "posts")
                    
                    self.log_message(f"📊 Обработан пост {i+1}/{len(self.state.post_urls)} (Аккаунт {self.account_manager.current_account_index + 1})")
                    
                    if self.account_manager.increment_scrape_count():
                        self.log_message("🔄 Смена аккаунта после 10 запросов...")
                        if self.perform_logout():
                            username, password = self.account_manager.rotate_account()
                            if not self.login_to_instagram(username, password):
                                self.log_message("❌ Не удалось сменить аккаунт - выход")
                                self.finished_signal.emit(False, "❌ Не удалось сменить аккаунт")
                                return
                
                if not self.state.profile_urls:
                    self.finished_signal.emit(False, "❌ Не найдено URL профилей")
                    return
                
                self.log_message(f"📡 Сбор Telegram URL из профилей ({self.state.processed_profiles}/{len(self.state.profile_urls)} обработано)...")
                for i in range(self.state.processed_profiles, len(self.state.profile_urls)):
                    if not self._is_running:
                        self.finished_signal.emit(False, "⏹️ Парсинг остановлен пользователем")
                        return
                    
                    profile_url = self.state.profile_urls[i]
                    self.log_message(f"🔎 Обработка профиля {i+1}/{len(self.state.profile_urls)} (Аккаунт {self.account_manager.current_account_index + 1})")
                    telegram_urls = self.scrape_telegram_url(profile_url)
                    for url in telegram_urls:
                        self.result_signal.emit(url)
                    self.state.telegram_urls.update(telegram_urls)
                    self.state.processed_profiles = i + 1
                    self.state.save_state()
                    self.progress_signal.emit(i+1, len(self.state.profile_urls), "profiles")
                    
                    if self.account_manager.increment_scrape_count():
                        self.log_message("🔄 Смена аккаунта после 10 запросов...")
                        if self.perform_logout():
                            username, password = self.account_manager.rotate_account()
                            if not self.login_to_instagram(username, password):
                                self.log_message("❌ Не удалось сменить аккаунт - выход")
                                self.finished_signal.emit(False, "❌ Не удалось сменить аккаунт")
                                return
                
                with open(f"instagram_{self.hashtag}_profiles.txt", 'w', encoding='utf-8') as f:
                    for url in sorted(self.state.profile_urls):
                        f.write(url + '\n')
                
                with open(f"instagram_{self.hashtag}_telegram.txt", 'w', encoding='utf-8') as f:
                    for url in sorted(self.state.telegram_urls):
                        f.write(url + '\n')
                
                success_message = f"🎉 Результаты сохранены:\n- {len(self.state.profile_urls)} URL профилей\n- {len(self.state.telegram_urls)} Telegram URL"
                self.finished_signal.emit(True, success_message)
                
            except Exception as e:
                self.finished_signal.emit(False, f"❌ Критическая ошибка: {str(e)}")
            finally:
                if self.driver:
                    self.driver.quit()
                self.state.save_state()
                
        except Exception as e:
            self.finished_signal.emit(False, f"❌ Ошибка инициализации: {str(e)}")

    def log_message(self, message):
        """Helper method to emit log messages"""
        self.update_signal.emit(message)

    def stop(self):
        self._is_running = False
        self.log_message("🛑 Остановка парсера... Пожалуйста, подождите")
        if self.driver:
            self.driver.quit()

    def verify_logout(self):
        try:
            self.driver.get("https://www.instagram.com/accounts/login/")
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.NAME, "password"))
            )
            return True
        except:
            return False

    def perform_logout(self):
        try:
            self.driver.delete_all_cookies()
            time.sleep(2)
            
            self.driver.get("https://www.instagram.com/accounts/logout/")
            time.sleep(3)
            
            if self.verify_logout():
                self.log_message("✅ Выход выполнен успешно")
                return True
            
            self.log_message("⚠️ Проверка выхода не удалась - пробуем альтернативный метод")
            self.driver.get("https://www.instagram.com/")
            time.sleep(2)
            try:
                menu = self.driver.find_element(By.XPATH, "//span[contains(@class, '_aa8h')]")
                menu.click()
                time.sleep(1)
                logout_btn = self.driver.find_element(By.XPATH, "//div[contains(text(), 'Log Out')]")
                logout_btn.click()
                time.sleep(3)
                return self.verify_logout()
            except:
                return False
                
        except Exception as e:
            self.log_message(f"⚠️ Ошибка при выходе: {str(e)}")
            return False

    def is_rate_limited(self):
        try:
            if "HTTP ERROR 429" in self.driver.page_source or "Please wait a few minutes" in self.driver.page_source:
                self.log_message("⚠️ Обнаружено ограничение запросов!")
                return True
            return False
        except:
            return False

    def safe_get(self, url):
        try:
            self.driver.get(url)
            time.sleep(random.uniform(2, 5))
            
            if self.is_rate_limited():
                self.log_message("⚠️ Лимит запросов! Ожидание 60 секунд и смена аккаунта...")
                time.sleep(60)
                
                if self.is_rate_limited():
                    self.log_message("⚠️ Все еще лимит после ожидания - выполняем выход")
                    if self.perform_logout():
                        username, password = self.account_manager.rotate_account()
                        if not self.login_to_instagram(username, password):
                            self.log_message("❌ Не удалось сменить аккаунт - выход")
                            return False
                        return self.safe_get(url)
                    else:
                        self.log_message("❌ Не удалось выйти - выход")
                        return False
                    
            return True
        except Exception as e:
            self.log_message(f"⚠️ Ошибка загрузки {url}: {str(e)}")
            return False

    def login_to_instagram(self, username, password, max_retries=3):
        retry_count = 0
        while retry_count < max_retries:
            try:
                if not self.safe_get("https://www.instagram.com/accounts/login/"):
                    return False
                    
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.NAME, "username"))
                )
                
                # Check for cookie consent button (only on first login attempt)
                if retry_count == 0:
                    try:
                        cookie_buttons = self.driver.find_elements(By.XPATH, "//button[contains(., 'Allow all cookies') or contains(., 'Accept all cookies')]")
                        for btn in cookie_buttons:
                            if btn.is_displayed():
                                btn.click()
                                self.log_message("🍪 Нажата кнопка согласия с куками")
                                time.sleep(2)
                                break
                    except Exception as e:
                        self.log_message(f"⚠️ Не удалось обработать согласие с куками: {str(e)}")
                
                self.driver.find_element(By.NAME, "username").clear()
                self.driver.find_element(By.NAME, "username").send_keys(username)
                self.driver.find_element(By.NAME, "password").clear()
                self.driver.find_element(By.NAME, "password").send_keys(password)
                
                login_button = self.driver.find_element(By.XPATH, "//button[@type='submit']")
                login_button.click()
                time.sleep(random.uniform(3, 7))
                
                for popup_text in ["Not Now", "Save Info", "Allow"]:
                    try:
                        WebDriverWait(self.driver, 5).until(
                            EC.presence_of_element_located((By.XPATH, f"//button[contains(text(), '{popup_text}')]"))
                        ).click()
                        time.sleep(random.uniform(1, 3))
                    except:
                        pass
                
                try:
                    WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.NAME, "password"))
                    )
                    self.log_message("🔒 Проверка входа не удалась - повторная попытка...")
                    retry_count += 1
                    time.sleep(random.uniform(5, 10))
                    continue
                except:
                    self.log_message(f"✅ Успешный вход для {username}")
                    return True
                    
            except Exception as e:
                self.log_message(f"⚠️ Ошибка входа: {str(e)}")
                retry_count += 1
                time.sleep(random.uniform(5, 15))
        
        self.log_message(f"❌ Не удалось войти после {max_retries} попыток")
        return False

    def scrape_hashtag_posts(self):
        try:
            if not self.safe_get(f"https://www.instagram.com/explore/tags/{self.hashtag}/"):
                return False
                
            time.sleep(random.uniform(3, 6))
            
            last_height = self.driver.execute_script("return document.body.scrollHeight")
            
            for _ in range(self.scroll_count):
                if not self._is_running:
                    return False
                    
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                self.log_message(f"🔄 Прокрутка ({self.account_manager.scrapes_count + 1}/10) с аккаунтом {self.account_manager.current_account_index + 1}")
                
                time.sleep(random.uniform(5, 8))
                
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    self.log_message("🔚 Достигнут конец доступного контента")
                    break
                last_height = new_height
                
                links = self.driver.find_elements(By.XPATH, "//a[contains(@href, '/p/')]")
                for link in links:
                    href = link.get_attribute("href")
                    if href and "/p/" in href:
                        clean_url = href.split('?')[0]
                        if clean_url not in self.state.post_urls:
                            self.state.post_urls.append(clean_url)
                time.sleep(random.uniform(1, 3))
                
                if self.account_manager.increment_scrape_count():
                    self.log_message("🔄 Смена аккаунта после 10 сборов...")
                    if self.perform_logout():
                        username, password = self.account_manager.rotate_account()
                        if not self.login_to_instagram(username, password):
                            self.log_message("❌ Не удалось сменить аккаунт - выход")
                            return False
            
            self.log_message(f"✅ Найдено {len(self.state.post_urls)} уникальных постов")
            return True
        except Exception as e:
            self.log_message(f"⚠️ Ошибка при сборе хэштегов: {str(e)}")
            return False

    def extract_profile_url(self, post_url):
        try:
            if not self.safe_get(post_url):
                return None
                
            time.sleep(random.uniform(2, 4))
            
            
            selectors = [
                "//a[contains(@class, 'x1i10hfl') and contains(@class, 'xjbqb8w') and contains(@class, '_a6hd') and contains(@href, '/')]",
                "//a[contains(@href, '/') and contains(@role, 'link')]",
                "//header//a[contains(@href, '/')]"
            ]
            
            for selector in selectors:
                try:
                    profile_element = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.XPATH, selector))
                    )
                    profile_url = profile_element.get_attribute('href')
                    if profile_url and "/" in profile_url:
                        return profile_url.split('?')[0]
                except:
                    continue
            
            self.log_message(f"⚠️ Не удалось извлечь URL профиля из {post_url} - возможно ограничение")
            if self.is_rate_limited():
                self.log_message("⚠️ Обнаружено ограничение запросов при извлечении профиля")
                if self.perform_logout():
                    username, password = self.account_manager.rotate_account()
                    if not self.login_to_instagram(username, password):
                        self.log_message("❌ Не удалось сменить аккаунт - выход")
                        return None
                    return self.extract_profile_url(post_url)
            
            return None
        except Exception as e:
            self.log_message(f"⚠️ Ошибка извлечения профиля из {post_url}: {str(e)}")
            return None

    def scrape_telegram_url(self, profile_url):
        try:
            if not self.safe_get(profile_url):
                return set()
                
            time.sleep(random.uniform(3, 6))
            
            found_telegram = set()
            
            telegram_spans = self.driver.find_elements(
                By.XPATH, "//span[contains(text(), 't.me/') or contains(text(), 'telegram.me/')]"
            )
            for span in telegram_spans:
                text = span.text
                if "t.me/" in text:
                    url_part = text.split("t.me/")[1].split()[0]
                    found_telegram.add(f"https://t.me/{url_part}")
                elif "telegram.me/" in text:
                    url_part = text.split("telegram.me/")[1].split()[0]
                    found_telegram.add(f"https://t.me/{url_part}")
                time.sleep(random.uniform(0.5, 1.5))
            
            telegram_links = self.driver.find_elements(
                By.XPATH, "//a[contains(@href, 't.me/') or contains(@href, 'telegram.me/')]"
            )
            for link in telegram_links:
                href = link.get_attribute('href')
                if "t.me/" in href:
                    username = href.split("t.me/")[1].split('/')[0]
                    found_telegram.add(f"https://t.me/{username}")
                elif "telegram.me/" in href:
                    username = href.split("telegram.me/")[1].split('/')[0]
                    found_telegram.add(f"https://t.me/{username}")
                time.sleep(random.uniform(0.3, 1.2))
            
            try:
                bio = self.driver.find_element(By.XPATH, "//div[contains(@class, '_aa_c')]").text
                telegram_pattern = re.compile(r'(?:t\.me/|telegram\.me/)([\w-]+)')
                for match in telegram_pattern.finditer(bio):
                    username = match.group(1)
                    found_telegram.add(f"https://t.me/{username}")
                time.sleep(random.uniform(1, 2))
            except:
                pass
            
            try:
                website = self.driver.find_element(By.XPATH, "//a[contains(@class, '_aa_s')]").get_attribute('href')
                if website and ("t.me/" in website or "telegram.me/" in website):
                    if "t.me/" in website:
                        username = website.split("t.me/")[1].split('/')[0]
                        found_telegram.add(f"https://t.me/{username}")
                    elif "telegram.me/" in website:
                        username = website.split("telegram.me/")[1].split('/')[0]
                        found_telegram.add(f"https://t.me/{username}")
                time.sleep(random.uniform(1, 2))
            except:
                pass
            
            self.log_message(f"✅ Найдено {len(found_telegram)} Telegram URL из {profile_url}")
            return found_telegram
        except Exception as e:
            self.log_message(f"⚠️ Ошибка при сборе Telegram из {profile_url}: {str(e)}")
            return set()

class AccountManager:
    def __init__(self, log_callback=None, credential_file='uid.txt'):
        self.credential_file = credential_file
        self.accounts = []
        self.current_account_index = 0
        self.scrapes_count = 0
        self.log_callback = log_callback
        self.load_accounts()
        
    def load_accounts(self):
        try:
            with open(self.credential_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and ':' in line:
                        username, password = line.split(':', 1)
                        self.accounts.append((username.strip(), password.strip()))
            
            if not self.accounts:
                raise ValueError("Не найдено валидных аккаунтов в файле с учетными данными")
                
            if self.log_callback:
                self.log_callback(f"✅ Загружено {len(self.accounts)} аккаунтов")
        except Exception as e:
            if self.log_callback:
                self.log_callback(f"❌ Ошибка чтения учетных данных: {str(e)}")
            raise

    def get_current_account(self):
        return self.accounts[self.current_account_index]

    def rotate_account(self):
        self.current_account_index = (self.current_account_index + 1) % len(self.accounts)
        self.scrapes_count = 0
        if self.log_callback:
            self.log_callback(f"🔄 Переключено на аккаунт {self.current_account_index + 1}/{len(self.accounts)}")
        return self.get_current_account()

    def increment_scrape_count(self):
        self.scrapes_count += 1
        if self.scrapes_count >= 10:
            return True
        return False

    def get_total_accounts(self):
        return len(self.accounts)

class ScraperState:
    def __init__(self, hashtag, log_callback=None):
        self.state_file = f"scraper_state_{hashtag}.txt"
        self.post_urls = []
        self.profile_urls = []
        self.telegram_urls = set()
        self.processed_posts = 0
        self.processed_profiles = 0
        self.log_callback = log_callback
        self.load_state()

    def load_state(self):
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    lines = [line.strip() for line in f.readlines()]
                    if len(lines) >= 3:
                        self.processed_posts = int(lines[0])
                        self.processed_profiles = int(lines[1])
                        self.post_urls = eval(lines[2]) if lines[2] else []
                        self.profile_urls = eval(lines[3]) if len(lines) > 3 and lines[3] else []
                        self.telegram_urls = set(eval(lines[4])) if len(lines) > 4 and lines[4] else set()
                if self.log_callback:
                    self.log_callback(f"✅ Загружено предыдущее состояние: {self.processed_posts} постов, {self.processed_profiles} профилей обработано")
        except Exception as e:
            if self.log_callback:
                self.log_callback(f"⚠️ Ошибка загрузки состояния: {str(e)}")
            self.reset_state()

    def save_state(self):
        try:
            with open(self.state_file, 'w', encoding='utf-8') as f:
                f.write(f"{self.processed_posts}\n")
                f.write(f"{self.processed_profiles}\n")
                f.write(f"{self.post_urls}\n")
                f.write(f"{self.profile_urls}\n")
                f.write(f"{list(self.telegram_urls)}\n")
        except Exception as e:
            if self.log_callback:
                self.log_callback(f"⚠️ Ошибка сохранения состояния: {str(e)}")

    def reset_state(self):
        self.post_urls = []
        self.profile_urls = []
        self.telegram_urls = set()
        self.processed_posts = 0
        self.processed_profiles = 0

class InstagramScraperGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Instagram Парсер")
        self.setGeometry(100, 100, 800, 600)
        
        self.scraper_thread = None
        self.setup_ui()
        
    def setup_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        layout = QVBoxLayout()
        main_widget.setLayout(layout)
        
        # Input fields
        input_layout = QHBoxLayout()
        
        hashtag_layout = QVBoxLayout()
        hashtag_layout.addWidget(QLabel("Хэштег (без #):"))
        self.hashtag_input = QLineEdit()
        hashtag_layout.addWidget(self.hashtag_input)
        
        scroll_layout = QVBoxLayout()
        scroll_layout.addWidget(QLabel("Количество прокруток (рекомендуется 1-20):"))
        self.scroll_slider = QSlider(Qt.Horizontal)
        self.scroll_slider.setRange(1, 20)
        self.scroll_slider.setValue(10)
        scroll_layout.addWidget(self.scroll_slider)
        self.scroll_value_label = QLabel("10")
        scroll_layout.addWidget(self.scroll_value_label)
        
        self.headless_checkbox = QCheckBox("Режим без отображения браузера")
        self.headless_checkbox.setChecked(False)
        
        input_layout.addLayout(hashtag_layout)
        input_layout.addLayout(scroll_layout)
        input_layout.addWidget(self.headless_checkbox)
        
        layout.addLayout(input_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        self.start_button = QPushButton("Начать парсинг")
        self.start_button.clicked.connect(self.start_scraping)
        self.stop_button = QPushButton("Остановить")
        self.stop_button.clicked.connect(self.stop_scraping)
        self.stop_button.setEnabled(False)
        
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.stop_button)
        layout.addLayout(button_layout)
        
        # Progress bars
        self.post_progress = QProgressBar()
        self.post_progress.setFormat("Посты: %v/%m")
        layout.addWidget(self.post_progress)
        
        self.profile_progress = QProgressBar()
        self.profile_progress.setFormat("Профили: %v/%m")
        layout.addWidget(self.profile_progress)
        
        # Splitter for logs and results
        splitter = QSplitter(Qt.Horizontal)
        
        # Log output
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        
        # Results output
        self.results_output = QTextEdit()
        self.results_output.setReadOnly(True)
        self.results_output.setPlaceholderText("Найденные Telegram URL будут отображаться здесь...")
        
        splitter.addWidget(self.log_output)
        splitter.addWidget(self.results_output)
        splitter.setSizes([400, 400])
        
        layout.addWidget(splitter)
        
        # Connect slider value change
        self.scroll_slider.valueChanged.connect(self.update_scroll_value)
        
    def update_scroll_value(self, value):
        self.scroll_value_label.setText(str(value))
        
    def start_scraping(self):
        hashtag = self.hashtag_input.text().strip()
        if not hashtag:
            QMessageBox.warning(self, "Ошибка ввода", "Пожалуйста, введите хэштег")
            return
            
        scroll_count = self.scroll_slider.value()
        headless_mode = self.headless_checkbox.isChecked()
        
        self.log_output.clear()
        self.results_output.clear()
        self.post_progress.setValue(0)
        self.profile_progress.setValue(0)
        
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        
        self.scraper_thread = ScraperThread(hashtag, scroll_count, headless_mode)
        self.scraper_thread.update_signal.connect(self.update_log)
        self.scraper_thread.result_signal.connect(self.update_results)
        self.scraper_thread.progress_signal.connect(self.update_progress)
        self.scraper_thread.finished_signal.connect(self.scraping_finished)
        self.scraper_thread.start()
        
    def stop_scraping(self):
        if self.scraper_thread and self.scraper_thread.isRunning():
            self.scraper_thread.stop()
            self.stop_button.setEnabled(False)
            
    def update_log(self, message):
        self.log_output.moveCursor(QTextCursor.End)
        self.log_output.insertPlainText(message + "\n")
        self.log_output.moveCursor(QTextCursor.End)
        
    def update_results(self, url):
        self.results_output.moveCursor(QTextCursor.End)
        self.results_output.insertPlainText(url + "\n")
        self.results_output.moveCursor(QTextCursor.End)
        
    def update_progress(self, current, total, stage):
        if stage == "posts":
            self.post_progress.setMaximum(total)
            self.post_progress.setValue(current)
        elif stage == "profiles":
            self.profile_progress.setMaximum(total)
            self.profile_progress.setValue(current)
            
    def scraping_finished(self, success, message):
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        
        self.update_log(message)
        
        if success:
            QMessageBox.information(self, "Успех", message)
        else:
            QMessageBox.warning(self, "Парсинг завершен", message)
            
        self.scraper_thread = None

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = InstagramScraperGUI()
    window.show()
    sys.exit(app.exec_())