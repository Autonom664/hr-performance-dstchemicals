import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate, useParams } from 'react-router-dom';
import Layout from '../components/Layout';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/table';
import { Loader2, Users, ChevronRight, FileText, Calendar, Star, Save, CheckCircle, Download, ArrowLeft } from 'lucide-react';
import { toast } from 'sonner';
import ReactQuill from 'react-quill';
import 'react-quill/dist/quill.snow.css';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import { Label } from '../components/ui/label';

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
  
  // Form state
  const [managerReview, setManagerReview] = useState('');
  const [ratings, setRatings] = useState({
    performance: '',
    collaboration: '',
    growth: '',
  });

  useEffect(() => {
    fetchReports();
    fetchCycle();
  }, []);

  useEffect(() => {
    if (employeeEmail) {
      fetchConversation(employeeEmail);
    } else {
      setSelectedEmployee(null);
      setConversation(null);
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
      setManagerReview(response.data.conversation?.manager_review || '');
      setRatings({
        performance: response.data.conversation?.ratings?.performance?.toString() || '',
        collaboration: response.data.conversation?.ratings?.collaboration?.toString() || '',
        growth: response.data.conversation?.ratings?.growth?.toString() || '',
      });
    } catch (error) {
      toast.error('Failed to load conversation');
      navigate('/manager');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async (complete = false) => {
    setSaving(true);
    try {
      const payload = {
        manager_review: managerReview,
        ratings: {
          performance: ratings.performance ? parseInt(ratings.performance) : null,
          collaboration: ratings.collaboration ? parseInt(ratings.collaboration) : null,
          growth: ratings.growth ? parseInt(ratings.growth) : null,
        },
      };
      
      if (complete) {
        payload.status = 'completed';
      }
      
      const response = await axiosInstance.put(`/manager/conversations/${employeeEmail}`, payload);
      setConversation(response.data);
      toast.success(complete ? 'Review completed!' : 'Review saved');
      
      if (complete) {
        navigate('/manager');
      }
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

  const quillModules = {
    toolbar: [
      ['bold', 'italic', 'underline'],
      [{ 'list': 'ordered'}, { 'list': 'bullet' }],
      ['clean']
    ],
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

  // Detail view
  if (employeeEmail && selectedEmployee) {
    const isCompleted = conversation?.status === 'completed';
    
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
            <div className="flex items-center gap-3">
              <Badge className={`${STATUS_COLORS[conversation?.status || 'not_started']} px-3 py-1 border`}>
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

          {/* Employee's Self Review */}
          <Card className="bg-[#121212] border-white/5">
            <CardHeader className="pb-3">
              <CardTitle className="text-lg flex items-center gap-2">
                <FileText className="w-5 h-5 text-[#00FF94]" />
                Employee's Self Review
              </CardTitle>
            </CardHeader>
            <CardContent>
              {conversation?.employee_self_review ? (
                <div 
                  className="prose prose-invert prose-sm max-w-none"
                  dangerouslySetInnerHTML={{ __html: conversation.employee_self_review }}
                />
              ) : (
                <p className="text-gray-500 italic">No self review submitted yet.</p>
              )}
            </CardContent>
          </Card>

          {/* Employee's Goals */}
          <Card className="bg-[#121212] border-white/5">
            <CardHeader className="pb-3">
              <CardTitle className="text-lg flex items-center gap-2">
                <FileText className="w-5 h-5 text-[#007AFF]" />
                Employee's Goals
              </CardTitle>
            </CardHeader>
            <CardContent>
              {conversation?.goals_next_period ? (
                <div 
                  className="prose prose-invert prose-sm max-w-none"
                  dangerouslySetInnerHTML={{ __html: conversation.goals_next_period }}
                />
              ) : (
                <p className="text-gray-500 italic">No goals submitted yet.</p>
              )}
            </CardContent>
          </Card>

          {/* Manager Review Form */}
          <Card className="bg-[#121212] border-white/5">
            <CardHeader className="pb-3">
              <CardTitle className="text-lg flex items-center gap-2">
                <Star className="w-5 h-5 text-yellow-400" />
                Your Feedback
              </CardTitle>
              <CardDescription>
                Provide constructive feedback and ratings for this employee
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <ReactQuill
                theme="snow"
                value={managerReview}
                onChange={setManagerReview}
                modules={quillModules}
                placeholder="Write your feedback here... Include strengths, areas for improvement, and recommendations."
                readOnly={isCompleted}
                data-testid="manager-review-editor"
              />

              {/* Ratings */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-4 border-t border-white/10">
                <div className="space-y-2">
                  <Label className="text-sm text-gray-400">Performance Rating</Label>
                  <Select
                    value={ratings.performance}
                    onValueChange={(v) => setRatings({ ...ratings, performance: v })}
                    disabled={isCompleted}
                  >
                    <SelectTrigger className="bg-[#1E1E1E] border-white/10" data-testid="performance-rating-select">
                      <SelectValue placeholder="Select rating" />
                    </SelectTrigger>
                    <SelectContent className="bg-[#1E1E1E] border-white/10">
                      {[1, 2, 3, 4, 5].map((n) => (
                        <SelectItem key={n} value={n.toString()}>{n} - {['Poor', 'Below Average', 'Average', 'Good', 'Excellent'][n-1]}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label className="text-sm text-gray-400">Collaboration Rating</Label>
                  <Select
                    value={ratings.collaboration}
                    onValueChange={(v) => setRatings({ ...ratings, collaboration: v })}
                    disabled={isCompleted}
                  >
                    <SelectTrigger className="bg-[#1E1E1E] border-white/10" data-testid="collaboration-rating-select">
                      <SelectValue placeholder="Select rating" />
                    </SelectTrigger>
                    <SelectContent className="bg-[#1E1E1E] border-white/10">
                      {[1, 2, 3, 4, 5].map((n) => (
                        <SelectItem key={n} value={n.toString()}>{n} - {['Poor', 'Below Average', 'Average', 'Good', 'Excellent'][n-1]}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label className="text-sm text-gray-400">Growth Rating</Label>
                  <Select
                    value={ratings.growth}
                    onValueChange={(v) => setRatings({ ...ratings, growth: v })}
                    disabled={isCompleted}
                  >
                    <SelectTrigger className="bg-[#1E1E1E] border-white/10" data-testid="growth-rating-select">
                      <SelectValue placeholder="Select rating" />
                    </SelectTrigger>
                    <SelectContent className="bg-[#1E1E1E] border-white/10">
                      {[1, 2, 3, 4, 5].map((n) => (
                        <SelectItem key={n} value={n.toString()}>{n} - {['Poor', 'Below Average', 'Average', 'Good', 'Excellent'][n-1]}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
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
                data-testid="save-review-btn"
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
