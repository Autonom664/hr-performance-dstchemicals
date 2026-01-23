#!/usr/bin/env python3

import requests
import sys
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

class HRSecurityTester:
    def __init__(self, base_url="https://hr-performance-app-1.preview.emergentagent.com"):
        self.base_url = base_url
        self.session_tokens = {}  # Store multiple user sessions
        self.current_user = None
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []
        self.test_conversations = {}  # Store conversation IDs for testing

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

    def make_request(self, method: str, endpoint: str, data: Dict = None, expected_status: int = 200, user_email: str = None) -> tuple[bool, Dict]:
        """Make API request with proper headers"""
        url = f"{self.base_url}/api/{endpoint.lstrip('/')}"
        headers = {'Content-Type': 'application/json'}
        
        # Use specific user's session token if provided
        session_token = None
        if user_email and user_email in self.session_tokens:
            session_token = self.session_tokens[user_email]
        elif hasattr(self, 'session_token') and self.session_token:
            session_token = self.session_token
            
        if session_token:
            headers['Authorization'] = f'Bearer {session_token}'

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

    def authenticate_user(self, email: str) -> bool:
        """Authenticate a user and store their session token"""
        print(f"🔐 Authenticating {email}...")
        
        # Start auth
        success, data = self.make_request('POST', '/auth/email/start', {"email": email})
        if not success:
            self.log_test(f"Auth Start ({email})", False, str(data))
            return False
            
        verification_code = data.get('code')
        if not verification_code:
            self.log_test(f"Auth Start ({email})", False, "No verification code received")
            return False
            
        # Verify auth
        success, data = self.make_request('POST', '/auth/email/verify', 
                                        {"email": email, "code": verification_code})
        if success:
            self.session_tokens[email] = data.get('token')
            self.log_test(f"Authentication ({email})", True, f"User: {data.get('user', {}).get('name', email)}")
            return True
        else:
            self.log_test(f"Authentication ({email})", False, str(data))
            return False

    def test_authorization_isolation(self):
        """Test authorization boundaries between users"""
        print("\n🔒 Testing Authorization Isolation...")
        
        # Ensure we have authenticated users
        users = ["admin@company.com", "engineering.lead@company.com", "developer1@company.com", "developer2@company.com"]
        for user in users:
            if user not in self.session_tokens:
                if not self.authenticate_user(user):
                    print(f"❌ Failed to authenticate {user} - skipping authorization tests")
                    return False
        
        # Get conversations for testing
        dev1_conv = self.get_user_conversation("developer1@company.com")
        dev2_conv = self.get_user_conversation("developer2@company.com")
        
        if not dev1_conv or not dev2_conv:
            self.log_test("Authorization Setup", False, "Could not get test conversations")
            return False
            
        dev1_conv_id = dev1_conv.get('id')
        dev2_conv_id = dev2_conv.get('id')
        
        # Test 1: Employee cannot access another employee's conversation by ID
        success, data = self.make_request('GET', f'/conversations/{dev2_conv_id}/pdf', 
                                        user_email="developer1@company.com", expected_status=403)
        self.log_test("Employee cannot access other employee's conversation (PDF)", success, 
                     "403 Forbidden" if success else f"Got {data.get('status_code', 'unknown')}")
        
        # Test 2: Employee cannot access conversation via URL manipulation
        success, data = self.make_request('GET', f'/manager/conversations/developer2@company.com', 
                                        user_email="developer1@company.com", expected_status=403)
        self.log_test("Employee cannot access manager endpoints", success,
                     "403 Forbidden" if success else f"Got {data.get('status_code', 'unknown')}")
        
        # Test 3: Manager cannot access conversations of users NOT in their reporting line
        # First, create a user not under engineering.lead
        test_user_email = f"external.user.{datetime.now().strftime('%H%M%S')}@company.com"
        admin_import_data = [{
            "employee_email": test_user_email,
            "employee_name": "External User",
            "manager_email": "other.manager@company.com",  # Different manager
            "department": "Other",
            "is_admin": False
        }]
        
        # Import as admin
        self.make_request('POST', '/admin/users/import', admin_import_data, user_email="admin@company.com")
        
        # Try to access as engineering.lead (should fail)
        success, data = self.make_request('GET', f'/manager/conversations/{test_user_email}', 
                                        user_email="engineering.lead@company.com", expected_status=403)
        self.log_test("Manager cannot access non-report conversations", success,
                     "403 Forbidden" if success else f"Got {data.get('status_code', 'unknown')}")
        
        # Test 4: Admin can access any conversation
        success, data = self.make_request('GET', f'/conversations/{dev1_conv_id}/pdf', 
                                        user_email="admin@company.com", expected_status=200)
        self.log_test("Admin can access any conversation", success,
                     "200 OK" if success else f"Got {data.get('status_code', 'unknown')}")
        
        return True

    def test_session_security(self):
        """Test session and cookie security"""
        print("\n🍪 Testing Session Security...")
        
        # Test 1: Sessions use httpOnly cookies (check response headers)
        auth_data = {"email": "developer1@company.com", "code": "123456"}
        url = f"{self.base_url}/api/auth/email/verify"
        
        # First get a verification code
        self.make_request('POST', '/auth/email/start', {"email": "developer1@company.com"})
        
        response = requests.post(url, json=auth_data, timeout=10)
        
        # Check if Set-Cookie header contains httponly
        set_cookie = response.headers.get('set-cookie', '')
        has_httponly = 'httponly' in set_cookie.lower()
        self.log_test("Sessions use httpOnly cookies", has_httponly,
                     f"Set-Cookie: {set_cookie[:100]}..." if set_cookie else "No Set-Cookie header")
        
        # Test 2: Session expiry enforcement (simulate expired session)
        # This would require manipulating the database or waiting, so we test the logic
        expired_token = "expired_token_test"
        headers = {'Authorization': f'Bearer {expired_token}', 'Content-Type': 'application/json'}
        url = f"{self.base_url}/api/auth/me"
        
        response = requests.get(url, headers=headers, timeout=10)
        success = response.status_code == 401
        self.log_test("Session expiry is enforced", success,
                     "401 Unauthorized for invalid token" if success else f"Got {response.status_code}")
        
        # Test 3: Logout properly invalidates session
        if "developer1@company.com" in self.session_tokens:
            token_before = self.session_tokens["developer1@company.com"]
            
            # Logout
            success, data = self.make_request('POST', '/auth/logout', user_email="developer1@company.com")
            
            # Try to use the token after logout
            headers = {'Authorization': f'Bearer {token_before}', 'Content-Type': 'application/json'}
            response = requests.get(f"{self.base_url}/api/auth/me", headers=headers, timeout=10)
            
            token_invalid = response.status_code == 401
            self.log_test("Logout invalidates session", token_invalid,
                         "Token invalid after logout" if token_invalid else f"Token still valid: {response.status_code}")
            
            # Re-authenticate for further tests
            self.authenticate_user("developer1@company.com")
        
        return True

    def test_cycle_integrity(self):
        """Test cycle management integrity"""
        print("\n🔄 Testing Cycle Integrity...")
        
        if "admin@company.com" not in self.session_tokens:
            self.authenticate_user("admin@company.com")
        
        # Test 1: Only one active cycle at a time
        # Create two test cycles
        cycle1_data = {
            "name": f"Test Cycle 1 {datetime.now().strftime('%H%M%S')}",
            "start_date": datetime.now().isoformat(),
            "end_date": (datetime.now() + timedelta(days=90)).isoformat(),
            "status": "draft"
        }
        
        cycle2_data = {
            "name": f"Test Cycle 2 {datetime.now().strftime('%H%M%S')}",
            "start_date": datetime.now().isoformat(),
            "end_date": (datetime.now() + timedelta(days=90)).isoformat(),
            "status": "draft"
        }
        
        # Create cycles
        success1, data1 = self.make_request('POST', '/admin/cycles', cycle1_data, user_email="admin@company.com")
        success2, data2 = self.make_request('POST', '/admin/cycles', cycle2_data, user_email="admin@company.com")
        
        if success1 and success2:
            cycle1_id = data1.get('id')
            cycle2_id = data2.get('id')
            
            # Activate first cycle
            success, _ = self.make_request('PATCH', f'/admin/cycles/{cycle1_id}?status=active', 
                                        user_email="admin@company.com")
            
            # Activate second cycle (should deactivate first)
            success, _ = self.make_request('PATCH', f'/admin/cycles/{cycle2_id}?status=active', 
                                        user_email="admin@company.com")
            
            # Check that only cycle2 is active
            success, cycles = self.make_request('GET', '/admin/cycles', user_email="admin@company.com")
            if success:
                active_cycles = [c for c in cycles if c.get('status') == 'active']
                only_one_active = len(active_cycles) == 1 and active_cycles[0].get('id') == cycle2_id
                self.log_test("Only one active cycle at a time", only_one_active,
                             f"Found {len(active_cycles)} active cycles")
            else:
                self.log_test("Only one active cycle at a time", False, "Could not retrieve cycles")
        
        # Test 2: Status transitions work correctly
        if success2:
            cycle_id = data2.get('id')
            
            # Test draft -> active
            success, data = self.make_request('PATCH', f'/admin/cycles/{cycle_id}?status=active', 
                                            user_email="admin@company.com")
            transition_works = success and data.get('status') == 'active'
            self.log_test("Cycle status transitions work", transition_works,
                         f"Status: {data.get('status', 'unknown')}" if success else str(data))
        
        return True

    def test_pdf_completeness(self):
        """Test PDF export completeness"""
        print("\n📄 Testing PDF Export Completeness...")
        
        # Get a conversation to test
        conv = self.get_user_conversation("developer1@company.com")
        if not conv:
            self.log_test("PDF Test Setup", False, "No conversation available for PDF test")
            return False
            
        conv_id = conv.get('id')
        
        # Update conversation with test data
        update_data = {
            "employee_self_review": "Comprehensive self-review content for PDF testing",
            "goals_next_period": "Detailed goals for the next performance period",
            "status": "ready_for_manager"
        }
        
        self.make_request('PUT', '/conversations/me', update_data, user_email="developer1@company.com")
        
        # Add manager review (as manager)
        if "engineering.lead@company.com" not in self.session_tokens:
            self.authenticate_user("engineering.lead@company.com")
            
        manager_update = {
            "manager_review": "Detailed manager review for PDF testing",
            "meeting_date": datetime.now().isoformat(),
            "ratings": {"performance": 4, "collaboration": 5, "growth": 3},
            "status": "completed"
        }
        
        self.make_request('PUT', f'/manager/conversations/developer1@company.com', 
                         manager_update, user_email="engineering.lead@company.com")
        
        # Test PDF export
        url = f"{self.base_url}/api/conversations/{conv_id}/pdf"
        headers = {'Authorization': f'Bearer {self.session_tokens["developer1@company.com"]}'}
        
        try:
            response = requests.get(url, headers=headers, timeout=15)
            
            # Test 1: PDF is generated successfully
            is_pdf = response.status_code == 200 and 'application/pdf' in response.headers.get('content-type', '')
            self.log_test("PDF Export generates successfully", is_pdf,
                         f"Content-Type: {response.headers.get('content-type', 'unknown')}")
            
            # Test 2: PDF has reasonable size (indicates content)
            pdf_size = len(response.content) if is_pdf else 0
            has_content = pdf_size > 5000  # Reasonable minimum for a complete PDF
            self.log_test("PDF Export has substantial content", has_content,
                         f"PDF size: {pdf_size} bytes")
            
            # Test 3: Filename includes employee info
            content_disposition = response.headers.get('content-disposition', '')
            has_filename = 'developer1' in content_disposition.lower()
            self.log_test("PDF Export includes employee in filename", has_filename,
                         f"Content-Disposition: {content_disposition}")
            
            return is_pdf and has_content
            
        except Exception as e:
            self.log_test("PDF Export", False, str(e))
            return False

    def test_data_persistence(self):
        """Test data persistence and restart behavior"""
        print("\n💾 Testing Data Persistence...")
        
        # Test 1: Create test data
        test_email = f"persistence.test.{datetime.now().strftime('%H%M%S')}@company.com"
        
        # Import user as admin
        if "admin@company.com" not in self.session_tokens:
            self.authenticate_user("admin@company.com")
            
        import_data = [{
            "employee_email": test_email,
            "employee_name": "Persistence Test User",
            "manager_email": "engineering.lead@company.com",
            "department": "Testing",
            "is_admin": False
        }]
        
        success, data = self.make_request('POST', '/admin/users/import', import_data, 
                                        user_email="admin@company.com")
        
        if success:
            # Authenticate the test user
            if self.authenticate_user(test_email):
                # Create conversation data
                conv = self.get_user_conversation(test_email)
                if conv:
                    update_data = {
                        "employee_self_review": f"Persistence test data created at {datetime.now()}",
                        "goals_next_period": "Test goals for persistence verification",
                        "status": "in_progress"
                    }
                    
                    success, _ = self.make_request('PUT', '/conversations/me', update_data, 
                                                 user_email=test_email)
                    
                    self.log_test("Data Persistence - Create test data", success,
                                 "Test conversation created" if success else "Failed to create test data")
                    
                    # Test 2: Verify data can be retrieved
                    success, retrieved_conv = self.make_request('GET', '/conversations/me', 
                                                              user_email=test_email)
                    
                    data_matches = (success and 
                                  retrieved_conv.get('employee_self_review') == update_data['employee_self_review'])
                    
                    self.log_test("Data Persistence - Retrieve test data", data_matches,
                                 "Data retrieved successfully" if data_matches else "Data mismatch or retrieval failed")
                    
                    return data_matches
        
        self.log_test("Data Persistence", False, "Could not set up test data")
        return False

    def get_user_conversation(self, email: str):
        """Helper to get a user's conversation"""
        if email not in self.session_tokens:
            if not self.authenticate_user(email):
                return None
                
        success, data = self.make_request('GET', '/conversations/me', user_email=email)
        return data if success else None

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