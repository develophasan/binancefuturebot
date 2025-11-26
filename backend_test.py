#!/usr/bin/env python3

import requests
import sys
import json
from datetime import datetime
import time

class BinanceFuturesBotTester:
    def __init__(self, base_url="https://smartfutures-1.preview.emergentagent.com"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def log_test(self, name, success, details=""):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name} - PASSED")
        else:
            print(f"❌ {name} - FAILED: {details}")
        
        self.test_results.append({
            "name": name,
            "success": success,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })

    def run_test(self, name, method, endpoint, expected_status=200, data=None, timeout=10):
        """Run a single API test"""
        url = f"{self.base_url}/api/{endpoint}"
        headers = {'Content-Type': 'application/json'}

        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=timeout)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=timeout)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers, timeout=timeout)

            success = response.status_code == expected_status
            
            if success:
                try:
                    response_data = response.json()
                    print(f"   Status: {response.status_code}")
                    print(f"   Response: {json.dumps(response_data, indent=2)[:200]}...")
                    self.log_test(name, True)
                    return True, response_data
                except:
                    print(f"   Status: {response.status_code}")
                    print(f"   Response: {response.text[:200]}...")
                    self.log_test(name, True)
                    return True, {}
            else:
                error_msg = f"Expected {expected_status}, got {response.status_code}"
                print(f"   Error: {error_msg}")
                print(f"   Response: {response.text[:200]}...")
                self.log_test(name, False, error_msg)
                return False, {}

        except requests.exceptions.Timeout:
            error_msg = f"Request timeout after {timeout}s"
            print(f"   Error: {error_msg}")
            self.log_test(name, False, error_msg)
            return False, {}
        except Exception as e:
            error_msg = f"Request failed: {str(e)}"
            print(f"   Error: {error_msg}")
            self.log_test(name, False, error_msg)
            return False, {}

    def test_bot_status(self):
        """Test bot status endpoint"""
        success, data = self.run_test("Bot Status", "GET", "bot/status")
        if success and data:
            required_fields = ['is_running', 'is_active', 'open_positions_count', 'trades_today', 'daily_pnl_usdt', 'total_equity_usdt']
            missing_fields = [field for field in required_fields if field not in data]
            if missing_fields:
                self.log_test("Bot Status Fields", False, f"Missing fields: {missing_fields}")
            else:
                self.log_test("Bot Status Fields", True)
        return success

    def test_settings(self):
        """Test settings endpoints"""
        # Get settings
        success, settings = self.run_test("Get Settings", "GET", "settings")
        if not success:
            return False
        
        # Update settings
        if settings:
            update_data = {
                "is_active": True,
                "position_size_value": 10.0,
                "max_leverage": 5
            }
            success, _ = self.run_test("Update Settings", "PUT", "settings", data=update_data)
        
        return success

    def test_positions(self):
        """Test positions endpoints"""
        # Get open positions
        success1, _ = self.run_test("Get Open Positions", "GET", "positions?status=OPEN")
        
        # Get closed positions
        success2, _ = self.run_test("Get Closed Positions", "GET", "positions?status=CLOSED")
        
        return success1 and success2

    def test_ai_decisions(self):
        """Test AI decisions endpoint"""
        success, data = self.run_test("Get AI Decisions", "GET", "decisions?limit=10")
        return success

    def test_market_data(self):
        """Test market data endpoints"""
        success, data = self.run_test("Get Top Gainers", "GET", "market/top-gainers?limit=5")
        if success and data:
            if isinstance(data, list) and len(data) > 0:
                required_fields = ['symbol', 'price_change_percent', 'volume_24h', 'price']
                first_item = data[0]
                missing_fields = [field for field in required_fields if field not in first_item]
                if missing_fields:
                    self.log_test("Top Gainers Fields", False, f"Missing fields: {missing_fields}")
                else:
                    self.log_test("Top Gainers Fields", True)
        return success

    def test_bot_control(self):
        """Test bot start/stop functionality"""
        # Test stop
        success1, _ = self.run_test("Stop Bot", "POST", "bot/stop")
        
        # Wait a moment
        time.sleep(1)
        
        # Test start
        success2, _ = self.run_test("Start Bot", "POST", "bot/start")
        
        return success1 and success2

    def run_all_tests(self):
        """Run all backend tests"""
        print("🚀 Starting Binance Futures AI Bot Backend Tests")
        print("=" * 60)
        
        # Test all endpoints
        self.test_bot_status()
        self.test_settings()
        self.test_positions()
        self.test_ai_decisions()
        self.test_market_data()
        self.test_bot_control()
        
        # Print summary
        print("\n" + "=" * 60)
        print(f"📊 Test Summary: {self.tests_passed}/{self.tests_run} tests passed")
        
        if self.tests_passed == self.tests_run:
            print("🎉 All tests passed!")
            return 0
        else:
            print("⚠️  Some tests failed!")
            failed_tests = [test for test in self.test_results if not test['success']]
            print("\nFailed tests:")
            for test in failed_tests:
                print(f"  - {test['name']}: {test['details']}")
            return 1

def main():
    tester = BinanceFuturesBotTester()
    return tester.run_all_tests()

if __name__ == "__main__":
    sys.exit(main())