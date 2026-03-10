import {
  Component,
  Input,
  Output,
  EventEmitter,
  signal,
  computed,
  OnChanges,
  SimpleChanges,
  ChangeDetectionStrategy,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatListModule } from '@angular/material/list';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatInputModule } from '@angular/material/input';
import { MatFormFieldModule } from '@angular/material/form-field';
import { ConversationListItem } from '../../../core/models';

interface GroupedConversations {
  label: string;
  conversations: ConversationListItem[];
}

@Component({
  selector: 'app-conversation-list',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatListModule,
    MatIconModule,
    MatButtonModule,
    MatTooltipModule,
    MatInputModule,
    MatFormFieldModule,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="conv-list-container">
      <div class="conv-list-header">
        <button mat-flat-button class="new-chat-btn" (click)="newConversation.emit()">
          <mat-icon>add</mat-icon>
          Nueva conversación
        </button>
      </div>

      <div class="conv-list-search">
        <mat-form-field appearance="outline" class="search-field">
          <mat-icon matPrefix>search</mat-icon>
          <input matInput
                 placeholder="Buscar..."
                 [(ngModel)]="searchText"
                 (ngModelChange)="onSearchChange()">
        </mat-form-field>
      </div>

      <div class="conv-list-body">
        @if (loading) {
          <div class="loading-state">
            <mat-icon>hourglass_empty</mat-icon>
            <span>Cargando...</span>
          </div>
        } @else if (groupedConversations().length === 0) {
          <div class="empty-state">
            <mat-icon>forum</mat-icon>
            <span>Sin conversaciones</span>
          </div>
        } @else {
          @for (group of groupedConversations(); track group.label) {
            <div class="conv-group">
              <div class="conv-group-label">{{ group.label }}</div>
              @for (conv of group.conversations; track conv.id) {
                <div class="conv-item"
                     [class.selected]="conv.id === selectedId"
                     (click)="conversationSelected.emit(conv.id)"
                     [matTooltip]="conv.title || 'Sin título'">
                  <mat-icon class="conv-icon">chat_bubble_outline</mat-icon>
                  <div class="conv-info">
                    <span class="conv-title">{{ conv.title || 'Sin título' }}</span>
                    <span class="conv-time">{{ formatRelativeTime(conv.updated_at) }}</span>
                  </div>
                  <button mat-icon-button
                          class="conv-delete"
                          (click)="onDelete($event, conv)"
                          matTooltip="Eliminar">
                    <mat-icon>close</mat-icon>
                  </button>
                </div>
              }
            </div>
          }
        }
      </div>
    </div>
  `,
  styles: [`
    :host {
      display: flex;
      flex-direction: column;
      height: 100%;
    }

    .conv-list-container {
      display: flex;
      flex-direction: column;
      height: 100%;
      background: white;
    }

    .conv-list-header {
      padding: 12px;
    }

    .new-chat-btn {
      width: 100%;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: white;
      font-weight: 500;
      border-radius: 8px;
      height: 40px;
    }

    .new-chat-btn mat-icon {
      font-size: 18px;
      width: 18px;
      height: 18px;
      margin-right: 6px;
    }

    .conv-list-search {
      padding: 0 12px;
    }

    .search-field {
      width: 100%;
    }

    :host ::ng-deep .search-field .mat-mdc-form-field-subscript-wrapper {
      display: none;
    }

    :host ::ng-deep .search-field .mat-mdc-text-field-wrapper {
      height: 36px;
    }

    :host ::ng-deep .search-field .mat-mdc-form-field-infix {
      padding-top: 6px;
      padding-bottom: 6px;
      min-height: unset;
    }

    :host ::ng-deep .search-field input {
      font-size: 13px;
    }

    .conv-list-body {
      flex: 1;
      overflow-y: auto;
      padding: 4px 8px;
    }

    .conv-group-label {
      font-size: 11px;
      font-weight: 600;
      text-transform: uppercase;
      color: #94a3b8;
      padding: 12px 8px 4px;
      letter-spacing: 0.5px;
    }

    .conv-item {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 8px 10px;
      border-radius: 8px;
      cursor: pointer;
      transition: background 0.15s ease;
      position: relative;
    }

    .conv-item:hover {
      background: #f1f5f9;
    }

    .conv-item.selected {
      background: rgba(102, 126, 234, 0.08);
      border-left: 3px solid #667eea;
    }

    .conv-icon {
      font-size: 18px;
      width: 18px;
      height: 18px;
      color: #94a3b8;
      flex-shrink: 0;
    }

    .conv-item.selected .conv-icon {
      color: #667eea;
    }

    .conv-info {
      flex: 1;
      min-width: 0;
      display: flex;
      flex-direction: column;
      gap: 2px;
    }

    .conv-title {
      font-size: 13px;
      color: #1e293b;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .conv-time {
      font-size: 11px;
      color: #94a3b8;
    }

    .conv-delete {
      opacity: 0;
      transition: all 0.15s ease;
      width: 28px;
      height: 28px;
      flex-shrink: 0;
      color: #94a3b8;
    }

    .conv-delete mat-icon {
      font-size: 16px;
      width: 16px;
      height: 16px;
    }

    .conv-item:hover .conv-delete {
      opacity: 0.7;
    }

    .conv-delete:hover {
      opacity: 1 !important;
      color: #ef4444;
    }

    .empty-state, .loading-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 8px;
      padding: 40px 16px;
      color: #94a3b8;
    }

    .empty-state mat-icon, .loading-state mat-icon {
      font-size: 32px;
      width: 32px;
      height: 32px;
      color: #cbd5e1;
    }
  `],
})
export class ConversationListComponent implements OnChanges {
  @Input() conversations: ConversationListItem[] = [];
  @Input() selectedId: string | null = null;
  @Input() loading = false;
  @Output() conversationSelected = new EventEmitter<string>();
  @Output() newConversation = new EventEmitter<void>();
  @Output() conversationDeleted = new EventEmitter<string>();

  searchText = '';
  private conversationList = signal<ConversationListItem[]>([]);
  private filteredConversations = signal<ConversationListItem[]>([]);

  ngOnChanges(changes: SimpleChanges) {
    if (changes['conversations']) {
      this.conversationList.set(this.conversations);
    }
  }

  groupedConversations = computed<GroupedConversations[]>(() => {
    const all = this.conversationList();
    const convs = this.filteredConversations().length > 0 || this.searchText
      ? this.filteredConversations()
      : all;

    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const yesterday = new Date(today.getTime() - 86400000);
    const weekAgo = new Date(today.getTime() - 7 * 86400000);

    const groups: Record<string, ConversationListItem[]> = {
      'Hoy': [],
      'Ayer': [],
      'Esta semana': [],
      'Anteriores': [],
    };

    for (const c of convs) {
      const d = new Date(c.updated_at);
      if (d >= today) groups['Hoy'].push(c);
      else if (d >= yesterday) groups['Ayer'].push(c);
      else if (d >= weekAgo) groups['Esta semana'].push(c);
      else groups['Anteriores'].push(c);
    }

    return Object.entries(groups)
      .filter(([, items]) => items.length > 0)
      .map(([label, conversations]) => ({ label, conversations }));
  });

  onSearchChange() {
    if (!this.searchText.trim()) {
      this.filteredConversations.set([]);
      return;
    }
    const q = this.searchText.toLowerCase();
    this.filteredConversations.set(
      this.conversationList().filter(c =>
        (c.title || '').toLowerCase().includes(q)
      )
    );
  }

  onDelete(event: Event, conv: ConversationListItem) {
    event.stopPropagation();
    const title = conv.title || 'Sin título';
    if (confirm(`¿Eliminar la conversación "${title}"? Esta acción no se puede deshacer.`)) {
      this.conversationDeleted.emit(conv.id);
    }
  }

  formatRelativeTime(dateStr: string): string {
    const d = new Date(dateStr);
    const now = new Date();
    const diff = now.getTime() - d.getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return 'Ahora';
    if (mins < 60) return `Hace ${mins}m`;
    const hours = Math.floor(mins / 60);
    if (hours < 24) return `Hace ${hours}h`;
    const days = Math.floor(hours / 24);
    if (days < 7) return `Hace ${days}d`;
    return d.toLocaleDateString('es-ES', { day: 'numeric', month: 'short' });
  }
}
