import '@testing-library/jest-dom';
import { vi } from 'vitest';

// server-only throws in jsdom; stub it out for unit tests
vi.mock('server-only', () => ({}));
