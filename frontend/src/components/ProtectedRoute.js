import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Loader2 } from 'lucide-react';

export const ProtectedRoute = ({ children, requiredRoles = [] }) => {
  const { user, loading, mustChangePassword } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#0A0A0A]">
        <Loader2 className="w-8 h-8 animate-spin text-[#007AFF]" />
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // If user must change password, redirect to login page for password change flow
  if (mustChangePassword) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // Check role requirements
  if (requiredRoles.length > 0) {
    const hasRequiredRole = requiredRoles.some(role => user.roles?.includes(role));
    if (!hasRequiredRole) {
      // Redirect to appropriate dashboard based on user's role
      if (user.roles?.includes('admin')) {
        return <Navigate to="/admin" replace />;
      } else if (user.roles?.includes('manager')) {
        return <Navigate to="/manager" replace />;
      } else {
        return <Navigate to="/employee" replace />;
      }
    }
  }

  return children;
};

export const PublicRoute = ({ children }) => {
  const { user, loading, mustChangePassword } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#0A0A0A]">
        <Loader2 className="w-8 h-8 animate-spin text-[#007AFF]" />
      </div>
    );
  }

  // If user must change password, let them stay on login page
  if (user && mustChangePassword) {
    return children;
  }

  if (user) {
    // Redirect to appropriate dashboard based on role
    if (user.roles?.includes('admin')) {
      return <Navigate to="/admin" replace />;
    } else if (user.roles?.includes('manager')) {
      return <Navigate to="/manager" replace />;
    } else {
      return <Navigate to="/employee" replace />;
    }
  }

  return children;
};
