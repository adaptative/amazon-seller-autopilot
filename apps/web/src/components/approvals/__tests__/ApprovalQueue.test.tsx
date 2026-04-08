import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ApprovalQueue } from '../ApprovalQueue';

const mockActions = [
  {
    id: 'act-1',
    agentType: 'listing',
    actionType: 'listing_optimize',
    targetAsin: 'B08ABC',
    status: 'proposed',
    proposedChange: { title: 'New title' },
    reasoning: 'Improve SEO ranking',
    confidenceScore: 0.92,
    priority: 'high' as const,
    createdAt: '2026-04-08T10:00:00Z',
    expiresAt: null,
  },
  {
    id: 'act-2',
    agentType: 'pricing',
    actionType: 'price_match',
    targetAsin: 'B08DEF',
    status: 'proposed',
    proposedChange: { new_price: 19.99 },
    reasoning: 'Competitor undercut detected',
    confidenceScore: 0.87,
    priority: 'medium' as const,
    createdAt: '2026-04-08T09:00:00Z',
    expiresAt: '2026-04-09T09:00:00Z',
  },
  {
    id: 'act-3',
    agentType: 'listing',
    actionType: 'listing_optimize',
    targetAsin: 'B08GHI',
    status: 'proposed',
    proposedChange: { title: 'Better title' },
    reasoning: 'Low health score',
    confidenceScore: 0.74,
    priority: 'low' as const,
    createdAt: '2026-04-08T08:00:00Z',
    expiresAt: null,
  },
];

vi.mock('@/lib/api', () => ({
  approvalsApi: {
    listPending: vi.fn(() => Promise.resolve({ actions: mockActions, total: 3 })),
    approve: vi.fn(() => Promise.resolve({ success: true, status: 'executing' })),
    reject: vi.fn(() => Promise.resolve({ success: true, status: 'rejected' })),
    bulkApprove: vi.fn(() => Promise.resolve({ approved_count: 2 })),
  },
}));

describe('ApprovalQueue', () => {
  const user = userEvent.setup();

  it('renders approval cards for each pending action', async () => {
    render(<ApprovalQueue />);
    await waitFor(() => {
      const cards = screen.getAllByTestId('approval-card');
      expect(cards).toHaveLength(3);
    });
  });

  it('displays agent type and confidence on each card', async () => {
    render(<ApprovalQueue />);
    await waitFor(() => {
      expect(screen.getByText('listing_optimize'.replace(/_/g, ' '))).toBeInTheDocument();
      expect(screen.getByText(/92% confidence/)).toBeInTheDocument();
    });
  });

  it('shows ASIN in data badge format', async () => {
    render(<ApprovalQueue />);
    await waitFor(() => {
      const asinBadge = screen.getByText('B08ABC');
      expect(asinBadge.className).toMatch(/border-dashed|primary-pop/);
    });
  });

  it('shows priority badges', async () => {
    render(<ApprovalQueue />);
    await waitFor(() => {
      const badges = screen.getAllByTestId('priority-badge');
      expect(badges.map((b) => b.textContent)).toEqual(
        expect.arrayContaining(['high', 'medium', 'low'])
      );
    });
  });

  it('filters by agent type', async () => {
    render(<ApprovalQueue />);
    await waitFor(() => screen.getAllByTestId('approval-card'));

    const filter = screen.getByTestId('agent-filter');
    await user.selectOptions(filter, 'pricing');

    const cards = screen.getAllByTestId('approval-card');
    expect(cards).toHaveLength(1);
    expect(within(cards[0]).getByText('pricing')).toBeInTheDocument();
  });

  it('sorts by confidence descending', async () => {
    render(<ApprovalQueue />);
    await waitFor(() => screen.getAllByTestId('approval-card'));

    const sortSelect = screen.getByTestId('sort-select');
    await user.selectOptions(sortSelect, 'confidence');

    const cards = screen.getAllByTestId('approval-card');
    const confidences = cards.map((c) => {
      const text = within(c).getByText(/confidence/).textContent!;
      return parseInt(text);
    });
    expect(confidences).toEqual([92, 87, 74]);
  });

  it('approve button removes card from list', async () => {
    render(<ApprovalQueue />);
    await waitFor(() => screen.getAllByTestId('approval-card'));

    const firstCard = screen.getAllByTestId('approval-card')[0];
    await user.click(within(firstCard).getByRole('button', { name: /approve/i }));

    const { approvalsApi } = await import('@/lib/api');
    expect(approvalsApi.approve).toHaveBeenCalled();
    await waitFor(() => {
      expect(screen.getAllByTestId('approval-card')).toHaveLength(2);
    });
  });

  it('reject button removes card from list', async () => {
    render(<ApprovalQueue />);
    await waitFor(() => screen.getAllByTestId('approval-card'));

    const firstCard = screen.getAllByTestId('approval-card')[0];
    await user.click(within(firstCard).getByRole('button', { name: /reject/i }));

    const { approvalsApi } = await import('@/lib/api');
    expect(approvalsApi.reject).toHaveBeenCalled();
    await waitFor(() => {
      expect(screen.getAllByTestId('approval-card')).toHaveLength(2);
    });
  });

  it('bulk approve calls API with threshold', async () => {
    render(<ApprovalQueue />);
    await waitFor(() => screen.getAllByTestId('approval-card'));

    await user.click(screen.getByTestId('bulk-approve-btn'));

    const { approvalsApi } = await import('@/lib/api');
    expect(approvalsApi.bulkApprove).toHaveBeenCalledWith(0.85);
  });

  it('shows empty state when no actions pending', async () => {
    const { approvalsApi } = await import('@/lib/api');
    (approvalsApi.listPending as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      actions: [],
      total: 0,
    });

    render(<ApprovalQueue />);
    await waitFor(() => {
      expect(screen.getByTestId('empty-state')).toBeInTheDocument();
      expect(screen.getByText(/all caught up/i)).toBeInTheDocument();
    });
  });
});
