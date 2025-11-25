import { NavLink, useLocation } from 'react-router-dom';
import { Home, Users, FileText, Bell, BarChart2, GitBranch, Settings, Shield, Building2, ChevronDown } from 'lucide-react';
import { useAppContext } from '@/context/AppContext';
import { useCustomers } from '@/hooks/useCustomers';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Button } from '@/components/ui/button';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { cn } from '@/lib/utils';

const navItems = [
  { to: '/dashboard', icon: Home, label: 'Dashboard' },
  { to: '/customers', icon: Users, label: 'Customers' },
  { to: '/rules', icon: FileText, label: 'Rules', requiresCustomer: true },
  { to: '/alarms', icon: Bell, label: 'Alarms', requiresCustomer: true },
  { to: '/analysis', icon: BarChart2, label: 'Analysis', requiresCustomer: true },
  { to: '/flow-diagram', icon: GitBranch, label: 'Flow Diagram', requiresCustomer: true },
  { to: '/logs', icon: FileText, label: 'Logs', requiresCustomer: false },
];

export default function Sidebar() {
  const { selectedCustomerId, setSelectedCustomerId } = useAppContext();
  const { customers, loading } = useCustomers();
  const location = useLocation();

  const selectedCustomer = customers.find(c => c.id === selectedCustomerId);

  return (
    <aside className="w-72 flex-shrink-0 bg-sidebar border-r border-sidebar-border flex flex-col">
      <div className="h-16 flex items-center px-6 mb-6 mt-2">
        <div className="p-2 rounded-lg bg-primary/10">
          <Shield className="h-8 w-8 text-primary" />
        </div>
        <h1 className="ml-3 text-xl font-bold bg-gradient-to-r from-primary to-primary/60 bg-clip-text text-transparent">
          RACC
        </h1>
      </div>

      <div className="mb-6 px-4">
        <Popover>
          <PopoverTrigger asChild>
            <Button variant="outline" className="w-full justify-between h-12 px-4 bg-background/50 border-border/50 hover:bg-background/80">
              <div className="flex items-center truncate">
                <Building2 className="h-4 w-4 mr-2 text-primary" />
                <span className="truncate font-medium">{selectedCustomer ? selectedCustomer.name : 'All Customers'}</span>
              </div>
              <ChevronDown className="h-4 w-4 text-muted-foreground" />
            </Button>
          </PopoverTrigger>
          <PopoverContent className="w-64 p-0">
            <ScrollArea className="h-48">
              {loading ? (
                <div className="p-4 text-sm text-muted-foreground">Loading...</div>
              ) : (
                <>
                  <Button
                    variant="ghost"
                    className="w-full justify-start rounded-none font-semibold border-b"
                    onClick={() => setSelectedCustomerId(null)}
                  >
                    All Customers
                  </Button>
                  {customers.map(customer => (
                    <Button
                      key={customer.id}
                      variant="ghost"
                      className="w-full justify-start rounded-none"
                      onClick={() => setSelectedCustomerId(customer.id)}
                    >
                      {customer.name}
                    </Button>
                  ))}
                </>
              )}
            </ScrollArea>
          </PopoverContent>
        </Popover>
      </div>

      <nav className="flex-1 space-y-1 px-4">
        {navItems.map((item) => {
          const isDisabled = item.requiresCustomer && !selectedCustomerId;
          const isActive = location.pathname.startsWith(item.to);
          return (
            <NavLink
              key={item.to}
              to={item.to}
              className={cn(
                'flex items-center px-4 py-3 text-sm font-medium rounded-lg transition-all duration-200',
                isActive
                  ? 'bg-primary text-primary-foreground shadow-sm'
                  : 'text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground',
                isDisabled && 'opacity-40 cursor-not-allowed pointer-events-none'
              )}
            >
              <item.icon className="mr-4 h-5 w-5" />
              {item.label}
            </NavLink>
          );
        })}
      </nav>

      <div className="mt-auto">
        <NavLink
          to="/settings"
          className={({ isActive }) =>
            cn(
              'flex items-center px-4 py-3 text-base font-medium rounded-lg transition-colors',
              isActive
                ? 'bg-primary text-primary-foreground shadow-inner'
                : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
            )
          }
        >
          <Settings className="mr-4 h-5 w-5" />
          Settings
        </NavLink>
      </div>
    </aside>
  );
}

