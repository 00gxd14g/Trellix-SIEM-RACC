import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import CustomerDetail from './CustomerDetail';
import { AppToastProvider } from '@/hooks/use-toast';
import { AppContext } from '@/context/AppContext';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { customerAPI } from '@/lib/api';

vi.mock('@/lib/api', () => ({
  customerAPI: {
    getById: vi.fn(),
    uploadFile: vi.fn(),
    downloadFile: vi.fn(),
    deleteFile: vi.fn(),
  },
}));

describe('CustomerDetail XML upload flow', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    customerAPI.getById.mockResolvedValue({
      data: {
        customer: {
          id: 1,
          name: 'Customer A',
          description: '',
          contact_email: '',
          contact_phone: '',
          files: [],
          recent_validations: [],
        },
      },
    });
    customerAPI.uploadFile.mockResolvedValue({
      data: {
        success: true,
        validation: {
          success: true,
          errors: [],
          items_processed: 10,
        },
      },
    });
  });

  it('uploads XML file via rule upload widget', async () => {
    vi.useFakeTimers();

    render(
      <AppToastProvider>
        <AppContext.Provider
          value={{
            customers: [{ id: 1, name: 'Customer A' }],
            selectedCustomerId: 1,
            setSelectedCustomerId: vi.fn(),
          }}
        >
          <MemoryRouter initialEntries={['/customers/1']}>
            <Routes>
              <Route path="/customers/:customerId" element={<CustomerDetail />} />
            </Routes>
          </MemoryRouter>
        </AppContext.Provider>
      </AppToastProvider>
    );

    await waitFor(() =>
      expect(customerAPI.getById).toHaveBeenCalledWith('1')
    );

    const fileInput = screen.getAllByRole('textbox', { hidden: true })[0] || document.querySelector('input[type="file"]');
    const file = new File(['<xml></xml>'], 'rules.xml', { type: 'text/xml' });

    fireEvent.change(fileInput, { target: { files: [file] } });

    await vi.runAllTimersAsync();

    await waitFor(() => {
      expect(customerAPI.uploadFile).toHaveBeenCalled();
      const [customerIdArg] = customerAPI.uploadFile.mock.calls[0];
      expect(customerIdArg).toBe('1');
    });

    vi.useRealTimers();
  });
});

