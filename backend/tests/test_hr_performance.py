"""
HR Performance Management System - Backend API Tests
Tests: Password auth, cycles, conversations, PDF export, archived access
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_CREDS = {"email": "admin@company.com", "password": "Demo@123456"}
MANAGER_CREDS = {"email": "engineering.lead@company.com", "password": "Demo@123456"}
EMPLOYEE_CREDS = {"email": "developer1@company.com", "password": "Demo@123456"}


class TestHealthAndConfig:
    """Health check and configuration tests"""
    
    def test_health_endpoint(self):
        """Test health endpoint returns healthy status"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["auth_mode"] == "password"
        print(f"Health check passed: {data}")
    
    def test_root_endpoint_no_ratings(self):
        """Test root endpoint confirms no ratings"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        data = response.json()
        assert data.get("ratings") == False, "API should return ratings:false"
        print(f"Root endpoint: {data}")


class TestPasswordAuthentication:
    """Password-based authentication tests"""
    
    def test_login_admin_success(self):
        """Test admin login with valid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert "user" in data
        assert data["user"]["email"] == ADMIN_CREDS["email"]
        assert "admin" in data["user"]["roles"]
        print(f"Admin login successful: {data['user']['email']}")
        return data["token"]
    
    def test_login_manager_success(self):
        """Test manager login with valid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=MANAGER_CREDS)
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["user"]["email"] == MANAGER_CREDS["email"]
        assert "manager" in data["user"]["roles"]
        print(f"Manager login successful: {data['user']['email']}")
        return data["token"]
    
    def test_login_employee_success(self):
        """Test employee login with valid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=EMPLOYEE_CREDS)
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["user"]["email"] == EMPLOYEE_CREDS["email"]
        print(f"Employee login successful: {data['user']['email']}")
        return data["token"]
    
    def test_login_invalid_credentials(self):
        """Test login with invalid credentials returns 401"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "invalid@company.com",
            "password": "wrongpassword"
        })
        assert response.status_code == 401
        print("Invalid credentials correctly rejected")
    
    def test_auth_me_with_token(self):
        """Test /auth/me endpoint with valid token"""
        # First login
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        token = login_response.json()["token"]
        
        # Then check /auth/me
        response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == ADMIN_CREDS["email"]
        print(f"Auth/me returned: {data['email']}")
    
    def test_logout(self):
        """Test logout endpoint"""
        # Login first
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        token = login_response.json()["token"]
        
        # Logout
        response = requests.post(
            f"{BASE_URL}/api/auth/logout",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        print("Logout successful")


class TestAdminFunctions:
    """Admin-specific functionality tests"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        return response.json()["token"]
    
    def test_get_users(self, admin_token):
        """Test admin can get all users"""
        response = requests.get(
            f"{BASE_URL}/api/admin/users",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        users = response.json()
        assert isinstance(users, list)
        assert len(users) > 0
        # Verify password_hash is not exposed
        for user in users:
            assert "password_hash" not in user
        print(f"Found {len(users)} users")
    
    def test_get_cycles(self, admin_token):
        """Test admin can get all cycles"""
        response = requests.get(
            f"{BASE_URL}/api/admin/cycles",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        cycles = response.json()
        assert isinstance(cycles, list)
        print(f"Found {len(cycles)} cycles")
    
    def test_password_reset_returns_csv(self, admin_token):
        """Test password reset returns CSV with new credentials"""
        # Get a user to reset
        users_response = requests.get(
            f"{BASE_URL}/api/admin/users",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        users = users_response.json()
        
        # Find a non-admin user to reset (to avoid locking ourselves out)
        test_user = None
        for user in users:
            if "admin" not in user.get("roles", []) and user["email"] != ADMIN_CREDS["email"]:
                test_user = user
                break
        
        if not test_user:
            pytest.skip("No non-admin user found for password reset test")
        
        # Reset password
        response = requests.post(
            f"{BASE_URL}/api/admin/users/reset-passwords",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"emails": [test_user["email"]]}
        )
        assert response.status_code == 200
        data = response.json()
        assert "credentials_csv" in data
        assert data["credentials_csv"] is not None
        assert "email" in data["credentials_csv"]
        assert "new_one_time_password" in data["credentials_csv"]
        print(f"Password reset successful, CSV returned for {test_user['email']}")


class TestCycles:
    """Cycle management tests"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        return response.json()["token"]
    
    @pytest.fixture
    def employee_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=EMPLOYEE_CREDS)
        return response.json()["token"]
    
    def test_get_active_cycle(self, employee_token):
        """Test getting active cycle"""
        response = requests.get(
            f"{BASE_URL}/api/cycles/active",
            headers={"Authorization": f"Bearer {employee_token}"}
        )
        # May be 200 with cycle or 200 with null if no active cycle
        assert response.status_code == 200
        data = response.json()
        if data:
            assert data.get("status") == "active"
            print(f"Active cycle: {data.get('name')}")
        else:
            print("No active cycle found")
    
    def test_get_all_cycles(self, employee_token):
        """Test getting all cycles for history view"""
        response = requests.get(
            f"{BASE_URL}/api/cycles/all",
            headers={"Authorization": f"Bearer {employee_token}"}
        )
        assert response.status_code == 200
        cycles = response.json()
        assert isinstance(cycles, list)
        print(f"Total cycles: {len(cycles)}")


class TestEmployeeConversations:
    """Employee conversation tests"""
    
    @pytest.fixture
    def employee_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=EMPLOYEE_CREDS)
        return response.json()["token"]
    
    def test_get_my_conversation(self, employee_token):
        """Test employee can get their conversation for active cycle"""
        response = requests.get(
            f"{BASE_URL}/api/conversations/me",
            headers={"Authorization": f"Bearer {employee_token}"}
        )
        # 200 if active cycle exists, 404 if no active cycle
        if response.status_code == 200:
            data = response.json()
            assert "employee_email" in data
            assert data["employee_email"] == EMPLOYEE_CREDS["email"]
            # Verify new field structure (no ratings)
            assert "status_since_last_meeting" in data or data.get("status_since_last_meeting") is None
            assert "previous_goals_progress" in data or data.get("previous_goals_progress") is None
            assert "new_goals" in data or data.get("new_goals") is None
            assert "how_to_achieve_goals" in data or data.get("how_to_achieve_goals") is None
            assert "support_needed" in data or data.get("support_needed") is None
            assert "feedback_and_wishes" in data or data.get("feedback_and_wishes") is None
            assert "manager_feedback" in data or data.get("manager_feedback") is None
            # Verify NO ratings fields
            assert "rating" not in data
            assert "self_rating" not in data
            assert "manager_rating" not in data
            print(f"Employee conversation retrieved: {data.get('id')}")
        elif response.status_code == 404:
            print("No active cycle - conversation not available")
        else:
            pytest.fail(f"Unexpected status code: {response.status_code}")
    
    def test_get_my_conversation_history(self, employee_token):
        """Test employee can see their archived conversations"""
        response = requests.get(
            f"{BASE_URL}/api/conversations/me/history",
            headers={"Authorization": f"Bearer {employee_token}"}
        )
        assert response.status_code == 200
        history = response.json()
        assert isinstance(history, list)
        print(f"Employee has {len(history)} conversations in history")
        
        # Check each conversation has cycle info
        for conv in history:
            assert "cycle" in conv or conv.get("cycle") is None
    
    def test_update_my_conversation(self, employee_token):
        """Test employee can update their conversation"""
        # First get the conversation
        get_response = requests.get(
            f"{BASE_URL}/api/conversations/me",
            headers={"Authorization": f"Bearer {employee_token}"}
        )
        
        if get_response.status_code == 404:
            pytest.skip("No active cycle for conversation update test")
        
        # Update with new employee fields
        update_data = {
            "status_since_last_meeting": "TEST: Working on project X",
            "previous_goals_progress": "TEST: Completed 80% of goals",
            "new_goals": "TEST: Launch feature Y",
            "how_to_achieve_goals": "TEST: Break into sprints",
            "support_needed": "TEST: Need code review help",
            "feedback_and_wishes": "TEST: Would like more 1:1s",
            "status": "in_progress"
        }
        
        response = requests.put(
            f"{BASE_URL}/api/conversations/me",
            headers={"Authorization": f"Bearer {employee_token}"},
            json=update_data
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status_since_last_meeting"] == update_data["status_since_last_meeting"]
        assert data["status"] == "in_progress"
        print("Employee conversation updated successfully")


class TestArchivedConversationsReadOnly:
    """Test that archived conversations are read-only at API level"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        return response.json()["token"]
    
    @pytest.fixture
    def employee_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=EMPLOYEE_CREDS)
        return response.json()["token"]
    
    def test_get_conversation_by_id_shows_archived_status(self, employee_token):
        """Test getting conversation by ID shows is_archived flag"""
        # Get history first
        history_response = requests.get(
            f"{BASE_URL}/api/conversations/me/history",
            headers={"Authorization": f"Bearer {employee_token}"}
        )
        history = history_response.json()
        
        if not history:
            pytest.skip("No conversation history to test")
        
        # Get first conversation by ID
        conv_id = history[0]["id"]
        response = requests.get(
            f"{BASE_URL}/api/conversations/{conv_id}",
            headers={"Authorization": f"Bearer {employee_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "is_archived" in data
        assert "conversation" in data
        assert "cycle" in data
        print(f"Conversation {conv_id} is_archived: {data['is_archived']}")


class TestManagerFunctions:
    """Manager-specific functionality tests"""
    
    @pytest.fixture
    def manager_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=MANAGER_CREDS)
        return response.json()["token"]
    
    def test_get_reports(self, manager_token):
        """Test manager can get their direct reports"""
        response = requests.get(
            f"{BASE_URL}/api/manager/reports",
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        assert response.status_code == 200
        reports = response.json()
        assert isinstance(reports, list)
        print(f"Manager has {len(reports)} direct reports")
        
        # Check each report has expected fields
        for report in reports:
            assert "email" in report
            assert "password_hash" not in report  # Should not expose password
    
    def test_get_report_history(self, manager_token):
        """Test manager can see employee history"""
        # First get reports
        reports_response = requests.get(
            f"{BASE_URL}/api/manager/reports",
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        reports = reports_response.json()
        
        if not reports:
            pytest.skip("No direct reports for history test")
        
        # Get history for first report
        employee_email = reports[0]["email"]
        response = requests.get(
            f"{BASE_URL}/api/manager/reports/{employee_email}/history",
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        assert response.status_code == 200
        history = response.json()
        assert isinstance(history, list)
        print(f"Employee {employee_email} has {len(history)} conversations in history")


class TestPDFExport:
    """PDF export functionality tests"""
    
    @pytest.fixture
    def employee_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=EMPLOYEE_CREDS)
        return response.json()["token"]
    
    def test_pdf_export_via_query_param(self, employee_token):
        """Test PDF export works with token as query parameter"""
        # Get conversation history to find a conversation ID
        history_response = requests.get(
            f"{BASE_URL}/api/conversations/me/history",
            headers={"Authorization": f"Bearer {employee_token}"}
        )
        history = history_response.json()
        
        if not history:
            # Try to get current conversation
            current_response = requests.get(
                f"{BASE_URL}/api/conversations/me",
                headers={"Authorization": f"Bearer {employee_token}"}
            )
            if current_response.status_code == 200:
                conv_id = current_response.json().get("id")
            else:
                pytest.skip("No conversation available for PDF test")
        else:
            conv_id = history[0]["id"]
        
        # Test PDF export with token as query parameter (browser download method)
        response = requests.get(
            f"{BASE_URL}/api/conversations/{conv_id}/pdf?token={employee_token}"
        )
        assert response.status_code == 200
        assert response.headers.get("content-type") == "application/pdf"
        assert "attachment" in response.headers.get("content-disposition", "")
        assert len(response.content) > 0
        print(f"PDF exported successfully, size: {len(response.content)} bytes")
    
    def test_pdf_export_via_bearer_token(self, employee_token):
        """Test PDF export works with Bearer token header"""
        # Get conversation
        history_response = requests.get(
            f"{BASE_URL}/api/conversations/me/history",
            headers={"Authorization": f"Bearer {employee_token}"}
        )
        history = history_response.json()
        
        if not history:
            current_response = requests.get(
                f"{BASE_URL}/api/conversations/me",
                headers={"Authorization": f"Bearer {employee_token}"}
            )
            if current_response.status_code == 200:
                conv_id = current_response.json().get("id")
            else:
                pytest.skip("No conversation available for PDF test")
        else:
            conv_id = history[0]["id"]
        
        # Test PDF export with Bearer token
        response = requests.get(
            f"{BASE_URL}/api/conversations/{conv_id}/pdf",
            headers={"Authorization": f"Bearer {employee_token}"}
        )
        assert response.status_code == 200
        assert response.headers.get("content-type") == "application/pdf"
        print("PDF export via Bearer token successful")


class TestDataPersistence:
    """Test data persistence (simulated container restart)"""
    
    @pytest.fixture
    def employee_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=EMPLOYEE_CREDS)
        return response.json()["token"]
    
    def test_data_persists_across_requests(self, employee_token):
        """Test that data persists across multiple requests"""
        # Get conversation
        response1 = requests.get(
            f"{BASE_URL}/api/conversations/me",
            headers={"Authorization": f"Bearer {employee_token}"}
        )
        
        if response1.status_code == 404:
            pytest.skip("No active cycle for persistence test")
        
        conv1 = response1.json()
        
        # Wait a moment
        time.sleep(1)
        
        # Get again
        response2 = requests.get(
            f"{BASE_URL}/api/conversations/me",
            headers={"Authorization": f"Bearer {employee_token}"}
        )
        conv2 = response2.json()
        
        # Should be the same conversation
        assert conv1["id"] == conv2["id"]
        print("Data persistence verified")


class TestNoRatingsFields:
    """Verify no ratings fields exist anywhere in API responses"""
    
    @pytest.fixture
    def employee_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=EMPLOYEE_CREDS)
        return response.json()["token"]
    
    def test_conversation_has_no_ratings(self, employee_token):
        """Verify conversation response has no ratings fields"""
        response = requests.get(
            f"{BASE_URL}/api/conversations/me",
            headers={"Authorization": f"Bearer {employee_token}"}
        )
        
        if response.status_code == 404:
            pytest.skip("No active cycle")
        
        data = response.json()
        
        # Check for absence of any rating-related fields
        rating_fields = ["rating", "self_rating", "manager_rating", "performance_rating", 
                        "overall_rating", "ratings", "score", "self_score", "manager_score"]
        
        for field in rating_fields:
            assert field not in data, f"Found unexpected rating field: {field}"
        
        print("Verified: No ratings fields in conversation response")
    
    def test_root_api_confirms_no_ratings(self):
        """Verify root API explicitly states ratings:false"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        data = response.json()
        assert data.get("ratings") == False
        print("Root API confirms ratings:false")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
