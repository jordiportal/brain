import { Component, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, Router } from '@angular/router';
import { MatSidenavModule } from '@angular/material/sidenav';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatListModule } from '@angular/material/list';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatMenuModule } from '@angular/material/menu';
import { MatDividerModule } from '@angular/material/divider';
import { MatTooltipModule } from '@angular/material/tooltip';
import { AuthService } from '../core/services/auth.service';
import { MenuItem } from '../core/models';
import { ArtifactFabComponent } from '../shared/components/artifact-sidebar/artifact-fab.component';

@Component({
  selector: 'app-main-layout',
  standalone: true,
  imports: [
    CommonModule,
    RouterModule,
    MatSidenavModule,
    MatToolbarModule,
    MatListModule,
    MatIconModule,
    MatButtonModule,
    MatMenuModule,
    MatDividerModule,
    MatTooltipModule,
    ArtifactFabComponent
  ],
  template: `
    <mat-sidenav-container class="sidenav-container">
      <!-- Sidebar -->
      <mat-sidenav #sidenav 
                   [mode]="sidenavMode()" 
                   [opened]="sidenavOpened()"
                   class="sidenav"
                   [class.collapsed]="sidenavCollapsed()">
        
        <!-- Logo -->
        <div class="sidenav-header" [class.collapsed]="sidenavCollapsed()">
          <span class="material-icons brain-icon">psychology</span>
          @if (!sidenavCollapsed()) {
            <span class="logo-text">Brain</span>
          }
        </div>

        <mat-divider></mat-divider>

        <!-- Menu Items - Icon Only -->
        <mat-nav-list class="icon-only-menu">
          @for (item of menuItems; track item.route) {
            <a mat-list-item 
               [routerLink]="item.route" 
               routerLinkActive="active"
               [matTooltip]="item.label"
               matTooltipPosition="right"
               class="icon-menu-item">
              <span class="material-icons" matListItemIcon>{{ item.icon }}</span>
            </a>
          }
        </mat-nav-list>

        <div class="sidenav-footer">
          <mat-divider></mat-divider>
          <div class="sidebar-version">
            <span>Brain 2.0</span>
          </div>
        </div>
      </mat-sidenav>

      <!-- Main Content -->
      <mat-sidenav-content class="main-content">
        <!-- Toolbar -->
        <mat-toolbar color="primary" class="toolbar">
          <button mat-icon-button (click)="sidenav.toggle()" class="menu-btn">
            <span class="material-icons">menu</span>
          </button>
          
          <span class="toolbar-title">{{ pageTitle() }}</span>
          
          <span class="spacer"></span>

          <!-- Status Indicators -->
          <div class="status-indicators">
            <span class="status-badge online" matTooltip="API Conectada">
              <span class="material-icons">cloud_done</span>
            </span>
          </div>

          <!-- User Menu -->
          <button mat-button [matMenuTriggerFor]="userMenu" class="user-menu-btn">
            <span class="material-icons">account_circle</span>
            <span class="username">{{ currentUser()?.username }}</span>
            <span class="material-icons">arrow_drop_down</span>
          </button>
          
          <mat-menu #userMenu="matMenu">
            <button mat-menu-item disabled>
              <span class="material-icons" style="margin-right: 8px;">email</span>
              <span>{{ currentUser()?.email }}</span>
            </button>
            <mat-divider></mat-divider>
            <button mat-menu-item routerLink="/settings">
              <span class="material-icons" style="margin-right: 8px;">settings</span>
              <span>Configuración</span>
            </button>
            <button mat-menu-item (click)="logout()">
              <span class="material-icons" style="margin-right: 8px;">logout</span>
              <span>Cerrar Sesión</span>
            </button>
          </mat-menu>
        </mat-toolbar>

        <!-- Page Content -->
        <main class="page-content">
          <router-outlet></router-outlet>
        </main>
      </mat-sidenav-content>

      <!-- Artifact FAB - Floating action button for artifacts -->
      <app-artifact-fab></app-artifact-fab>
    </mat-sidenav-container>
  `,
  styles: [`
    .sidenav-container {
      height: 100vh;
    }

    /* Modern Dark Sidebar - Navy Theme - Icon Only */
    .sidenav {
      width: 72px;
      background: #0f172a;
      transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1);
      border-right: 1px solid rgba(255, 255, 255, 0.05);
    }

    .sidenav.collapsed {
      width: 72px;
    }

    /* Sidebar Header - Icon Only */
    .sidenav-header {
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 24px 0;
      border-bottom: 1px solid rgba(255, 255, 255, 0.05);
    }

    .sidenav-header.collapsed {
      justify-content: center;
      padding: 24px 0;
    }

    .brain-icon {
      color: #3b82f6;
      font-size: 28px;
      width: 28px;
      height: 28px;
      font-family: 'Material Icons';
      font-weight: normal;
      font-style: normal;
      line-height: 1;
      display: inline-block;
    }

    .logo-text {
      display: none;
    }

    /* Menu Items - Icon Only Design */
    mat-nav-list {
      padding: 16px 12px;
    }

    mat-nav-list.icon-only-menu {
      padding: 12px;
    }

    mat-nav-list a.icon-menu-item {
      color: rgba(255, 255, 255, 0.5);
      margin: 4px 0;
      border-radius: 12px;
      height: 48px;
      width: 48px;
      padding: 0 !important;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: all 0.2s ease;
    }

    mat-nav-list a.icon-menu-item:hover {
      background: rgba(255, 255, 255, 0.08);
      color: white;
    }

    mat-nav-list a.icon-menu-item.active {
      background: rgba(59, 130, 246, 0.15);
      color: #3b82f6;
    }

    mat-nav-list a.icon-menu-item.active::before {
      content: '';
      position: absolute;
      left: 0;
      top: 50%;
      transform: translateY(-50%);
      width: 3px;
      height: 20px;
      background: #3b82f6;
      border-radius: 0 3px 3px 0;
    }

    mat-nav-list a.icon-menu-item .material-icons {
      color: inherit;
      margin: 0;
      font-size: 24px;
      width: 24px;
      height: 24px;
      font-family: 'Material Icons';
      font-weight: normal;
      font-style: normal;
      line-height: 1;
      letter-spacing: normal;
      text-transform: none;
      display: inline-block;
      white-space: nowrap;
      word-wrap: normal;
      direction: ltr;
      -webkit-font-feature-settings: 'liga';
      -webkit-font-smoothing: antialiased;
    }

    /* Sidebar Footer - Icon Only */
    .sidenav-footer {
      position: absolute;
      bottom: 0;
      left: 0;
      right: 0;
      padding: 12px;
      border-top: 1px solid rgba(255, 255, 255, 0.05);
    }

    .sidebar-version {
      text-align: center;
      font-size: 10px;
      color: rgba(255, 255, 255, 0.3);
      font-weight: 500;
    }

    /* Main Content Area */
    .main-content {
      background: #f1f5f9;
    }

    /* Clean Toolbar - No gradient */
    .toolbar {
      position: sticky;
      top: 0;
      z-index: 100;
      background: #0f172a;
      border-bottom: 1px solid rgba(255, 255, 255, 0.05);
      height: 64px;
      padding: 0 24px;
    }

    .menu-btn {
      margin-right: 16px;
      color: rgba(255, 255, 255, 0.6);
      transition: color 0.2s ease;
    }

    .menu-btn:hover {
      color: white;
    }

    .toolbar-title {
      font-size: 20px;
      font-weight: 600;
      color: white;
      letter-spacing: -0.3px;
    }

    .spacer {
      flex: 1;
    }

    /* Status Indicators - Clean badges */
    .status-indicators {
      display: flex;
      align-items: center;
      gap: 12px;
      margin-right: 20px;
    }

    .status-badge {
      display: flex;
      align-items: center;
      justify-content: center;
      width: 36px;
      height: 36px;
      border-radius: 10px;
      background: rgba(255, 255, 255, 0.05);
      transition: all 0.2s ease;
    }

    .status-badge:hover {
      background: rgba(255, 255, 255, 0.1);
    }

    .status-badge.online {
      background: rgba(34, 197, 94, 0.15);
    }

    .status-badge.online mat-icon {
      color: #22c55e;
      font-size: 20px;
      width: 20px;
      height: 20px;
    }

    /* User Menu - Clean Design */
    .user-menu-btn {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 8px 12px;
      border-radius: 10px;
      background: rgba(255, 255, 255, 0.05);
      color: rgba(255, 255, 255, 0.8);
      font-weight: 500;
      transition: all 0.2s ease;
    }

    .user-menu-btn:hover {
      background: rgba(255, 255, 255, 0.1);
      color: white;
    }

    .username {
      max-width: 140px;
      overflow: hidden;
      text-overflow: ellipsis;
      font-size: 14px;
    }

    /* Page Content - Better spacing */
    .page-content {
      padding: 32px;
      min-height: calc(100vh - 64px);
    }

    mat-divider {
      border-color: rgba(255, 255, 255, 0.05);
    }

    /* Responsive - Keep icon-only on all sizes */
    @media (max-width: 768px) {
      .username {
        display: none;
      }
      
      .sidenav {
        width: 72px !important;
      }

      .toolbar {
        padding: 0 16px;
      }

      .page-content {
        padding: 20px;
      }
    }
  `]
})
export class MainLayoutComponent {
  sidenavOpened = signal(true);
  sidenavCollapsed = signal(false);
  sidenavMode = signal<'side' | 'over'>('side');
  pageTitle = signal('Dashboard');

