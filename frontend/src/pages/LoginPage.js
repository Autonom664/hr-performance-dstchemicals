import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Loader2, Mail, Lock, ArrowRight, Building2, Eye, EyeOff, KeyRound } from 'lucide-react';
import { toast } from 'sonner';

const LoginPage = () => {
  const navigate = useNavigate();
  const { login, changePassword, user, mustChangePassword } = useAuth();
  const [step, setStep] = useState('login'); // 'login' or 'change-password'
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  
  // Change password state
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  // Handle redirect for authenticated users
  useEffect(() => {
    if (user && !mustChangePassword) {
      redirectByRole(user);
    } else if (user && mustChangePassword) {
      setStep('change-password');
      setCurrentPassword(password); // Pre-fill with login password
    }
  }, [user, mustChangePassword]);

  const redirectByRole = (userData) => {
    if (userData.roles?.includes('admin')) {
      navigate('/admin');
    } else if (userData.roles?.includes('manager')) {
      navigate('/manager');
    } else {
      navigate('/employee');
    }
  };

  const handleLoginSubmit = async (e) => {
    e.preventDefault();
    if (!email || !password) return;

    setLoading(true);
    try {
      const response = await login(email.toLowerCase(), password);
      
      if (response.must_change_password) {
        setStep('change-password');
        setCurrentPassword(password);
        toast.info('Please change your password to continue');
      } else {
        toast.success('Login successful!');
        redirectByRole(response.user);
      }
    } catch (error) {
      const message = error.response?.data?.detail || 'Invalid email or password';
      toast.error(message);
    } finally {
      setLoading(false);
    }
  };

  const handleChangePasswordSubmit = async (e) => {
    e.preventDefault();
    
    if (newPassword.length < 8) {
      toast.error('New password must be at least 8 characters');
      return;
    }
    
    if (newPassword !== confirmPassword) {
      toast.error('Passwords do not match');
      return;
    }

    setLoading(true);
    try {
      await changePassword(currentPassword, newPassword);
      toast.success('Password changed successfully!');
      redirectByRole(user);
    } catch (error) {
      const message = error.response?.data?.detail || 'Failed to change password';
      toast.error(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4 relative overflow-hidden">
      {/* Background gradient */}
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_30%_20%,rgba(0,122,255,0.08)_0%,transparent_50%)]" />
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_70%_80%,rgba(0,255,148,0.05)_0%,transparent_50%)]" />
      
      <div className="w-full max-w-md z-10">
        {/* Logo/Brand */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-[#007AFF] mb-4">
            <Building2 className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-3xl font-bold tracking-tight">HR Performance</h1>
          <p className="text-gray-400 mt-2">Annual Performance Review System</p>
        </div>

        <Card className="bg-[#121212] border-white/5">
          <CardHeader className="space-y-1 pb-4">
            <CardTitle className="text-xl font-semibold">
              {step === 'login' ? 'Sign in to your account' : 'Change your password'}
            </CardTitle>
            <CardDescription className="text-gray-400">
              {step === 'login' 
                ? 'Enter your email and password'
                : 'You must change your password before continuing'
              }
            </CardDescription>
          </CardHeader>
          <CardContent>
            {step === 'login' ? (
              <form onSubmit={handleLoginSubmit} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="email" className="text-sm text-gray-300">Email address</Label>
                  <div className="relative">
                    <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
                    <Input
                      id="email"
                      type="email"
                      placeholder="you@company.com"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      className="pl-10 bg-[#1E1E1E] border-white/10 h-11"
                      data-testid="login-email-input"
                      required
                      autoComplete="email"
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="password" className="text-sm text-gray-300">Password</Label>
                  <div className="relative">
                    <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
                    <Input
                      id="password"
                      type={showPassword ? 'text' : 'password'}
                      placeholder="Enter your password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      className="pl-10 pr-10 bg-[#1E1E1E] border-white/10 h-11"
                      data-testid="login-password-input"
                      required
                      autoComplete="current-password"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300"
                      tabIndex={-1}
                    >
                      {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                </div>
                <Button 
                  type="submit" 
                  className="w-full h-11 bg-[#007AFF] hover:bg-[#007AFF]/90 btn-glow"
                  disabled={loading}
                  data-testid="login-submit-btn"
                >
                  {loading ? (
                    <Loader2 className="w-4 h-4 animate-spin mr-2" />
                  ) : null}
                  Sign In
                  <ArrowRight className="w-4 h-4 ml-2" />
                </Button>
              </form>
            ) : (
              <form onSubmit={handleChangePasswordSubmit} className="space-y-4">
                <div className="p-4 rounded-lg bg-yellow-500/10 border border-yellow-500/20 mb-4">
                  <p className="text-sm text-yellow-400">
                    This is your first login. Please set a new password to continue.
                  </p>
                </div>
                
                <div className="space-y-2">
                  <Label htmlFor="current-password" className="text-sm text-gray-300">Current Password</Label>
                  <div className="relative">
                    <KeyRound className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
                    <Input
                      id="current-password"
                      type="password"
                      value={currentPassword}
                      onChange={(e) => setCurrentPassword(e.target.value)}
                      className="pl-10 bg-[#1E1E1E] border-white/10 h-11"
                      data-testid="current-password-input"
                      required
                      autoComplete="current-password"
                    />
                  </div>
                </div>
                
                <div className="space-y-2">
                  <Label htmlFor="new-password" className="text-sm text-gray-300">New Password</Label>
                  <div className="relative">
                    <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
                    <Input
                      id="new-password"
                      type="password"
                      placeholder="At least 8 characters"
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      className="pl-10 bg-[#1E1E1E] border-white/10 h-11"
                      data-testid="new-password-input"
                      required
                      minLength={8}
                      autoComplete="new-password"
                    />
                  </div>
                </div>
                
                <div className="space-y-2">
                  <Label htmlFor="confirm-password" className="text-sm text-gray-300">Confirm New Password</Label>
                  <div className="relative">
                    <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
                    <Input
                      id="confirm-password"
                      type="password"
                      placeholder="Repeat your new password"
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      className="pl-10 bg-[#1E1E1E] border-white/10 h-11"
                      data-testid="confirm-password-input"
                      required
                      minLength={8}
                      autoComplete="new-password"
                    />
                  </div>
                </div>
                
                <Button 
                  type="submit" 
                  className="w-full h-11 bg-[#007AFF] hover:bg-[#007AFF]/90 btn-glow"
                  disabled={loading}
                  data-testid="change-password-btn"
                >
                  {loading ? (
                    <Loader2 className="w-4 h-4 animate-spin mr-2" />
                  ) : null}
                  Change Password & Continue
                </Button>
              </form>
            )}
          </CardContent>
        </Card>

        {/* Security notice */}
        <div className="mt-6 p-4 rounded-lg bg-white/5 border border-white/10">
          <p className="text-xs text-gray-400">
            Your password was provided by your administrator. If you haven't received it, please contact HR.
          </p>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
