import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';
import Layout from '../components/Layout';
import RichTextEditor from '../components/RichTextEditor';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Loader2, FileText, Calendar, Target, Save, Send, Download, MessageSquare, History, ChevronRight, Clock } from 'lucide-react';
import { toast } from 'sonner';

const STATUS_LABELS = {
  not_started: 'Not Started',
  in_progress: 'In Progress',
  ready_for_manager: 'Ready for Manager',
  completed: 'Completed',
};

const STATUS_COLORS = {
  not_started: 'bg-red-500/10 text-red-400 border-red-500/20',
  in_progress: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20',
  ready_for_manager: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
  completed: 'bg-green-500/10 text-green-400 border-green-500/20',
};

const EmployeeDashboard = () => {
  const { user, axiosInstance, API_URL } = useAuth();
  const navigate = useNavigate();
  const [cycle, setCycle] = useState(null);
  const [conversation, setConversation] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [activeTab, setActiveTab] = useState('current');
  const [viewingArchived, setViewingArchived] = useState(null);
  
  // Form state for employee fields (new structure)
  const [formData, setFormData] = useState({
    previous_goals_progress: '',
    status_since_last_meeting: '',
    new_goals: '',
    how_to_achieve_goals: '',
    support_needed: '',
    feedback_and_wishes: '',
  });

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [cycleRes, convRes, historyRes] = await Promise.all([
        axiosInstance.get('/cycles/active').catch(() => ({ data: null })),
        axiosInstance.get('/conversations/me').catch(() => ({ data: null })),
        axiosInstance.get('/conversations/me/history'),
      ]);
      
      setCycle(cycleRes.data);
      setConversation(convRes.data);
      setHistory(historyRes.data || []);
      
      if (convRes.data) {
        setFormData({
          previous_goals_progress: convRes.data.previous_goals_progress || '',
          status_since_last_meeting: convRes.data.status_since_last_meeting || '',
          new_goals: convRes.data.new_goals || '',
          how_to_achieve_goals: convRes.data.how_to_achieve_goals || '',
          support_needed: convRes.data.support_needed || '',
          feedback_and_wishes: convRes.data.feedback_and_wishes || '',
        });
      }
    } catch (error) {
      if (error.response?.status !== 404) {
        toast.error('Failed to load data');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async (newStatus = null) => {
    setSaving(true);
    try {
      const payload = { ...formData };
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

  const handleExportPDF = async (conversationId) => {
    if (!conversationId) return;
    try {
      const token = localStorage.getItem('session_token');
      window.open(`${API_URL}/conversations/${conversationId}/pdf?token=${token}`, '_blank');
    } catch (error) {
      toast.error('Failed to export PDF');
    }
  };

  const viewArchivedConversation = async (convId) => {
    try {
      const response = await axiosInstance.get(`/conversations/${convId}`);
      setViewingArchived(response.data);
    } catch (error) {
      toast.error('Failed to load archived conversation');
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

  const isCompleted = conversation?.status === 'completed';
  const isReadyForManager = conversation?.status === 'ready_for_manager';
  const archivedConversations = history.filter(h => h.cycle?.status === 'archived');

  // Archived conversation view
  if (viewingArchived) {
    const { conversation: archivedConv, cycle: archivedCycle } = viewingArchived;
    
    return (
      <Layout>
        <div className="max-w-4xl mx-auto space-y-6" data-testid="archived-conversation-view">
          <div className="flex items-center gap-4">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setViewingArchived(null)}
              className="hover:bg-white/5"
              data-testid="back-to-current-btn"
            >
              <ChevronRight className="w-4 h-4 mr-2 rotate-180" />
              Back to Current
            </Button>
          </div>

          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <h1 className="text-2xl md:text-3xl font-bold tracking-tight">{archivedCycle?.name || 'Archived Review'}</h1>
              <p className="text-gray-400 mt-1">Read-only archived conversation</p>
            </div>
            <div className="flex items-center gap-3">
              <Badge className="bg-yellow-500/10 text-yellow-400 border-yellow-500/20 px-3 py-1 border">
                Archived
              </Badge>
              <Button 
                variant="outline" 
                size="sm"
                onClick={() => handleExportPDF(archivedConv.id)}
                className="border-white/10 hover:bg-white/5"
                data-testid="export-archived-pdf-btn"
              >
                <Download className="w-4 h-4 mr-2" />
                Export PDF
              </Button>
            </div>
          </div>

          {/* Employee Sections (Read-only) */}
          <Card className="bg-[#121212] border-white/5">
            <CardHeader className="pb-3">
              <CardTitle className="text-lg flex items-center gap-2">
                <Target className="w-5 h-5 text-[#00FF94]" />
                1. Status Since Last Meeting
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <p className="text-sm text-gray-400 mb-2">How have your previous goals progressed?</p>
                <div className="prose prose-invert prose-sm max-w-none p-3 bg-[#1E1E1E] rounded-lg" 
                     dangerouslySetInnerHTML={{ __html: archivedConv.previous_goals_progress || '<em class="text-gray-500">No response</em>' }} />
              </div>
              <div>
                <p className="text-sm text-gray-400 mb-2">General status update:</p>
                <div className="prose prose-invert prose-sm max-w-none p-3 bg-[#1E1E1E] rounded-lg"
                     dangerouslySetInnerHTML={{ __html: archivedConv.status_since_last_meeting || '<em class="text-gray-500">No response</em>' }} />
              </div>
            </CardContent>
          </Card>

          <Card className="bg-[#121212] border-white/5">
            <CardHeader className="pb-3">
              <CardTitle className="text-lg flex items-center gap-2">
                <FileText className="w-5 h-5 text-[#007AFF]" />
                2. New Goals and How to Achieve Them
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <p className="text-sm text-gray-400 mb-2">Key goals for the next 1-3 months:</p>
                <div className="prose prose-invert prose-sm max-w-none p-3 bg-[#1E1E1E] rounded-lg"
                     dangerouslySetInnerHTML={{ __html: archivedConv.new_goals || '<em class="text-gray-500">No response</em>' }} />
              </div>
              <div>
                <p className="text-sm text-gray-400 mb-2">How are you going to achieve them?</p>
                <div className="prose prose-invert prose-sm max-w-none p-3 bg-[#1E1E1E] rounded-lg"
                     dangerouslySetInnerHTML={{ __html: archivedConv.how_to_achieve_goals || '<em class="text-gray-500">No response</em>' }} />
              </div>
              <div>
                <p className="text-sm text-gray-400 mb-2">Support or learning needed:</p>
                <div className="prose prose-invert prose-sm max-w-none p-3 bg-[#1E1E1E] rounded-lg"
                     dangerouslySetInnerHTML={{ __html: archivedConv.support_needed || '<em class="text-gray-500">No response</em>' }} />
              </div>
            </CardContent>
          </Card>

          <Card className="bg-[#121212] border-white/5">
            <CardHeader className="pb-3">
              <CardTitle className="text-lg flex items-center gap-2">
                <MessageSquare className="w-5 h-5 text-purple-400" />
                3. Feedback and Wishes for the Future
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="prose prose-invert prose-sm max-w-none p-3 bg-[#1E1E1E] rounded-lg"
                   dangerouslySetInnerHTML={{ __html: archivedConv.feedback_and_wishes || '<em class="text-gray-500">No response</em>' }} />
            </CardContent>
          </Card>

          {/* Manager Feedback */}
          <Card className="bg-[#121212] border-white/5">
            <CardHeader className="pb-3">
              <CardTitle className="text-lg flex items-center gap-2">
                <FileText className="w-5 h-5 text-orange-400" />
                Manager Feedback
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="prose prose-invert prose-sm max-w-none p-3 bg-[#1E1E1E] rounded-lg"
                   dangerouslySetInnerHTML={{ __html: archivedConv.manager_feedback || '<em class="text-gray-500">No feedback provided</em>' }} />
            </CardContent>
          </Card>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="max-w-4xl mx-auto space-y-6" data-testid="employee-dashboard">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl md:text-3xl font-bold tracking-tight">
              {cycle ? cycle.name : 'Performance Review'}
            </h1>
            <p className="text-gray-400 mt-1">Your performance review conversation</p>
          </div>
        </div>

        {/* Tabs for Current vs History */}
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="bg-[#1E1E1E] border border-white/10">
            <TabsTrigger value="current" className="data-[state=active]:bg-[#007AFF]" data-testid="current-tab">
              <Calendar className="w-4 h-4 mr-2" />
              Current Cycle
            </TabsTrigger>
            <TabsTrigger value="history" className="data-[state=active]:bg-[#007AFF]" data-testid="history-tab">
              <History className="w-4 h-4 mr-2" />
              History ({archivedConversations.length})
            </TabsTrigger>
          </TabsList>

          {/* Current Cycle Tab */}
          <TabsContent value="current" className="space-y-6 mt-6">
            {!cycle ? (
              <div className="flex flex-col items-center justify-center h-[40vh] text-center">
                <Calendar className="w-16 h-16 text-gray-600 mb-4" />
                <h2 className="text-2xl font-semibold mb-2">No Active Cycle</h2>
                <p className="text-gray-400 max-w-md">
                  There is no active performance review cycle at the moment. 
                  Please check back later or contact your HR administrator.
                </p>
              </div>
            ) : (
              <>
                {/* Status and Actions Header */}
                <div className="flex items-center justify-between">
                  <Badge className={`${STATUS_COLORS[conversation?.status || 'not_started']} px-3 py-1 border`}>
                    {STATUS_LABELS[conversation?.status || 'not_started']}
                  </Badge>
                  {conversation?.id && (
                    <Button 
                      variant="outline" 
                      size="sm"
                      onClick={() => handleExportPDF(conversation.id)}
                      className="border-white/10 hover:bg-white/5"
                      data-testid="export-pdf-btn"
                    >
                      <Download className="w-4 h-4 mr-2" />
                      Export PDF
                    </Button>
                  )}
                </div>

                {/* Manager Feedback Card (if exists) */}
                {conversation?.manager_feedback && (
                  <Card className="bg-[#121212] border-orange-500/20">
                    <CardHeader className="pb-3">
                      <CardTitle className="text-lg flex items-center gap-2">
                        <FileText className="w-5 h-5 text-orange-400" />
                        Manager's Feedback
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div 
                        className="prose prose-invert prose-sm max-w-none"
                        dangerouslySetInnerHTML={{ __html: conversation.manager_feedback }}
                      />
                    </CardContent>
                  </Card>
                )}

                {/* Section 1: Status Since Last Meeting */}
                <Card className="bg-[#121212] border-white/5">
                  <CardHeader className="pb-3">
                    <CardTitle className="text-lg flex items-center gap-2">
                      <Target className="w-5 h-5 text-[#00FF94]" />
                      1. Status Since Last Meeting
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-6">
                    <div className="space-y-2">
                      <CardDescription className="text-gray-300 font-medium">
                        a) How have your previous goals progressed?
                      </CardDescription>
                      <RichTextEditor
                        value={formData.previous_goals_progress}
                        onChange={(val) => setFormData(prev => ({ ...prev, previous_goals_progress: val }))}
                        placeholder="Describe the progress on your previous goals..."
                        disabled={isCompleted}
                        data-testid="previous-goals-progress-editor"
                      />
                    </div>
                    <div className="space-y-2">
                      <CardDescription className="text-gray-300 font-medium">
                        General status update (optional):
                      </CardDescription>
                      <RichTextEditor
                        value={formData.status_since_last_meeting}
                        onChange={(val) => setFormData(prev => ({ ...prev, status_since_last_meeting: val }))}
                        placeholder="Any other updates since the last meeting..."
                        disabled={isCompleted}
                        data-testid="status-since-last-editor"
                      />
                    </div>
                  </CardContent>
                </Card>

                {/* Section 2: New Goals */}
                <Card className="bg-[#121212] border-white/5">
                  <CardHeader className="pb-3">
                    <CardTitle className="text-lg flex items-center gap-2">
                      <FileText className="w-5 h-5 text-[#007AFF]" />
                      2. New Goals and How to Achieve Them
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-6">
                    <div className="space-y-2">
                      <CardDescription className="text-gray-300 font-medium">
                        a) What are your key goals for the next 1–3 months (or until next review)?
                      </CardDescription>
                      <RichTextEditor
                        value={formData.new_goals}
                        onChange={(val) => setFormData(prev => ({ ...prev, new_goals: val }))}
                        placeholder="List your key goals for the upcoming period..."
                        disabled={isCompleted}
                        data-testid="new-goals-editor"
                      />
                    </div>
                    <div className="space-y-2">
                      <CardDescription className="text-gray-300 font-medium">
                        b) How are you going to achieve them?
                      </CardDescription>
                      <RichTextEditor
                        value={formData.how_to_achieve_goals}
                        onChange={(val) => setFormData(prev => ({ ...prev, how_to_achieve_goals: val }))}
                        placeholder="Describe your approach and action plan..."
                        disabled={isCompleted}
                        data-testid="how-to-achieve-editor"
                      />
                    </div>
                    <div className="space-y-2">
                      <CardDescription className="text-gray-300 font-medium">
                        c) If needed – what support or learning do you need?
                      </CardDescription>
                      <RichTextEditor
                        value={formData.support_needed}
                        onChange={(val) => setFormData(prev => ({ ...prev, support_needed: val }))}
                        placeholder="Describe any support, resources, or training you need..."
                        disabled={isCompleted}
                        data-testid="support-needed-editor"
                      />
                    </div>
                  </CardContent>
                </Card>

                {/* Section 3: Feedback and Wishes */}
                <Card className="bg-[#121212] border-white/5">
                  <CardHeader className="pb-3">
                    <CardTitle className="text-lg flex items-center gap-2">
                      <MessageSquare className="w-5 h-5 text-purple-400" />
                      3. Feedback and Wishes for the Future
                    </CardTitle>
                    <CardDescription>
                      Share any feedback, suggestions, or wishes for your role or the organization
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <RichTextEditor
                      value={formData.feedback_and_wishes}
                      onChange={(val) => setFormData(prev => ({ ...prev, feedback_and_wishes: val }))}
                      placeholder="Share your thoughts, feedback, or suggestions..."
                      disabled={isCompleted}
                      data-testid="feedback-wishes-editor"
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
              </>
            )}
          </TabsContent>

          {/* History Tab */}
          <TabsContent value="history" className="space-y-4 mt-6">
            {archivedConversations.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-[40vh] text-center">
                <History className="w-16 h-16 text-gray-600 mb-4" />
                <h2 className="text-2xl font-semibold mb-2">No History Yet</h2>
                <p className="text-gray-400 max-w-md">
                  You don't have any archived performance reviews yet.
                </p>
              </div>
            ) : (
              archivedConversations.map((item) => (
                <Card 
                  key={item.id} 
                  className="bg-[#121212] border-white/5 hover:border-white/10 cursor-pointer transition-colors"
                  onClick={() => viewArchivedConversation(item.id)}
                  data-testid={`archived-conversation-${item.id}`}
                >
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <h3 className="font-semibold">{item.cycle?.name || 'Archived Review'}</h3>
                        <div className="flex items-center gap-2 text-sm text-gray-400 mt-1">
                          <Clock className="w-4 h-4" />
                          {item.cycle?.start_date ? new Date(item.cycle.start_date).toLocaleDateString() : 'Unknown'} - 
                          {item.cycle?.end_date ? new Date(item.cycle.end_date).toLocaleDateString() : 'Unknown'}
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        <Badge className={`${STATUS_COLORS[item.status || 'not_started']} border`}>
                          {STATUS_LABELS[item.status || 'not_started']}
                        </Badge>
                        <ChevronRight className="w-5 h-5 text-gray-500" />
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))
            )}
          </TabsContent>
        </Tabs>
      </div>
    </Layout>
  );
};

export default EmployeeDashboard;
