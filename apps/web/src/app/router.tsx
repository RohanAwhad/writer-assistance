import { createBrowserRouter } from 'react-router-dom';

import { ProjectRoute } from '../routes/project';
import { RootRoute } from '../routes/root';

export const router = createBrowserRouter([
  {
    path: '/',
    element: <RootRoute />,
  },
  {
    path: '/projects/:projectId',
    element: <ProjectRoute />,
  },
]);
