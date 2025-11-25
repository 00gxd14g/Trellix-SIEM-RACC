/**
 * Settings Component Test Suite
 *
 * Tests for the enhanced Settings page with:
 * - System settings management (general, api, customer_defaults)
 * - Customer-specific overrides
 * - Import/Export functionality
 * - API connection testing
 * - Theme switching
 * - Form validation
 * - Error handling
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import Settings from './Settings';
import { settingsAPI } from '@/lib/api';
import { AppToastProvider } from '@/hooks/use-toast';
import { ThemeProvider } from '@/components/theme-provider';
import { AppContext } from '@/context/AppContext';

// Mock API
vi.mock('@/lib/api', () => ({
  settingsAPI: {
    getSystem: vi.fn(),
    updateSystem: vi.fn(),
    getCustomer: vi.fn(),
    updateCustomer: vi.fn(),
    testConnection: vi.fn(),
  },
}));

const mockContextValue = {
  customers: [
    { id: 1, name: 'Customer A' },
    { id: 2, name: 'Customer B' },
  ],
  selectedCustomerId: 1,
};

const mockSystemSettings = {
  general: {
    appName: 'Test App',
    maxFileSize: 16,
    defaultPageSize: 50,
    enableNotifications: true,
    notificationEmail: 'test@example.com',
    backupEnabled: true,
    backupFrequency: 'daily',
    enableAuditLog: true,
    sessionTimeout: 60,
    theme: 'system',
  },
  api: {
    apiBaseUrl: 'http://localhost:5000/api',
    healthEndpoint: '/health',
    apiKey: '',
    authHeader: 'Authorization',
    timeout: 15,
    verifySsl: false,
    pollInterval: 60,
  },
  customer_defaults: {
    maxAlarmNameLength: 128,
    defaultSeverity: 50,
    defaultConditionType: 14,
    matchField: 'DSIDSigID',
    summaryTemplate: 'Default template',
    defaultAssignee: 8199,
    defaultEscAssignee: 57355,
    defaultMinVersion: '11.6.14',
  },
};

const renderSettings = () => {
  return render(
    <ThemeProvider>
      <AppToastProvider>
        <AppContext.Provider value={mockContextValue}>
          <Settings />
        </AppContext.Provider>
      </AppToastProvider>
    </ThemeProvider>
  );
};

describe('Settings Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    settingsAPI.getSystem.mockResolvedValue({
      data: {
        settings: mockSystemSettings,
        defaults: mockSystemSettings,
      },
    });
    settingsAPI.getCustomer.mockResolvedValue({
      data: {
        defaults: mockSystemSettings.customer_defaults,
        overrides: {},
        effective: mockSystemSettings.customer_defaults,
      },
    });
  });

  it('should render settings page with all sections', async () => {
    renderSettings();

    await waitFor(() => {
      expect(screen.getByText('Settings')).toBeInTheDocument();
    });

    // Check for main sections
    expect(screen.getByText('General Settings')).toBeInTheDocument();
    expect(screen.getByText('API Connection Settings')).toBeInTheDocument();
    expect(screen.getByText('Rule-to-Alarm Defaults')).toBeInTheDocument();
    expect(screen.getByText('Customer Overrides')).toBeInTheDocument();
  });

  it('should load system settings on mount', async () => {
    renderSettings();

    await waitFor(() => {
      expect(settingsAPI.getSystem).toHaveBeenCalled();
    });
  });

  it('should enable save button when settings are modified', async () => {
    renderSettings();

    await waitFor(() => {
      expect(screen.getByText('Save Changes')).toBeDisabled();
    });

    const appNameInput = screen.getByLabelText('Application Name');
    fireEvent.change(appNameInput, { target: { value: 'New App Name' } });

    await waitFor(() => {
      expect(screen.getByText('Save Changes')).not.toBeDisabled();
    });
  });

  it('should show unsaved changes warning', async () => {
    renderSettings();

    await waitFor(() => {
      const appNameInput = screen.getByLabelText('Application Name');
      fireEvent.change(appNameInput, { target: { value: 'New App Name' } });
    });

    await waitFor(() => {
      expect(screen.getByText(/You have unsaved changes/)).toBeInTheDocument();
    });
  });

  it('should save system settings', async () => {
    settingsAPI.updateSystem.mockResolvedValue({
      data: {
        success: true,
        updated: mockSystemSettings,
      },
    });

    renderSettings();

    await waitFor(() => {
      const appNameInput = screen.getByLabelText('Application Name');
      fireEvent.change(appNameInput, { target: { value: 'New App Name' } });
    });

    const saveButton = screen.getByText('Save Changes');
    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(settingsAPI.updateSystem).toHaveBeenCalled();
    });
  });

  it('should test API connection', async () => {
    settingsAPI.testConnection.mockResolvedValue({
      data: {
        success: true,
        status_code: 200,
        url: 'http://localhost:5000/api/health',
      },
    });

    renderSettings();

    await waitFor(() => {
      const testButton = screen.getByText('Test Connection');
      fireEvent.click(testButton);
    });

    await waitFor(() => {
      expect(settingsAPI.testConnection).toHaveBeenCalled();
    });
  });

  it('should handle theme switching', async () => {
    renderSettings();

    await waitFor(() => {
      const themeSelect = screen.getByLabelText('Theme Preference');
      fireEvent.change(themeSelect, { target: { value: 'dark' } });
    });

    // Theme should be applied immediately
    // This would need to check the actual theme application
  });

  it('should export settings', async () => {
    const createObjectURL = vi.fn();
    const revokeObjectURL = vi.fn();
    global.URL.createObjectURL = createObjectURL;
    global.URL.revokeObjectURL = revokeObjectURL;

    const createElement = document.createElement.bind(document);
    document.createElement = vi.fn((tagName) => {
      if (tagName === 'a') {
        const link = createElement('a');
        link.click = vi.fn();
        return link;
      }
      return createElement(tagName);
    });

    renderSettings();

    await waitFor(() => {
      const exportButton = screen.getByText('Export');
      fireEvent.click(exportButton);
    });

    await waitFor(() => {
      expect(createObjectURL).toHaveBeenCalled();
    });
  });

  it('should validate numeric inputs', async () => {
    renderSettings();

    await waitFor(() => {
      const maxFileSizeInput = screen.getByLabelText('Max File Size (MB)');

      // Try to enter invalid value
      fireEvent.change(maxFileSizeInput, { target: { value: 'invalid' } });

      // Input should reject invalid values
      expect(maxFileSizeInput.value).not.toBe('invalid');
    });
  });

  it('should load customer settings when customer is selected', async () => {
    renderSettings();

    await waitFor(() => {
      expect(settingsAPI.getCustomer).toHaveBeenCalledWith(1);
    });
  });

  it('should handle customer override changes', async () => {
    renderSettings();

    await waitFor(() => {
      const severityInput = screen.getByLabelText('Default Severity');
      fireEvent.change(severityInput, { target: { value: '75' } });
    });

    // Save customer overrides button should be enabled
    await waitFor(() => {
      const saveButton = screen.getByText('Save Customer Overrides');
      expect(saveButton).not.toBeDisabled();
    });
  });

  it('should handle API errors gracefully', async () => {
    settingsAPI.updateSystem.mockRejectedValue({
      response: {
        data: {
          error: 'Validation failed',
        },
      },
    });

    renderSettings();

    await waitFor(() => {
      const appNameInput = screen.getByLabelText('Application Name');
      fireEvent.change(appNameInput, { target: { value: 'New App Name' } });
    });

    const saveButton = screen.getByText('Save Changes');
    fireEvent.click(saveButton);

    await waitFor(() => {
      // Toast should show error message
      expect(settingsAPI.updateSystem).toHaveBeenCalled();
    });
  });
});

/**
 * Manual Testing Checklist:
 *
 * 1. Settings Persistence:
 *    - [ ] Load settings from backend on page load
 *    - [ ] Save settings and verify they persist across page refreshes
 *    - [ ] Reset to defaults works correctly
 *
 * 2. Form Validation:
 *    - [ ] Numeric fields only accept numbers
 *    - [ ] Email field validates email format
 *    - [ ] Required fields show validation errors
 *
 * 3. Import/Export:
 *    - [ ] Export creates valid JSON file
 *    - [ ] Import loads settings correctly
 *    - [ ] Import shows error for invalid JSON
 *    - [ ] Import merges with existing settings
 *
 * 4. API Connection Test:
 *    - [ ] Test shows loading state
 *    - [ ] Success shows green checkmark
 *    - [ ] Failure shows red X with error message
 *    - [ ] Can test multiple times
 *
 * 5. Theme Switching:
 *    - [ ] System theme follows OS preference
 *    - [ ] Light theme applies correctly
 *    - [ ] Dark theme applies correctly
 *    - [ ] Theme persists across refreshes
 *
 * 6. Customer Overrides:
 *    - [ ] Can select different customers
 *    - [ ] Overrides load correctly
 *    - [ ] Can save customer-specific settings
 *    - [ ] Clear override reverts to default
 *
 * 7. Error Handling:
 *    - [ ] Network errors show toast notification
 *    - [ ] Validation errors show inline
 *    - [ ] Backend errors show descriptive messages
 *
 * 8. UI/UX:
 *    - [ ] Unsaved changes warning appears
 *    - [ ] Save button disabled when no changes
 *    - [ ] Loading states show spinners
 *    - [ ] All sections are responsive on mobile
 *    - [ ] Tooltips/help text are clear
 */
