import '@testing-library/jest-dom/vitest';
import { render, screen } from '@testing-library/react';

import { RootRoute } from './root';

it('shows the project empty state', () => {
  render(<RootRoute />);
  expect(screen.getByText('Create your first project')).toBeInTheDocument();
});
