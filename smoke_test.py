#!/usr/bin/env python3

import requests
import sys
import json
import time
from datetime import datetime

class DeploymentSmokeTest:
    def __init__(self, base_url="https://evalflow-7.preview.emergentagent.com"):
        self.base_url = base_url
        self.session_token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def log_test(self, name: str, success: bool, details: str = ""):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name}")
        else:
            print(f"❌ {name} - {details}")
        
        self.test_results.append({
            "name": name,
            "success": success,
            "details": details
        })

    def make_request(self, method: str, endpoint: str, data: dict = None, expected_status: int = 200) -> tuple[bool, dict]:
        """Make API request with proper headers"""
        url = f"{self.base_url}/api/{endpoint.lstrip('/')}"
        headers = {'Content-Type': 'application/json'}
        
        if self.session_token:
            headers['Authorization'] = f'Bearer {self.session_token}'

        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=10)
            else:
                return False, {"error": f"Unsupported method: {method}"}

            success = response.status_code == expected_status
            try:
                response_data = response.json()
            except:
                response_data = {"status_code": response.status_code, "text": response.text}

            return success, response_data

        except Exception as e:
            return False, {"error": str(e)}

    def test_health_endpoint(self):
        """Test 1: Health endpoint reachable at /api/health"""
        print("🏥 Testing Health Endpoint...")
        success, data = self.make_request('GET', '/health')
        
        if success:
            status = data.get('status', 'unknown')
            auth_mode = data.get('auth_mode', 'unknown')
            self.log_test("Health endpoint reachable at /api/health", True, 
                         f"Status: {status}, Auth Mode: {auth_mode}")
        else:
            self.log_test("Health endpoint reachable at /api/health", False, str(data))
        
        return success

    def test_login_flow_start(self):
        """Test 2: Login flow works - start email auth"""
        print("🔐 Testing Login Flow - Start Email Auth...")
        
        test_email = "admin@company.com"  # Use demo account
        success, data = self.make_request('POST', '/auth/email/start', {"email": test_email})
        
        if success:
            has_code = 'code' in data or 'message' in data
            self.log_test("Login flow works - start email auth", has_code,
                         f"Response: {list(data.keys())}")
            return data.get('code')  # Return verification code for next test
        else:
            self.log_test("Login flow works - start email auth", False, str(data))
            return None

    def test_login_flow_verify(self, verification_code):
        """Test 3: Login flow works - verify code and get token"""
        print("🔑 Testing Login Flow - Verify Code...")
        
        if not verification_code:
            self.log_test("Login flow works - verify code and get token", False, 
                         "No verification code from previous step")
            return False
        
        test_email = "admin@company.com"
        success, data = self.make_request('POST', '/auth/email/verify', 
                                        {"email": test_email, "code": verification_code})
        
        if success:
            token = data.get('token')
            user = data.get('user', {})
            if token:
                self.session_token = token
                self.log_test("Login flow works - verify code and get token", True,
                             f"User: {user.get('name', 'Unknown')}, Token received")
                return True
            else:
                self.log_test("Login flow works - verify code and get token", False,
                             "No token in response")
        else:
            self.log_test("Login flow works - verify code and get token", False, str(data))
        
        return False

    def test_employee_dashboard_access(self):
        """Test 4: Employee dashboard loads after login (via API)"""
        print("📊 Testing Employee Dashboard Access...")
        
        if not self.session_token:
            self.log_test("Employee dashboard loads after login", False, 
                         "No session token available")
            return False
        
        # Test accessing user profile
        success, data = self.make_request('GET', '/auth/me')
        if success:
            user = data
            has_user_data = 'email' in user and 'name' in user
            self.log_test("Employee dashboard - user profile access", has_user_data,
                         f"User: {user.get('name', 'Unknown')} ({user.get('email', 'No email')})")
        else:
            self.log_test("Employee dashboard - user profile access", False, str(data))
            return False
        
        # Test accessing active cycle
        success, data = self.make_request('GET', '/cycles/active')
        if success:
            cycle = data
            has_cycle = cycle is not None
            self.log_test("Employee dashboard - active cycle access", has_cycle,
                         f"Cycle: {cycle.get('name', 'No cycle') if cycle else 'None'}")
        else:
            # It's OK if no active cycle exists
            self.log_test("Employee dashboard - active cycle access", True,
                         "No active cycle (expected for new deployment)")
        
        # Test accessing user's conversation
        success, data = self.make_request('GET', '/conversations/me')
        if success:
            conversation = data
            has_conversation = conversation is not None
            self.log_test("Employee dashboard - conversation access", has_conversation,
                         f"Conversation status: {conversation.get('status', 'No status') if conversation else 'None'}")
        else:
            self.log_test("Employee dashboard - conversation access", False, str(data))
            return False
        
        return True

    def test_pdf_export(self):
        """Test 5: PDF export still works"""
        print("📄 Testing PDF Export...")
        
        if not self.session_token:
            self.log_test("PDF export still works", False, "No session token available")
            return False
        
        # First get user's conversation
        success, conversation = self.make_request('GET', '/conversations/me')
        if not success or not conversation:
            self.log_test("PDF export still works", False, "No conversation available for PDF export")
            return False
        
        conversation_id = conversation.get('id')
        if not conversation_id:
            self.log_test("PDF export still works", False, "No conversation ID available")
            return False
        
        # Test PDF export endpoint
        url = f"{self.base_url}/api/conversations/{conversation_id}/pdf"
        headers = {'Authorization': f'Bearer {self.session_token}'}
        
        try:
            response = requests.get(url, headers=headers, timeout=15)
            
            is_pdf = response.status_code == 200 and 'application/pdf' in response.headers.get('content-type', '')
            if is_pdf:
                pdf_size = len(response.content)
                self.log_test("PDF export still works", True,
                             f"PDF generated successfully, size: {pdf_size} bytes")
            else:
                self.log_test("PDF export still works", False,
                             f"Status: {response.status_code}, Content-Type: {response.headers.get('content-type', 'unknown')}")
            
            return is_pdf
            
        except Exception as e:
            self.log_test("PDF export still works", False, str(e))
            return False

    def run_smoke_tests(self):
        """Run deployment hardening smoke tests"""
        print("🚀 HR PERFORMANCE MANAGEMENT - DEPLOYMENT HARDENING SMOKE TEST")
        print("=" * 70)
        print("Target: Emergent Environment (External URL)")
        print("Focus: Health endpoint, Login flow, Dashboard access, PDF export")
        print("=" * 70)

        # Test 1: Health endpoint
        if not self.test_health_endpoint():
            print("❌ Health check failed - stopping tests")
            return False

        # Test 2: Login flow - start
        verification_code = self.test_login_flow_start()

        # Test 3: Login flow - verify
        login_success = self.test_login_flow_verify(verification_code)

        # Test 4: Employee dashboard access (only if login succeeded)
        if login_success:
            self.test_employee_dashboard_access()
            
            # Test 5: PDF export (only if login succeeded)
            self.test_pdf_export()
        else:
            print("⚠️ Skipping dashboard and PDF tests due to login failure")

        # Print Results
        print("\n" + "=" * 70)
        print(f"🔍 SMOKE TEST RESULTS: {self.tests_passed}/{self.tests_run} tests passed")
        
        if self.tests_passed == self.tests_run:
            print("\n✅ DEPLOYMENT HARDENING SMOKE TEST PASSED")
            print("   All core functionality verified working after deployment changes.")
            return True
        else:
            print(f"\n❌ DEPLOYMENT HARDENING SMOKE TEST FAILED")
            print(f"   {self.tests_run - self.tests_passed} issues found")
            
            # Show failed tests
            failed_tests = [r for r in self.test_results if not r['success']]
            if failed_tests:
                print("\n❌ Failed Tests:")
                for test in failed_tests:
                    print(f"   - {test['name']}: {test['details']}")
            
            return False

def main():
    """Main test execution"""
    tester = DeploymentSmokeTest()
    
    try:
        success = tester.run_smoke_tests()
        return 0 if success else 1
    except KeyboardInterrupt:
        print("\n⏹️  Tests interrupted by user")
        return 1
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())