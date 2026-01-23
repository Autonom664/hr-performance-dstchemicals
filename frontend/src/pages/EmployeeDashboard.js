import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';
import Layout from '../components/Layout';
import RichTextEditor from '../components/RichTextEditor';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Loader2, FileText, Calendar, Target, Save, Send, Download } from 'lucide-react';
import { toast } from 'sonner';

const STATUS_LABELS = {
  not_started: 'Not Started',
  in_progress: 'In Progress',
  ready_for_manager: 'Ready for Manager',
  completed: 'Completed',
};

const EmployeeDashboard = () => {
  const { user, axiosInstance, API_URL } = useAuth();
  const navigate = useNavigate();
  const [cycle, setCycle] = useState(null);
  const [conversation, setConversation] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [selfReview, setSelfReview] = useState('');
  const [goals, setGoals] = useState('');

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [cycleRes, convRes] = await Promise.all([
        axiosInstance.get('/cycles/active'),
        axiosInstance.get('/conversations/me'),
      ]);
      setCycle(cycleRes.data);
      setConversation(convRes.data);
      setSelfReview(convRes.data?.employee_self_review || '');
      setGoals(convRes.data?.goals_next_period || '');
    } catch (error) {
      if (error.response?.status === 404) {
        toast.info('No active performance cycle found');
      } else {
        toast.error('Failed to load data');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async (newStatus = null) => {
    setSaving(true);
    try {
      const payload = {
        employee_self_review: selfReview,
        goals_next_period: goals,
      };
      if (newStatus) {
        payload.status = newStatus;
      }
      
      const response = await axiosInstance.put('/conversations/me', payload);
      setConversation(response.data);
      toast.success(newStatus === 'ready_for_manager' ? 'Submitted for manager review!' : 'Progress saved');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to save');
    } finally {
      setSaving(false);
    }
  };

  const handleExportPDF = async () => {
    if (!conversation?.id) return;
    try {
      const token = localStorage.getItem('session_token');
      window.open(`${API_URL}/conversations/${conversation.id}/pdf?token=${token}`, '_blank');
    } catch (error) {
      toast.error('Failed to export PDF');
    }
  };

  if (loading) {
    return (
      <Layout>
        <div className="flex items-center justify-center h-[60vh]">
          <Loader2 className="w-8 h-8 animate-spin text-[#007AFF]" />
        </div>
      </Layout>
    );
  }

  if (!cycle) {
    return (
      <Layout>
        <div className="flex flex-col items-center justify-center h-[60vh] text-center">
          <Calendar className="w-16 h-16 text-gray-600 mb-4" />
          <h2 className="text-2xl font-semibold mb-2">No Active Cycle</h2>
          <p className="text-gray-400 max-w-md">
            There is no active performance review cycle at the moment. 
            Please check back later or contact your HR administrator.
          </p>
        </div>
      </Layout>
    );
  }

  const isCompleted = conversation?.status === 'completed';
  const isReadyForManager = conversation?.status === 'ready_for_manager';

  return (
    <Layout>
      <div className="max-w-4xl mx-auto space-y-6" data-testid="employee-dashboard">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl md:text-3xl font-bold tracking-tight">{cycle.name}</h1>
            <p className="text-gray-400 mt-1">Your performance review for this cycle</p>
          </div>
          <div className="flex items-center gap-3">
            <Badge className={`status-${conversation?.status || 'not_started'} px-3 py-1`}>
              {STATUS_LABELS[conversation?.status || 'not_started']}
            </Badge>
            {conversation?.id && (
              <Button 
                variant="outline" 
                size="sm"
                onClick={handleExportPDF}
                className="border-white/10 hover:bg-white/5"
                data-testid="export-pdf-btn"
              >
                <Download className="w-4 h-4 mr-2" />
                Export PDF
              </Button>
            )}
          </div>
        </div>

        {/* Manager Review Card (if exists) */}
        {conversation?.manager_review && (
          <Card className="bg-[#121212] border-white/5">
            <CardHeader className="pb-3">
              <CardTitle className="text-lg flex items-center gap-2">
                <FileText className="w-5 h-5 text-[#007AFF]" />
                Manager's Feedback
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div 
                className="prose prose-invert prose-sm max-w-none"
                dangerouslySetInnerHTML={{ __html: conversation.manager_review }}
              />
              {conversation.ratings && (
                <div className="mt-4 pt-4 border-t border-white/10">
                  <p className="text-sm text-gray-400 mb-2">Ratings</p>
                  <div className="flex flex-wrap gap-4">
                    {conversation.ratings.performance && (
                      <div className="flex items-center gap-2">
                        <span className="text-sm text-gray-400">Performance:</span>
                        <span className="font-semibold">{conversation.ratings.performance}/5</span>
                      </div>
                    )}
                    {conversation.ratings.collaboration && (
                      <div className="flex items-center gap-2">
                        <span className="text-sm text-gray-400">Collaboration:</span>
                        <span className="font-semibold">{conversation.ratings.collaboration}/5</span>
                      </div>
                    )}
                    {conversation.ratings.growth && (
                      <div className="flex items-center gap-2">
                        <span className="text-sm text-gray-400">Growth:</span>
                        <span className="font-semibold">{conversation.ratings.growth}/5</span>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {/* Self Review */}
        <Card className="bg-[#121212] border-white/5">
          <CardHeader className="pb-3">
            <CardTitle className="text-lg flex items-center gap-2">
              <FileText className="w-5 h-5 text-[#00FF94]" />
              Self Review
            </CardTitle>
            <CardDescription>
              Reflect on your accomplishments, challenges, and growth this period
            </CardDescription>
          </CardHeader>
          <CardContent>
            <RichTextEditor
              value={selfReview}
              onChange={setSelfReview}
              placeholder="Describe your key accomplishments, challenges you overcame, and how you've grown..."
              disabled={isCompleted}
              data-testid="self-review-editor"
            />
          </CardContent>
        </Card>

        {/* Goals */}
        <Card className="bg-[#121212] border-white/5">
          <CardHeader className="pb-3">
            <CardTitle className="text-lg flex items-center gap-2">
              <Target className="w-5 h-5 text-[#007AFF]" />
              Goals for Next Period
            </CardTitle>
            <CardDescription>
              Set clear, measurable goals for your next review period
            </CardDescription>
          </CardHeader>
          <CardContent>
            <RichTextEditor
              value={goals}
              onChange={setGoals}
              placeholder="Define your goals, objectives, and development areas for the upcoming period..."
              disabled={isCompleted}
              data-testid="goals-editor"
            />
          </CardContent>
        </Card>

        {/* Actions */}
        {!isCompleted && (
          <div className="flex flex-col sm:flex-row gap-3 justify-end">
            <Button
              variant="outline"
              onClick={() => handleSave('in_progress')}
              disabled={saving}
              className="border-white/10 hover:bg-white/5"
              data-testid="save-draft-btn"
            >
              {saving ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Save className="w-4 h-4 mr-2" />}
              Save Draft
            </Button>
            {!isReadyForManager && (
              <Button
                onClick={() => handleSave('ready_for_manager')}
                disabled={saving}
                className="bg-[#007AFF] hover:bg-[#007AFF]/90 btn-glow"
                data-testid="submit-review-btn"
              >
                {saving ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Send className="w-4 h-4 mr-2" />}
                Submit for Manager Review
              </Button>
            )}
          </div>
        )}

        {isCompleted && (
          <div className="p-4 rounded-lg bg-green-500/10 border border-green-500/20 text-center">
            <p className="text-green-400">This review has been completed by your manager.</p>
          </div>
        )}

        {isReadyForManager && !isCompleted && (
          <div className="p-4 rounded-lg bg-blue-500/10 border border-blue-500/20 text-center">
            <p className="text-blue-400">Your review is submitted and waiting for manager feedback.</p>
          </div>
        )}
      </div>
    </Layout>
  );
};

export default EmployeeDashboard;
