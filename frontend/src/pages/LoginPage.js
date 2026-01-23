import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Loader2, Mail, KeyRound, ArrowRight, Building2 } from 'lucide-react';
import { toast } from 'sonner';

const LoginPage = () => {
  const navigate = useNavigate();
  const { startEmailAuth, verifyEmailCode, user } = useAuth();
  const [step, setStep] = useState('email'); // 'email' or 'verify'
  const [email, setEmail] = useState('');
  const [code, setCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [displayCode, setDisplayCode] = useState(null);

  // Redirect if already logged in
  React.useEffect(() => {
    if (user) {
      if (user.roles?.includes('admin')) {
        navigate('/admin');
      } else if (user.roles?.includes('manager')) {
        navigate('/manager');
      } else {
        navigate('/employee');
      }
    }
  }, [user, navigate]);

  const handleEmailSubmit = async (e) => {
    e.preventDefault();
    if (!email) return;

    setLoading(true);
    try {
      const response = await startEmailAuth(email.toLowerCase());
      if (response.code) {
        setDisplayCode(response.code);
      }
      setStep('verify');
      toast.success('Verification code sent!');
    } catch (error) {
      const message = error.response?.data?.detail || 'Failed to send verification code';
      toast.error(message);
    } finally {
      setLoading(false);
    }
  };

  const handleVerifySubmit = async (e) => {
    e.preventDefault();
    if (!code) return;

    setLoading(true);
    try {
      const response = await verifyEmailCode(email.toLowerCase(), code);
      toast.success('Login successful!');
      
      // Navigate based on role
      if (response.user?.roles?.includes('admin')) {
        navigate('/admin');
      } else if (response.user?.roles?.includes('manager')) {
        navigate('/manager');
      } else {
        navigate('/employee');
      }
    } catch (error) {
      const message = error.response?.data?.detail || 'Invalid verification code';
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
              {step === 'email' ? 'Sign in to your account' : 'Enter verification code'}
            </CardTitle>
            <CardDescription className="text-gray-400">
              {step === 'email' 
                ? 'Enter your company email to receive a verification code'
                : `We sent a code to ${email}`
              }
            </CardDescription>
          </CardHeader>
          <CardContent>
            {step === 'email' ? (
              <form onSubmit={handleEmailSubmit} className="space-y-4">
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
                    />
                  </div>
                </div>
                <Button 
                  type="submit" 
                  className="w-full h-11 bg-[#007AFF] hover:bg-[#007AFF]/90 btn-glow"
                  disabled={loading}
                  data-testid="login-continue-btn"
                >
                  {loading ? (
                    <Loader2 className="w-4 h-4 animate-spin mr-2" />
                  ) : null}
                  Continue
                  <ArrowRight className="w-4 h-4 ml-2" />
                </Button>
              </form>
            ) : (
              <form onSubmit={handleVerifySubmit} className="space-y-4">
                {displayCode && (
                  <div className="p-4 rounded-lg bg-[#007AFF]/10 border border-[#007AFF]/20 mb-4">
                    <p className="text-xs text-gray-400 mb-1">Your verification code (dev mode):</p>
                    <p className="text-2xl font-mono font-bold text-[#007AFF] tracking-widest">{displayCode}</p>
                  </div>
                )}
                <div className="space-y-2">
                  <Label htmlFor="code" className="text-sm text-gray-300">Verification code</Label>
                  <div className="relative">
                    <KeyRound className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
                    <Input
                      id="code"
                      type="text"
                      placeholder="Enter 6-digit code"
                      value={code}
                      onChange={(e) => setCode(e.target.value)}
                      className="pl-10 bg-[#1E1E1E] border-white/10 h-11 font-mono text-lg tracking-widest"
                      data-testid="login-code-input"
                      maxLength={6}
                      required
                    />
                  </div>
                </div>
                <Button 
                  type="submit" 
                  className="w-full h-11 bg-[#007AFF] hover:bg-[#007AFF]/90 btn-glow"
                  disabled={loading}
                  data-testid="login-verify-btn"
                >
                  {loading ? (
                    <Loader2 className="w-4 h-4 animate-spin mr-2" />
                  ) : null}
                  Verify & Sign in
                </Button>
                <Button 
                  type="button"
                  variant="ghost" 
                  className="w-full text-gray-400 hover:text-white"
                  onClick={() => {
                    setStep('email');
                    setCode('');
                    setDisplayCode(null);
                  }}
                  data-testid="login-back-btn"
                >
                  Use a different email
                </Button>
              </form>
            )}
          </CardContent>
        </Card>

        {/* Demo accounts hint */}
        <div className="mt-6 p-4 rounded-lg bg-white/5 border border-white/10">
          <p className="text-xs text-gray-400 mb-2">Demo accounts:</p>
          <div className="space-y-1 text-xs font-mono text-gray-500">
            <p>Admin: admin@company.com</p>
            <p>Manager: engineering.lead@company.com</p>
            <p>Employee: developer1@company.com</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
