import React from 'react';
import { render, screen } from '@testing-library/react';
import App from './app/App';

test('renders app title', () => {
  render(<App />);
  expect(screen.getByText(/QtoINS/i)).toBeInTheDocument();
});