  currentUser = computed(() => this.authService.currentUser());

  menuItems: MenuItem[] = [
    { label: 'Dashboard', icon: 'dashboard', route: '/dashboard' },
    { label: 'Cadenas', icon: 'account_tree', route: '/chains' },
    { label: 'Subagentes', icon: 'smart_toy', route: '/subagents' },
    { label: 'Herramientas', icon: 'build', route: '/tools' },
    { label: 'API Externa', icon: 'api', route: '/external-api' },
    { label: 'Testing LLM', icon: 'science', route: '/testing' },
    { label: 'Monitorización', icon: 'monitoring', route: '/monitoring' },
    { label: 'RAG / Documentos', icon: 'description', route: '/rag' },
    { label: 'Configuración', icon: 'settings', route: '/settings' },
  ];

  constructor(
    private authService: AuthService,
    private router: Router
  ) {
    // Ajustar sidebar según tamaño de pantalla
    this.checkScreenSize();
    window.addEventListener('resize', () => this.checkScreenSize());
  }

  private checkScreenSize(): void {
    if (window.innerWidth < 768) {
      this.sidenavMode.set('over');
      this.sidenavOpened.set(false);
    } else {
      this.sidenavMode.set('side');
      this.sidenavOpened.set(true);
    }
  }

  toggleSidenavCollapse(): void {
    this.sidenavCollapsed.update(v => !v);
  }

  logout(): void {
    this.authService.logout();
  }
}
