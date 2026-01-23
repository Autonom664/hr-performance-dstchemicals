#!/usr/bin/env python3

import requests
import sys
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

class HRPerformanceAPITester:
    def __init__(self, base_url="https://hr-performance-app-1.preview.emergentagent.com"):
        self.base_url = base_url
        self.session_token = None
        self.current_user = None
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

    def make_request(self, method: str, endpoint: str, data: Dict = None, expected_status: int = 200) -> tuple[bool, Dict]:
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
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers, timeout=10)
            elif method == 'PATCH':
                response = requests.patch(url, json=data, headers=headers, timeout=10)
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

    def test_health_check(self):
        """Test health check endpoint"""
        success, data = self.make_request('GET', '/health')
        self.log_test("Health Check", success, 
                     f"Status: {data.get('status', 'unknown')}" if success else str(data))
        return success

    def test_email_auth_start(self, email: str):
        """Test starting email authentication"""
        success, data = self.make_request('POST', '/auth/email/start', 
                                        {"email": email})
        
        if success:
            verification_code = data.get('code')
            self.log_test(f"Email Auth Start ({email})", True, 
                         f"Code: {verification_code}" if verification_code else "Code sent")
            return verification_code
        else:
            self.log_test(f"Email Auth Start ({email})", False, str(data))
            return None

    def test_email_auth_verify(self, email: str, code: str):
        """Test verifying email authentication"""
        success, data = self.make_request('POST', '/auth/email/verify', 
                                        {"email": email, "code": code})
        
        if success:
            self.session_token = data.get('token')
            self.current_user = data.get('user')
            self.log_test(f"Email Auth Verify ({email})", True, 
                         f"User: {self.current_user.get('name', email)}")
            return True
        else:
            self.log_test(f"Email Auth Verify ({email})", False, str(data))
            return False

    def test_auth_me(self):
        """Test getting current user info"""
        success, data = self.make_request('GET', '/auth/me')
        self.log_test("Get Current User", success, 
                     f"User: {data.get('email', 'unknown')}" if success else str(data))
        return success

    def test_get_active_cycle(self):
        """Test getting active cycle"""
        success, data = self.make_request('GET', '/cycles/active')
        # Note: 404 is acceptable if no active cycle exists
        if success or (not success and data.get('status_code') == 404):
            self.log_test("Get Active Cycle", True, 
                         f"Cycle: {data.get('name', 'No active cycle')}")
            return data if success else None
        else:
            self.log_test("Get Active Cycle", False, str(data))
            return None

    def test_get_my_conversation(self):
        """Test getting user's conversation"""
        success, data = self.make_request('GET', '/conversations/me')
        # 404 is acceptable if no active cycle
        if success or (not success and data.get('status_code') == 404):
            self.log_test("Get My Conversation", True, 
                         f"Status: {data.get('status', 'No conversation')}")
            return data if success else None
        else:
            self.log_test("Get My Conversation", False, str(data))
            return None

    def test_update_my_conversation(self):
        """Test updating user's conversation"""
        update_data = {
            "employee_self_review": "Test self review content",
            "goals_next_period": "Test goals for next period",
            "status": "in_progress"
        }
        
        success, data = self.make_request('PUT', '/conversations/me', update_data)
        self.log_test("Update My Conversation", success, 
                     f"Status: {data.get('status', 'unknown')}" if success else str(data))
        return success

    def test_admin_get_users(self):
        """Test getting all users (admin only)"""
        success, data = self.make_request('GET', '/admin/users')
        if success:
            user_count = len(data) if isinstance(data, list) else 0
            self.log_test("Admin Get Users", True, f"Found {user_count} users")
            return data
        else:
            self.log_test("Admin Get Users", False, str(data))
            return None

    def test_admin_import_users(self):
        """Test importing users (admin only)"""
        test_users = [
            {
                "employee_email": f"test.user.{datetime.now().strftime('%H%M%S')}@company.com",
                "employee_name": "Test User",
                "department": "Testing",
                "is_admin": False
            }
        ]
        
        success, data = self.make_request('POST', '/admin/users/import', test_users)
        self.log_test("Admin Import Users", success, 
                     f"Imported: {data.get('imported', 0)}" if success else str(data))
        return success

    def test_admin_get_cycles(self):
        """Test getting all cycles (admin only)"""
        success, data = self.make_request('GET', '/admin/cycles')
        if success:
            cycle_count = len(data) if isinstance(data, list) else 0
            self.log_test("Admin Get Cycles", True, f"Found {cycle_count} cycles")
            return data
        else:
            self.log_test("Admin Get Cycles", False, str(data))
            return None

    def test_admin_create_cycle(self):
        """Test creating a performance cycle (admin only)"""
        cycle_data = {
            "name": f"Test Cycle {datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "start_date": datetime.now().isoformat(),
            "end_date": (datetime.now() + timedelta(days=90)).isoformat(),
            "status": "draft"
        }
        
        success, data = self.make_request('POST', '/admin/cycles', cycle_data, 200)
        if success:
            cycle_id = data.get('id')
            self.log_test("Admin Create Cycle", True, f"Created cycle: {cycle_id}")
            return cycle_id
        else:
            self.log_test("Admin Create Cycle", False, str(data))
            return None

    def test_admin_update_cycle_status(self, cycle_id: str):
        """Test updating cycle status (admin only)"""
        success, data = self.make_request('PATCH', f'/admin/cycles/{cycle_id}?status=active')
        self.log_test("Admin Update Cycle Status", success, 
                     f"Status: {data.get('status', 'unknown')}" if success else str(data))
        return success

    def test_manager_get_reports(self):
        """Test getting direct reports (manager only)"""
        success, data = self.make_request('GET', '/manager/reports')
        if success:
            report_count = len(data) if isinstance(data, list) else 0
            self.log_test("Manager Get Reports", True, f"Found {report_count} reports")
            return data
        else:
            self.log_test("Manager Get Reports", False, str(data))
            return None

    def test_pdf_export(self, conversation_id: str):
        """Test PDF export functionality"""
        if not conversation_id:
            self.log_test("PDF Export", False, "No conversation ID provided")
            return False
            
        # For PDF export, we expect a different response type
        url = f"{self.base_url}/api/conversations/{conversation_id}/pdf"
        headers = {}
        if self.session_token:
            headers['Authorization'] = f'Bearer {self.session_token}'
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            success = response.status_code == 200 and 'application/pdf' in response.headers.get('content-type', '')
            self.log_test("PDF Export", success, 
                         f"Content-Type: {response.headers.get('content-type', 'unknown')}")
            return success
        except Exception as e:
            self.log_test("PDF Export", False, str(e))
            return False

    def run_full_test_suite(self):
        """Run comprehensive test suite"""
        print("🚀 Starting HR Performance Management API Tests")
        print("=" * 60)

        # Test 1: Health Check
        if not self.test_health_check():
            print("❌ Health check failed - stopping tests")
            return False

        # Test 2: Authentication Flow - Admin
        print("\n📧 Testing Admin Authentication...")
        admin_code = self.test_email_auth_start("admin@company.com")
        if not admin_code:
            print("❌ Admin auth start failed - stopping tests")
            return False

        if not self.test_email_auth_verify("admin@company.com", admin_code):
            print("❌ Admin auth verify failed - stopping tests")
            return False

        self.test_auth_me()

        # Test 3: Admin Functions
        print("\n👑 Testing Admin Functions...")
        self.test_admin_get_users()
        self.test_admin_import_users()
        cycles = self.test_admin_get_cycles()
        
        # Create a test cycle
        cycle_id = self.test_admin_create_cycle()
        if cycle_id:
            self.test_admin_update_cycle_status(cycle_id)

        # Test 4: Employee Functions
        print("\n👤 Testing Employee Functions...")
        self.test_get_active_cycle()
        conversation = self.test_get_my_conversation()
        self.test_update_my_conversation()

        # Test 5: Manager Authentication and Functions
        print("\n👔 Testing Manager Authentication...")
        manager_code = self.test_email_auth_start("engineering.lead@company.com")
        if manager_code:
            if self.test_email_auth_verify("engineering.lead@company.com", manager_code):
                self.test_manager_get_reports()

        # Test 6: Employee Authentication
        print("\n👨‍💼 Testing Employee Authentication...")
        employee_code = self.test_email_auth_start("developer1@company.com")
        if employee_code:
            if self.test_email_auth_verify("developer1@company.com", employee_code):
                employee_conversation = self.test_get_my_conversation()
                if employee_conversation and employee_conversation.get('id'):
                    self.test_pdf_export(employee_conversation['id'])

        # Print Results
        print("\n" + "=" * 60)
        print(f"📊 Test Results: {self.tests_passed}/{self.tests_run} passed")
        
        if self.tests_passed == self.tests_run:
            print("🎉 All tests passed!")
            return True
        else:
            print(f"⚠️  {self.tests_run - self.tests_passed} tests failed")
            return False

def main():
    """Main test execution"""
    tester = HRPerformanceAPITester()
    
    try:
        success = tester.run_full_test_suite()
        return 0 if success else 1
    except KeyboardInterrupt:
        print("\n⏹️  Tests interrupted by user")
        return 1
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())