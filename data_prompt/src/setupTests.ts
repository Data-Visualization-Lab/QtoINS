// jest-dom adds custom jest matchers for asserting on DOM nodes.
// allows you to do things like:
// expect(element).toHaveTextContent(/react/i)
// learn more: https://github.com/testing-library/jest-dom
import '@testing-library/jest-dom';

// JSDOM doesn't implement the canvas APIs required by react-vega.
// Mocking the component keeps unit tests focused on app rendering behavior.
jest.mock('react-vega', () => ({
  VegaLite: () => null,
}));
