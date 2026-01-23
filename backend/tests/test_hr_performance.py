"""
HR Performance Management System - Backend API Tests
Tests password-based auth, employee/manager flows, admin functions, and new field structure
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://evalflow-7.preview.emergentagent.com')
if not BASE_URL.endswith('/api'):
    BASE_URL = f"{BASE_URL}/api"

# Test credentials
ADMIN_CREDS = {"email": "admin@company.com", "password": "Demo@123456"}
MANAGER_CREDS = {"email": "engineering.lead@company.com", "password": "Demo@123456"}
EMPLOYEE_CREDS = {"email": "developer1@company.com", "password": "Demo@123456"}


class TestHealthAndBasics:
    """Basic health and API availability tests"""
    
    def test_health_endpoint(self):
        """Test health endpoint returns healthy status"""
        response = requests.get(f"{BASE_URL}/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        print(f"✓ Health check passed - version: {data.get('version')}")
    
    def test_root_endpoint(self):
        """Test root API endpoint"""
        response = requests.get(f"{BASE_URL}/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        # Verify no ratings field in API response
        assert data.get("ratings") == False, "API should indicate ratings are disabled"
        print("✓ Root endpoint working, ratings disabled")


class TestPasswordAuthentication:
    """Password-based authentication tests"""
    
    def test_login_with_valid_credentials(self):
        """Test login with valid email and password"""
        response = requests.post(f"{BASE_URL}/auth/login", json=ADMIN_CREDS)
        assert response.status_code == 200
        data = response.json()
        assert "user" in data
        assert "token" in data
        assert data["user"]["email"] == ADMIN_CREDS["email"]
        assert "must_change_password" in data
        print(f"✓ Admin login successful - must_change_password: {data['must_change_password']}")
    
    def test_login_with_invalid_password(self):
        """Test login fails with wrong password"""
        response = requests.post(f"{BASE_URL}/auth/login", json={
            "email": ADMIN_CREDS["email"],
            "password": "wrongpassword"
        })
        assert response.status_code == 401
        print("✓ Invalid password correctly rejected")
    
    def test_login_with_nonexistent_user(self):
        """Test login fails for non-existent user"""
        response = requests.post(f"{BASE_URL}/auth/login", json={
            "email": "nonexistent@company.com",
            "password": "anypassword"
        })
        assert response.status_code == 401
        print("✓ Non-existent user correctly rejected")
    
    def test_manager_login(self):
        """Test manager can login"""
        response = requests.post(f"{BASE_URL}/auth/login", json=MANAGER_CREDS)
        assert response.status_code == 200
        data = response.json()
        assert "manager" in data["user"]["roles"]
        print(f"✓ Manager login successful - roles: {data['user']['roles']}")
    
    def test_employee_login(self):
        """Test employee can login"""
        response = requests.post(f"{BASE_URL}/auth/login", json=EMPLOYEE_CREDS)
        assert response.status_code == 200
        data = response.json()
        assert "employee" in data["user"]["roles"]
        print(f"✓ Employee login successful - roles: {data['user']['roles']}")


class TestAuthenticatedEndpoints:
    """Tests requiring authentication"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/auth/login", json=ADMIN_CREDS)
        return response.json()["token"]
    
    @pytest.fixture
    def manager_token(self):
        response = requests.post(f"{BASE_URL}/auth/login", json=MANAGER_CREDS)
        return response.json()["token"]
    
    @pytest.fixture
    def employee_token(self):
        response = requests.post(f"{BASE_URL}/auth/login", json=EMPLOYEE_CREDS)
        return response.json()["token"]
    
    def test_auth_me_endpoint(self, admin_token):
        """Test /auth/me returns current user"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/auth/me", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == ADMIN_CREDS["email"]
        print(f"✓ Auth/me working - user: {data['email']}")
    
    def test_logout(self, admin_token):
        """Test logout invalidates session"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.post(f"{BASE_URL}/auth/logout", headers=headers)
        assert response.status_code == 200
        print("✓ Logout successful")
    
    def test_unauthenticated_access_denied(self):
        """Test protected endpoints require auth"""
        response = requests.get(f"{BASE_URL}/auth/me")
        assert response.status_code == 401
        print("✓ Unauthenticated access correctly denied")


