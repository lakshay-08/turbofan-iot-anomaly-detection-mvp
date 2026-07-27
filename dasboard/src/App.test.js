import { render, screen } from '@testing-library/react';
import App from './App';

beforeEach(() => {
  global.fetch = jest.fn(() =>
    Promise.resolve({
      ok: true,
      json: async () => [],
    })
  );
});

test('renders the monitoring dashboard heading', async () => {
  render(<App />);
  expect(await screen.findByText(/predictive maintenance monitoring/i)).toBeInTheDocument();
});
