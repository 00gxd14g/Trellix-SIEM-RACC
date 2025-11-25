import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import Analysis from './Analysis';
import FlowDiagram from './FlowDiagram';
import { AppContext } from '@/context/AppContext';
import { AppToastProvider } from '@/hooks/use-toast';
import { analysisAPI, ruleAPI, alarmAPI } from '@/lib/api';

vi.mock('@/lib/api', () => ({
  analysisAPI: {
    getCoverage: vi.fn(),
    getRelationships: vi.fn(),
    getUnmatchedRules: vi.fn(),
    getUnmatchedAlarms: vi.fn(),
    getEventUsage: vi.fn(),
    detectRelationships: vi.fn(),
  },
  ruleAPI: {
    getAll: vi.fn(),
    getById: vi.fn(),
  },
  alarmAPI: {
    getAll: vi.fn(),
  },
}));

describe('Analysis and Flow Diagram navigation basics', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    analysisAPI.getCoverage.mockResolvedValue({
      data: {
        coverage: {
          total_rules: 1,
          matched_rules: 1,
          total_alarms: 1,
          matched_alarms: 1,
          coverage_percentage: 100,
        },
      },
    });
    analysisAPI.getRelationships.mockResolvedValue({
      data: { relationships: [] },
    });
    analysisAPI.getUnmatchedRules.mockResolvedValue({
      data: { unmatched_rules: [] },
    });
    analysisAPI.getUnmatchedAlarms.mockResolvedValue({
      data: { unmatched_alarms: [] },
    });
    analysisAPI.getEventUsage.mockResolvedValue({
      data: {
        event_usage: { total_unique_events: 0, events: [] },
      },
    });
    ruleAPI.getAll.mockResolvedValue({
      data: { rules: [] },
    });
  });

  it('renders Analysis dashboard for selected customer', async () => {
    render(
      <AppToastProvider>
        <AppContext.Provider
          value={{
            customers: [{ id: 1, name: 'Customer A' }],
            selectedCustomerId: 1,
            setSelectedCustomerId: vi.fn(),
          }}
        >
          <MemoryRouter initialEntries={['/analysis']}>
            <Routes>
              <Route path="/analysis" element={<Analysis />} />
            </Routes>
          </MemoryRouter>
        </AppContext.Provider>
      </AppToastProvider>
    );

    await waitFor(() => {
      expect(analysisAPI.getCoverage).toHaveBeenCalledWith(1);
    });

    expect(screen.getByText(/Analysis Dashboard/i)).toBeInTheDocument();
  });

  it('renders Flow Diagram for selected customer', async () => {
    render(
      <AppToastProvider>
        <AppContext.Provider
          value={{
            customers: [{ id: 1, name: 'Customer A' }],
            selectedCustomerId: 1,
            setSelectedCustomerId: vi.fn(),
          }}
        >
          <MemoryRouter initialEntries={['/flow-diagram']}>
            <Routes>
              <Route path="/flow-diagram" element={<FlowDiagram />} />
            </Routes>
          </MemoryRouter>
        </AppContext.Provider>
      </AppToastProvider>
    );

    await waitFor(() => {
      expect(ruleAPI.getAll).toHaveBeenCalledWith(1);
    });

    expect(screen.getByText(/Flow Diagram/i)).toBeInTheDocument();
  });
});

