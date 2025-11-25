import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from '@/components/ui/toaster';
import { ThemeProvider } from '@/components/theme-provider';
import ErrorBoundary from '@/components/ui/error-boundary';
import Sidebar from '@/components/layout/Sidebar';
import Header from '@/components/layout/Header';
import Dashboard from '@/components/pages/Dashboard';
import Customers from '@/components/pages/Customers';
import CustomerDetail from '@/components/pages/CustomerDetail';
import Rules from '@/components/pages/Rules';
import Alarms from '@/components/pages/Alarms';
import Analysis from '@/components/pages/Analysis';
import FlowDiagram from '@/components/pages/FlowDiagram';
import Settings from '@/components/pages/Settings';
import Logs from '@/components/pages/Logs';
import { AppProvider } from '@/context/AppContext';
import { AppToastProvider } from '@/hooks/use-toast';
import logger from '@/lib/logger';
import './App.css';

// Make logger available globally for debugging
if (import.meta.env.DEV) {
  window.logger = logger;
}

function App() {
  return (
    <AppProvider>
      <ThemeProvider defaultTheme="dark" storageKey="vite-ui-theme">
        <AppToastProvider>
          <MainLayout />
        </AppToastProvider>
      </ThemeProvider>
    </AppProvider>
  );
}

function MainLayout() {
  return (
    <ErrorBoundary>
      <Router>
        <div className="flex h-screen bg-background text-foreground">
          <Sidebar />
          <div className="flex-1 flex flex-col overflow-hidden">
            <Header />
            <main className="flex-1 overflow-y-auto p-4 md:p-6 lg:p-8">
              <Routes>
                <Route path="/" element={<Navigate to="/dashboard" replace />} />
                <Route path="/dashboard" element={<Dashboard />} />
                <Route path="/customers" element={<Customers />} />
                <Route path="/customers/:customerId" element={<CustomerDetail />} />
                <Route path="/rules" element={<Rules />} />
                <Route path="/alarms" element={<Alarms />} />
                <Route path="/analysis" element={<Analysis />} />
                <Route path="/flow-diagram" element={<FlowDiagram />} />
                <Route path="/logs" element={<Logs />} />
                <Route path="/settings" element={<Settings />} />
              </Routes>
            </main>
          </div>
          <Toaster />
        </div>
      </Router>
    </ErrorBoundary>
  );
}

export default App;

