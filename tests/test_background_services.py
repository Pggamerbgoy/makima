import unittest
import sys
import os
import time
import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.background_services import (
    ServiceManager, WhatsAppService, EmailService, FileService, ActivityLog
)

class TestBackgroundServices(unittest.TestCase):
    
    def setUp(self):
        self.mock_ai = MagicMock()
        self.mock_ai.chat.return_value = ("Mock AI Summary", "neutral")
        self.activity_log = ActivityLog()
        
        # Suppress logging during tests
        import logging
        logging.getLogger("Makima.BGServices").setLevel(logging.CRITICAL)

    # ─── Activity Log Tests ─────────────────────────────────────────────────
    
    def test_activity_log(self):
        log = ActivityLog()
        log.add("TestService", "TestAction", "Details")
        recent = log.recent(1)
        self.assertEqual(len(recent), 1)
        self.assertEqual(recent[0]['service'], "TestService")
        
        summary = log.summary()
        self.assertIn("TestService", summary)

    # ─── File Service Tests ─────────────────────────────────────────────────

    def test_file_service_organization(self):
        """Test that FileService correctly organizes files into subfolders."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            
            # Create dummy files
            (tmp_path / "test.jpg").touch()
            (tmp_path / "doc.pdf").touch()
            (tmp_path / "random.xyz").touch()
            
            # Set modification time to past (so it's not skipped as "too new")
            past = time.time() - 100
            os.utime(tmp_path / "test.jpg", (past, past))
            os.utime(tmp_path / "doc.pdf", (past, past))

            fs = FileService(self.activity_log)
            fs.watched_folders = [tmp_path]
            
            # Run organization manually
            moved = fs._organize_folder(tmp_path)
            
            self.assertEqual(moved, 2)
            self.assertTrue((tmp_path / "Images" / "test.jpg").exists())
            self.assertTrue((tmp_path / "Documents" / "doc.pdf").exists())
            self.assertTrue((tmp_path / "random.xyz").exists()) # Should not move

    def test_file_service_cleanup(self):
        """Test that FileService cleans up old temp files."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            temp_file = tmp_path / "junk.tmp"
            temp_file.touch()
            
            # Age it beyond 30 days
            old_time = time.time() - (31 * 86400)
            os.utime(temp_file, (old_time, old_time))
            
            fs = FileService(self.activity_log)
            deleted, freed = fs._cleanup_temp_files(tmp_path)
            
            self.assertEqual(deleted, 1)
            self.assertFalse(temp_file.exists())

    # ─── Email Service Tests ────────────────────────────────────────────────

    @patch('imaplib.IMAP4_SSL')
    def test_email_service_fetch(self, mock_imap_cls):
        """Test email fetching and priority detection logic."""
        mock_imap = mock_imap_cls.return_value
        mock_imap.search.return_value = ('OK', [b'1'])
        
        # Mock fetching an email
        email_body = b'Subject: Urgent Invoice\r\nFrom: boss@company.com\r\n\r\nPay this ASAP.'
        mock_imap.fetch.return_value = ('OK', [(b'1 (RFC822 {100}', email_body), b')'])
        
        es = EmailService(self.mock_ai, self.activity_log)
        es._email_addr = "test@test.com"
        es._password = "pass"
        
        # Mock urgent callback
        urgent_mock = MagicMock()
        es.urgent_callback = urgent_mock
        
        # Run fetch
        emails = es._fetch_new_emails()
        self.assertEqual(len(emails), 1)
        self.assertIn("Urgent Invoice", emails[0]['subject'])
        
        # Process logic
        es._process_email(emails[0])
        
        # Should trigger urgent callback because "Urgent" and "ASAP" are priority keywords
        urgent_mock.assert_called()
        self.mock_ai.chat.assert_called()

    # ─── WhatsApp Service Tests ─────────────────────────────────────────────

    def test_whatsapp_service_init(self):
        """Test WhatsApp service initialization and status."""
        ws = WhatsAppService(self.mock_ai, self.activity_log)
        status = ws.get_status()
        self.assertIn("monitoring only", status)
        
        ws.enable(away_msg="Busy", use_ai=False)
        self.assertTrue(ws.auto_reply)
        self.assertEqual(ws.away_message, "Busy")

    @patch('selenium.webdriver.Chrome')
    def test_whatsapp_headless_setup(self, mock_chrome):
        """Test that headless browser options are configured correctly."""
        ws = WhatsAppService(self.mock_ai, self.activity_log)
        
        # Mock webdriver manager
        with patch('webdriver_manager.chrome.ChromeDriverManager.install', return_value='/tmp/driver'):
            with patch('selenium.webdriver.chrome.service.Service'):
                ws._init_headless_browser()
                
                # Verify headless argument was passed
                args, kwargs = mock_chrome.call_args
                options = kwargs['options']
                self.assertTrue(any("--headless" in arg for arg in options.arguments))

    # ─── Service Manager Tests ──────────────────────────────────────────────

    def test_service_manager_integration(self):
        """Test the central manager controls."""
        sm = ServiceManager(self.mock_ai)
        
        # Test toggles
        res = sm.toggle_auto_organize(False)
        self.assertFalse(sm.files.auto_organize)
        self.assertIn("disabled", res)
        
        # Test status aggregation
        full_status = sm.full_status()
        self.assertIn("WhatsApp", full_status)
        self.assertIn("Email", full_status)

if __name__ == "__main__":
    unittest.main()
