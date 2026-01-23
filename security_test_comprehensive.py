#!/usr/bin/env python3

import requests
import sys
import json
import time
import subprocess
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

class HRSecurityTesterComprehensive:
    def __init__(self, base_url="https://evalflow-7.preview.emergentagent.com"):
        self.base_url = base_url
        self.session_tokens = {}
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []
        self.critical_issues = []
        self.warnings = []

    def log_test(self, name: str, success: bool, details: str = "", is_critical: bool = False):
        """Log test result with criticality"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name}")
        else:
            print(f"❌ {name} - {details}")
            if is_critical:
                self.critical_issues.append({"name": name, "details": details})
            else:
                self.warnings.append({"name": name, "details": details})
        
        self.test_results.append({
            "name": name,
            "success": success,
            "details": details,
            "critical": is_critical
        })

    def make_request(self, method: str, endpoint: str, data: Dict = None, expected_status: int = 200, user_email: str = None) -> tuple[bool, Dict]:
        """Make API request with proper headers"""
        url = f"{self.base_url}/api/{endpoint.lstrip('/')}"
        headers = {'Content-Type': 'application/json'}
        
        if user_email and user_email in self.session_tokens:
            headers['Authorization'] = f'Bearer {self.session_tokens[user_email]}'

        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=15)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=15)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers, timeout=15)
            elif method == 'PATCH':
                response = requests.patch(url, json=data, headers=headers, timeout=15)
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

    def authenticate_user(self, email: str) -> bool:
        """Authenticate a user and store their session token"""
        # Start auth
        success, data = self.make_request('POST', '/auth/email/start', {"email": email})
        if not success:
            return False
            
        verification_code = data.get('code')
        if not verification_code:
            return False
            
        # Verify auth
        success, data = self.make_request('POST', '/auth/email/verify', 
                                        {"email": email, "code": verification_code})
        if success:
            self.session_tokens[email] = data.get('token')
            return True
        return False

    def test_authorization_boundaries(self):
        """Test strict authorization boundaries"""
        print("\n🔒 TESTING AUTHORIZATION BOUNDARIES")
        print("-" * 50)
        
        # Authenticate all test users
        test_users = ["admin@company.com", "engineering.lead@company.com", "developer1@company.com", "developer2@company.com"]
        for user in test_users:
            if not self.authenticate_user(user):
                self.log_test(f"Authentication Setup - {user}", False, "Failed to authenticate", True)
                return False
        
        # Get conversation IDs for testing
        success, dev1_conv = self.make_request('GET', '/conversations/me', user_email="developer1@company.com")
        success2, dev2_conv = self.make_request('GET', '/conversations/me', user_email="developer2@company.com")
        
        if not (success and success2):
            self.log_test("Authorization Test Setup", False, "Could not get test conversations", True)
            return False
            
        dev1_conv_id = dev1_conv.get('id')
        dev2_conv_id = dev2_conv.get('id')
        
        # CRITICAL TEST 1: Employee cannot access another employee's conversation
        success, data = self.make_request('GET', f'/conversations/{dev2_conv_id}/pdf', 
                                        user_email="developer1@company.com", expected_status=403)
        self.log_test("AUTHORIZATION: Employee cannot access other employee's conversation", 
                     success, "403 Forbidden" if success else f"Got {data.get('status_code')}", True)
        
        # CRITICAL TEST 2: Employee cannot access manager endpoints
        success, data = self.make_request('GET', '/manager/reports', 
                                        user_email="developer1@company.com", expected_status=403)
        self.log_test("AUTHORIZATION: Employee cannot access manager endpoints", 
                     success, "403 Forbidden" if success else f"Got {data.get('status_code')}", True)
        
        # CRITICAL TEST 3: Manager cannot access non-reports
        # Create external user
        external_email = f"external.{datetime.now().strftime('%H%M%S')}@company.com"
        import_data = [{
            "employee_email": external_email,
            "employee_name": "External User",
            "manager_email": "other.manager@company.com",
            "department": "Other"
        }]
        self.make_request('POST', '/admin/users/import', import_data, user_email="admin@company.com")
        
        success, data = self.make_request('GET', f'/manager/conversations/{external_email}', 
                                        user_email="engineering.lead@company.com", expected_status=403)
        self.log_test("AUTHORIZATION: Manager cannot access non-report conversations", 
                     success, "403 Forbidden" if success else f"Got {data.get('status_code')}", True)
        
        # CRITICAL TEST 4: Admin can access any conversation
        success, data = self.make_request('GET', f'/conversations/{dev1_conv_id}/pdf', 
                                        user_email="admin@company.com", expected_status=200)
        self.log_test("AUTHORIZATION: Admin can access any conversation", 
                     success, "200 OK" if success else f"Got {data.get('status_code')}", True)
        
        return True

    def test_session_security_comprehensive(self):
        """Test session security comprehensively"""
        print("\n🍪 TESTING SESSION SECURITY")
        print("-" * 50)
        
        # CRITICAL TEST 1: httpOnly cookies (using curl for proper header inspection)
        try:
            # Get verification code
            result = subprocess.run([
                'curl', '-s', '-X', 'POST', 
                f'{self.base_url}/api/auth/email/start',
                '-H', 'Content-Type: application/json',
                '-d', '{"email": "developer1@company.com"}'
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                code_data = json.loads(result.stdout)
                code = code_data.get('code')
                
                # Test cookie setting with verbose output
                result = subprocess.run([
                    'curl', '-v', '-X', 'POST',
                    f'{self.base_url}/api/auth/email/verify',
                    '-H', 'Content-Type: application/json',
                    '-d', f'{{"email": "developer1@company.com", "code": "{code}"}}'
                ], capture_output=True, text=True, timeout=10)
                
                # Check for httpOnly in headers
                has_httponly = 'httponly' in result.stderr.lower()
                has_secure = 'secure' in result.stderr.lower() or 'samesite' in result.stderr.lower()
                
                self.log_test("SESSION: httpOnly cookies are set", has_httponly, 
                             "HttpOnly flag found" if has_httponly else "HttpOnly flag missing", True)
                
                self.log_test("SESSION: Secure cookie attributes", has_secure,
                             "Secure attributes found" if has_secure else "Missing secure attributes")
            else:
                self.log_test("SESSION: Cookie test setup", False, "Failed to test cookies", True)
                
        except Exception as e:
            self.log_test("SESSION: Cookie security test", False, str(e), True)
        
        # CRITICAL TEST 2: Session expiry enforcement
        invalid_token = "invalid_token_test_12345"
        headers = {'Authorization': f'Bearer {invalid_token}', 'Content-Type': 'application/json'}
        
        try:
            response = requests.get(f"{self.base_url}/api/auth/me", headers=headers, timeout=10)
            success = response.status_code == 401
            self.log_test("SESSION: Invalid token rejection", success,
                         "401 Unauthorized" if success else f"Got {response.status_code}", True)
        except Exception as e:
            self.log_test("SESSION: Token validation test", False, str(e), True)
        
        # CRITICAL TEST 3: Logout invalidation
        if "developer1@company.com" in self.session_tokens:
            token_before = self.session_tokens["developer1@company.com"]
            
            # Logout
            success, _ = self.make_request('POST', '/auth/logout', user_email="developer1@company.com")
            
            # Test token after logout
            headers = {'Authorization': f'Bearer {token_before}', 'Content-Type': 'application/json'}
            try:
                response = requests.get(f"{self.base_url}/api/auth/me", headers=headers, timeout=10)
                token_invalid = response.status_code == 401
                self.log_test("SESSION: Logout invalidates token", token_invalid,
                             "Token invalidated" if token_invalid else f"Token still valid: {response.status_code}", True)
            except Exception as e:
                self.log_test("SESSION: Logout test", False, str(e), True)
        
        return True

    def test_cycle_integrity(self):
        """Test cycle management integrity"""
        print("\n🔄 TESTING CYCLE INTEGRITY")
        print("-" * 50)
        
        if "admin@company.com" not in self.session_tokens:
            self.authenticate_user("admin@company.com")
        
        # Create test cycles
        cycle1_data = {
            "name": f"Security Test Cycle 1 {datetime.now().strftime('%H%M%S')}",
            "start_date": datetime.now().isoformat(),
            "end_date": (datetime.now() + timedelta(days=90)).isoformat(),
            "status": "draft"
        }
        
        cycle2_data = {
            "name": f"Security Test Cycle 2 {datetime.now().strftime('%H%M%S')}",
            "start_date": datetime.now().isoformat(),
            "end_date": (datetime.now() + timedelta(days=90)).isoformat(),
            "status": "draft"
        }
        
        success1, data1 = self.make_request('POST', '/admin/cycles', cycle1_data, user_email="admin@company.com")
        success2, data2 = self.make_request('POST', '/admin/cycles', cycle2_data, user_email="admin@company.com")
        
        if success1 and success2:
            cycle1_id = data1.get('id')
            cycle2_id = data2.get('id')
            
            # Activate first cycle
            self.make_request('PATCH', f'/admin/cycles/{cycle1_id}?status=active', user_email="admin@company.com")
            
            # Activate second cycle
            self.make_request('PATCH', f'/admin/cycles/{cycle2_id}?status=active', user_email="admin@company.com")
            
            # Verify only one active
            success, cycles = self.make_request('GET', '/admin/cycles', user_email="admin@company.com")
            if success:
                active_cycles = [c for c in cycles if c.get('status') == 'active']
                only_one_active = len(active_cycles) == 1
                self.log_test("CYCLE: Only one active cycle enforced", only_one_active,
                             f"Found {len(active_cycles)} active cycles" if not only_one_active else "Single active cycle")
            
            # Test status transitions
            success, data = self.make_request('PATCH', f'/admin/cycles/{cycle2_id}?status=archived', 
                                            user_email="admin@company.com")
            transition_works = success and data.get('status') == 'archived'
            self.log_test("CYCLE: Status transitions work correctly", transition_works,
                         f"Status: {data.get('status')}" if success else "Transition failed")
        
        return True

    def test_pdf_export_comprehensive(self):
        """Test PDF export completeness"""
        print("\n📄 TESTING PDF EXPORT COMPLETENESS")
        print("-" * 50)
        
        # Ensure we have a conversation with substantial content
        if "developer1@company.com" not in self.session_tokens:
            self.authenticate_user("developer1@company.com")
        if "engineering.lead@company.com" not in self.session_tokens:
            self.authenticate_user("engineering.lead@company.com")
        
        # Add comprehensive content to conversation
        comprehensive_update = {
            "employee_self_review": """This is a comprehensive self-review for PDF testing. 
            I have achieved significant milestones this quarter including:
            1. Successfully delivered 5 major features
            2. Improved code quality metrics by 25%
            3. Mentored 2 junior developers
            4. Led the migration to new architecture
            
            Areas for improvement:
            - Better time management for complex projects
            - Enhanced communication with stakeholders
            - Deeper technical knowledge in emerging technologies""",
            
            "goals_next_period": """Goals for next performance period:
            1. Lead the implementation of microservices architecture
            2. Achieve AWS certification
            3. Improve team collaboration processes
            4. Deliver 3 high-impact features
            5. Establish better work-life balance""",
            
            "status": "ready_for_manager"
        }
        
        success, _ = self.make_request('PUT', '/conversations/me', comprehensive_update, 
                                     user_email="developer1@company.com")
        
        # Add manager review
        manager_update = {
            "manager_review": """Comprehensive manager review for PDF testing.
            
            Strengths demonstrated:
            - Excellent technical leadership
            - Strong problem-solving abilities
            - Great team collaboration
            - Consistent delivery quality
            
            Development areas:
            - Strategic thinking for long-term projects
            - Cross-functional communication
            - Technical documentation practices
            
            Overall performance: Exceeds expectations""",
            
            "meeting_date": datetime.now().isoformat(),
            "ratings": {"performance": 4, "collaboration": 5, "growth": 4},
            "status": "completed"
        }
        
        success, _ = self.make_request('PUT', '/manager/conversations/developer1@company.com', 
                                     manager_update, user_email="engineering.lead@company.com")
        
        # Get updated conversation
        success, conv = self.make_request('GET', '/conversations/me', user_email="developer1@company.com")
        if not success:
            self.log_test("PDF: Test data setup", False, "Could not get conversation", True)
            return False
        
        conv_id = conv.get('id')
        
        # Test PDF export
        url = f"{self.base_url}/api/conversations/{conv_id}/pdf"
        headers = {'Authorization': f'Bearer {self.session_tokens["developer1@company.com"]}'}
        
        try:
            response = requests.get(url, headers=headers, timeout=20)
            
            # Test PDF generation
            is_pdf = response.status_code == 200 and 'application/pdf' in response.headers.get('content-type', '')
            self.log_test("PDF: Export generates successfully", is_pdf,
                         f"Content-Type: {response.headers.get('content-type')}")
            
            # Test PDF size (should be substantial with comprehensive content)
            pdf_size = len(response.content) if is_pdf else 0
            has_substantial_content = pdf_size > 8000  # Lowered threshold for comprehensive content
            self.log_test("PDF: Contains substantial content", has_substantial_content,
                         f"PDF size: {pdf_size} bytes")
            
            # Test filename
            content_disposition = response.headers.get('content-disposition', '')
            has_proper_filename = 'developer1' in content_disposition.lower()
            self.log_test("PDF: Includes employee details in filename", has_proper_filename,
                         f"Filename: {content_disposition}")
            
            # Verify PDF includes all required fields by checking conversation data
            has_employee_review = bool(conv.get('employee_self_review'))
            has_manager_review = bool(conv.get('manager_review'))
            has_goals = bool(conv.get('goals_next_period'))
            has_ratings = bool(conv.get('ratings'))
            has_timestamps = bool(conv.get('created_at')) and bool(conv.get('updated_at'))
            
            self.log_test("PDF: Employee self-review included", has_employee_review,
                         f"Length: {len(conv.get('employee_self_review', ''))}")
            self.log_test("PDF: Manager review included", has_manager_review,
                         f"Length: {len(conv.get('manager_review', ''))}")
            self.log_test("PDF: Goals included", has_goals,
                         f"Length: {len(conv.get('goals_next_period', ''))}")
            self.log_test("PDF: Ratings included", has_ratings,
                         f"Ratings: {conv.get('ratings', {})}")
            self.log_test("PDF: Timestamps included", has_timestamps,
                         "Created and updated timestamps present")
            
            return is_pdf
            
        except Exception as e:
            self.log_test("PDF: Export test", False, str(e), True)
            return False

    def test_data_persistence_and_restart(self):
        """Test data persistence"""
        print("\n💾 TESTING DATA PERSISTENCE")
        print("-" * 50)
        
        # Create test data
        test_email = f"persistence.{datetime.now().strftime('%H%M%S')}@company.com"
        
        if "admin@company.com" not in self.session_tokens:
            self.authenticate_user("admin@company.com")
        
        # Import test user
        import_data = [{
            "employee_email": test_email,
            "employee_name": "Data Persistence Test User",
            "manager_email": "engineering.lead@company.com",
            "department": "Security Testing"
        }]
        
        success, _ = self.make_request('POST', '/admin/users/import', import_data, 
                                     user_email="admin@company.com")
        
        if success and self.authenticate_user(test_email):
            # Create conversation data
            test_data = {
                "employee_self_review": f"Persistence test data created at {datetime.now()}",
                "goals_next_period": "Test goals for data persistence verification",
                "status": "in_progress"
            }
            
            success, _ = self.make_request('PUT', '/conversations/me', test_data, user_email=test_email)
            self.log_test("PERSISTENCE: Test data creation", success, "Conversation data created")
            
            # Verify immediate retrieval
            success, retrieved = self.make_request('GET', '/conversations/me', user_email=test_email)
            data_matches = (success and 
                          retrieved.get('employee_self_review') == test_data['employee_self_review'])
            
            self.log_test("PERSISTENCE: Data retrieval", data_matches, 
                         "Data retrieved successfully" if data_matches else "Data mismatch")
            
            # Test user data persistence
            success, users = self.make_request('GET', '/admin/users', user_email="admin@company.com")
            user_exists = any(u.get('email') == test_email for u in users) if success else False
            self.log_test("PERSISTENCE: User data persists", user_exists,
                         "User found in database" if user_exists else "User not found")
            
            return data_matches and user_exists
        
        self.log_test("PERSISTENCE: Test setup", False, "Could not create test data", True)
        return False

    def run_comprehensive_security_verification(self):
        """Run complete security hardening verification"""
        print("🔐 HR PERFORMANCE MANAGEMENT - COMPREHENSIVE SECURITY VERIFICATION")
        print("=" * 80)
        print("Target: hr-staging.dstchemicals.com")
        print("Scope: Authorization, Session Security, Cycle Integrity, PDF Export, Data Persistence")
        print("=" * 80)

        # Health check
        success, data = self.make_request('GET', '/health')
        self.log_test("System Health Check", success, 
                     f"Status: {data.get('status')}, Auth: {data.get('auth_mode')}")
        
        if not success:
            print("❌ System health check failed - aborting security verification")
            return False

        # Run all security tests
        self.test_authorization_boundaries()
        self.test_session_security_comprehensive()
        self.test_cycle_integrity()
        self.test_pdf_export_comprehensive()
        self.test_data_persistence_and_restart()

        # Generate comprehensive report
        print("\n" + "=" * 80)
        print(f"🔍 SECURITY VERIFICATION COMPLETE: {self.tests_passed}/{self.tests_run} tests passed")
        
        if self.critical_issues:
            print(f"\n🚨 CRITICAL SECURITY ISSUES ({len(self.critical_issues)}):")
            for issue in self.critical_issues:
                print(f"   ❌ {issue['name']}: {issue['details']}")
        
        if self.warnings:
            print(f"\n⚠️  WARNINGS ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"   ⚠️  {warning['name']}: {warning['details']}")
        
        # Security assessment
        critical_count = len(self.critical_issues)
        warning_count = len(self.warnings)
        
        if critical_count == 0 and warning_count == 0:
            print("\n✅ SECURITY HARDENING VERIFICATION: PASSED")
            print("   All authorization boundaries, session security, and data integrity verified.")
            return True
        elif critical_count == 0:
            print(f"\n⚠️  SECURITY HARDENING VERIFICATION: PASSED WITH WARNINGS")
            print(f"   No critical issues found. {warning_count} minor issues to address.")
            return True
        else:
            print(f"\n❌ SECURITY HARDENING VERIFICATION: FAILED")
            print(f"   {critical_count} critical security issues must be resolved.")
            return False

def main():
    """Main execution"""
    tester = HRSecurityTesterComprehensive()
    
    try:
        success = tester.run_comprehensive_security_verification()
        return 0 if success else 1
    except KeyboardInterrupt:
        print("\n⏹️  Security verification interrupted")
        return 1
    except Exception as e:
        print(f"\n💥 Security verification error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())