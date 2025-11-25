import React, { useEffect, useState, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { useToast } from '@/hooks/use-toast';
import { customerAPI } from '@/lib/api';
import { 
  Mail, 
  Phone, 
  FileText, 
  Bell, 
  Download, 
  Trash2, 
  RefreshCw, 
  Edit, 
  Info, 
  CheckCircle, 
  CheckCircle2,
  AlertCircle 
} from 'lucide-react';
import { FileUpload, FileUploadProgress } from '@/components/ui/file-upload';
import CustomerForm from '@/components/forms/CustomerForm';
import { LoadingSpinner } from '@/components/ui/loading';
import { useAppContext } from '@/context/AppContext';

export default function CustomerDetail() {
  const { customerId } = useParams();
  const { setSelectedCustomerId } = useAppContext();
  const [customer, setCustomer] = useState(null);
  const [loading, setLoading] = useState(true);
  const [uploadingFile, setUploadingFile] = useState(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadStatus, setUploadStatus] = useState('idle'); // idle, uploading, success, error
  const [showEditForm, setShowEditForm] = useState(false);
  const { toast } = useToast();

  const fetchCustomerDetails = useCallback(async () => {
    setLoading(true);
    try {
      const response = await customerAPI.getById(customerId);
      setCustomer(response.data.customer);
    } catch (error) {
      console.error('Failed to fetch customer details:', error);
      toast({ title: "Error", description: "Failed to load customer details.", variant: "destructive" });
    } finally {
      setLoading(false);
    }
  }, [customerId, toast]);

  useEffect(() => {
    if (customerId) {
      setSelectedCustomerId(parseInt(customerId));
      fetchCustomerDetails();
    }
  }, [customerId, setSelectedCustomerId, fetchCustomerDetails]);

  const handleFileUpload = async (file, fileType) => {
    setUploadingFile(file.name);
    setUploadProgress(0);
    setUploadStatus('uploading');

    const formData = new FormData();
    formData.append('file', file);
    formData.append('file_type', fileType);

    try {
      // Simulate progress for demonstration
      for (let i = 0; i <= 100; i += 10) {
        setUploadProgress(i);
        await new Promise(resolve => setTimeout(resolve, 100));
      }

      const response = await customerAPI.uploadFile(customerId, formData);
      if (response.data.success) {
        const validation = response.data.validation;
        
        if (validation && validation.success) {
          setUploadStatus('success');
          toast({ 
            title: "Success", 
            description: `${file.name} uploaded and validated successfully.` 
          });
        } else if (validation) {
          setUploadStatus('error');
          const errorDetails = validation.errors ? validation.errors.slice(0, 3).join('; ') : 'Validation failed';
          toast({ 
            title: "Validation Error", 
            description: `${file.name} uploaded but validation failed: ${errorDetails}${validation.errors?.length > 3 ? '...' : ''}`, 
            variant: "destructive" 
          });
        } else {
          setUploadStatus('success');
          toast({ title: "Success", description: `${file.name} uploaded successfully.` });
        }
        
        fetchCustomerDetails();
      } else {
        setUploadStatus('error');
        toast({ title: "Error", description: `Failed to process ${file.name}: ${response.data.error}`, variant: "destructive" });
      }
    } catch (error) {
      console.error('File upload failed:', error);
      setUploadStatus('error');
      toast({ title: "Error", description: `File upload failed: ${error.response?.data?.error || error.message}`, variant: "destructive" });
    } finally {
      setUploadingFile(null);
      setUploadProgress(0);
    }
  };

  const handleDownloadFile = async (fileType) => {
    try {
      const response = await customerAPI.downloadFile(customerId, fileType);
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `${fileType}.xml`); // Or use the actual filename from response if available
      document.body.appendChild(link);
      link.click();
      link.remove();
      toast({ title: "Success", description: `${fileType} file downloaded successfully.` });
    } catch (error) {
      console.error(`Failed to download ${fileType} file:`, error);
      toast({ title: "Error", description: `Failed to download ${fileType} file: ${error.response?.data?.error || error.message}`, variant: "destructive" });
    }
  };

  const handleValidateFile = async (fileType) => {
    try {
      const response = await fetch(`/api/customers/${customerId}/files/${fileType}/validate`, {
        method: 'POST',
        headers: {
          'X-Customer-ID': customerId.toString()
        }
      });
      
      const data = await response.json();
      
      if (data.success) {
        if (data.validation.success) {
          toast({ title: "Success", description: `${fileType} file validation passed.` });
        } else {
          const errorDetails = data.validation.errors ? data.validation.errors.slice(0, 3).join('; ') : 'Validation failed';
          toast({ 
            title: "Validation Failed", 
            description: `${errorDetails}${data.validation.errors?.length > 3 ? '...' : ''}`, 
            variant: "destructive" 
          });
        }
        fetchCustomerDetails(); // Refresh to show updated validation status
      } else {
        toast({ title: "Error", description: `Failed to validate ${fileType} file: ${data.error}`, variant: "destructive" });
      }
    } catch (error) {
      console.error(`Failed to validate ${fileType} file:`, error);
      toast({ title: "Error", description: `Failed to validate ${fileType} file: ${error.message}`, variant: "destructive" });
    }
  };

  const handleDeleteFile = async (fileType) => {
    if (!window.confirm(`Are you sure you want to delete the ${fileType} file? This will also delete associated rules/alarms.`)) {
      return;
    }
    try {
      await customerAPI.deleteFile(customerId, fileType);
      toast({ title: "Success", description: `${fileType} file deleted successfully.` });
      fetchCustomerDetails();
    } catch (error) {
      console.error(`Failed to delete ${fileType} file:`, error);
      toast({ title: "Error", description: `Failed to delete ${fileType} file: ${error.response?.data?.error || error.message}`, variant: "destructive" });
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <LoadingSpinner />
      </div>
    );
  }

  if (!customer) {
    return (
      <div className="text-center py-10">
        <Info className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
        <h3 className="text-xl font-semibold">Customer Not Found</h3>
        <p className="text-muted-foreground mt-2">The customer you are looking for does not exist.</p>
        <Link to="/customers" className="mt-4 inline-flex items-center text-primary hover:underline">
          Back to Customers
        </Link>
      </div>
    );
  }

  const ruleFile = customer.files.find(f => f.file_type === 'rule');
  const alarmFile = customer.files.find(f => f.file_type === 'alarm');

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">{customer.name}</h1>
          <p className="text-muted-foreground mt-1">Manage details and files for this customer</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={() => setShowEditForm(true)}>
            <Edit className="h-4 w-4 mr-2" />
            Edit Customer
          </Button>
          <Button variant="outline" onClick={fetchCustomerDetails}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh Data
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle>Customer Information</CardTitle>
            <CardDescription>Basic details about the customer</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <p className="text-muted-foreground">Description:</p>
              <p className="font-medium">{customer.description || 'N/A'}</p>
            </div>
            {customer.contact_email && (
              <div className="flex items-center text-sm">
                <Mail className="h-4 w-4 mr-2 text-muted-foreground" />
                <span>{customer.contact_email}</span>
              </div>
            )}
            {customer.contact_phone && (
              <div className="flex items-center text-sm">
                <Phone className="h-4 w-4 mr-2 text-muted-foreground" />
                <span>{customer.contact_phone}</span>
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Customer Files</CardTitle>
            <CardDescription>Upload and manage rule and alarm XML files</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Rule File Upload */}
              <div className="space-y-4">
                <h3 className="text-lg font-semibold flex items-center">
                  <FileText className="h-5 w-5 mr-2" /> Rule File (.xml)
                </h3>
                <FileUpload
                  onFileSelect={(file) => handleFileUpload(file, 'rule')}
                  accept=".xml"
                  maxSize={10 * 1024 * 1024} // 10MB for rules
                />
                {ruleFile && (
                  <div className="flex items-center justify-between p-3 border rounded-md bg-muted/20">
                    <div className="flex items-center space-x-3">
                      <FileText className="h-5 w-5 text-primary" />
                      <span className="text-sm font-medium truncate max-w-[150px]">{ruleFile.filename}</span>
                      <span className="text-xs text-muted-foreground">({(ruleFile.file_size / 1024 / 1024).toFixed(2)} MB)</span>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Button variant="ghost" size="sm" onClick={() => handleValidateFile('rule')} className="h-8 w-8 p-0" title="Validate file">
                        <RefreshCw className="h-4 w-4" />
                      </Button>
                      <Button variant="ghost" size="sm" onClick={() => handleDownloadFile('rule')} className="h-8 w-8 p-0" title="Download file">
                        <Download className="h-4 w-4" />
                      </Button>
                      <Button variant="ghost" size="sm" onClick={() => handleDeleteFile('rule')} className="h-8 w-8 p-0 text-destructive hover:text-destructive" title="Delete file">
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                )}
                {uploadingFile && uploadingFile === ruleFile?.filename && uploadStatus === 'uploading' && (
                  <FileUploadProgress fileName={uploadingFile} progress={uploadProgress} status={uploadStatus} />
                )}
                {uploadingFile && uploadingFile === ruleFile?.filename && uploadStatus === 'success' && (
                  <FileUploadProgress fileName={uploadingFile} progress={100} status={uploadStatus} />
                )}
                {uploadingFile && uploadingFile === ruleFile?.filename && uploadStatus === 'error' && (
                  <FileUploadProgress fileName={uploadingFile} progress={uploadProgress} status={uploadStatus} />
                )}
                {ruleFile?.validation_status === 'valid' && (
                  <div className="text-sm text-green-600 flex items-center mt-2">
                    <CheckCircle2 className="h-4 w-4 mr-2" />
                    File validated successfully
                  </div>
                )}
                {ruleFile?.validation_status === 'invalid' && ruleFile?.validation_errors && (
                  <div className="space-y-2 mt-2">
                    <div className="text-sm text-destructive flex items-center">
                      <AlertCircle className="h-4 w-4 mr-2" />
                      Validation Failed
                    </div>
                    <div className="text-xs text-muted-foreground bg-destructive/5 p-2 rounded border">
                      {JSON.parse(ruleFile.validation_errors).slice(0, 5).map((error, index) => (
                        <div key={index}>• {error}</div>
                      ))}
                      {JSON.parse(ruleFile.validation_errors).length > 5 && (
                        <div className="text-xs text-muted-foreground mt-1">
                          ... and {JSON.parse(ruleFile.validation_errors).length - 5} more errors
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>

              {/* Alarm File Upload */}
              <div className="space-y-4">
                <h3 className="text-lg font-semibold flex items-center">
                  <Bell className="h-5 w-5 mr-2" /> Alarm File (.xml)
                </h3>
                <FileUpload
                  onFileSelect={(file) => handleFileUpload(file, 'alarm')}
                  accept=".xml"
                  maxSize={10 * 1024 * 1024} // 10MB for alarms
                />
                {alarmFile && (
                  <div className="flex items-center justify-between p-3 border rounded-md bg-muted/20">
                    <div className="flex items-center space-x-3">
                      <Bell className="h-5 w-5 text-primary" />
                      <span className="text-sm font-medium truncate max-w-[150px]">{alarmFile.filename}</span>
                      <span className="text-xs text-muted-foreground">({(alarmFile.file_size / 1024 / 1024).toFixed(2)} MB)</span>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Button variant="ghost" size="sm" onClick={() => handleValidateFile('alarm')} className="h-8 w-8 p-0" title="Validate file">
                        <RefreshCw className="h-4 w-4" />
                      </Button>
                      <Button variant="ghost" size="sm" onClick={() => handleDownloadFile('alarm')} className="h-8 w-8 p-0" title="Download file">
                        <Download className="h-4 w-4" />
                      </Button>
                      <Button variant="ghost" size="sm" onClick={() => handleDeleteFile('alarm')} className="h-8 w-8 p-0 text-destructive hover:text-destructive" title="Delete file">
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                )}
                {uploadingFile && uploadingFile === alarmFile?.filename && uploadStatus === 'uploading' && (
                  <FileUploadProgress fileName={uploadingFile} progress={uploadProgress} status={uploadStatus} />
                )}
                {uploadingFile && uploadingFile === alarmFile?.filename && uploadStatus === 'success' && (
                  <FileUploadProgress fileName={uploadingFile} progress={100} status={uploadStatus} />
                )}
                {uploadingFile && uploadingFile === alarmFile?.filename && uploadStatus === 'error' && (
                  <FileUploadProgress fileName={uploadingFile} progress={uploadProgress} status={uploadStatus} />
                )}
                {alarmFile?.validation_status === 'valid' && (
                  <div className="text-sm text-green-600 flex items-center mt-2">
                    <CheckCircle2 className="h-4 w-4 mr-2" />
                    File validated successfully
                  </div>
                )}
                {alarmFile?.validation_status === 'invalid' && alarmFile?.validation_errors && (
                  <div className="space-y-2 mt-2">
                    <div className="text-sm text-destructive flex items-center">
                      <AlertCircle className="h-4 w-4 mr-2" />
                      Validation Failed
                    </div>
                    <div className="text-xs text-muted-foreground bg-destructive/5 p-2 rounded border">
                      {JSON.parse(alarmFile.validation_errors).slice(0, 5).map((error, index) => (
                        <div key={index}>• {error}</div>
                      ))}
                      {JSON.parse(alarmFile.validation_errors).length > 5 && (
                        <div className="text-xs text-muted-foreground mt-1">
                          ... and {JSON.parse(alarmFile.validation_errors).length - 5} more errors
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </div>

            <Card className="mt-6">
              <CardHeader>
                <CardTitle>Recent Validations</CardTitle>
                <CardDescription>Last 10 file validation attempts</CardDescription>
              </CardHeader>
              <CardContent>
                {customer.recent_validations && customer.recent_validations.length > 0 ? (
                  <div className="space-y-3">
                    {customer.recent_validations.map((log) => (
                      <div key={log.id} className="flex items-center justify-between text-sm">
                        <div className="flex items-center space-x-2">
                          {log.status === 'success' ? (
                            <CheckCircle className="h-4 w-4 text-green-500" />
                          ) : (
                            <AlertCircle className="h-4 w-4 text-destructive" />
                          )}
                          <span>{log.file_type.toUpperCase()} - {log.message}</span>
                        </div>
                        <span className="text-muted-foreground text-xs">
                          {new Date(log.created_at).toLocaleString()}
                        </span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-muted-foreground text-sm">No recent validation logs.</p>
                )}
              </CardContent>
            </Card>
          </CardContent>
        </Card>
      </div>

      {showEditForm && (
        <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4">
          <CustomerForm
            customer={customer}
            onClose={() => setShowEditForm(false)}
            onSuccess={() => { setShowEditForm(false); fetchCustomerDetails(); }}
          />
        </div>
      )}
    </div>
  );
}
