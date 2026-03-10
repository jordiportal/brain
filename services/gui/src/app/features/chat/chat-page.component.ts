import {
  Component,
  OnInit,
  signal,
  inject,
  ChangeDetectionStrategy,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatSelectModule } from '@angular/material/select';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';

import { ChatComponent } from '../../shared/components/chat/chat.component';
import { ChatMessage, ChatFeatures } from '../../shared/components/chat/chat-message.interface';
import { ConversationListComponent } from '../../shared/components/conversation-list/conversation-list.component';
import { MemoryPanelComponent } from '../../shared/components/memory-panel/memory-panel.component';
import { SseStreamService } from '../../shared/services/sse-stream.service';
import { ConversationService } from '../../core/services/conversation.service';
import { AuthService } from '../../core/services/auth.service';
import { ApiService } from '../../core/services/api.service';
import { ConversationListItem } from '../../core/models';
import { environment } from '../../../environments/environment';

interface EngineChainItem {
  id: string;
  name: string;
}

@Component({
  selector: 'app-chat-page',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatIconModule,
    MatButtonModule,
    MatTooltipModule,
    MatSelectModule,
    MatFormFieldModule,
    MatSnackBarModule,
    ChatComponent,
    ConversationListComponent,
    MemoryPanelComponent,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="chat-page">
      <!-- Left sidebar: conversation list -->
      <div class="sidebar-left" [class.collapsed]="sidebarCollapsed()">
        @if (!sidebarCollapsed()) {
          <app-conversation-list
            [conversations]="conversations()"
            [selectedId]="activeConversationId()"
            [loading]="loadingConversations()"
            (conversationSelected)="onConversationSelected($event)"
            (newConversation)="onNewConversation()"
            (conversationDeleted)="onConversationDeleted($event)">
          </app-conversation-list>
        }
        <button mat-icon-button
                class="sidebar-toggle left-toggle"
                (click)="sidebarCollapsed.set(!sidebarCollapsed())"
                [matTooltip]="sidebarCollapsed() ? 'Mostrar conversaciones' : 'Ocultar'">
          <mat-icon>{{ sidebarCollapsed() ? 'chevron_right' : 'chevron_left' }}</mat-icon>
        </button>
      </div>

      <!-- Center: chat area -->
      <div class="chat-center">
        <!-- Toolbar -->
        <div class="chat-toolbar">
          <div class="toolbar-left">
            <mat-icon class="toolbar-icon">forum</mat-icon>
            <span class="toolbar-title">
              {{ activeTitle() || 'Nueva conversación' }}
            </span>
          </div>
          <div class="toolbar-right">
            <mat-form-field appearance="outline" class="chain-selector">
              <mat-select [(value)]="selectedChainId" (selectionChange)="onChainChange()" placeholder="Asistente">
                @for (chain of chains(); track chain.id) {
                  <mat-option [value]="chain.id">{{ chain.name }}</mat-option>
                }
              </mat-select>
            </mat-form-field>
            <button mat-icon-button
                    (click)="memoryPanelVisible.set(!memoryPanelVisible())"
                    [matTooltip]="memoryPanelVisible() ? 'Ocultar memoria' : 'Ver memoria'"
                    [class.active]="memoryPanelVisible()">
              <mat-icon>psychology</mat-icon>
            </button>
          </div>
        </div>

        <!-- Memory badge -->
        @if (memoryFactsCount() > 0) {
          <div class="memory-indicator" (click)="memoryPanelVisible.set(true)">
            <mat-icon>psychology</mat-icon>
            Brain recuerda {{ memoryFactsCount() }} hechos sobre ti
          </div>
        }

        <!-- Chat -->
        <app-chat
          [messages]="messages"
          [features]="chatFeatures"
          [isLoading]="isExecuting"
          [currentStepName]="currentStep"
          placeholder="Escribe un mensaje..."
          emptyMessage="Selecciona o crea una conversación para empezar"
          (messageSent)="onMessageSent($event)">
        </app-chat>
      </div>

      <!-- Right sidebar: memory panel -->
      @if (memoryPanelVisible()) {
        <div class="sidebar-right">
          <app-memory-panel
            [userId]="currentUserId()"
            [agentId]="null">
          </app-memory-panel>
        </div>
      }
    </div>
  `,
  styles: [`
    :host {
      display: block;
      height: calc(100vh - 64px);
      margin: -32px;
    }

    .chat-page {
      display: flex;
      height: 100%;
      overflow: hidden;
      background: #f1f5f9;
    }

    /* Left sidebar */
    .sidebar-left {
      width: 280px;
      flex-shrink: 0;
      display: flex;
      flex-direction: column;
      position: relative;
      background: white;
      border-right: 1px solid #e2e8f0;
      transition: width 0.2s ease;
    }

    .sidebar-left.collapsed {
      width: 40px;
    }

    .sidebar-toggle {
      position: absolute;
      bottom: 12px;
      width: 32px;
      height: 32px;
      z-index: 5;
      color: #64748b;
    }

    .left-toggle {
      right: 4px;
    }

    .sidebar-left.collapsed .left-toggle {
      right: 4px;
    }

    /* Center */
    .chat-center {
      flex: 1;
      display: flex;
      flex-direction: column;
      min-width: 0;
      position: relative;
    }

    .chat-toolbar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 8px 20px;
      background: white;
      border-bottom: 1px solid #e2e8f0;
      min-height: 52px;
    }

    .toolbar-left {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .toolbar-icon {
      font-size: 20px;
      width: 20px;
      height: 20px;
      color: #667eea;
    }

    .toolbar-title {
      font-size: 14px;
      font-weight: 600;
      color: #1e293b;
    }

    .toolbar-right {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .toolbar-right button {
      color: #64748b;
    }

    .toolbar-right button.active {
      color: #667eea;
      background: rgba(102, 126, 234, 0.08);
    }

    .chain-selector {
      width: 180px;
    }

    :host ::ng-deep .chain-selector .mat-mdc-form-field-subscript-wrapper {
      display: none;
    }

    :host ::ng-deep .chain-selector .mat-mdc-text-field-wrapper {
      height: 36px;
    }

    :host ::ng-deep .chain-selector .mat-mdc-form-field-infix {
      padding-top: 6px;
      padding-bottom: 6px;
      min-height: unset;
    }

    :host ::ng-deep .chain-selector .mat-mdc-select-trigger {
      font-size: 13px;
    }

    .memory-indicator {
      display: flex;
      align-items: center;
      gap: 6px;
      padding: 6px 20px;
      font-size: 12px;
      color: #667eea;
      background: rgba(102, 126, 234, 0.06);
      cursor: pointer;
      transition: background 0.15s ease;
    }

    .memory-indicator:hover {
      background: rgba(102, 126, 234, 0.12);
    }

    .memory-indicator mat-icon {
      font-size: 16px;
      width: 16px;
      height: 16px;
    }

    /* Right sidebar */
    .sidebar-right {
      width: 300px;
      flex-shrink: 0;
      overflow: hidden;
      background: white;
      border-left: 1px solid #e2e8f0;
    }

    /* Chat fills remaining space */
    :host ::ng-deep app-chat {
      flex: 1;
      display: flex;
      flex-direction: column;
      min-height: 0;
    }

    :host ::ng-deep .chat-container {
      flex: 1;
      display: flex;
      flex-direction: column;
      border-radius: 0;
    }
  `],
})
export class ChatPageComponent implements OnInit {
  private convService = inject(ConversationService);
  private sseStream = inject(SseStreamService);
  private authService = inject(AuthService);
  private apiService = inject(ApiService);
  private http = inject(HttpClient);
  private snackBar = inject(MatSnackBar);

  conversations = signal<ConversationListItem[]>([]);
  loadingConversations = signal(false);
  activeConversationId = signal<string | null>(null);
  activeTitle = signal<string | null>(null);
  sidebarCollapsed = signal(false);
  memoryPanelVisible = signal(false);
  memoryFactsCount = signal(0);
  isExecuting = signal(false);
  currentStep = signal<string | null>(null);

  messages = signal<ChatMessage[]>([]);
  chains = signal<EngineChainItem[]>([]);
  selectedChainId = 'adaptive';

  private activeProviderUrl = '';
  private activeProviderType = '';
  private activeProviderApiKey = '';
  private activeModel = '';

  currentUserId = signal<string | null>(null);

  chatFeatures: ChatFeatures = {
    intermediateSteps: true,
    images: true,
    videos: true,
    presentations: true,
    streaming: true,
    tokens: true,
    timestamps: false,
    clearButton: false,
    configPanel: false,
    attachments: true,
  };

  ngOnInit() {
    const user = this.authService.currentUser();
    if (user) {
      this.currentUserId.set(user.email);
    }

    this.loadConversations();
    this.loadChains();
    this.loadMemoryStats();
  }

  private loadConversations() {
    this.loadingConversations.set(true);
    this.convService.listConversations(100).subscribe({
      next: (res) => {
        this.conversations.set(res.conversations);
        this.loadingConversations.set(false);
      },
      error: () => this.loadingConversations.set(false),
    });
  }

  private loadChains() {
    this.apiService.getChains().subscribe({
      next: (res: any) => {
        const chainsList = (res.chains || res || []).map((c: any) => ({
          id: c.id || c.slug,
          name: c.name,
        }));
        this.chains.set(chainsList);
        if (chainsList.length > 0 && !chainsList.find((c: any) => c.id === this.selectedChainId)) {
          this.selectedChainId = chainsList[0].id;
        }
        this.loadChainProvider(this.selectedChainId);
      },
    });
  }

  onChainChange() {
    this.loadChainProvider(this.selectedChainId);
  }

  private loadChainProvider(chainId: string) {
    this.http.get<any>(`${environment.apiUrl}/chains/${chainId}/details`).subscribe({
      next: (response) => {
        const provider = response.llm_provider;
        if (provider) {
          this.activeProviderUrl = provider.baseUrl || '';
          this.activeProviderType = provider.type || 'ollama';
          this.activeProviderApiKey = provider.apiKey || '';
          this.activeModel = response.default_llm?.model
            || provider.defaultModel
            || '';
        }
      },
      error: () => {},
    });
  }

  private loadMemoryStats() {
    const uid = this.currentUserId();
    if (!uid) return;
    this.convService.getMemoryContext(uid).subscribe({
      next: (res) => this.memoryFactsCount.set(res.facts_count ?? res.facts.length),
      error: () => {},
    });
  }

  onConversationSelected(id: string) {
    this.activeConversationId.set(id);
    this.messages.set([]);

    this.convService.getConversation(id).subscribe({
      next: (detail) => {
        this.activeTitle.set(detail.title);
        if (detail.chain_id) {
          this.selectedChainId = detail.chain_id;
        }
        const chatMsgs: ChatMessage[] = detail.messages.map(m => ({
          role: m.role === 'assistant' ? 'assistant' : m.role === 'system' ? 'system' : 'user',
          content: m.content,
          timestamp: new Date(m.created_at),
          tokens: m.tokens_used || undefined,
        }));
        this.messages.set(chatMsgs);
      },
      error: () => {
        this.snackBar.open('Error cargando conversación', 'Cerrar', { duration: 3000 });
      },
    });
  }

  onNewConversation() {
    const id = crypto.randomUUID();
    this.activeConversationId.set(id);
    this.activeTitle.set(null);
    this.messages.set([]);
  }

  onConversationDeleted(id: string) {
    this.convService.deleteConversation(id).subscribe({
      next: () => {
        if (this.activeConversationId() === id) {
          this.activeConversationId.set(null);
          this.activeTitle.set(null);
          this.messages.set([]);
        }
        this.loadConversations();
      },
    });
  }

  async onMessageSent(event: any) {
    const content = typeof event === 'string' ? event : event.content;
    if (!content?.trim()) return;

    let convId = this.activeConversationId();
    if (!convId) {
      convId = crypto.randomUUID();
      this.activeConversationId.set(convId);
    }

    this.messages.update(msgs => [...msgs, {
      role: 'user' as const,
      content,
      timestamp: new Date(),
    }]);

    this.isExecuting.set(true);

    const chainId = this.selectedChainId || 'adaptive';

    const url = `${environment.apiUrl}/chains/${chainId}/invoke/stream?session_id=${convId}`;

    const result = await this.sseStream.stream({
      url,
      payload: {
        input: { message: content },
        llm_provider_url: this.activeProviderUrl || environment.ollamaDefaultUrl,
        llm_provider_type: this.activeProviderType || 'ollama',
        api_key: this.activeProviderApiKey || undefined,
        model: this.activeModel || undefined,
      },
      messages: this.messages,
      finalResponseNodeIds: ['synthesizer', 'adaptive_agent'],
    });

    this.isExecuting.set(false);

    if (!this.activeTitle()) {
      const title = content.length > 50 ? content.substring(0, 50) + '...' : content;
      this.activeTitle.set(title);
    }

    this.loadConversations();
    this.loadMemoryStats();
  }
}
