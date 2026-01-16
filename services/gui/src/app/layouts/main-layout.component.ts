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
    MatTooltipModule
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
          <mat-icon class="brain-icon">psychology</mat-icon>
          @if (!sidenavCollapsed()) {
            <span class="logo-text">Brain</span>
          }
        </div>

        <mat-divider></mat-divider>

        <!-- Menu Items -->
        <mat-nav-list>
          @for (item of menuItems; track item.route) {
            <a mat-list-item 
               [routerLink]="item.route" 
               routerLinkActive="active"
               [matTooltip]="sidenavCollapsed() ? item.label : ''"
               matTooltipPosition="right">
              <mat-icon matListItemIcon>{{ item.icon }}</mat-icon>
              @if (!sidenavCollapsed()) {
                <span matListItemTitle>{{ item.label }}</span>
              }
            </a>
          }
        </mat-nav-list>

        <div class="sidenav-footer">
          <mat-divider></mat-divider>
          <button mat-icon-button (click)="toggleSidenavCollapse()" class="collapse-btn">
            <mat-icon>{{ sidenavCollapsed() ? 'chevron_right' : 'chevron_left' }}</mat-icon>
          </button>
        </div>
      </mat-sidenav>

      <!-- Main Content -->
      <mat-sidenav-content class="main-content">
        <!-- Toolbar -->
        <mat-toolbar color="primary" class="toolbar">
          <button mat-icon-button (click)="sidenav.toggle()" class="menu-btn">
            <mat-icon>menu</mat-icon>
          </button>
          
          <span class="toolbar-title">{{ pageTitle() }}</span>
          
          <span class="spacer"></span>

          <!-- Status Indicators -->
          <div class="status-indicators">
            <span class="status-badge online" matTooltip="API Conectada">
              <mat-icon>cloud_done</mat-icon>
            </span>
          </div>

          <!-- User Menu -->
          <button mat-button [matMenuTriggerFor]="userMenu" class="user-menu-btn">
            <mat-icon>account_circle</mat-icon>
            <span class="username">{{ currentUser()?.username }}</span>
            <mat-icon>arrow_drop_down</mat-icon>
          </button>
          
          <mat-menu #userMenu="matMenu">
            <button mat-menu-item disabled>
              <mat-icon>email</mat-icon>
              <span>{{ currentUser()?.email }}</span>
            </button>
            <mat-divider></mat-divider>
            <button mat-menu-item routerLink="/settings">
              <mat-icon>settings</mat-icon>
              <span>Configuración</span>
            </button>
            <button mat-menu-item (click)="logout()">
              <mat-icon>logout</mat-icon>
              <span>Cerrar Sesión</span>
            </button>
          </mat-menu>
        </mat-toolbar>

        <!-- Page Content -->
        <main class="page-content">
          <router-outlet></router-outlet>
        </main>
      </mat-sidenav-content>
    </mat-sidenav-container>
  `,
  styles: [`
    .sidenav-container {
      height: 100vh;
    }

    .sidenav {
      width: 260px;
      background: #1a1a2e;
      transition: width 0.3s ease;
    }

    .sidenav.collapsed {
      width: 72px;
    }

    .sidenav-header {
      display: flex;
      align-items: center;
      padding: 20px;
      gap: 12px;
    }

    .sidenav-header.collapsed {
      justify-content: center;
      padding: 20px 0;
    }

    .brain-icon {
      color: #e94560;
      font-size: 32px;
      width: 32px;
      height: 32px;
    }

    .logo-text {
      font-size: 24px;
      font-weight: 700;
      color: white;
    }

    mat-nav-list {
      padding-top: 8px;
    }

    mat-nav-list a {
      color: rgba(255, 255, 255, 0.7);
      margin: 4px 8px;
      border-radius: 8px;
    }

    mat-nav-list a:hover {
      background: rgba(255, 255, 255, 0.1);
      color: white;
    }

    mat-nav-list a.active {
      background: rgba(233, 69, 96, 0.2);
      color: #e94560;
    }

    mat-nav-list a mat-icon {
      color: inherit;
    }

    .sidenav-footer {
      position: absolute;
      bottom: 0;
      left: 0;
      right: 0;
      padding: 8px;
    }

    .collapse-btn {
      width: 100%;
      color: rgba(255, 255, 255, 0.5);
    }

    .main-content {
      background: #f5f5f5;
    }

    .toolbar {
      position: sticky;
      top: 0;
      z-index: 100;
      background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    }

    .menu-btn {
      margin-right: 8px;
    }

    .toolbar-title {
      font-size: 18px;
      font-weight: 500;
    }

    .spacer {
      flex: 1;
    }

    .status-indicators {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-right: 16px;
    }

    .status-badge {
      display: flex;
      align-items: center;
      padding: 4px 8px;
      border-radius: 16px;
      font-size: 12px;
    }

    .status-badge.online {
      background: rgba(76, 175, 80, 0.2);
      color: #4caf50;
    }

    .status-badge mat-icon {
      font-size: 18px;
      width: 18px;
      height: 18px;
    }

    .user-menu-btn {
      display: flex;
      align-items: center;
      gap: 4px;
    }

    .username {
      max-width: 120px;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .page-content {
      padding: 24px;
      min-height: calc(100vh - 64px);
    }

    mat-divider {
      border-color: rgba(255, 255, 255, 0.1);
    }

    @media (max-width: 768px) {
      .username {
        display: none;
      }
      
      .sidenav {
        width: 260px !important;
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
    { label: 'Herramientas', icon: 'build', route: '/tools' },
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
