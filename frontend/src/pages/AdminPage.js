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
import { Checkbox } from '../components/ui/checkbox';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogFooter,
} from '../components/ui/dialog';
import { Calendar } from '../components/ui/calendar';
import { Popover, PopoverContent, PopoverTrigger } from '../components/ui/popover';
import { Loader2, Users, Calendar as CalendarIcon, Upload, Plus, Play, Archive, Download, KeyRound, AlertTriangle, FileText, Trash2, Edit2, Code, Copy, CheckCircle2 } from 'lucide-react';
import { toast } from 'sonner';
import { format } from 'date-fns';

const STATUS_COLORS = {
  draft: 'bg-gray-500/10 text-gray-400 border-gray-500/20',
  active: 'bg-green-500/10 text-green-400 border-green-500/20',
  archived: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20',
};

const ENTRA_EXPORT_SCRIPT = `<#
.SYNOPSIS
  Export employees from Entra ID to JSON, ONLY including members of the distribution group:
    dstchemicals@dstchemicals.com  (DSTChemicalsGroup)

  Output format:
  [
    {
      "employee_email": "...",
      "employee_name": "...",
      "manager_email": "...",
      "department": "...",
      "is_admin": true/false
    }
  ]

.VERSION
  1.1.1 (2026-01-27)

.NOTES
  Admin membership is determined by membership in AdminGroupDisplayName (default: Group_HRsystemAdmins)

#>

[CmdletBinding()]
param(
  [string]$OutFile = ".\\employees.json",

  # Admin group (members => is_admin=true)
  [string]$AdminGroupDisplayName = "Group_HRsystemAdmins",
  [string]$AdminGroupId = "",

  # "Real users" must be members of this mail-enabled group
  [string]$CompanyGroupMail = "dstchemicals@dstchemicals.com",
  [string]$CompanyGroupDisplayName = "DSTChemicalsGroup",

  # Optional domain filter (extra safety)
  [string]$EmailDomainFilter = "dstchemicals.com"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Info([string]$m) { Write-Host ("[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $m) }

function Retry([scriptblock]$sb, [int]$Max=6) {
  $a=0
  while ($true) {
    try { return & $sb }
    catch {
      $a++
      $msg = $_.Exception.Message
      $th = $msg -match "Too Many Requests|throttl|429"
      $tr = $msg -match "temporarily|timeout|503|Service Unavailable|gateway"
      if ($a -ge $Max -or (-not ($th -or $tr))) { throw }
      $s = [Math]::Min(60, [Math]::Pow(2,$a) + (Get-Random -Minimum 0 -Maximum 3))
      Info "Transient/Throttle. Retry $a/$Max in $s sec..."
      Start-Sleep -Seconds $s
    }
  }
}

function ConnectGraph {
  # Safe import order (Authentication first)
  Import-Module Microsoft.Graph.Authentication -Force -ErrorAction Stop | Out-Null
  Import-Module Microsoft.Graph.Users -Force -ErrorAction Stop | Out-Null
  Import-Module Microsoft.Graph.Groups -Force -ErrorAction Stop | Out-Null

  Info "Export-EntraEmployees.ps1 v1.1.1 starting..."
  Info "Connecting to Microsoft Graph (interactive)..."
  $scopes = @("User.Read.All","Group.Read.All","Directory.Read.All")
  Connect-MgGraph -Scopes $scopes -NoWelcome | Out-Null

  $ctx = Get-MgContext
  Info ("Connected. Tenant: {0}, Account: {1}" -f $ctx.TenantId, ($ctx.Account ?? "<unknown>"))
}

function GetGroupIdByMailOrName([string]$mail, [string]$name) {
  if (-not [string]::IsNullOrWhiteSpace($mail)) {
    $safeMail = $mail.Replace("'","''")
    Info "Resolving group by mail: $mail"
    $g = Retry { Get-MgGroup -Filter "mail eq '$safeMail'" -Property "id,displayName,mail" } | Select-Object -First 1
    if ($g) { Info ("Group found: {0} ({1})" -f $g.DisplayName, $g.Id); return $g.Id }
  }

  if (-not [string]::IsNullOrWhiteSpace($name)) {
    $safeName = $name.Replace("'","''")
    Info "Resolving group by displayName: $name"
    $g = Retry { Get-MgGroup -Filter "displayName eq '$safeName'" -Property "id,displayName,mail" } | Select-Object -First 1
    if ($g) { Info ("Group found: {0} ({1})" -f $g.DisplayName, $g.Id); return $g.Id }
  }

  return $null
}

function GetUserIdsFromGroup([string]$groupId) {
  $set = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
  if ([string]::IsNullOrWhiteSpace($groupId)) { return $set }

  Info "Fetching members of groupId $groupId ..."
  $members = Retry { Get-MgGroupMember -GroupId $groupId -All }

  foreach ($m in $members) {
    if ($m.AdditionalProperties["@odata.type"] -eq "#microsoft.graph.user") {
      $null = $set.Add([string]$m.Id)
    }
  }

  Info ("User members in group: {0}" -f $set.Count)
  return $set
}

function GetUsersByAllowedIdSet([System.Collections.Generic.HashSet[string]]$allowedIds) {
  Info "Fetching users and filtering to allowed IDs..."
  $all = Retry { Get-MgUser -All -Property "id,displayName,mail,userPrincipalName,department,accountEnabled" }

  $list = @(
    foreach ($u in $all) {
      if ($u.AccountEnabled -ne $true) { continue }
      if (-not $allowedIds.Contains($u.Id)) { continue }

      $email = $u.Mail
      if ([string]::IsNullOrWhiteSpace($email)) { $email = $u.UserPrincipalName }
      if ([string]::IsNullOrWhiteSpace($email)) { continue }

      if (-not [string]::IsNullOrWhiteSpace($EmailDomainFilter)) {
        if (-not $email.ToLowerInvariant().EndsWith("@$($EmailDomainFilter.ToLowerInvariant())")) { continue }
      }

      [pscustomobject]@{
        Id          = $u.Id
        DisplayName = $u.DisplayName
        Email       = $email
        Department  = $u.Department
      }
    }
  )

  Info ("Users selected for export: {0}" -f $list.Count)
  return $list
}

function GetManagerEmailMap([object[]]$users) {
  Info "Building manager_email map..."
  $map = @{}
  $i=0

  foreach ($u in $users) {
    $i++
    if ($i % 50 -eq 0) { Info ("Manager lookup progress: {0}/{1}" -f $i, $users.Count) }

    $mgrEmail = $null
    try {
      $mgr = Retry { Get-MgUserManager -UserId $u.Id -ErrorAction Stop }
      if ($mgr -and $mgr.Id) {
        $mgrUser = Retry { Get-MgUser -UserId $mgr.Id -Property "mail,userPrincipalName" }
        $mgrEmail = $mgrUser.Mail
        if ([string]::IsNullOrWhiteSpace($mgrEmail)) { $mgrEmail = $mgrUser.UserPrincipalName }
      }
    } catch { $mgrEmail = $null }

    $map[$u.Id] = $mgrEmail
  }

  Info "Manager map complete."
  return $map
}

# -------- MAIN --------
ConnectGraph

# 1) Resolve company group and get "real user" ids
$companyGroupId = GetGroupIdByMailOrName -mail $CompanyGroupMail -name $CompanyGroupDisplayName
if (-not $companyGroupId) {
  throw "Could not find company group by mail '$CompanyGroupMail' or name '$CompanyGroupDisplayName'."
}
$realUserIds = GetUserIdsFromGroup -groupId $companyGroupId

# 2) Resolve admin group (optional)
$adminGroupId = $null
if (-not [string]::IsNullOrWhiteSpace($AdminGroupId)) {
  $adminGroupId = $AdminGroupId
  Info "Using AdminGroupId override: $adminGroupId"
} else {
  $adminGroupId = GetGroupIdByMailOrName -mail "" -name $AdminGroupDisplayName
  if (-not $adminGroupId) { Info "WARNING: Admin group '$AdminGroupDisplayName' not found. is_admin will be FALSE for all users." }
}
$adminIds = GetUserIdsFromGroup -groupId $adminGroupId

# 3) Pull user details ONLY for real users
$users = GetUsersByAllowedIdSet -allowedIds $realUserIds
$mgrMap = GetManagerEmailMap -users $users

# 4) Transform to JSON schema
Info "Transforming to required JSON schema..."
$out = @(
  foreach ($u in $users) {
    [pscustomobject]@{
      employee_email = $u.Email
      employee_name  = $u.DisplayName
      manager_email  = $mgrMap[$u.Id]
      department     = $u.Department
      is_admin       = $adminIds.Contains($u.Id)
    }
  }
) | Sort-Object employee_email

$out | ConvertTo-Json -Depth 4 | Out-File -FilePath $OutFile -Encoding utf8
Info ("Done. Wrote {0} employees to {1}" -f $out.Count, (Resolve-Path $OutFile))
Info "Sample (first 3):"
$out | Select-Object -First 3 | ConvertTo-Json -Depth 4 | Write-Host
`;

