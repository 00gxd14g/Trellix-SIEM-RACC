import { useLocation } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Search, Bell, Settings, Sun, Moon, X } from 'lucide-react';
import { useAppContext } from '@/context/AppContext';
import { useTheme } from '@/components/theme-provider';

export default function Header() {
  const location = useLocation();
  const { customers, selectedCustomerId, setSelectedCustomerId } = useAppContext();
  const selectedCustomer = customers.find(c => c.id === selectedCustomerId);
  const { theme, setTheme } = useTheme();

  const getPageTitle = () => {
    switch (location.pathname) {
      case '/dashboard':
        return 'Dashboard';
      case '/customers':
        return 'Customers';
      case '/rules':
        return 'Rules';
      case '/alarms':
        return 'Alarms';
      case '/analysis':
        return 'Analysis';
      case '/flow-diagram':
        return 'Flow Diagram';
      case '/settings':
        return 'Settings';
      default:
        if (location.pathname.startsWith('/customers/')) {
          const customerId = location.pathname.split('/')[2];
          const customer = customers.find(c => c.id === parseInt(customerId));
          return customer ? `Customer: ${customer.name}` : 'Customer Detail';
        }
        return 'Trellix SIEM Editor';
    }
  };

  const toggleTheme = () => {
    setTheme(theme === 'light' ? 'dark' : 'light');
  };

  return (
    <header className="h-16 bg-card border-b border-border flex items-center justify-between px-6 shadow-sm">
      <h2 className="text-xl font-semibold text-foreground">{getPageTitle()}</h2>
      <div className="flex items-center space-x-4">
        {selectedCustomer && (
          <div className="flex items-center bg-primary/10 text-primary px-3 py-1 rounded-full text-sm font-medium animate-in fade-in zoom-in duration-200">
            <span className="mr-2">{selectedCustomer.name}</span>
            <button
              onClick={() => setSelectedCustomerId(null)}
              className="hover:bg-primary/20 rounded-full p-0.5 transition-colors"
              title="Clear selection"
            >
              <X className="h-3 w-3" />
            </button>
          </div>
        )}
        <div className="flex items-center space-x-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              type="text"
              placeholder="Search..."
              className="pl-9 pr-3 py-2 rounded-md bg-input border border-border focus:ring-2 focus:ring-primary focus:border-transparent"
            />
          </div>
          <Button variant="ghost" size="icon" className="text-muted-foreground hover:text-primary">
            <Bell className="h-5 w-5" />
          </Button>
          <Button variant="ghost" size="icon" className="text-muted-foreground hover:text-primary" onClick={toggleTheme}>
            {theme === 'light' ? <Moon className="h-5 w-5" /> : <Sun className="h-5 w-5" />}
          </Button>
          <Button variant="ghost" size="icon" className="text-muted-foreground hover:text-primary">
            <Settings className="h-5 w-5" />
          </Button>
        </div>
      </div>
    </header>
  );
}

