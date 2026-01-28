/**
 * brain-model-config router
 * 
 * Rutas con API Token authentication
 */

import { factories } from '@strapi/strapi';

// Custom routes para single type
const customRoutes = {
  routes: [
    {
      method: 'GET',
      path: '/brain-model-config',
      handler: 'brain-model-config.find',
    },
    {
      method: 'PUT',
      path: '/brain-model-config',
      handler: 'brain-model-config.update',
    },
    {
      method: 'DELETE',
      path: '/brain-model-config',
      handler: 'brain-model-config.delete',
    }
  ]
};

export default customRoutes;
