import { createBrowserRouter } from 'react-router-dom';

import { RootRoute } from '../routes/root';

export const router = createBrowserRouter([
  {
    path: '/',
    element: <RootRoute />,
  },
]);
