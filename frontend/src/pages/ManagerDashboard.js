import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate, useParams } from 'react-router-dom';
import Layout from '../components/Layout';
import RichTextEditor from '../components/RichTextEditor';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/table';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Loader2, Users, ChevronRight, FileText, Calendar, Save, CheckCircle, Download, ArrowLeft, Target, MessageSquare, History, Clock, Info } from 'lucide-react';
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

const ManagerDashboard = () => {
  const { user, axiosInstance, API_URL } = useAuth();
  const navigate = useNavigate();
  const { employeeEmail } = useParams();
  const [reports, setReports] = useState([]);
  const [cycle, setCycle] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedEmployee, setSelectedEmployee] = useState(null);
  const [conversation, setConversation] = useState(null);
  const [saving, setSaving] = useState(false);
  const [employeeHistory, setEmployeeHistory] = useState([]);
  const [viewingArchived, setViewingArchived] = useState(null);
  const [activeDetailTab, setActiveDetailTab] = useState('current');
  
  // Form state - only manager feedback (no ratings)
  const [managerFeedback, setManagerFeedback] = useState('');

  useEffect(() => {
    fetchReports();
    fetchCycle();
  }, []);

  useEffect(() => {
    if (employeeEmail) {
      fetchConversation(employeeEmail);
      fetchEmployeeHistory(employeeEmail);
    } else {
      setSelectedEmployee(null);
      setConversation(null);
      setEmployeeHistory([]);
      setViewingArchived(null);
    }
  }, [employeeEmail]);

  const fetchCycle = async () => {
    try {
      const response = await axiosInstance.get('/cycles/active');
      setCycle(response.data);
    } catch (error) {
      console.error('No active cycle:', error);
    }
  };

  const fetchReports = async () => {
    try {
      const response = await axiosInstance.get('/manager/reports');
      setReports(response.data);
    } catch (error) {
      toast.error('Failed to load reports');
    } finally {
      setLoading(false);
    }
  };

  const fetchConversation = async (email) => {
    setLoading(true);
    try {
      const response = await axiosInstance.get(`/manager/conversations/${email}`);
      setSelectedEmployee(response.data.employee);
      setConversation(response.data.conversation);
      setManagerFeedback(response.data.conversation?.manager_feedback || '');
    } catch (error) {
      toast.error('Failed to load conversation');
      navigate('/manager');
    } finally {
      setLoading(false);
    }
  };

  const fetchEmployeeHistory = async (email) => {
    try {
      const response = await axiosInstance.get(`/manager/reports/${email}/history`);
      setEmployeeHistory(response.data || []);
    } catch (error) {
      console.error('Failed to load history:', error);
    }
  };

  const handleSave = async (complete = false) => {
    setSaving(true);
    try {
      const payload = {
        manager_feedback: managerFeedback,
      };
      
      if (complete) {
        payload.status = 'completed';
      }
      
      const response = await axiosInstance.put(`/manager/conversations/${employeeEmail}`, payload);
      setConversation(response.data);
      toast.success(complete ? 'Review completed!' : 'Feedback saved');
      
      if (complete) {
        navigate('/manager');
      }
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

  if (loading && !employeeEmail) {
    return (
      <Layout>
        <div className="flex items-center justify-center h-[60vh]">
          <Loader2 className="w-8 h-8 animate-spin text-[#007AFF]" />
        </div>
      </Layout>
    );
  }

  // Archived conversation view
  if (viewingArchived) {
    const { conversation: archivedConv, cycle: archivedCycle, employee } = viewingArchived;
    
    return (
      <Layout>
        <div className="max-w-4xl mx-auto space-y-6" data-testid="archived-manager-view">
          <div className="flex items-center gap-4">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setViewingArchived(null)}
              className="hover:bg-white/5"
            >
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back
            </Button>
          </div>

          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <h1 className="text-2xl md:text-3xl font-bold tracking-tight">
                {employee?.name || employee?.email} - {archivedCycle?.name || 'Archived'}
              </h1>
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
          <Card className="bg-[#121212] border-orange-500/20">
            <CardHeader className="pb-3">
              <CardTitle className="text-lg flex items-center gap-2">
                <FileText className="w-5 h-5 text-orange-400" />
                Your Feedback
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

  // Detail view
  if (employeeEmail && selectedEmployee) {
    const isCompleted = conversation?.status === 'completed';
    const archivedConversations = employeeHistory.filter(h => h.cycle?.status === 'archived');
    
    return (
      <Layout>
        <div className="max-w-4xl mx-auto space-y-6" data-testid="manager-review-detail">
          {/* Back button and header */}
          <div className="flex items-center gap-4">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => navigate('/manager')}
              className="hover:bg-white/5"
              data-testid="back-to-reports-btn"
            >
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back to Reports
            </Button>
          </div>

          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <h1 className="text-2xl md:text-3xl font-bold tracking-tight">
                {selectedEmployee.name || selectedEmployee.email}
              </h1>
              <p className="text-gray-400 mt-1">{selectedEmployee.department || 'No department'}</p>
            </div>
          </div>

          {/* Tabs for Current vs History */}
          <Tabs value={activeDetailTab} onValueChange={setActiveDetailTab}>
            <TabsList className="bg-[#1E1E1E] border border-white/10">
              <TabsTrigger value="current" className="data-[state=active]:bg-[#007AFF]">
                <Calendar className="w-4 h-4 mr-2" />
                Current Review
              </TabsTrigger>
              <TabsTrigger value="history" className="data-[state=active]:bg-[#007AFF]">
                <History className="w-4 h-4 mr-2" />
                History ({archivedConversations.length})
              </TabsTrigger>
            </TabsList>

            {/* Current Review Tab */}
            <TabsContent value="current" className="space-y-6 mt-6">
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

              {/* Employee's Section 1: Status Since Last Meeting */}
              <Card className="bg-[#121212] border-white/5">
                <CardHeader className="pb-3">
                  <CardTitle className="text-lg flex items-center gap-2">
                    <Target className="w-5 h-5 text-[#00FF94]" />
                    1. Employee's Status Since Last Meeting
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <p className="text-sm text-gray-400 mb-2">How have previous goals progressed?</p>
                    {conversation?.previous_goals_progress ? (
                      <div className="prose prose-invert prose-sm max-w-none p-3 bg-[#1E1E1E] rounded-lg"
                           dangerouslySetInnerHTML={{ __html: conversation.previous_goals_progress }} />
                    ) : (
                      <p className="text-gray-500 italic p-3 bg-[#1E1E1E] rounded-lg">Not submitted yet</p>
                    )}
                  </div>
                  <div>
                    <p className="text-sm text-gray-400 mb-2">General status update:</p>
                    {conversation?.status_since_last_meeting ? (
                      <div className="prose prose-invert prose-sm max-w-none p-3 bg-[#1E1E1E] rounded-lg"
                           dangerouslySetInnerHTML={{ __html: conversation.status_since_last_meeting }} />
                    ) : (
                      <p className="text-gray-500 italic p-3 bg-[#1E1E1E] rounded-lg">Not provided</p>
                    )}
                  </div>
                </CardContent>
              </Card>

              {/* Employee's Section 2: New Goals */}
              <Card className="bg-[#121212] border-white/5">
                <CardHeader className="pb-3">
                  <CardTitle className="text-lg flex items-center gap-2">
                    <FileText className="w-5 h-5 text-[#007AFF]" />
                    2. Employee's New Goals
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <p className="text-sm text-gray-400 mb-2">Key goals for the next 1-3 months:</p>
                    {conversation?.new_goals ? (
                      <div className="prose prose-invert prose-sm max-w-none p-3 bg-[#1E1E1E] rounded-lg"
                           dangerouslySetInnerHTML={{ __html: conversation.new_goals }} />
                    ) : (
                      <p className="text-gray-500 italic p-3 bg-[#1E1E1E] rounded-lg">Not submitted yet</p>
                    )}
                  </div>
                  <div>
                    <p className="text-sm text-gray-400 mb-2">How they plan to achieve them:</p>
                    {conversation?.how_to_achieve_goals ? (
                      <div className="prose prose-invert prose-sm max-w-none p-3 bg-[#1E1E1E] rounded-lg"
                           dangerouslySetInnerHTML={{ __html: conversation.how_to_achieve_goals }} />
                    ) : (
                      <p className="text-gray-500 italic p-3 bg-[#1E1E1E] rounded-lg">Not provided</p>
                    )}
                  </div>
                  <div>
                    <p className="text-sm text-gray-400 mb-2">Support or learning needed:</p>
                    {conversation?.support_needed ? (
                      <div className="prose prose-invert prose-sm max-w-none p-3 bg-[#1E1E1E] rounded-lg"
                           dangerouslySetInnerHTML={{ __html: conversation.support_needed }} />
                    ) : (
                      <p className="text-gray-500 italic p-3 bg-[#1E1E1E] rounded-lg">None specified</p>
                    )}
                  </div>
                </CardContent>
              </Card>

              {/* Employee's Section 3: Feedback and Wishes */}
              <Card className="bg-[#121212] border-white/5">
                <CardHeader className="pb-3">
                  <CardTitle className="text-lg flex items-center gap-2">
                    <MessageSquare className="w-5 h-5 text-purple-400" />
                    3. Employee's Feedback and Wishes
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  {conversation?.feedback_and_wishes ? (
                    <div className="prose prose-invert prose-sm max-w-none p-3 bg-[#1E1E1E] rounded-lg"
                         dangerouslySetInnerHTML={{ __html: conversation.feedback_and_wishes }} />
                  ) : (
                    <p className="text-gray-500 italic p-3 bg-[#1E1E1E] rounded-lg">Not submitted yet</p>
                  )}
                </CardContent>
              </Card>

              {/* Manager Feedback Form */}
              <Card className="bg-[#121212] border-orange-500/20">
                <CardHeader className="pb-3">
                  <CardTitle className="text-lg flex items-center gap-2">
                    <FileText className="w-5 h-5 text-orange-400" />
                    Your Feedback
                  </CardTitle>
                  <CardDescription>
                    Provide your feedback for this employee's performance review
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <RichTextEditor
                    value={managerFeedback}
                    onChange={setManagerFeedback}
                    placeholder="Write your feedback here... Include strengths, areas for improvement, and recommendations."
                    disabled={isCompleted}
                    data-testid="manager-feedback-editor"
                  />
                </CardContent>
              </Card>

              {/* Actions */}
              {!isCompleted && (
                <div className="flex flex-col sm:flex-row gap-3 justify-end">
                  <Button
                    variant="outline"
                    onClick={() => handleSave(false)}
                    disabled={saving}
                    className="border-white/10 hover:bg-white/5"
                    data-testid="save-feedback-btn"
                  >
                    {saving ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Save className="w-4 h-4 mr-2" />}
                    Save Draft
                  </Button>
                  <Button
                    onClick={() => handleSave(true)}
                    disabled={saving}
                    className="bg-[#00FF94] text-black hover:bg-[#00FF94]/90"
                    data-testid="complete-review-btn"
                  >
                    {saving ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <CheckCircle className="w-4 h-4 mr-2" />}
                    Complete Review
                  </Button>
                </div>
              )}

              {isCompleted && (
                <div className="p-4 rounded-lg bg-green-500/10 border border-green-500/20 text-center">
                  <p className="text-green-400">This review has been completed.</p>
                </div>
              )}
            </TabsContent>

            {/* History Tab */}
            <TabsContent value="history" className="space-y-4 mt-6">
              {archivedConversations.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-[30vh] text-center">
                  <History className="w-12 h-12 text-gray-600 mb-4" />
                  <h3 className="text-xl font-semibold mb-2">No History</h3>
                  <p className="text-gray-400">No archived reviews for this employee.</p>
                </div>
              ) : (
                archivedConversations.map((item) => (
                  <Card 
                    key={item.id} 
                    className="bg-[#121212] border-white/5 hover:border-white/10 cursor-pointer transition-colors"
                    onClick={() => viewArchivedConversation(item.id)}
                    data-testid={`archived-${item.id}`}
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
  }

  // List view
  return (
    <Layout>
      <div className="max-w-6xl mx-auto space-y-6" data-testid="manager-dashboard">
        {/* Header */}
        <div>
          <h1 className="text-2xl md:text-3xl font-bold tracking-tight">Team Reviews</h1>
          <p className="text-gray-400 mt-1">
            {cycle ? cycle.name : 'No active cycle'} • {reports.length} direct reports
          </p>
        </div>

        {/* Help Text Card */}
        <Card className="bg-blue-500/5 border border-blue-500/20">
          <CardContent className="p-4 flex gap-3">
            <Info className="w-5 h-5 text-blue-400 flex-shrink-0 mt-0.5" />
            <div className="text-sm text-gray-300">
              <p className="font-semibold text-blue-400 mb-1">What You Can See</p>
              <p>You can only see your team members' conversations after they submit them. Drafts are private to the employee while they're working on them. Once a team member clicks "Submit to Manager", you'll be notified and can review their responses.</p>
            </div>
          </CardContent>
        </Card>

        {/* Stats cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {['not_started', 'in_progress', 'ready_for_manager', 'completed'].map((status) => {
            const count = reports.filter(r => (r.conversation_status || 'not_started') === status).length;
            return (
              <Card key={status} className="bg-[#121212] border-white/5">
                <CardContent className="pt-4">
                  <div className={`text-2xl font-bold ${STATUS_COLORS[status].split(' ')[1]}`}>{count}</div>
                  <div className="text-sm text-gray-400">{STATUS_LABELS[status]}</div>
                </CardContent>
              </Card>
            );
          })}
        </div>

        {/* Reports table */}
        <Card className="bg-[#121212] border-white/5">
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Users className="w-5 h-5 text-[#007AFF]" />
              Direct Reports
            </CardTitle>
          </CardHeader>
          <CardContent>
            {reports.length === 0 ? (
              <div className="text-center py-8">
                <Users className="w-12 h-12 text-gray-600 mx-auto mb-3" />
                <p className="text-gray-400">No direct reports found</p>
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow className="border-white/10 hover:bg-transparent">
                    <TableHead className="text-gray-400">Employee</TableHead>
                    <TableHead className="text-gray-400">Department</TableHead>
                    <TableHead className="text-gray-400">Status</TableHead>
                    <TableHead className="text-gray-400 text-right">Action</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {reports.map((report) => (
                    <TableRow 
                      key={report.email} 
                      className="border-white/10 hover:bg-white/5 cursor-pointer"
                      onClick={() => navigate(`/manager/review/${report.email}`)}
                      data-testid={`report-row-${report.email}`}
                    >
                      <TableCell>
                        <div>
                          <div className="font-medium">{report.name || 'Unnamed'}</div>
                          <div className="text-sm text-gray-500">{report.email}</div>
                        </div>
                      </TableCell>
                      <TableCell className="text-gray-400">{report.department || '-'}</TableCell>
                      <TableCell>
                        <Badge className={`${STATUS_COLORS[report.conversation_status || 'not_started']} border`}>
                          {STATUS_LABELS[report.conversation_status || 'not_started']}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right">
                        <Button 
                          variant="ghost" 
                          size="sm"
                          className="hover:bg-white/10"
                          data-testid={`review-btn-${report.email}`}
                        >
                          Review <ChevronRight className="w-4 h-4 ml-1" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      </div>
    </Layout>
  );
};

export default ManagerDashboard;
