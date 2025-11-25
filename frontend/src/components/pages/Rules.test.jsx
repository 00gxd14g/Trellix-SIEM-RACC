import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import Rules from './Rules';
import { AppToastProvider } from '@/hooks/use-toast';
import { AppContext } from '@/context/AppContext';
import { ruleAPI } from '@/lib/api';

vi.mock('@/lib/api', () => ({
  ruleAPI: {
    getAll: vi.fn(),
    generateAlarms: vi.fn(),
    delete: vi.fn(),
    update: vi.fn(),
    exportAll: vi.fn(),
    getById: vi.fn(),
    getStats: vi.fn(),
  },
  customerAPI: {
    uploadFile: vi.fn(),
  },
}));

describe('Rules page - Rule to Alarm generation', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    ruleAPI.getAll.mockResolvedValue({
      data: {
        rules: [
          {
            id: 1,
            name: 'Rule One',
            rule_id: 'R-1',
            severity: 50,
            sig_id: '47-1',
            description: '',
          },
        ],
      },
    });
    ruleAPI.generateAlarms.mockResolvedValue({
      data: {
        success: true,
        generated_count: 1,
      },
    });
  });

  it('calls generateAlarms when rules are selected and button clicked', async () => {
    render(
      <AppToastProvider>
        <AppContext.Provider
          value={{
            customers: [{ id: 1, name: 'Customer A' }],
            selectedCustomerId: 1,
            setSelectedCustomerId: vi.fn(),
          }}
        >
          <Rules />
        </AppContext.Provider>
      </AppToastProvider>
    );

    await waitFor(() => {
      expect(ruleAPI.getAll).toHaveBeenCalledWith(1, {
        search: '',
        severity_min: 0,
        severity_max: 100,
      });
    });

    const checkboxButtons = await screen.findAllByRole('button', { name: '' });
    const rowSelectButton = checkboxButtons[0];
    fireEvent.click(rowSelectButton);

    const generateButton = screen.getByText(/Generate Alarms/i);
    fireEvent.click(generateButton);

    await waitFor(() => {
      expect(ruleAPI.generateAlarms).toHaveBeenCalledWith(1, [1]);
    });
  });
});