const AdminPage = () => {
  const { axiosInstance } = useAuth();
  const [users, setUsers] = useState([]);
  const [cycles, setCycles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [importDialogOpen, setImportDialogOpen] = useState(false);
  const [cycleDialogOpen, setCycleDialogOpen] = useState(false);
  const [resetPasswordDialogOpen, setResetPasswordDialogOpen] = useState(false);
  const [singleUserResetDialogOpen, setSingleUserResetDialogOpen] = useState(false);
  const [singleUserResetEmail, setSingleUserResetEmail] = useState(null);
  const [singleUserResetPassword, setSingleUserResetPassword] = useState(null);
  const [deleteUserDialogOpen, setDeleteUserDialogOpen] = useState(false);
  const [deleteUserEmail, setDeleteUserEmail] = useState(null);
  const [deletingUser, setDeletingUser] = useState(false);
  const [deleteCycleDialogOpen, setDeleteCycleDialogOpen] = useState(false);
  const [deleteCycleId, setDeleteCycleId] = useState(null);
  const [deleteCycleName, setDeleteCycleName] = useState(null);
  const [deletingCycle, setDeletingCycle] = useState(false);
  const [importing, setImporting] = useState(false);
  const [creatingCycle, setCreatingCycle] = useState(false);
  const [resettingPasswords, setResettingPasswords] = useState(false);
  const [resettingSinglePassword, setResettingSinglePassword] = useState(false);
  const [createUserDialogOpen, setCreateUserDialogOpen] = useState(false);
  const [editUserDialogOpen, setEditUserDialogOpen] = useState(false);
  const [editingUser, setEditingUser] = useState(null);
  const [creatingUser, setCreatingUser] = useState(false);
  const [editingUserData, setEditingUserData] = useState(false);
  const [newUserPassword, setNewUserPassword] = useState(null);
  const [copiedCommand, setCopiedCommand] = useState(false);
  const fileInputRef = useRef(null);
  
  // Import form state
  const [importMethod, setImportMethod] = useState('json');
  const [jsonInput, setJsonInput] = useState('');
  const [lastImportCredentials, setLastImportCredentials] = useState(null);
  
  // Cycle form state
  const [cycleName, setCycleName] = useState('');
  const [cycleStartDate, setCycleStartDate] = useState(null);
  const [cycleEndDate, setCycleEndDate] = useState(null);
  
  // Edit cycle state
  const [editCycleDialogOpen, setEditCycleDialogOpen] = useState(false);
  const [editingCycle, setEditingCycle] = useState(null);
  const [editingCycleData, setEditingCycleData] = useState(false);
  const [editCycleForm, setEditCycleForm] = useState({
    name: '',
    start_date: null,
    end_date: null,
  });
  
  // User form state (for create and edit)
  const [userForm, setUserForm] = useState({
    employee_email: '',
    employee_name: '',
    department: '',
    manager_email: '',
    is_admin: false,
  });
  
  // Password reset state
  const [selectedUsersForReset, setSelectedUsersForReset] = useState([]);
  const [lastResetCredentials, setLastResetCredentials] = useState(null);

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
      
      // Store credentials for download if new users were created
      if (response.data.credentials_csv) {
        setLastImportCredentials(response.data.credentials_csv);
      }
      
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
      
      // Store credentials for download if new users were created
      if (response.data.credentials_csv) {
        setLastImportCredentials(response.data.credentials_csv);
      }
      
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'CSV import failed');
    } finally {
      setImporting(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const downloadCredentialsCsv = (csvContent, filename) => {
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const handleDownloadImportCredentials = () => {
    if (lastImportCredentials) {
      downloadCredentialsCsv(lastImportCredentials, `user_credentials_${new Date().toISOString().slice(0,10)}.csv`);
      setLastImportCredentials(null); // Clear after download (one-time)
      setImportDialogOpen(false);
      toast.success('Credentials downloaded. This was a one-time download.');
    }
  };

  const handleResetPasswords = async () => {
    if (selectedUsersForReset.length === 0) {
      toast.error('Please select at least one user');
      return;
    }

    setResettingPasswords(true);
    try {
      const response = await axiosInstance.post('/admin/users/reset-passwords', {
        emails: selectedUsersForReset,
      });
      
      toast.success(response.data.message);
      
      if (response.data.credentials_csv) {
        setLastResetCredentials(response.data.credentials_csv);
      }
      
      setSelectedUsersForReset([]);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Password reset failed');
    } finally {
      setResettingPasswords(false);
    }
  };

  const handleDownloadResetCredentials = () => {
    if (lastResetCredentials) {
      downloadCredentialsCsv(lastResetCredentials, `password_reset_${new Date().toISOString().slice(0,10)}.csv`);
      setLastResetCredentials(null);
      setResetPasswordDialogOpen(false);
      toast.success('Reset credentials downloaded. This was a one-time download.');
    }
  };

  const handleResetSingleUserPassword = async (email) => {
    if (!email) return;
    
    setResettingSinglePassword(true);
    try {
      const response = await axiosInstance.post(`/admin/users/reset-password?email=${encodeURIComponent(email)}`);
      setSingleUserResetEmail(email);
      setSingleUserResetPassword(response.data.one_time_password);
      setSingleUserResetDialogOpen(true);
      toast.success(`Password reset for ${email}`);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Password reset failed');
    } finally {
      setResettingSinglePassword(false);
    }
  };

  const handleDeleteUser = async () => {
    if (!deleteUserEmail) return;
    setDeletingUser(true);
    try {
      const response = await axiosInstance.delete(`/admin/users/${deleteUserEmail}`);
      toast.success(response.data.message);
      setDeleteUserDialogOpen(false);
      setDeleteUserEmail(null);
      await fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to delete user');
    } finally {
      setDeletingUser(false);
    }
  };

  const handleDeleteCycle = async () => {
    if (!deleteCycleId) return;
    setDeletingCycle(true);
    try {
      const response = await axiosInstance.delete(`/admin/cycles/${deleteCycleId}`);
      toast.success(response.data.message);
      setDeleteCycleDialogOpen(false);
      setDeleteCycleId(null);
      setDeleteCycleName(null);
      await fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to delete cycle');
    } finally {
      setDeletingCycle(false);
    }
  };

  const handleCreateUser = async () => {
    if (!userForm.employee_email || !userForm.employee_name) {
      toast.error('Email and name are required');
      return;
    }
    setCreatingUser(true);
    try {
      const response = await axiosInstance.post('/admin/users', userForm);
      setNewUserPassword(response.data.one_time_password);
      toast.success(response.data.message);
      setUserForm({
        employee_email: '',
        employee_name: '',
        department: '',
        manager_email: '',
        is_admin: false,
      });
      await fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create user');
    } finally {
      setCreatingUser(false);
    }
  };

  const handleEditUser = async () => {
    if (!editingUser?.email) return;
    setEditingUserData(true);
    try {
      const response = await axiosInstance.put(`/admin/users/${editingUser.email}`, userForm);
      toast.success(response.data.message);
      setEditUserDialogOpen(false);
      setEditingUser(null);
      setUserForm({
        employee_email: '',
        employee_name: '',
        department: '',
        manager_email: '',
        is_admin: false,
      });
      await fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to edit user');
    } finally {
      setEditingUserData(false);
    }
  };

  const openEditUserDialog = (user) => {
    setEditingUser(user);
    setUserForm({
      employee_email: user.email,
      employee_name: user.name || '',
      department: user.department || '',
      manager_email: user.manager_email || '',
      is_admin: user.roles?.includes('admin') || false,
    });
    setEditUserDialogOpen(true);
  };

  const handleCopyNewPassword = () => {
    if (newUserPassword) {
      navigator.clipboard.writeText(newUserPassword);
      toast.success('Password copied to clipboard');
    }
  };

  const handleCopySinglePassword = () => {
    if (singleUserResetPassword) {
      navigator.clipboard.writeText(singleUserResetPassword);
      toast.success('Password copied to clipboard');
    }
  };

  const toggleUserSelection = (email) => {
    setSelectedUsersForReset(prev => 
      prev.includes(email) 
        ? prev.filter(e => e !== email)
        : [...prev, email]
    );
  };

  const selectAllUsers = () => {
    if (selectedUsersForReset.length === users.length) {
      setSelectedUsersForReset([]);
    } else {
      setSelectedUsersForReset(users.map(u => u.email));
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

  const openEditCycleDialog = (cycle) => {
    setEditingCycle(cycle);
    setEditCycleForm({
      name: cycle.name,
      start_date: new Date(cycle.start_date),
      end_date: new Date(cycle.end_date),
    });
    setEditCycleDialogOpen(true);
  };

  const handleEditCycle = async () => {
    if (!editingCycle?.id || !editCycleForm.name || !editCycleForm.start_date || !editCycleForm.end_date) {
      toast.error('Please fill all fields');
      return;
    }

    setEditingCycleData(true);
    try {
      await axiosInstance.put(`/admin/cycles/${editingCycle.id}`, {
        name: editCycleForm.name,
        start_date: editCycleForm.start_date.toISOString(),
        end_date: editCycleForm.end_date.toISOString(),
      });
      toast.success('Cycle updated successfully');
      setEditCycleDialogOpen(false);
      setEditingCycle(null);
      setEditCycleForm({
        name: '',
        start_date: null,
        end_date: null,
      });
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to edit cycle');
    } finally {
      setEditingCycleData(false);
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
            <p className="text-gray-400 mt-1">Manage users, cycles, and passwords</p>
          </div>
        </div>

        {/* Help Text Card */}
        <Card className="bg-blue-500/5 border border-blue-500/20">
          <CardContent className="p-4 flex gap-3">
            <AlertTriangle className="w-5 h-5 text-blue-400 flex-shrink-0 mt-0.5" />
            <div className="text-sm text-gray-300">
              <p className="font-semibold text-blue-400 mb-1">Important</p>
              <ul className="space-y-1 ml-4 list-disc text-gray-300">
                <li><span className="font-semibold">Reset Password:</span> Generate a one-time password for a user. They must change it on their next login.</li>
                <li><span className="font-semibold">Delete User:</span> Permanently removes user and all their conversation data.</li>
                <li><span className="font-semibold">Delete Cycle:</span> Permanently removes the cycle and all associated conversations.</li>
              </ul>
            </div>
          </CardContent>
        </Card>

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
            <TabsTrigger value="tools" className="data-[state=active]:bg-[#007AFF]" data-testid="tools-tab">
              <Code className="w-4 h-4 mr-2" />
              Tools & Scripts
            </TabsTrigger>
          </TabsList>

          {/* Users Tab */}
          <TabsContent value="users" className="space-y-4">
            <div className="flex flex-wrap justify-between items-center gap-4">
              <p className="text-gray-400">{users.length} users in system</p>
              <div className="flex gap-2">
                {/* New User Dialog */}
                <Dialog open={createUserDialogOpen} onOpenChange={setCreateUserDialogOpen}>
                  <DialogTrigger asChild>
                    <Button className="bg-[#007AFF] hover:bg-[#007AFF]/90" data-testid="new-user-btn">
                      <Plus className="w-4 h-4 mr-2" />
                      New User
                    </Button>
                  </DialogTrigger>
                  <DialogContent className="bg-[#121212] border-white/10">
                    <DialogHeader>
                      <DialogTitle className="flex items-center gap-2">
                        <Plus className="w-5 h-5 text-[#007AFF]" />
                        Create New User
                      </DialogTitle>
                      <DialogDescription>
                        Add a new user to the system. A one-time password will be generated.
                      </DialogDescription>
                    </DialogHeader>

                    {newUserPassword ? (
                      <div className="space-y-4 mt-4">
                        <div className="p-4 rounded-lg bg-green-500/10 border border-green-500/20">
                          <p className="text-green-400 font-medium mb-2">User created successfully!</p>
                          <p className="text-sm text-gray-400">
                            Share the one-time password below with the new user.
                          </p>
                        </div>
                        <div className="space-y-2">
                          <Label>One-Time Password</Label>
                          <div className="flex gap-2">
                            <Input
                              type="text"
                              value={newUserPassword}
                              readOnly
                              className="bg-[#1C1C1E] border-white/10"
                            />
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={handleCopyNewPassword}
                              className="border-white/10 hover:bg-white/5 px-3"
                              data-testid="copy-new-password-btn"
                            >
                              Copy
                            </Button>
                          </div>
                        </div>
                        <Button
                          onClick={() => {
                            setCreateUserDialogOpen(false);
                            setNewUserPassword(null);
                          }}
                          className="w-full bg-[#007AFF] hover:bg-[#007AFF]/90"
                        >
                          Done
                        </Button>
                      </div>
                    ) : (
                      <div className="space-y-4 mt-4">
                        <div>
                          <Label>Email</Label>
                          <Input
                            type="email"
                            placeholder="user@company.com"
                            value={userForm.employee_email}
                            onChange={(e) => setUserForm({...userForm, employee_email: e.target.value})}
                            className="bg-[#1C1C1E] border-white/10 mt-1"
                            data-testid="new-user-email"
                          />
                        </div>
                        <div>
                          <Label>Full Name</Label>
                          <Input
                            placeholder="John Doe"
                            value={userForm.employee_name}
                            onChange={(e) => setUserForm({...userForm, employee_name: e.target.value})}
                            className="bg-[#1C1C1E] border-white/10 mt-1"
                            data-testid="new-user-name"
                          />
                        </div>
                        <div>
                          <Label>Department</Label>
                          <Input
                            placeholder="Engineering"
                            value={userForm.department}
                            onChange={(e) => setUserForm({...userForm, department: e.target.value})}
                            className="bg-[#1C1C1E] border-white/10 mt-1"
                            data-testid="new-user-dept"
                          />
                        </div>
                        <div>
                          <Label>Manager Email (optional)</Label>
                          <Input
                            type="email"
                            placeholder="manager@company.com"
                            value={userForm.manager_email}
                            onChange={(e) => setUserForm({...userForm, manager_email: e.target.value})}
                            className="bg-[#1C1C1E] border-white/10 mt-1"
                            data-testid="new-user-manager"
                          />
                        </div>
                        <div className="flex items-center gap-2">
                          <Checkbox
                            id="new-user-admin"
                            checked={userForm.is_admin}
                            onCheckedChange={(checked) => setUserForm({...userForm, is_admin: checked})}
                          />
                          <Label htmlFor="new-user-admin" className="cursor-pointer">
                            Make this user an admin
                          </Label>
                        </div>
                        <DialogFooter className="mt-6">
                          <Button
                            variant="outline"
                            onClick={() => {
                              setCreateUserDialogOpen(false);
                              setUserForm({
                                employee_email: '',
                                employee_name: '',
                                department: '',
                                manager_email: '',
                                is_admin: false,
                              });
                            }}
                          >
                            Cancel
                          </Button>
                          <Button
                            onClick={handleCreateUser}
                            disabled={creatingUser}
                            className="bg-[#007AFF] hover:bg-[#007AFF]/90"
                            data-testid="submit-new-user-btn"
                          >
                            {creatingUser ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Plus className="w-4 h-4 mr-2" />}
                            Create User
                          </Button>
                        </DialogFooter>
                      </div>
                    )}
                  </DialogContent>
                </Dialog>

                {/* Reset Password Dialog */}
                <Dialog open={resetPasswordDialogOpen} onOpenChange={setResetPasswordDialogOpen}>
                  <DialogTrigger asChild>
                    <Button variant="outline" className="border-yellow-500/30 text-yellow-400 hover:bg-yellow-500/10" data-testid="reset-passwords-btn">
                      <KeyRound className="w-4 h-4 mr-2" />
                      Reset Passwords
                    </Button>
                  </DialogTrigger>
                  <DialogContent className="bg-[#121212] border-white/10 max-w-2xl max-h-[80vh] overflow-y-auto">
                    <DialogHeader>
                      <DialogTitle className="flex items-center gap-2">
                        <KeyRound className="w-5 h-5 text-yellow-400" />
                        Reset User Passwords
                      </DialogTitle>
                      <DialogDescription>
                        Generate new one-time passwords for selected users. Their current passwords will be invalidated immediately.
                      </DialogDescription>
                    </DialogHeader>
                    
                    {lastResetCredentials ? (
                      <div className="space-y-4 mt-4">
                        <div className="p-4 rounded-lg bg-green-500/10 border border-green-500/20">
                          <p className="text-green-400 font-medium mb-2">Passwords reset successfully!</p>
                          <p className="text-sm text-gray-400">
                            Download the CSV file containing the new passwords. This is a ONE-TIME download - 
                            passwords will not be shown again.
                          </p>
                        </div>
                        <Button 
                          onClick={handleDownloadResetCredentials}
                          className="w-full bg-green-600 hover:bg-green-700"
                          data-testid="download-reset-csv-btn"
                        >
                          <Download className="w-4 h-4 mr-2" />
                          Download Password CSV (One-Time)
                        </Button>
                      </div>
                    ) : (
                      <div className="space-y-4 mt-4">
                        <div className="p-4 rounded-lg bg-yellow-500/10 border border-yellow-500/20">
                          <div className="flex items-start gap-2">
                            <AlertTriangle className="w-5 h-5 text-yellow-400 mt-0.5" />
                            <div>
                              <p className="text-yellow-400 font-medium">Security Warning</p>
                              <p className="text-sm text-gray-400 mt-1">
                                Resetting passwords will immediately invalidate existing passwords and log users out. 
                                Users will need to use the new password and must change it on first login.
                              </p>
                            </div>
                          </div>
                        </div>
                        
                        <div className="space-y-2">
                          <div className="flex items-center justify-between">
                            <Label>Select Users ({selectedUsersForReset.length} selected)</Label>
                            <Button variant="ghost" size="sm" onClick={selectAllUsers} className="text-xs">
                              {selectedUsersForReset.length === users.length ? 'Deselect All' : 'Select All'}
                            </Button>
                          </div>
                          <div className="max-h-[300px] overflow-y-auto border border-white/10 rounded-lg divide-y divide-white/10">
                            {users.map((user) => (
                              <div 
                                key={user.email} 
                                className="flex items-center gap-3 p-3 hover:bg-white/5 cursor-pointer"
                                onClick={() => toggleUserSelection(user.email)}
                              >
                                <Checkbox 
                                  checked={selectedUsersForReset.includes(user.email)}
                                  onCheckedChange={() => toggleUserSelection(user.email)}
                                />
                                <div className="flex-1 min-w-0">
                                  <p className="font-medium truncate">{user.name || user.email}</p>
                                  <p className="text-xs text-gray-500 truncate">{user.email}</p>
                                </div>
                                <div className="flex gap-1">
                                  {user.roles?.map((role) => (
                                    <Badge key={role} variant="outline" className="text-xs border-gray-500/30 text-gray-400">
                                      {role}
                                    </Badge>
                                  ))}
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                        
                        <Button 
                          onClick={handleResetPasswords}
                          disabled={resettingPasswords || selectedUsersForReset.length === 0}
                          className="w-full bg-yellow-600 hover:bg-yellow-700"
                          data-testid="confirm-reset-btn"
                        >
                          {resettingPasswords ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <KeyRound className="w-4 h-4 mr-2" />}
                          Reset {selectedUsersForReset.length} Password(s)
                        </Button>
                      </div>
                    )}
                  </DialogContent>
                </Dialog>

                {/* Single User Password Reset Dialog */}
                <Dialog open={singleUserResetDialogOpen} onOpenChange={setSingleUserResetDialogOpen}>
                  <DialogContent className="bg-[#121212] border-white/10 max-w-md">
                    <DialogHeader>
                      <DialogTitle className="flex items-center gap-2">
                        <KeyRound className="w-5 h-5 text-green-400" />
                        Password Reset Successful
                      </DialogTitle>
                    </DialogHeader>
                    
                    <div className="space-y-4 mt-4">
                      <div className="p-4 rounded-lg bg-green-500/10 border border-green-500/20">
                        <p className="text-sm text-gray-400 mb-3">
                          New one-time password generated for:
                        </p>
                        <p className="font-mono text-green-400 font-medium break-all">
                          {singleUserResetEmail}
                        </p>
                      </div>
                      
                      <div className="space-y-2">
                        <Label className="text-gray-400">One-Time Password</Label>
                        <div className="flex gap-2">
                          <div className="flex-1 p-3 rounded-lg bg-[#1E1E1E] border border-white/10 font-mono text-sm break-all">
                            {singleUserResetPassword}
                          </div>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={handleCopySinglePassword}
                            className="border-white/10 hover:bg-white/5 px-3"
                            data-testid="copy-password-btn"
                          >
                            Copy
                          </Button>
                        </div>
                      </div>
                      
                      <div className="p-3 rounded-lg bg-yellow-500/10 border border-yellow-500/20">
                        <p className="text-xs text-yellow-400">
                          <strong>Important:</strong> Share this password with the user. They must change it on their first login. This password will not be shown again.
                        </p>
                      </div>
                      
                      <Button
                        onClick={() => setSingleUserResetDialogOpen(false)}
                        className="w-full bg-green-600 hover:bg-green-700"
                        data-testid="close-single-reset-btn"
                      >
                        Done
                      </Button>
                    </div>
                  </DialogContent>
                </Dialog>

                {/* Import Users Dialog */}
                <Dialog open={importDialogOpen} onOpenChange={(open) => {
                  setImportDialogOpen(open);
                  if (!open) {
                    setLastImportCredentials(null);
                  }
                }}>
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
                        Import users from CSV or JSON format. New users will receive generated passwords.
                      </DialogDescription>
                    </DialogHeader>
                    
                    {lastImportCredentials ? (
                      <div className="space-y-4 mt-4">
                        <div className="p-4 rounded-lg bg-green-500/10 border border-green-500/20">
                          <p className="text-green-400 font-medium mb-2">Users imported successfully!</p>
                          <p className="text-sm text-gray-400">
                            Download the CSV file containing user emails and their one-time passwords. 
                            This is a ONE-TIME download - passwords will not be shown again.
                          </p>
                        </div>
                        <Button 
                          onClick={handleDownloadImportCredentials}
                          className="w-full bg-green-600 hover:bg-green-700"
                          data-testid="download-credentials-btn"
                        >
                          <Download className="w-4 h-4 mr-2" />
                          Download Credentials CSV (One-Time)
                        </Button>
                      </div>
                    ) : (
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
                              Required: employee_email. Optional: employee_name, manager_email, department, is_admin
                            </p>
                          </div>
                          <div className="p-3 rounded-lg bg-blue-500/10 border border-blue-500/20">
                            <p className="text-xs text-blue-400">
                              <strong>Note:</strong> New users will receive randomly generated passwords. 
                              After import, you'll be able to download a CSV with the credentials for mail merge.
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
                          <div className="p-3 rounded-lg bg-blue-500/10 border border-blue-500/20">
                            <p className="text-xs text-blue-400">
                              <strong>Note:</strong> New users will receive randomly generated passwords. 
                              After import, you'll be able to download a CSV with the credentials for mail merge.
                            </p>
                          </div>
                        </TabsContent>
                      </Tabs>
                    )}
                  </DialogContent>
                </Dialog>
              </div>
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
                      <TableHead className="text-gray-400">Status</TableHead>
                      <TableHead className="text-gray-400">Actions</TableHead>
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
                        <TableCell>
                          {user.must_change_password ? (
                            <Badge variant="outline" className="border-yellow-500/30 text-yellow-400">
                              Pending
                            </Badge>
                          ) : (
                            <Badge variant="outline" className="border-green-500/30 text-green-400">
                              Active
                            </Badge>
                          )}
                        </TableCell>
                        <TableCell>
                          <div className="flex gap-2">
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => openEditUserDialog(user)}
                              disabled={editingUserData}
                              className="border-blue-500/30 text-blue-400 hover:bg-blue-500/10"
                              data-testid={`edit-user-btn-${user.email}`}
                              title="Edit user"
                            >
                              <Edit2 className="w-3 h-3" />
                            </Button>
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => handleResetSingleUserPassword(user.email)}
                              disabled={resettingSinglePassword}
                              className="border-yellow-500/30 text-yellow-400 hover:bg-yellow-500/10"
                              data-testid={`reset-password-btn-${user.email}`}
                              title="Reset password"
                            >
                              <KeyRound className="w-3 h-3" />
                            </Button>
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => {
                                setDeleteUserEmail(user.email);
                                setDeleteUserDialogOpen(true);
                              }}
                              disabled={deletingUser}
                              className="border-red-500/30 text-red-400 hover:bg-red-500/10"
                              data-testid={`delete-user-btn-${user.email}`}
                              title="Delete user"
                            >
                              <Trash2 className="w-3 h-3" />
                            </Button>
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
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => openEditCycleDialog(cycle)}
                            disabled={editingCycleData}
                            className="border-blue-500/30 text-blue-400 hover:bg-blue-500/10"
                            data-testid={`edit-cycle-btn-${cycle.id}`}
                            title="Edit cycle"
                          >
                            <Edit2 className="w-3 h-3" />
                          </Button>
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
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => {
                              setDeleteCycleId(cycle.id);
                              setDeleteCycleName(cycle.name);
                              setDeleteCycleDialogOpen(true);
                            }}
                            disabled={deletingCycle}
                            className="border-red-500/30 text-red-400 hover:bg-red-500/10"
                            data-testid={`delete-cycle-${cycle.id}`}
                          >
                            <Trash2 className="w-4 h-4 mr-1" />
                            Delete
                          </Button>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))
              )}
            </div>
          </TabsContent>

          {/* Tools & Scripts Tab */}
          <TabsContent value="tools" className="space-y-4">
            <div className="space-y-4">
              {/* Help Card */}
              <Card className="bg-blue-500/5 border border-blue-500/20">
                <CardContent className="p-4">
                  <div className="flex gap-3">
                    <AlertTriangle className="w-5 h-5 text-blue-400 flex-shrink-0 mt-0.5" />
                    <div className="text-sm text-gray-300">
                      <p className="font-semibold text-blue-400 mb-2">Employee Export Script</p>
                      <p>This PowerShell script exports employees from your Entra ID directory to JSON format for bulk import into the HR system. Run this script periodically to keep employee data synchronized.</p>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Usage Instructions */}
              <Card className="bg-[#121212] border-white/5">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <AlertTriangle className="w-5 h-5 text-yellow-400" />
                    How to Use
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <h4 className="font-semibold text-gray-200 mb-2">Prerequisites:</h4>
                    <ul className="list-disc list-inside space-y-1 text-gray-400 ml-2">
                      <li>PowerShell 7+ or Windows PowerShell</li>
                      <li>Microsoft.Graph PowerShell module installed</li>
                      <li>Permissions to query Entra ID groups</li>
                    </ul>
                  </div>

                  <div>
                    <h4 className="font-semibold text-gray-200 mb-2">Installation:</h4>
                    <div className="bg-[#1E1E1E] border border-white/10 rounded p-3 font-mono text-sm text-gray-300 overflow-x-auto">
                      <code>Install-Module Microsoft.Graph -Repository PSGallery -Scope CurrentUser</code>
                    </div>
                  </div>

                  <div>
                    <h4 className="font-semibold text-gray-200 mb-2">Run the script:</h4>
                    <div className="bg-[#1E1E1E] border border-white/10 rounded p-3 font-mono text-sm text-gray-300 overflow-x-auto">
                      <code>./Export-EntraEmployees.ps1 -OutFile ".\employees.json" -AdminGroupDisplayName "Group_HRsystemAdmins" -CompanyGroupMail "dstchemicals@dstchemicals.com" -CompanyGroupDisplayName "DSTChemicalsGroup" -EmailDomainFilter "dstchemicals.com"</code>
                    </div>
                  </div>

                  <div>
                    <h4 className="font-semibold text-gray-200 mb-2">Import the exported file:</h4>
                    <p className="text-gray-400 text-sm">Once you have the employees.json file, use the "Import Users" feature in the Users tab to import the employee data into the system.</p>
                  </div>
                </CardContent>
              </Card>

              {/* Script Display */}
              <Card className="bg-[#121212] border-white/5">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Code className="w-5 h-5" />
                    PowerShell Script
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div>
                    <Label className="text-gray-300 mb-2 block">Export-EntraEmployees.ps1</Label>
                    <div className="bg-[#0A0A0A] border border-white/10 rounded font-mono text-sm text-gray-300 overflow-x-auto p-4 max-h-96 overflow-y-auto">
                      <pre className="whitespace-pre-wrap break-words text-xs">{ENTRA_EXPORT_SCRIPT}</pre>
                    </div>
                  </div>

                  <div className="flex gap-2">
                    <Button
                      onClick={() => {
                        const element = document.createElement('a');
                        const file = new Blob([ENTRA_EXPORT_SCRIPT], { type: 'text/plain' });
                        element.href = URL.createObjectURL(file);
                        element.download = 'Export-EntraEmployees.ps1';
                        document.body.appendChild(element);
                        element.click();
                        document.body.removeChild(element);
                      }}
                      className="bg-green-600 hover:bg-green-700"
                    >
                      <Download className="w-4 h-4 mr-2" />
                      Download Script
                    </Button>

                    <Button
                      onClick={() => {
                        navigator.clipboard.writeText(ENTRA_EXPORT_SCRIPT);
                        setCopiedCommand(true);
                        setTimeout(() => setCopiedCommand(false), 2000);
                      }}
                      variant="outline"
                      className="border-white/10 hover:bg-white/5"
                    >
                      {copiedCommand ? (
                        <>
                          <CheckCircle2 className="w-4 h-4 mr-2 text-green-400" />
                          Copied!
                        </>
                      ) : (
                        <>
                          <Copy className="w-4 h-4 mr-2" />
                          Copy Script
                        </>
                      )}
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>
        </Tabs>

        {/* Edit Cycle Dialog */}
        <Dialog open={editCycleDialogOpen} onOpenChange={setEditCycleDialogOpen}>
          <DialogContent className="bg-[#1C1C1E] border-white/10">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <Edit2 className="w-5 h-5 text-blue-400" />
                Edit Performance Cycle
              </DialogTitle>
              <DialogDescription>
                Update cycle details
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4 mt-4">
              <div className="space-y-2">
                <Label>Cycle Name</Label>
                <Input
                  value={editCycleForm.name}
                  onChange={(e) => setEditCycleForm({...editCycleForm, name: e.target.value})}
                  placeholder="e.g., 2025 Annual Review"
                  className="bg-[#1E1E1E] border-white/10"
                  data-testid="edit-cycle-name"
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
                        data-testid="edit-start-date-btn"
                      >
                        <CalendarIcon className="mr-2 h-4 w-4" />
                        {editCycleForm.start_date ? format(editCycleForm.start_date, 'PPP') : 'Pick a date'}
                      </Button>
                    </PopoverTrigger>
                    <PopoverContent className="w-auto p-0 bg-[#1E1E1E] border-white/10" align="start">
                      <Calendar
                        mode="single"
                        selected={editCycleForm.start_date}
                        onSelect={(date) => setEditCycleForm({...editCycleForm, start_date: date})}
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
                        data-testid="edit-end-date-btn"
                      >
                        <CalendarIcon className="mr-2 h-4 w-4" />
                        {editCycleForm.end_date ? format(editCycleForm.end_date, 'PPP') : 'Pick a date'}
                      </Button>
                    </PopoverTrigger>
                    <PopoverContent className="w-auto p-0 bg-[#1E1E1E] border-white/10" align="start">
                      <Calendar
                        mode="single"
                        selected={editCycleForm.end_date}
                        onSelect={(date) => setEditCycleForm({...editCycleForm, end_date: date})}
                        initialFocus
                      />
                    </PopoverContent>
                  </Popover>
                </div>
              </div>
            </div>

            <DialogFooter className="mt-6">
              <Button
                variant="outline"
                onClick={() => {
                  setEditCycleDialogOpen(false);
                  setEditingCycle(null);
                  setEditCycleForm({
                    name: '',
                    start_date: null,
                    end_date: null,
                  });
                }}
                disabled={editingCycleData}
              >
                Cancel
              </Button>
              <Button
                onClick={handleEditCycle}
                disabled={editingCycleData}
                className="bg-blue-600 hover:bg-blue-700"
                data-testid="submit-edit-cycle-btn"
              >
                {editingCycleData ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Edit2 className="w-4 h-4 mr-2" />}
                Save Changes
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Edit User Dialog */}
        <Dialog open={editUserDialogOpen} onOpenChange={setEditUserDialogOpen}>
          <DialogContent className="bg-[#1C1C1E] border-white/10">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <Edit2 className="w-5 h-5 text-blue-400" />
                Edit User
              </DialogTitle>
              <DialogDescription>
                Update user information and settings
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4 mt-4">
              <div>
                <Label>Email</Label>
                <Input
                  type="email"
                  value={userForm.employee_email}
                  disabled
                  className="bg-[#0A0A0A] border-white/5 mt-1 text-gray-500"
                />
                <p className="text-xs text-gray-500 mt-1">Email cannot be changed</p>
              </div>
              <div>
                <Label>Full Name</Label>
                <Input
                  placeholder="John Doe"
                  value={userForm.employee_name}
                  onChange={(e) => setUserForm({...userForm, employee_name: e.target.value})}
                  className="bg-[#1C1C1E] border-white/10 mt-1"
                  data-testid="edit-user-name"
                />
              </div>
              <div>
                <Label>Department</Label>
                <Input
                  placeholder="Engineering"
                  value={userForm.department}
                  onChange={(e) => setUserForm({...userForm, department: e.target.value})}
                  className="bg-[#1C1C1E] border-white/10 mt-1"
                  data-testid="edit-user-dept"
                />
              </div>
              <div>
                <Label>Manager Email (optional)</Label>
                <Input
                  type="email"
                  placeholder="manager@company.com"
                  value={userForm.manager_email}
                  onChange={(e) => setUserForm({...userForm, manager_email: e.target.value})}
                  className="bg-[#1C1C1E] border-white/10 mt-1"
                  data-testid="edit-user-manager"
                />
              </div>
              <div className="flex items-center gap-2">
                <Checkbox
                  id="edit-user-admin"
                  checked={userForm.is_admin}
                  onCheckedChange={(checked) => setUserForm({...userForm, is_admin: checked})}
                  data-testid="edit-user-admin"
                />
                <Label htmlFor="edit-user-admin" className="cursor-pointer">
                  Make this user an admin
                </Label>
              </div>
            </div>

            <DialogFooter className="mt-6">
              <Button
                variant="outline"
                onClick={() => {
                  setEditUserDialogOpen(false);
                  setEditingUser(null);
                  setUserForm({
                    employee_email: '',
                    employee_name: '',
                    department: '',
                    manager_email: '',
                    is_admin: false,
                  });
                }}
                disabled={editingUserData}
              >
                Cancel
              </Button>
              <Button
                onClick={handleEditUser}
                disabled={editingUserData}
                className="bg-blue-600 hover:bg-blue-700"
                data-testid="submit-edit-user-btn"
              >
                {editingUserData ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Edit2 className="w-4 h-4 mr-2" />}
                Save Changes
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Delete User Confirmation Dialog */}
        <Dialog open={deleteUserDialogOpen} onOpenChange={setDeleteUserDialogOpen}>
          <DialogContent className="bg-[#1C1C1E] border-white/10">
            <DialogHeader>
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-red-500/10">
                  <AlertTriangle className="w-6 h-6 text-red-400" />
                </div>
                <div>
                  <DialogTitle className="text-xl">Delete User</DialogTitle>
                  <DialogDescription className="text-gray-400">
                    This action cannot be undone
                  </DialogDescription>
                </div>
              </div>
            </DialogHeader>
            <div className="space-y-4">
              <p className="text-gray-300">
                Are you sure you want to delete user <span className="font-semibold text-red-400">{deleteUserEmail}</span>?
              </p>
              <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-4">
                <p className="text-sm text-red-400 flex items-start gap-2">
                  <AlertTriangle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                  <span>This will permanently delete the user and all their conversations.</span>
                </p>
              </div>
            </div>
            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => {
                  setDeleteUserDialogOpen(false);
                  setDeleteUserEmail(null);
                }}
                disabled={deletingUser}
              >
                Cancel
              </Button>
              <Button
                onClick={handleDeleteUser}
                disabled={deletingUser}
                className="bg-red-600 hover:bg-red-700"
              >
                {deletingUser ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Trash2 className="w-4 h-4 mr-2" />}
                Delete User
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Delete Cycle Confirmation Dialog */}
        <Dialog open={deleteCycleDialogOpen} onOpenChange={setDeleteCycleDialogOpen}>
          <DialogContent className="bg-[#1C1C1E] border-white/10">
            <DialogHeader>
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-red-500/10">
                  <AlertTriangle className="w-6 h-6 text-red-400" />
                </div>
                <div>
                  <DialogTitle className="text-xl">Delete Cycle</DialogTitle>
                  <DialogDescription className="text-gray-400">
                    This action cannot be undone
                  </DialogDescription>
                </div>
              </div>
            </DialogHeader>
            <div className="space-y-4">
              <p className="text-gray-300">
                Are you sure you want to delete cycle <span className="font-semibold text-red-400">{deleteCycleName}</span>?
              </p>
              <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-4">
                <p className="text-sm text-red-400 flex items-start gap-2">
                  <AlertTriangle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                  <span>This will permanently delete the cycle and all conversations within it.</span>
                </p>
              </div>
            </div>
            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => {
                  setDeleteCycleDialogOpen(false);
                  setDeleteCycleId(null);
                  setDeleteCycleName(null);
                }}
                disabled={deletingCycle}
              >
                Cancel
              </Button>
              <Button
                onClick={handleDeleteCycle}
                disabled={deletingCycle}
                className="bg-red-600 hover:bg-red-700"
              >
                {deletingCycle ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Trash2 className="w-4 h-4 mr-2" />}
                Delete Cycle
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </Layout>
  );
};

export default AdminPage;