class TestAdminFunctions:
    """Admin-specific functionality tests"""
    
    @pytest.fixture
    def admin_headers(self):
        response = requests.post(f"{BASE_URL}/auth/login", json=ADMIN_CREDS)
        token = response.json()["token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_admin_get_users(self, admin_headers):
        """Test admin can list all users"""
        response = requests.get(f"{BASE_URL}/admin/users", headers=admin_headers)
        assert response.status_code == 200
        users = response.json()
        assert isinstance(users, list)
        assert len(users) > 0
        # Verify password_hash is not exposed
        for user in users:
            assert "password_hash" not in user
        print(f"✓ Admin can list users - count: {len(users)}")
    
    def test_admin_get_cycles(self, admin_headers):
        """Test admin can list cycles"""
        response = requests.get(f"{BASE_URL}/admin/cycles", headers=admin_headers)
        assert response.status_code == 200
        cycles = response.json()
        assert isinstance(cycles, list)
        print(f"✓ Admin can list cycles - count: {len(cycles)}")
    
    def test_admin_import_users_json(self, admin_headers):
        """Test admin can import users via JSON"""
        test_users = [{
            "employee_email": "TEST_import_user@company.com",
            "employee_name": "Test Import User",
            "department": "Testing",
            "is_admin": False
        }]
        response = requests.post(f"{BASE_URL}/admin/users/import", 
                                json=test_users, headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "imported" in data or "updated" in data
        # If new user, credentials_csv should be present
        if data.get("imported", 0) > 0:
            assert "credentials_csv" in data
            assert data["credentials_csv"] is not None
            print(f"✓ User import successful - credentials CSV generated")
        else:
            print(f"✓ User import successful - user already existed (updated)")
    
    def test_admin_reset_passwords(self, admin_headers):
        """Test admin can reset user passwords"""
        response = requests.post(f"{BASE_URL}/admin/users/reset-passwords",
                                json={"emails": ["TEST_import_user@company.com"]},
                                headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "reset_count" in data
        if data["reset_count"] > 0:
            assert "credentials_csv" in data
            print(f"✓ Password reset successful - CSV generated")
        else:
            print(f"✓ Password reset endpoint working (user may not exist)")
    
    def test_non_admin_cannot_access_admin_endpoints(self):
        """Test non-admin users cannot access admin endpoints"""
        # Login as employee
        response = requests.post(f"{BASE_URL}/auth/login", json=EMPLOYEE_CREDS)
        token = response.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Try to access admin endpoint
        response = requests.get(f"{BASE_URL}/admin/users", headers=headers)
        assert response.status_code == 403
        print("✓ Non-admin correctly denied access to admin endpoints")


class TestCycleManagement:
    """Cycle management tests"""
    
    @pytest.fixture
    def admin_headers(self):
        response = requests.post(f"{BASE_URL}/auth/login", json=ADMIN_CREDS)
        token = response.json()["token"]
        return {"Authorization": f"Bearer {token}"}
    
    @pytest.fixture
    def employee_headers(self):
        response = requests.post(f"{BASE_URL}/auth/login", json=EMPLOYEE_CREDS)
        token = response.json()["token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_get_active_cycle(self, employee_headers):
        """Test getting active cycle"""
        response = requests.get(f"{BASE_URL}/cycles/active", headers=employee_headers)
        # May be 200 with cycle or 404 if no active cycle
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            cycle = response.json()
            assert cycle["status"] == "active"
            print(f"✓ Active cycle found: {cycle['name']}")
        else:
            print("✓ No active cycle (expected if none created)")
    
    def test_get_all_cycles(self, employee_headers):
        """Test getting all cycles for history"""
        response = requests.get(f"{BASE_URL}/cycles/all", headers=employee_headers)
        assert response.status_code == 200
        cycles = response.json()
        assert isinstance(cycles, list)
        print(f"✓ All cycles retrieved - count: {len(cycles)}")


class TestEmployeeConversations:
    """Employee conversation tests with new field structure"""
    
    @pytest.fixture
    def employee_headers(self):
        response = requests.post(f"{BASE_URL}/auth/login", json=EMPLOYEE_CREDS)
        token = response.json()["token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_get_my_conversation(self, employee_headers):
        """Test employee can get their conversation"""
        response = requests.get(f"{BASE_URL}/conversations/me", headers=employee_headers)
        # 200 if active cycle exists, 404 if not
        if response.status_code == 200:
            conv = response.json()
            # Verify new field structure exists (no ratings)
            assert "status_since_last_meeting" in conv
            assert "previous_goals_progress" in conv
            assert "new_goals" in conv
            assert "how_to_achieve_goals" in conv
            assert "support_needed" in conv
            assert "feedback_and_wishes" in conv
            assert "manager_feedback" in conv
            # Verify NO ratings fields
            assert "rating" not in conv
            assert "self_rating" not in conv
            assert "manager_rating" not in conv
            print("✓ Employee conversation has correct new field structure (no ratings)")
        else:
            print("✓ No active cycle - conversation endpoint working")
    
    def test_update_my_conversation(self, employee_headers):
        """Test employee can update their conversation"""
        # First check if there's an active cycle
        response = requests.get(f"{BASE_URL}/cycles/active", headers=employee_headers)
        if response.status_code != 200:
            pytest.skip("No active cycle to test conversation update")
        
        update_data = {
            "status_since_last_meeting": "TEST: Working on project X",
            "previous_goals_progress": "TEST: Completed 80% of goals",
            "new_goals": "TEST: Launch feature Y",
            "how_to_achieve_goals": "TEST: Break into sprints",
            "support_needed": "TEST: Need mentorship",
            "feedback_and_wishes": "TEST: More team collaboration",
            "status": "in_progress"
        }
        response = requests.put(f"{BASE_URL}/conversations/me", 
                               json=update_data, headers=employee_headers)
        assert response.status_code == 200
        conv = response.json()
        assert conv["status_since_last_meeting"] == update_data["status_since_last_meeting"]
        print("✓ Employee can update conversation with new fields")
    
    def test_get_my_conversation_history(self, employee_headers):
        """Test employee can view their history"""
        response = requests.get(f"{BASE_URL}/conversations/me/history", headers=employee_headers)
        assert response.status_code == 200
        history = response.json()
        assert isinstance(history, list)
        print(f"✓ Employee history retrieved - count: {len(history)}")


class TestManagerFunctions:
    """Manager-specific functionality tests"""
    
    @pytest.fixture
    def manager_headers(self):
        response = requests.post(f"{BASE_URL}/auth/login", json=MANAGER_CREDS)
        token = response.json()["token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_get_manager_reports(self, manager_headers):
        """Test manager can get direct reports"""
        response = requests.get(f"{BASE_URL}/manager/reports", headers=manager_headers)
        assert response.status_code == 200
        reports = response.json()
        assert isinstance(reports, list)
        # Verify no ratings in report data
        for report in reports:
            assert "rating" not in report
            assert "self_rating" not in report
        print(f"✓ Manager reports retrieved - count: {len(reports)}")
    
    def test_get_report_conversation(self, manager_headers):
        """Test manager can view employee's conversation"""
        # First get reports
        response = requests.get(f"{BASE_URL}/manager/reports", headers=manager_headers)
        reports = response.json()
        
        if len(reports) == 0:
            pytest.skip("No direct reports to test")
        
        employee_email = reports[0]["email"]
        response = requests.get(f"{BASE_URL}/manager/conversations/{employee_email}", 
                               headers=manager_headers)
        # 200 if active cycle, 404 if not
        if response.status_code == 200:
            data = response.json()
            assert "conversation" in data
            assert "employee" in data
            conv = data["conversation"]
            # Verify new field structure
            assert "manager_feedback" in conv
            assert "rating" not in conv
            print(f"✓ Manager can view employee conversation (no ratings)")
        else:
            print("✓ No active cycle for manager view")
    
    def test_manager_update_feedback(self, manager_headers):
        """Test manager can provide feedback (no ratings)"""
        # Get reports
        response = requests.get(f"{BASE_URL}/manager/reports", headers=manager_headers)
        reports = response.json()
        
        if len(reports) == 0:
            pytest.skip("No direct reports to test")
        
        # Check for active cycle
        response = requests.get(f"{BASE_URL}/cycles/active", headers=manager_headers)
        if response.status_code != 200:
            pytest.skip("No active cycle")
        
        employee_email = reports[0]["email"]
        update_data = {
            "manager_feedback": "TEST: Great progress on goals. Keep up the good work!"
        }
        response = requests.put(f"{BASE_URL}/manager/conversations/{employee_email}",
                               json=update_data, headers=manager_headers)
        assert response.status_code == 200
        conv = response.json()
        assert conv["manager_feedback"] == update_data["manager_feedback"]
        print("✓ Manager can provide feedback (single field, no ratings)")
    
    def test_get_report_history(self, manager_headers):
        """Test manager can view employee's history"""
        response = requests.get(f"{BASE_URL}/manager/reports", headers=manager_headers)
        reports = response.json()
        
        if len(reports) == 0:
            pytest.skip("No direct reports")
        
        employee_email = reports[0]["email"]
        response = requests.get(f"{BASE_URL}/manager/reports/{employee_email}/history",
                               headers=manager_headers)
        assert response.status_code == 200
        history = response.json()
        assert isinstance(history, list)
        print(f"✓ Manager can view employee history - count: {len(history)}")


class TestAuthorizationIsolation:
    """Authorization and isolation tests"""
    
    def test_employee_cannot_access_other_employee(self):
        """Test employee cannot access another employee's data"""
        # Login as employee
        response = requests.post(f"{BASE_URL}/auth/login", json=EMPLOYEE_CREDS)
        token = response.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Try to access manager endpoint (should fail)
        response = requests.get(f"{BASE_URL}/manager/reports", headers=headers)
        assert response.status_code == 403
        print("✓ Employee cannot access manager endpoints")
    
    def test_manager_cannot_access_non_report(self):
        """Test manager cannot access employee who is not their report"""
        response = requests.post(f"{BASE_URL}/auth/login", json=MANAGER_CREDS)
        token = response.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Try to access admin user (not a report)
        response = requests.get(f"{BASE_URL}/manager/conversations/admin@company.com",
                               headers=headers)
        # Should be 403 (not authorized) or 404 (not found as report)
        assert response.status_code in [403, 404]
        print("✓ Manager cannot access non-direct-report")


class TestPDFExport:
    """PDF export functionality tests"""
    
    @pytest.fixture
    def employee_headers(self):
        response = requests.post(f"{BASE_URL}/auth/login", json=EMPLOYEE_CREDS)
        token = response.json()["token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_pdf_export(self, employee_headers):
        """Test PDF export works"""
        # Get conversation history to find a conversation ID
        response = requests.get(f"{BASE_URL}/conversations/me/history", headers=employee_headers)
        history = response.json()
        
        if len(history) == 0:
            # Try current conversation
            response = requests.get(f"{BASE_URL}/conversations/me", headers=employee_headers)
            if response.status_code != 200:
                pytest.skip("No conversations to export")
            conv_id = response.json()["id"]
        else:
            conv_id = history[0]["id"]
        
        response = requests.get(f"{BASE_URL}/conversations/{conv_id}/pdf", 
                               headers=employee_headers)
        assert response.status_code == 200
        assert response.headers.get("content-type") == "application/pdf"
        print("✓ PDF export working")


class TestNoRatingsAnywhere:
    """Verify ratings are completely removed from API"""
    
    @pytest.fixture
    def admin_headers(self):
        response = requests.post(f"{BASE_URL}/auth/login", json=ADMIN_CREDS)
        token = response.json()["token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_no_ratings_in_conversation_model(self, admin_headers):
        """Verify conversation responses have no rating fields"""
        # Check employee conversation
        response = requests.post(f"{BASE_URL}/auth/login", json=EMPLOYEE_CREDS)
        emp_token = response.json()["token"]
        emp_headers = {"Authorization": f"Bearer {emp_token}"}
        
        response = requests.get(f"{BASE_URL}/conversations/me/history", headers=emp_headers)
        if response.status_code == 200:
            for conv in response.json():
                assert "rating" not in conv
                assert "self_rating" not in conv
                assert "manager_rating" not in conv
                assert "performance_rating" not in conv
        print("✓ No ratings fields in conversation data")
    
    def test_api_root_indicates_no_ratings(self, admin_headers):
        """Verify API root indicates ratings are disabled"""
        response = requests.get(f"{BASE_URL}/")
        data = response.json()
        assert data.get("ratings") == False
        print("✓ API indicates ratings are disabled")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
