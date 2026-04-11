import { describe, it, expect } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Sidebar } from '../Sidebar';

describe('Sidebar', () => {
  const user = userEvent.setup();

  it('renders collapsed by default (64px)', () => {
    const { container } = render(<Sidebar activePath="/dashboard" />);
    const sidebar = container.firstChild as HTMLElement;
    expect(sidebar.className).toMatch(/w-16/);
  });

  it('shows navigation icons', () => {
    render(<Sidebar activePath="/dashboard" />);
    expect(screen.getByTestId('nav-dashboard')).toBeInTheDocument();
    expect(screen.getByTestId('nav-listings')).toBeInTheDocument();
    expect(screen.getByTestId('nav-pricing')).toBeInTheDocument();
  });

  it('highlights active nav item', () => {
    render(<Sidebar activePath="/dashboard" />);
    const dashItem = screen.getByTestId('nav-dashboard');
    expect(dashItem.className).toMatch(/bg-blue|active/);
  });

  it('expands on hover showing labels', async () => {
    render(<Sidebar activePath="/dashboard" />);
    const sidebar = screen.getByTestId('sidebar');
    await user.hover(sidebar);
    await waitFor(() => {
      expect(screen.getByText('Dashboard')).toBeVisible();
      expect(screen.getByText('Listings')).toBeVisible();
    });
  });

  it('has dark background', () => {
    const { container } = render(<Sidebar activePath="/dashboard" />);
    const sidebar = container.firstChild as HTMLElement;
    expect(sidebar.className).toMatch(/bg-\[#1e293b\]/);
  });

  it('shows logo at top', () => {
    render(<Sidebar activePath="/dashboard" />);
    expect(screen.getByTestId('sidebar-logo')).toBeInTheDocument();
  });
});
