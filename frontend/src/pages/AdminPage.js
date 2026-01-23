import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '../contexts/AuthContext';
import Layout from '../components/Layout';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/table';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogFooter,
} from '../components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import { Calendar } from '../components/ui/calendar';
import { Popover, PopoverContent, PopoverTrigger } from '../components/ui/popover';
import { Loader2, Users, Calendar as CalendarIcon, Upload, Plus, Play, Archive, FileText, Settings } from 'lucide-react';
import { toast } from 'sonner';
import { format } from 'date-fns';

const STATUS_COLORS = {
  draft: 'bg-gray-500/10 text-gray-400 border-gray-500/20',
  active: 'bg-green-500/10 text-green-400 border-green-500/20',
  archived: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20',
};

const AdminPage = () => {
  const { axiosInstance } = useAuth();
  const [users, setUsers] = useState([]);
  const [cycles, setCycles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [importDialogOpen, setImportDialogOpen] = useState(false);
  const [cycleDialogOpen, setCycleDialogOpen] = useState(false);
  const [importing, setImporting] = useState(false);
  const [creatingCycle, setCreatingCycle] = useState(false);
  const fileInputRef = useRef(null);
  
  // Import form state
  const [importMethod, setImportMethod] = useState('json');
  const [jsonInput, setJsonInput] = useState('');
  
  // Cycle form state
  const [cycleName, setCycleName] = useState('');
  const [cycleStartDate, setCycleStartDate] = useState(null);
  const [cycleEndDate, setCycleEndDate] = useState(null);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [usersRes, cyclesRes] = await Promise.all([
        axiosInstance.get('/admin/users'),
        axiosInstance.get('/admin/cycles'),
      ]);
      setUsers(usersRes.data);
      setCycles(cyclesRes.data);
    } catch (error) {
      toast.error('Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  const handleJsonImport = async () => {
    if (!jsonInput.trim()) {
      toast.error('Please enter JSON data');
      return;
    }

    setImporting(true);
    try {
      const data = JSON.parse(jsonInput);
      const usersArray = Array.isArray(data) ? data : [data];
      
      const response = await axiosInstance.post('/admin/users/import', usersArray);
      toast.success(response.data.message);
      setImportDialogOpen(false);
      setJsonInput('');
      fetchData();
    } catch (error) {
      if (error instanceof SyntaxError) {
        toast.error('Invalid JSON format');
      } else {
        toast.error(error.response?.data?.detail || 'Import failed');
      }
    } finally {
      setImporting(false);
    }
  };

  const handleCsvImport = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setImporting(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      
      const response = await axiosInstance.post('/admin/users/import/csv', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      toast.success(response.data.message);
      setImportDialogOpen(false);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'CSV import failed');
    } finally {
      setImporting(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleCreateCycle = async () => {
    if (!cycleName || !cycleStartDate || !cycleEndDate) {
      toast.error('Please fill all fields');
      return;
    }

    setCreatingCycle(true);
    try {
      await axiosInstance.post('/admin/cycles', {
        name: cycleName,
        start_date: cycleStartDate.toISOString(),
        end_date: cycleEndDate.toISOString(),
        status: 'draft',
      });
      toast.success('Cycle created');
      setCycleDialogOpen(false);
      setCycleName('');
      setCycleStartDate(null);
      setCycleEndDate(null);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create cycle');
    } finally {
      setCreatingCycle(false);
    }
  };

  const handleCycleStatusChange = async (cycleId, newStatus) => {
    try {
      await axiosInstance.patch(`/admin/cycles/${cycleId}?status=${newStatus}`);
      toast.success(`Cycle ${newStatus === 'active' ? 'activated' : 'archived'}`);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to update cycle');
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

  const sampleJson = `[
  {
    "employee_email": "john@company.com",
    "employee_name": "John Doe",
    "manager_email": "manager@company.com",
    "department": "Engineering",
    "is_admin": false
  }
]`;

  return (
    <Layout>
      <div className="max-w-6xl mx-auto space-y-6" data-testid="admin-dashboard">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl md:text-3xl font-bold tracking-tight">Admin Dashboard</h1>
            <p className="text-gray-400 mt-1">Manage users, cycles, and system settings</p>
          </div>
        </div>

        <Tabs defaultValue="users" className="space-y-6">
          <TabsList className="bg-[#1E1E1E] border border-white/10">
            <TabsTrigger value="users" className="data-[state=active]:bg-[#007AFF]" data-testid="users-tab">
              <Users className="w-4 h-4 mr-2" />
              Users
            </TabsTrigger>
            <TabsTrigger value="cycles" className="data-[state=active]:bg-[#007AFF]" data-testid="cycles-tab">
              <CalendarIcon className="w-4 h-4 mr-2" />
              Cycles
            </TabsTrigger>
          </TabsList>

          {/* Users Tab */}
          <TabsContent value="users" className="space-y-4">
            <div className="flex justify-between items-center">
              <p className="text-gray-400">{users.length} users in system</p>
              <Dialog open={importDialogOpen} onOpenChange={setImportDialogOpen}>
                <DialogTrigger asChild>
                  <Button className="bg-[#007AFF] hover:bg-[#007AFF]/90" data-testid="import-users-btn">
                    <Upload className="w-4 h-4 mr-2" />
                    Import Users
                  </Button>
                </DialogTrigger>
                <DialogContent className="bg-[#121212] border-white/10 max-w-2xl">
                  <DialogHeader>
                    <DialogTitle>Import Users</DialogTitle>
                    <DialogDescription>
                      Import users from CSV or JSON format
                    </DialogDescription>
                  </DialogHeader>
                  
                  <Tabs value={importMethod} onValueChange={setImportMethod} className="mt-4">
                    <TabsList className="bg-[#1E1E1E] border border-white/10">
                      <TabsTrigger value="json" data-testid="json-import-tab">JSON</TabsTrigger>
                      <TabsTrigger value="csv" data-testid="csv-import-tab">CSV</TabsTrigger>
                    </TabsList>
                    
                    <TabsContent value="json" className="space-y-4 mt-4">
                      <div className="space-y-2">
                        <Label>JSON Data</Label>
                        <Textarea
                          value={jsonInput}
                          onChange={(e) => setJsonInput(e.target.value)}
                          placeholder={sampleJson}
                          className="min-h-[200px] font-mono text-sm bg-[#1E1E1E] border-white/10"
                          data-testid="json-input"
                        />
                        <p className="text-xs text-gray-500">
                          Required fields: employee_email. Optional: employee_name, manager_email, department, is_admin
                        </p>
                      </div>
                      <Button 
                        onClick={handleJsonImport} 
                        disabled={importing}
                        className="w-full bg-[#007AFF] hover:bg-[#007AFF]/90"
                        data-testid="import-json-btn"
                      >
                        {importing ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
                        Import JSON
                      </Button>
                    </TabsContent>
                    
                    <TabsContent value="csv" className="space-y-4 mt-4">
                      <div className="space-y-2">
                        <Label>CSV File</Label>
                        <div className="border-2 border-dashed border-white/10 rounded-lg p-8 text-center">
                          <input
                            ref={fileInputRef}
                            type="file"
                            accept=".csv"
                            onChange={handleCsvImport}
                            className="hidden"
                            id="csv-upload"
                            data-testid="csv-input"
                          />
                          <label htmlFor="csv-upload" className="cursor-pointer">
                            <Upload className="w-8 h-8 mx-auto text-gray-500 mb-2" />
                            <p className="text-gray-400">Click to upload CSV file</p>
                            <p className="text-xs text-gray-500 mt-1">
                              Headers: employee_email, employee_name, manager_email, department, is_admin
                            </p>
                          </label>
                        </div>
                        {importing && (
                          <div className="flex items-center justify-center gap-2 text-gray-400">
                            <Loader2 className="w-4 h-4 animate-spin" />
                            Importing...
                          </div>
                        )}
                      </div>
                    </TabsContent>
                  </Tabs>
                </DialogContent>
              </Dialog>
            </div>

            <Card className="bg-[#121212] border-white/5">
              <CardContent className="p-0">
                <Table>
                  <TableHeader>
                    <TableRow className="border-white/10 hover:bg-transparent">
                      <TableHead className="text-gray-400">Name</TableHead>
                      <TableHead className="text-gray-400">Email</TableHead>
                      <TableHead className="text-gray-400">Department</TableHead>
                      <TableHead className="text-gray-400">Manager</TableHead>
                      <TableHead className="text-gray-400">Roles</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {users.map((user) => (
                      <TableRow key={user.email} className="border-white/10 hover:bg-white/5" data-testid={`user-row-${user.email}`}>
                        <TableCell className="font-medium">{user.name || '-'}</TableCell>
                        <TableCell className="font-mono text-sm">{user.email}</TableCell>
                        <TableCell className="text-gray-400">{user.department || '-'}</TableCell>
                        <TableCell className="text-gray-400 text-sm">{user.manager_email || '-'}</TableCell>
                        <TableCell>
                          <div className="flex gap-1 flex-wrap">
                            {user.roles?.map((role) => (
                              <Badge 
                                key={role} 
                                variant="outline" 
                                className={
                                  role === 'admin' 
                                    ? 'border-red-500/30 text-red-400' 
                                    : role === 'manager'
                                    ? 'border-blue-500/30 text-blue-400'
                                    : 'border-gray-500/30 text-gray-400'
                                }
                              >
                                {role}
                              </Badge>
                            ))}
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Cycles Tab */}
          <TabsContent value="cycles" className="space-y-4">
            <div className="flex justify-between items-center">
              <p className="text-gray-400">{cycles.length} performance cycles</p>
              <Dialog open={cycleDialogOpen} onOpenChange={setCycleDialogOpen}>
                <DialogTrigger asChild>
                  <Button className="bg-[#007AFF] hover:bg-[#007AFF]/90" data-testid="create-cycle-btn">
                    <Plus className="w-4 h-4 mr-2" />
                    New Cycle
                  </Button>
                </DialogTrigger>
                <DialogContent className="bg-[#121212] border-white/10">
                  <DialogHeader>
                    <DialogTitle>Create Performance Cycle</DialogTitle>
                    <DialogDescription>
                      Create a new performance review cycle
                    </DialogDescription>
                  </DialogHeader>
                  
                  <div className="space-y-4 mt-4">
                    <div className="space-y-2">
                      <Label>Cycle Name</Label>
                      <Input
                        value={cycleName}
                        onChange={(e) => setCycleName(e.target.value)}
                        placeholder="e.g., 2025 Annual Review"
                        className="bg-[#1E1E1E] border-white/10"
                        data-testid="cycle-name-input"
                      />
                    </div>
                    
                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label>Start Date</Label>
                        <Popover>
                          <PopoverTrigger asChild>
                            <Button
                              variant="outline"
                              className="w-full justify-start text-left font-normal bg-[#1E1E1E] border-white/10"
                              data-testid="start-date-btn"
                            >
                              <CalendarIcon className="mr-2 h-4 w-4" />
                              {cycleStartDate ? format(cycleStartDate, 'PPP') : 'Pick a date'}
                            </Button>
                          </PopoverTrigger>
                          <PopoverContent className="w-auto p-0 bg-[#1E1E1E] border-white/10" align="start">
                            <Calendar
                              mode="single"
                              selected={cycleStartDate}
                              onSelect={setCycleStartDate}
                              initialFocus
                            />
                          </PopoverContent>
                        </Popover>
                      </div>
                      
                      <div className="space-y-2">
                        <Label>End Date</Label>
                        <Popover>
                          <PopoverTrigger asChild>
                            <Button
                              variant="outline"
                              className="w-full justify-start text-left font-normal bg-[#1E1E1E] border-white/10"
                              data-testid="end-date-btn"
                            >
                              <CalendarIcon className="mr-2 h-4 w-4" />
                              {cycleEndDate ? format(cycleEndDate, 'PPP') : 'Pick a date'}
                            </Button>
                          </PopoverTrigger>
                          <PopoverContent className="w-auto p-0 bg-[#1E1E1E] border-white/10" align="start">
                            <Calendar
                              mode="single"
                              selected={cycleEndDate}
                              onSelect={setCycleEndDate}
                              initialFocus
                            />
                          </PopoverContent>
                        </Popover>
                      </div>
                    </div>
                  </div>
                  
                  <DialogFooter className="mt-6">
                    <Button
                      onClick={handleCreateCycle}
                      disabled={creatingCycle}
                      className="bg-[#007AFF] hover:bg-[#007AFF]/90"
                      data-testid="submit-cycle-btn"
                    >
                      {creatingCycle ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
                      Create Cycle
                    </Button>
                  </DialogFooter>
                </DialogContent>
              </Dialog>
            </div>

            <div className="grid gap-4">
              {cycles.length === 0 ? (
                <Card className="bg-[#121212] border-white/5">
                  <CardContent className="py-12 text-center">
                    <CalendarIcon className="w-12 h-12 mx-auto text-gray-600 mb-3" />
                    <p className="text-gray-400">No performance cycles yet</p>
                    <p className="text-sm text-gray-500">Create your first cycle to get started</p>
                  </CardContent>
                </Card>
              ) : (
                cycles.map((cycle) => (
                  <Card key={cycle.id} className="bg-[#121212] border-white/5" data-testid={`cycle-card-${cycle.id}`}>
                    <CardContent className="p-6">
                      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                        <div className="flex-1">
                          <div className="flex items-center gap-3 mb-2">
                            <h3 className="text-lg font-semibold">{cycle.name}</h3>
                            <Badge className={`${STATUS_COLORS[cycle.status]} border`}>
                              {cycle.status}
                            </Badge>
                          </div>
                          <p className="text-sm text-gray-400">
                            {new Date(cycle.start_date).toLocaleDateString()} - {new Date(cycle.end_date).toLocaleDateString()}
                          </p>
                        </div>
                        <div className="flex gap-2">
                          {cycle.status === 'draft' && (
                            <Button
                              size="sm"
                              onClick={() => handleCycleStatusChange(cycle.id, 'active')}
                              className="bg-green-600 hover:bg-green-700"
                              data-testid={`activate-cycle-${cycle.id}`}
                            >
                              <Play className="w-4 h-4 mr-1" />
                              Activate
                            </Button>
                          )}
                          {cycle.status === 'active' && (
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => handleCycleStatusChange(cycle.id, 'archived')}
                              className="border-yellow-500/30 text-yellow-400 hover:bg-yellow-500/10"
                              data-testid={`archive-cycle-${cycle.id}`}
                            >
                              <Archive className="w-4 h-4 mr-1" />
                              Archive
                            </Button>
                          )}
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))
              )}
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </Layout>
  );
};

export default AdminPage;
