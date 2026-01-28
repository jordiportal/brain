/**
 * brain-api-key router
 * 
 * Rutas con API Token authentication
 */

import { factories } from '@strapi/strapi';

// Custom routes con auth habilitada para API tokens
const customRoutes = {
  routes: [
    {
      method: 'GET',
      path: '/brain-api-keys',
      handler: 'brain-api-key.find',
    },
    {
      method: 'GET',
      path: '/brain-api-keys/:id',
      handler: 'brain-api-key.findOne',
    },
    {
      method: 'POST',
      path: '/brain-api-keys',
      handler: 'brain-api-key.create',
    },
    {
      method: 'PUT',
      path: '/brain-api-keys/:id',
      handler: 'brain-api-key.update',
    },
    {
      method: 'DELETE',
      path: '/brain-api-keys/:id',
      handler: 'brain-api-key.delete',
    }
  ]
};

export default customRoutes;
