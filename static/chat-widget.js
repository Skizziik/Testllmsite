/**
 * Tryll RAG Chat Widget
 * Floating chat button with full transparency on RAG results
 */

(function() {
    'use strict';

    // Configuration
    const CONFIG = {
        serverUrl: null, // Will be fetched from /api/chat/config
        wsReconnectInterval: 3000,
        maxReconnectAttempts: 5
    };

    // State
    let state = {
        isOpen: false,
        isConnected: false,
        isProcessing: false,
        ws: null,
        reconnectAttempts: 0,
        currentSession: null,
        messages: [],
        lastRagChunks: [],
        lastRagIds: [],
        serverConfig: null,
        agentId: null
    };

    // Create widget HTML
    function createWidget() {
        const widget = document.createElement('div');
        widget.id = 'tryll-chat-widget';
        widget.innerHTML = `
            <!-- Floating Button -->
            <button id="tryll-chat-btn" class="tryll-chat-btn" title="Ask Minecraft Assistant">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                </svg>
                <span class="tryll-status-dot"></span>
            </button>

            <!-- Chat Window -->
            <div id="tryll-chat-window" class="tryll-chat-window">
                <div class="tryll-chat-header">
                    <div class="tryll-chat-title">
                        <span class="tryll-chat-icon">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="20" height="20">
                                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                            </svg>
                        </span>
                        <div>
                            <span class="tryll-title-text">Minecraft Assistant</span>
                            <span class="tryll-connection-status" id="tryll-connection-status">Connecting...</span>
                        </div>
                    </div>
                    <div class="tryll-chat-actions">
                        <button class="tryll-action-btn" id="tryll-config-btn" title="Server Config">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18">
                                <circle cx="12" cy="12" r="3"></circle>
                                <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
                            </svg>
                        </button>
                        <button class="tryll-action-btn" id="tryll-minimize-btn" title="Minimize">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18">
                                <line x1="5" y1="12" x2="19" y2="12"></line>
                            </svg>
                        </button>
                    </div>
                </div>

                <div class="tryll-chat-body" id="tryll-chat-body">
                    <div class="tryll-welcome-message">
                        <div class="tryll-welcome-icon">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="48" height="48">
                                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                            </svg>
                        </div>
                        <h3>Minecraft Assistant</h3>
                        <p>Ask any question about Minecraft!</p>
                        <p class="tryll-welcome-hint">Try: "How do I craft a pickaxe?"</p>
                    </div>
                </div>

                <div class="tryll-chat-input-container">
                    <textarea
                        id="tryll-chat-input"
                        class="tryll-chat-input"
                        placeholder="Ask about Minecraft..."
                        rows="1"
                    ></textarea>
                    <button id="tryll-send-btn" class="tryll-send-btn" disabled>
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="20" height="20">
                            <line x1="22" y1="2" x2="11" y2="13"></line>
                            <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
                        </svg>
                    </button>
                </div>
            </div>

            <!-- Config Modal -->
            <div id="tryll-config-modal" class="tryll-modal">
                <div class="tryll-modal-content">
                    <div class="tryll-modal-header">
                        <h3>Server Configuration</h3>
                        <button class="tryll-modal-close" id="tryll-config-close">&times;</button>
                    </div>
                    <div class="tryll-modal-body" id="tryll-config-body">
                        <div class="tryll-loading">Loading configuration...</div>
                    </div>
                </div>
            </div>

            <!-- RAG Details Modal -->
            <div id="tryll-rag-modal" class="tryll-modal">
                <div class="tryll-modal-content tryll-modal-large">
                    <div class="tryll-modal-header">
                        <h3>RAG Chunks Details</h3>
                        <button class="tryll-modal-close" id="tryll-rag-close">&times;</button>
                    </div>
                    <div class="tryll-modal-body" id="tryll-rag-body">
                    </div>
                </div>
            </div>

            <!-- Feedback Modal -->
            <div id="tryll-feedback-modal" class="tryll-modal">
                <div class="tryll-modal-content">
                    <div class="tryll-modal-header">
                        <h3>Send Feedback</h3>
                        <button class="tryll-modal-close" id="tryll-feedback-close">&times;</button>
                    </div>
                    <div class="tryll-modal-body">
                        <div class="tryll-feedback-form">
                            <label>What could be improved?</label>
                            <textarea id="tryll-feedback-text" placeholder="Describe what was wrong or how the answer could be better..."></textarea>
                            <label>Suggested better answer (optional)</label>
                            <textarea id="tryll-feedback-suggestion" placeholder="Write a better answer if you know one..."></textarea>
                            <button id="tryll-feedback-submit" class="tryll-btn-primary">Submit Feedback</button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(widget);
        injectStyles();
        attachEventListeners();
    }

    // Inject CSS styles
    function injectStyles() {
        const style = document.createElement('style');
        style.textContent = `
            /* Chat Widget Styles - Matching Tryll Dashboard Theme */
            #tryll-chat-widget {
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
                -webkit-font-smoothing: antialiased;
            }

            /* Floating Button */
            .tryll-chat-btn {
                position: fixed;
                bottom: 24px;
                right: 24px;
                width: 60px;
                height: 60px;
                border-radius: 50%;
                background: linear-gradient(135deg, #3B82F6 0%, #1D4ED8 100%);
                border: none;
                cursor: pointer;
                box-shadow: 0 4px 20px rgba(59, 130, 246, 0.4);
                transition: all 0.3s ease;
                z-index: 10000;
                display: flex;
                align-items: center;
                justify-content: center;
                color: white;
            }

            .tryll-chat-btn:hover {
                transform: scale(1.1);
                box-shadow: 0 6px 30px rgba(59, 130, 246, 0.5);
            }

            .tryll-chat-btn svg {
                width: 28px;
                height: 28px;
            }

            .tryll-status-dot {
                position: absolute;
                top: 8px;
                right: 8px;
                width: 12px;
                height: 12px;
                border-radius: 50%;
                background: #EF4444;
                border: 2px solid white;
                transition: background 0.3s ease;
            }

            .tryll-status-dot.connected {
                background: #10B981;
            }

            .tryll-chat-btn.open {
                transform: rotate(90deg) scale(0);
                opacity: 0;
                pointer-events: none;
            }

            /* Chat Window */
            .tryll-chat-window {
                position: fixed;
                bottom: 24px;
                right: 24px;
                width: 420px;
                height: 600px;
                max-height: calc(100vh - 48px);
                background: #000000;
                background-image: radial-gradient(ellipse 80% 50% at 50% -20%, rgba(59, 130, 246, 0.15), transparent);
                border-radius: 16px;
                border: 1px solid rgba(255, 255, 255, 0.1);
                box-shadow: 0 25px 50px rgba(0, 0, 0, 0.5);
                display: flex;
                flex-direction: column;
                z-index: 10001;
                transform: scale(0.8) translateY(20px);
                opacity: 0;
                pointer-events: none;
                transition: all 0.3s ease;
            }

            .tryll-chat-window.open {
                transform: scale(1) translateY(0);
                opacity: 1;
                pointer-events: all;
            }

            /* Chat Header */
            .tryll-chat-header {
                padding: 16px 20px;
                border-bottom: 1px solid rgba(255, 255, 255, 0.08);
                display: flex;
                justify-content: space-between;
                align-items: center;
                background: rgba(0, 0, 0, 0.3);
                border-radius: 16px 16px 0 0;
            }

            .tryll-chat-title {
                display: flex;
                align-items: center;
                gap: 12px;
            }

            .tryll-chat-icon {
                width: 40px;
                height: 40px;
                background: rgba(59, 130, 246, 0.15);
                border: 1px solid rgba(59, 130, 246, 0.3);
                border-radius: 10px;
                display: flex;
                align-items: center;
                justify-content: center;
                color: #3B82F6;
            }

            .tryll-title-text {
                display: block;
                color: #F6F0EB;
                font-weight: 600;
                font-size: 1rem;
            }

            .tryll-connection-status {
                font-size: 0.75rem;
                color: rgba(255, 255, 255, 0.5);
            }

            .tryll-connection-status.connected {
                color: #10B981;
            }

            .tryll-connection-status.error {
                color: #EF4444;
            }

            .tryll-chat-actions {
                display: flex;
                gap: 8px;
            }

            .tryll-action-btn {
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                padding: 8px;
                cursor: pointer;
                color: rgba(255, 255, 255, 0.6);
                transition: all 0.2s ease;
            }

            .tryll-action-btn:hover {
                background: rgba(59, 130, 246, 0.2);
                color: #3B82F6;
                border-color: rgba(59, 130, 246, 0.3);
            }

            /* Chat Body */
            .tryll-chat-body {
                flex: 1;
                overflow-y: auto;
                padding: 20px;
                display: flex;
                flex-direction: column;
                gap: 16px;
            }

            .tryll-welcome-message {
                text-align: center;
                padding: 40px 20px;
                color: rgba(255, 255, 255, 0.7);
            }

            .tryll-welcome-icon {
                margin-bottom: 16px;
                color: rgba(59, 130, 246, 0.5);
            }

            .tryll-welcome-message h3 {
                color: #F6F0EB;
                margin-bottom: 8px;
                font-size: 1.25rem;
            }

            .tryll-welcome-message p {
                margin-bottom: 8px;
            }

            .tryll-welcome-hint {
                font-size: 0.85rem;
                color: rgba(255, 255, 255, 0.4);
                font-style: italic;
            }

            /* Messages */
            .tryll-message {
                display: flex;
                flex-direction: column;
                max-width: 90%;
            }

            .tryll-message.user {
                align-self: flex-end;
            }

            .tryll-message.assistant {
                align-self: flex-start;
            }

            .tryll-message-content {
                padding: 12px 16px;
                border-radius: 12px;
                font-size: 0.9rem;
                line-height: 1.5;
            }

            .tryll-message.user .tryll-message-content {
                background: #3B82F6;
                color: white;
                border-bottom-right-radius: 4px;
            }

            .tryll-message.assistant .tryll-message-content {
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                color: rgba(255, 255, 255, 0.9);
                border-bottom-left-radius: 4px;
            }

            /* RAG Info */
            .tryll-rag-info {
                margin-top: 8px;
                padding: 10px 12px;
                background: rgba(59, 130, 246, 0.1);
                border: 1px solid rgba(59, 130, 246, 0.2);
                border-radius: 8px;
                font-size: 0.8rem;
            }

            .tryll-rag-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                color: rgba(255, 255, 255, 0.6);
                margin-bottom: 6px;
            }

            .tryll-rag-view-btn {
                background: transparent;
                border: none;
                color: #3B82F6;
                cursor: pointer;
                font-size: 0.75rem;
                padding: 2px 6px;
                border-radius: 4px;
                transition: background 0.2s;
            }

            .tryll-rag-view-btn:hover {
                background: rgba(59, 130, 246, 0.2);
            }

            .tryll-rag-chunks {
                display: flex;
                flex-wrap: wrap;
                gap: 4px;
            }

            .tryll-chunk-tag {
                background: rgba(59, 130, 246, 0.2);
                color: #60A5FA;
                padding: 2px 8px;
                border-radius: 4px;
                font-size: 0.7rem;
                font-family: monospace;
            }

            /* Feedback Actions */
            .tryll-feedback-actions {
                display: flex;
                gap: 8px;
                margin-top: 8px;
            }

            .tryll-feedback-btn {
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 6px;
                padding: 6px 12px;
                cursor: pointer;
                color: rgba(255, 255, 255, 0.6);
                font-size: 0.8rem;
                display: flex;
                align-items: center;
                gap: 4px;
                transition: all 0.2s ease;
            }

            .tryll-feedback-btn:hover {
                background: rgba(255, 255, 255, 0.1);
            }

            .tryll-feedback-btn.positive:hover {
                background: rgba(16, 185, 129, 0.2);
                border-color: rgba(16, 185, 129, 0.3);
                color: #10B981;
            }

            .tryll-feedback-btn.negative:hover {
                background: rgba(239, 68, 68, 0.2);
                border-color: rgba(239, 68, 68, 0.3);
                color: #EF4444;
            }

            .tryll-feedback-btn.active.positive {
                background: rgba(16, 185, 129, 0.3);
                border-color: #10B981;
                color: #10B981;
            }

            .tryll-feedback-btn.active.negative {
                background: rgba(239, 68, 68, 0.3);
                border-color: #EF4444;
                color: #EF4444;
            }

            /* Typing Indicator */
            .tryll-typing {
                display: flex;
                gap: 4px;
                padding: 12px 16px;
            }

            .tryll-typing-dot {
                width: 8px;
                height: 8px;
                background: rgba(59, 130, 246, 0.5);
                border-radius: 50%;
                animation: tryll-bounce 1.4s infinite ease-in-out;
            }

            .tryll-typing-dot:nth-child(1) { animation-delay: -0.32s; }
            .tryll-typing-dot:nth-child(2) { animation-delay: -0.16s; }

            @keyframes tryll-bounce {
                0%, 80%, 100% { transform: scale(0); }
                40% { transform: scale(1); }
            }

            /* Input Area */
            .tryll-chat-input-container {
                padding: 16px;
                border-top: 1px solid rgba(255, 255, 255, 0.08);
                display: flex;
                gap: 12px;
                align-items: flex-end;
            }

            .tryll-chat-input {
                flex: 1;
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 12px;
                padding: 12px 16px;
                color: rgba(255, 255, 255, 0.9);
                font-size: 0.9rem;
                font-family: inherit;
                resize: none;
                max-height: 120px;
                line-height: 1.4;
                transition: border-color 0.2s ease;
            }

            .tryll-chat-input:focus {
                outline: none;
                border-color: #3B82F6;
            }

            .tryll-chat-input::placeholder {
                color: rgba(255, 255, 255, 0.4);
            }

            .tryll-send-btn {
                width: 44px;
                height: 44px;
                background: #3B82F6;
                border: none;
                border-radius: 12px;
                cursor: pointer;
                color: white;
                display: flex;
                align-items: center;
                justify-content: center;
                transition: all 0.2s ease;
            }

            .tryll-send-btn:hover:not(:disabled) {
                background: #2563EB;
                transform: scale(1.05);
            }

            .tryll-send-btn:disabled {
                opacity: 0.5;
                cursor: not-allowed;
            }

            /* Modals */
            .tryll-modal {
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0, 0, 0, 0.8);
                display: none;
                justify-content: center;
                align-items: center;
                z-index: 10002;
                backdrop-filter: blur(4px);
            }

            .tryll-modal.open {
                display: flex;
            }

            .tryll-modal-content {
                background: #0a0a0a;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 16px;
                width: 90%;
                max-width: 500px;
                max-height: 80vh;
                overflow: hidden;
                display: flex;
                flex-direction: column;
            }

            .tryll-modal-large {
                max-width: 800px;
            }

            .tryll-modal-header {
                padding: 20px;
                border-bottom: 1px solid rgba(255, 255, 255, 0.08);
                display: flex;
                justify-content: space-between;
                align-items: center;
            }

            .tryll-modal-header h3 {
                color: #F6F0EB;
                font-size: 1.1rem;
                font-weight: 600;
            }

            .tryll-modal-close {
                background: transparent;
                border: none;
                color: rgba(255, 255, 255, 0.6);
                font-size: 1.5rem;
                cursor: pointer;
                padding: 0;
                line-height: 1;
            }

            .tryll-modal-close:hover {
                color: white;
            }

            .tryll-modal-body {
                padding: 20px;
                overflow-y: auto;
                color: rgba(255, 255, 255, 0.8);
            }

            /* Config Display */
            .tryll-config-grid {
                display: grid;
                gap: 12px;
            }

            .tryll-config-item {
                display: flex;
                justify-content: space-between;
                padding: 12px;
                background: rgba(255, 255, 255, 0.03);
                border-radius: 8px;
                border: 1px solid rgba(255, 255, 255, 0.05);
            }

            .tryll-config-label {
                color: rgba(255, 255, 255, 0.6);
                font-size: 0.85rem;
            }

            .tryll-config-value {
                color: #3B82F6;
                font-weight: 500;
                font-family: monospace;
            }

            /* RAG Details */
            .tryll-chunk-detail {
                background: rgba(255, 255, 255, 0.03);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 12px;
                padding: 16px;
                margin-bottom: 16px;
            }

            .tryll-chunk-detail-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 12px;
                padding-bottom: 12px;
                border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            }

            .tryll-chunk-id {
                font-family: monospace;
                color: #3B82F6;
                font-size: 0.9rem;
            }

            .tryll-chunk-meta {
                display: flex;
                gap: 8px;
                flex-wrap: wrap;
            }

            .tryll-meta-tag {
                background: rgba(59, 130, 246, 0.1);
                color: rgba(255, 255, 255, 0.7);
                padding: 2px 8px;
                border-radius: 4px;
                font-size: 0.75rem;
            }

            .tryll-chunk-text {
                font-size: 0.85rem;
                line-height: 1.6;
                color: rgba(255, 255, 255, 0.8);
                white-space: pre-wrap;
            }

            /* Feedback Form */
            .tryll-feedback-form {
                display: flex;
                flex-direction: column;
                gap: 16px;
            }

            .tryll-feedback-form label {
                color: rgba(255, 255, 255, 0.7);
                font-size: 0.85rem;
                margin-bottom: -8px;
            }

            .tryll-feedback-form textarea {
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 8px;
                padding: 12px;
                color: rgba(255, 255, 255, 0.9);
                font-family: inherit;
                font-size: 0.9rem;
                min-height: 80px;
                resize: vertical;
            }

            .tryll-feedback-form textarea:focus {
                outline: none;
                border-color: #3B82F6;
            }

            .tryll-btn-primary {
                background: #3B82F6;
                border: none;
                border-radius: 8px;
                padding: 12px 20px;
                color: white;
                font-weight: 500;
                cursor: pointer;
                transition: background 0.2s ease;
            }

            .tryll-btn-primary:hover {
                background: #2563EB;
            }

            /* Loading */
            .tryll-loading {
                text-align: center;
                padding: 20px;
                color: rgba(255, 255, 255, 0.5);
            }

            /* Scrollbar */
            .tryll-chat-body::-webkit-scrollbar,
            .tryll-modal-body::-webkit-scrollbar {
                width: 6px;
            }

            .tryll-chat-body::-webkit-scrollbar-track,
            .tryll-modal-body::-webkit-scrollbar-track {
                background: transparent;
            }

            .tryll-chat-body::-webkit-scrollbar-thumb,
            .tryll-modal-body::-webkit-scrollbar-thumb {
                background: rgba(255, 255, 255, 0.2);
                border-radius: 3px;
            }

            /* Mobile responsive */
            @media (max-width: 480px) {
                .tryll-chat-window {
                    width: calc(100% - 16px);
                    height: calc(100vh - 16px);
                    bottom: 8px;
                    right: 8px;
                    border-radius: 12px;
                }
            }
        `;
        document.head.appendChild(style);
    }

    // Attach event listeners
    function attachEventListeners() {
        // Toggle chat
        document.getElementById('tryll-chat-btn').addEventListener('click', toggleChat);
        document.getElementById('tryll-minimize-btn').addEventListener('click', toggleChat);

        // Send message
        document.getElementById('tryll-send-btn').addEventListener('click', sendMessage);
        document.getElementById('tryll-chat-input').addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });

        // Auto-resize textarea
        document.getElementById('tryll-chat-input').addEventListener('input', (e) => {
            e.target.style.height = 'auto';
            e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px';
            updateSendButton();
        });

        // Config modal
        document.getElementById('tryll-config-btn').addEventListener('click', showConfigModal);
        document.getElementById('tryll-config-close').addEventListener('click', () => {
            document.getElementById('tryll-config-modal').classList.remove('open');
        });

        // RAG modal
        document.getElementById('tryll-rag-close').addEventListener('click', () => {
            document.getElementById('tryll-rag-modal').classList.remove('open');
        });

        // Feedback modal
        document.getElementById('tryll-feedback-close').addEventListener('click', () => {
            document.getElementById('tryll-feedback-modal').classList.remove('open');
        });
        document.getElementById('tryll-feedback-submit').addEventListener('click', submitFeedback);

        // Close modals on backdrop click
        document.querySelectorAll('.tryll-modal').forEach(modal => {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) modal.classList.remove('open');
            });
        });
    }

    // Toggle chat window
    function toggleChat() {
        state.isOpen = !state.isOpen;
        document.getElementById('tryll-chat-btn').classList.toggle('open', state.isOpen);
        document.getElementById('tryll-chat-window').classList.toggle('open', state.isOpen);

        if (state.isOpen && !state.ws) {
            connectToServer();
        }

        if (state.isOpen) {
            document.getElementById('tryll-chat-input').focus();
        }
    }

    // Update connection status
    function updateConnectionStatus(connected, message) {
        state.isConnected = connected;
        const statusEl = document.getElementById('tryll-connection-status');
        const dotEl = document.querySelector('.tryll-status-dot');

        statusEl.textContent = message;
        statusEl.className = 'tryll-connection-status ' + (connected ? 'connected' : 'error');
        dotEl.classList.toggle('connected', connected);
        updateSendButton();
    }

    // Update send button state
    function updateSendButton() {
        const input = document.getElementById('tryll-chat-input');
        const btn = document.getElementById('tryll-send-btn');
        btn.disabled = !state.isConnected || !input.value.trim() || state.isProcessing;
    }

    // Connect to server via WebSocket proxy
    async function connectToServer() {
        updateConnectionStatus(false, 'Connecting...');

        try {
            // First, get server config
            const configResponse = await fetch('/api/chat/config');
            if (!configResponse.ok) {
                throw new Error('Failed to get server config');
            }

            const config = await configResponse.json();
            state.serverConfig = config;

            // Determine WebSocket URL
            let wsUrl;
            if (config.tunnel_url) {
                // Use cloudflared tunnel (convert https:// to wss://)
                const tunnelUrl = config.tunnel_url.replace('https://', 'wss://').replace('http://', 'ws://');
                wsUrl = `${tunnelUrl}/ws`;
                console.log('Using tunnel URL:', wsUrl);
            } else {
                // Fallback to local proxy
                const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                wsUrl = `${wsProtocol}//${window.location.host}/api/chat/ws`;
                console.log('Using local proxy:', wsUrl);
            }

            state.ws = new WebSocket(wsUrl);

            state.ws.onopen = () => {
                console.log('WebSocket connected');
                state.reconnectAttempts = 0;
                // Wait for server info message
            };

            state.ws.onmessage = (event) => {
                handleServerMessage(event.data);
            };

            state.ws.onclose = () => {
                console.log('WebSocket closed');
                updateConnectionStatus(false, 'Disconnected');
                state.ws = null;
                state.agentId = null;

                // Attempt reconnect
                if (state.isOpen && state.reconnectAttempts < CONFIG.maxReconnectAttempts) {
                    state.reconnectAttempts++;
                    setTimeout(connectToServer, CONFIG.wsReconnectInterval);
                }
            };

            state.ws.onerror = (error) => {
                console.error('WebSocket error:', error);
                updateConnectionStatus(false, 'Connection error');
            };

        } catch (error) {
            console.error('Connection error:', error);
            updateConnectionStatus(false, 'Server unavailable');
        }
    }

    // Handle messages from server
    function handleServerMessage(data) {
        try {
            // Server sends JSON with trailing comma, handle multiple messages
            const cleaned = '[' + data.slice(0, -1) + ']';
            const messages = JSON.parse(cleaned);

            for (const msg of messages) {
                if (msg.server) {
                    // Server state update
                    if (msg.server.state === 1) {
                        updateConnectionStatus(true, 'Connected');
                    } else if (msg.server.state === 3) {
                        state.isProcessing = true;
                        updateSendButton();
                    }
                } else if (msg.models) {
                    // Models info received
                    console.log('Models available:', msg.models);
                } else if (msg.agent) {
                    handleAgentMessage(msg.agent);
                }
            }
        } catch (e) {
            console.error('Parse error:', e, data);
        }
    }

    // Handle agent-specific messages
    function handleAgentMessage(agent) {
        const stateCode = agent.state;

        if (stateCode === 2) {
            // START_STREAMING
            showTypingIndicator();
        } else if (stateCode === 3) {
            // STREAMING token
            appendToLastMessage(agent.message);
        } else if (stateCode === 4) {
            // FINISH_STREAMING
            hideTypingIndicator();
            state.isProcessing = false;
            updateSendButton();

            // Parse RAG chunk IDs if present
            if (agent.message) {
                state.lastRagIds = agent.message.split(';').filter(id => id);
            }

            finalizeLastMessage();
        } else if (stateCode === 1) {
            // FULL_MESSAGE (non-streaming)
            hideTypingIndicator();
            addAssistantMessage(agent.message);
            state.isProcessing = false;
            updateSendButton();
        } else if (stateCode === 8) {
            // DATA_SOURCES
            console.log('Data source:', agent.message);
        }
    }

    // Send message to server
    function sendMessage() {
        const input = document.getElementById('tryll-chat-input');
        const message = input.value.trim();

        if (!message || !state.isConnected || state.isProcessing) return;

        // Add user message to UI
        addUserMessage(message);

        // Send to server
        const payload = JSON.stringify({
            agent_message: {
                id: state.agentId || 0,
                message: message
            }
        });

        state.ws.send(payload);
        state.isProcessing = true;

        // Clear input
        input.value = '';
        input.style.height = 'auto';
        updateSendButton();

        // Save to session
        state.currentSession = {
            question: message,
            timestamp: new Date().toISOString()
        };
    }

    // Add user message to chat
    function addUserMessage(text) {
        const body = document.getElementById('tryll-chat-body');
        const welcome = body.querySelector('.tryll-welcome-message');
        if (welcome) welcome.remove();

        const msgEl = document.createElement('div');
        msgEl.className = 'tryll-message user';
        msgEl.innerHTML = `
            <div class="tryll-message-content">${escapeHtml(text)}</div>
        `;
        body.appendChild(msgEl);
        body.scrollTop = body.scrollHeight;

        state.messages.push({ role: 'user', content: text });
    }

    // Add assistant message to chat
    function addAssistantMessage(text) {
        const body = document.getElementById('tryll-chat-body');

        const msgEl = document.createElement('div');
        msgEl.className = 'tryll-message assistant';
        msgEl.dataset.msgIndex = state.messages.length;

        msgEl.innerHTML = `
            <div class="tryll-message-content">${escapeHtml(text)}</div>
            ${createRagInfoHtml()}
            ${createFeedbackActionsHtml()}
        `;

        body.appendChild(msgEl);
        body.scrollTop = body.scrollHeight;

        state.messages.push({
            role: 'assistant',
            content: text,
            ragIds: [...state.lastRagIds],
            timestamp: new Date().toISOString()
        });

        // Update current session
        if (state.currentSession) {
            state.currentSession.answer = text;
            state.currentSession.ragChunkIds = [...state.lastRagIds];
        }
    }

    // Show typing indicator
    function showTypingIndicator() {
        const body = document.getElementById('tryll-chat-body');
        const welcome = body.querySelector('.tryll-welcome-message');
        if (welcome) welcome.remove();

        // Remove existing typing indicator
        hideTypingIndicator();

        const typing = document.createElement('div');
        typing.id = 'tryll-typing-indicator';
        typing.className = 'tryll-message assistant';
        typing.innerHTML = `
            <div class="tryll-message-content tryll-typing">
                <div class="tryll-typing-dot"></div>
                <div class="tryll-typing-dot"></div>
                <div class="tryll-typing-dot"></div>
            </div>
        `;
        body.appendChild(typing);
        body.scrollTop = body.scrollHeight;
    }

    // Hide typing indicator
    function hideTypingIndicator() {
        const typing = document.getElementById('tryll-typing-indicator');
        if (typing) typing.remove();
    }

    // Append streaming token to last message
    let streamingMessageEl = null;

    function appendToLastMessage(token) {
        const body = document.getElementById('tryll-chat-body');

        if (!streamingMessageEl) {
            hideTypingIndicator();

            streamingMessageEl = document.createElement('div');
            streamingMessageEl.className = 'tryll-message assistant';
            streamingMessageEl.innerHTML = `
                <div class="tryll-message-content"></div>
            `;
            body.appendChild(streamingMessageEl);
        }

        const content = streamingMessageEl.querySelector('.tryll-message-content');
        content.textContent += token;
        body.scrollTop = body.scrollHeight;
    }

    // Finalize streaming message
    function finalizeLastMessage() {
        if (streamingMessageEl) {
            const content = streamingMessageEl.querySelector('.tryll-message-content').textContent;

            // Add RAG info and feedback buttons
            streamingMessageEl.dataset.msgIndex = state.messages.length;
            streamingMessageEl.innerHTML = `
                <div class="tryll-message-content">${escapeHtml(content)}</div>
                ${createRagInfoHtml()}
                ${createFeedbackActionsHtml()}
            `;

            state.messages.push({
                role: 'assistant',
                content: content,
                ragIds: [...state.lastRagIds],
                timestamp: new Date().toISOString()
            });

            // Update current session
            if (state.currentSession) {
                state.currentSession.answer = content;
                state.currentSession.ragChunkIds = [...state.lastRagIds];
            }

            streamingMessageEl = null;
        }
    }

    // Create RAG info HTML
    function createRagInfoHtml() {
        if (state.lastRagIds.length === 0) return '';

        return `
            <div class="tryll-rag-info">
                <div class="tryll-rag-header">
                    <span>RAG Chunks (${state.lastRagIds.length})</span>
                    <button class="tryll-rag-view-btn" onclick="window.tryllChat.showRagDetails()">View Details</button>
                </div>
                <div class="tryll-rag-chunks">
                    ${state.lastRagIds.map(id => `<span class="tryll-chunk-tag">${escapeHtml(id)}</span>`).join('')}
                </div>
            </div>
        `;
    }

    // Create feedback actions HTML
    function createFeedbackActionsHtml() {
        return `
            <div class="tryll-feedback-actions">
                <button class="tryll-feedback-btn positive" onclick="window.tryllChat.submitQuickFeedback(this, true)">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
                        <path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3zM7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3"></path>
                    </svg>
                    Helpful
                </button>
                <button class="tryll-feedback-btn negative" onclick="window.tryllChat.submitQuickFeedback(this, false)">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
                        <path d="M10 15v4a3 3 0 0 0 3 3l4-9V2H5.72a2 2 0 0 0-2 1.7l-1.38 9a2 2 0 0 0 2 2.3zm7-13h2.67A2.31 2.31 0 0 1 22 4v7a2.31 2.31 0 0 1-2.33 2H17"></path>
                    </svg>
                    Not helpful
                </button>
                <button class="tryll-feedback-btn" onclick="window.tryllChat.showFeedbackModal()">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
                        <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
                        <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
                    </svg>
                    Write feedback
                </button>
            </div>
        `;
    }

    // Show config modal
    async function showConfigModal() {
        const modal = document.getElementById('tryll-config-modal');
        const body = document.getElementById('tryll-config-body');
        modal.classList.add('open');

        body.innerHTML = '<div class="tryll-loading">Loading configuration...</div>';

        try {
            const response = await fetch('/api/chat/config');
            const config = await response.json();

            body.innerHTML = `
                <div class="tryll-config-grid">
                    <div class="tryll-config-item">
                        <span class="tryll-config-label">Server Status</span>
                        <span class="tryll-config-value">${state.isConnected ? 'Connected' : 'Disconnected'}</span>
                    </div>
                    <div class="tryll-config-item">
                        <span class="tryll-config-label">RAG Chunks</span>
                        <span class="tryll-config-value">${config.rag_chunks_number || 'N/A'}</span>
                    </div>
                    <div class="tryll-config-item">
                        <span class="tryll-config-label">Score Threshold</span>
                        <span class="tryll-config-value">${config.rag_score_threshold || 'N/A'}</span>
                    </div>
                    <div class="tryll-config-item">
                        <span class="tryll-config-label">Double Tower</span>
                        <span class="tryll-config-value">${config.rag_double_tower ? 'Yes' : 'No'}</span>
                    </div>
                    <div class="tryll-config-item">
                        <span class="tryll-config-label">Embedding Model</span>
                        <span class="tryll-config-value">${config.embedding_model_name || 'default'}</span>
                    </div>
                    <div class="tryll-config-item">
                        <span class="tryll-config-label">Semantic Filter Threshold</span>
                        <span class="tryll-config-value">${config.semantic_filter_threshold || 'N/A'}</span>
                    </div>
                </div>
            `;
        } catch (e) {
            body.innerHTML = `<div class="tryll-loading">Failed to load configuration</div>`;
        }
    }

    // Show RAG details modal
    async function showRagDetails() {
        const modal = document.getElementById('tryll-rag-modal');
        const body = document.getElementById('tryll-rag-body');
        modal.classList.add('open');

        if (state.lastRagIds.length === 0) {
            body.innerHTML = '<div class="tryll-loading">No RAG chunks for this response</div>';
            return;
        }

        body.innerHTML = '<div class="tryll-loading">Loading chunk details...</div>';

        try {
            const response = await fetch('/api/chat/chunks?ids=' + state.lastRagIds.join(','));
            const chunks = await response.json();

            body.innerHTML = chunks.map(chunk => `
                <div class="tryll-chunk-detail">
                    <div class="tryll-chunk-detail-header">
                        <span class="tryll-chunk-id">${escapeHtml(chunk.id)}</span>
                        <div class="tryll-chunk-meta">
                            ${chunk.metadata?.type ? `<span class="tryll-meta-tag">${chunk.metadata.type}</span>` : ''}
                            ${chunk.metadata?.page_title ? `<span class="tryll-meta-tag">${chunk.metadata.page_title}</span>` : ''}
                        </div>
                    </div>
                    <div class="tryll-chunk-text">${escapeHtml(chunk.text || 'No text available')}</div>
                </div>
            `).join('');
        } catch (e) {
            body.innerHTML = `<div class="tryll-loading">Failed to load chunk details</div>`;
        }
    }

    // Submit quick feedback (thumbs up/down)
    async function submitQuickFeedback(btn, isPositive) {
        const actions = btn.closest('.tryll-feedback-actions');
        const allBtns = actions.querySelectorAll('.tryll-feedback-btn');

        // Toggle active state
        allBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');

        // Get message data
        const msgEl = btn.closest('.tryll-message');
        const msgIndex = parseInt(msgEl.dataset.msgIndex);
        const msg = state.messages[msgIndex];

        // Send feedback to server
        try {
            await fetch('/api/chat/feedback', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    session_id: state.currentSession?.timestamp || new Date().toISOString(),
                    question: state.currentSession?.question || '',
                    answer: msg?.content || '',
                    rag_chunk_ids: msg?.ragIds || [],
                    is_positive: isPositive,
                    feedback_type: 'quick',
                    server_config: state.serverConfig
                })
            });
        } catch (e) {
            console.error('Failed to submit feedback:', e);
        }
    }

    // Show feedback modal
    function showFeedbackModal() {
        document.getElementById('tryll-feedback-modal').classList.add('open');
        document.getElementById('tryll-feedback-text').value = '';
        document.getElementById('tryll-feedback-suggestion').value = '';
    }

    // Submit detailed feedback
    async function submitFeedback() {
        const text = document.getElementById('tryll-feedback-text').value;
        const suggestion = document.getElementById('tryll-feedback-suggestion').value;

        if (!text.trim()) {
            alert('Please describe what could be improved');
            return;
        }

        const lastAssistantMsg = state.messages.filter(m => m.role === 'assistant').pop();

        try {
            await fetch('/api/chat/feedback', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    session_id: state.currentSession?.timestamp || new Date().toISOString(),
                    question: state.currentSession?.question || '',
                    answer: lastAssistantMsg?.content || '',
                    rag_chunk_ids: lastAssistantMsg?.ragIds || [],
                    is_positive: false,
                    feedback_type: 'detailed',
                    feedback_text: text,
                    suggested_answer: suggestion,
                    server_config: state.serverConfig
                })
            });

            document.getElementById('tryll-feedback-modal').classList.remove('open');
            alert('Thank you for your feedback!');
        } catch (e) {
            console.error('Failed to submit feedback:', e);
            alert('Failed to submit feedback. Please try again.');
        }
    }

    // Escape HTML
    function escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // Initialize widget
    function init() {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', createWidget);
        } else {
            createWidget();
        }
    }

    // Expose API
    window.tryllChat = {
        open: () => { if (!state.isOpen) toggleChat(); },
        close: () => { if (state.isOpen) toggleChat(); },
        showRagDetails: showRagDetails,
        submitQuickFeedback: submitQuickFeedback,
        showFeedbackModal: showFeedbackModal
    };

    init();
})();
