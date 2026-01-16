import { Routes } from '@angular/router';
import { authGuard, publicGuard } from './core/guards/auth.guard';

export const routes: Routes = [
  // Public routes
  {
    path: 'login',
    canActivate: [publicGuard],
    loadComponent: () => import('./features/auth/login.component').then(m => m.LoginComponent)
  },

  // Protected routes with main layout
  {
    path: '',
    canActivate: [authGuard],
    loadComponent: () => import('./layouts/main-layout.component').then(m => m.MainLayoutComponent),
    children: [
      {
        path: '',
        redirectTo: 'dashboard',
        pathMatch: 'full'
      },
      {
        path: 'dashboard',
        loadComponent: () => import('./features/dashboard/dashboard.component').then(m => m.DashboardComponent)
      },
      {
        path: 'chains',
        loadComponent: () => import('./features/chains/chains.component').then(m => m.ChainsComponent)
      },
      {
        path: 'monitoring',
        loadComponent: () => import('./features/monitoring/monitoring.component').then(m => m.MonitoringComponent)
      },
      {
        path: 'settings',
        loadComponent: () => import('./features/settings/settings.component').then(m => m.SettingsComponent)
      },
      {
        path: 'rag',
        loadComponent: () => import('./features/rag/rag.component').then(m => m.RagComponent)
      },
      {
        path: 'testing',
        loadComponent: () => import('./features/testing/testing.component').then(m => m.TestingComponent)
      },
      {
        path: 'tools',
        loadComponent: () => import('./features/tools/tools.component').then(m => m.ToolsComponent)
      }
    ]
  },

  // Fallback
  {
    path: '**',
    redirectTo: 'dashboard'
  }
];
