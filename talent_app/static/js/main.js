/**
 * Talent Growth Platform - Interactive UI Engine
 * Powers tab navigation, modal popups, live search, MCQ assessments, and AI Coach chat.
 */

document.addEventListener('DOMContentLoaded', () => {
    // 1. Tab Switching Engine
    const urlParams = new URLSearchParams(window.location.search);
    const activeTabParam = urlParams.get('tab') || window.location.hash.replace('#', '');

    function switchTab(targetId) {
        if (!targetId) return;

        // Find buttons targeting this pane
        const buttons = document.querySelectorAll(`[data-tab-target="${targetId}"]`);
        buttons.forEach(btn => {
            const parent = btn.closest('.nav-tabs-wrapper') || btn.parentElement;
            if (parent) {
                parent.querySelectorAll('[data-tab-target]').forEach(b => {
                    b.classList.remove('active');
                });
            }
            btn.classList.add('active');
        });

        // Hide sibling panes and show target
        const targetPane = document.getElementById(targetId);
        if (targetPane) {
            const paneContainer = targetPane.parentElement;
            if (paneContainer) {
                paneContainer.querySelectorAll('.tab-pane').forEach(p => {
                    p.style.display = 'none';
                    p.classList.remove('active');
                });
            }
            targetPane.style.display = 'block';
            targetPane.classList.add('active');
        }
    }

    // Bind tab clicks
    document.querySelectorAll('[data-tab-target]').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            const targetId = btn.getAttribute('data-tab-target');
            switchTab(targetId);
            // Optionally update URL hash without jump
            history.replaceState(null, null, `?tab=${targetId}`);
        });
    });

    // Auto-activate tab from URL param or default
    if (activeTabParam) {
        switchTab(activeTabParam);
    }

    // 2. Client-side Search and Filtering for Tables
    document.querySelectorAll('[data-table-search]').forEach(input => {
        const targetTableId = input.getAttribute('data-table-search');
        const table = document.getElementById(targetTableId);
        if (!table) return;

        input.addEventListener('input', () => {
            const query = input.value.toLowerCase().trim();
            const rows = table.querySelectorAll('tbody tr');
            rows.forEach(row => {
                const text = row.innerText.toLowerCase();
                row.style.display = text.includes(query) ? '' : 'none';
            });
        });
    });

    // 3. Modal Popup Dialogs
    window.openModal = function(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.style.display = 'flex';
            document.body.style.overflow = 'hidden';
        }
    };

    window.closeModal = function(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.style.display = 'none';
            document.body.style.overflow = 'auto';
        }
    };

    document.querySelectorAll('.modal-overlay').forEach(overlay => {
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) {
                overlay.style.display = 'none';
                document.body.style.overflow = 'auto';
            }
        });
    });

    // 4. Auto-dismiss alerts
    document.querySelectorAll('.alert-dismissible').forEach(alert => {
        setTimeout(() => {
            alert.style.transition = 'opacity 0.4s ease';
            alert.style.opacity = '0';
            setTimeout(() => alert.remove(), 400);
        }, 5000);
    });

    // 5. Interactive AI Career Coach Chat Interface
    const coachForm = document.getElementById('coach-chat-form');
    const coachInput = document.getElementById('coach-message-input');
    const chatContainer = document.getElementById('coach-chat-history');

    if (coachForm && coachInput && chatContainer) {
        coachForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const message = coachInput.value.trim();
            if (!message) return;

            // Append user bubble
            appendChatBubble('user', message);
            coachInput.value = '';

            // Append loading indicator
            const loadingBubble = appendChatBubble('ai', 'Thinking and formulating executive growth strategy...');

            // Send AJAX
            const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
            const formData = new FormData();
            formData.append('message', message);
            formData.append('csrfmiddlewaretoken', csrfToken);

            fetch('/career-coach/chat/', {
                method: 'POST',
                body: formData
            })
            .then(res => res.json())
            .then(data => {
                loadingBubble.innerText = data.reply || "Strategy formulated. Review key competencies above.";
                chatContainer.scrollTop = chatContainer.scrollHeight;
            })
            .catch(() => {
                loadingBubble.innerText = "Focus on continuous skill development, targeted peer feedback, and architecture specifications.";
            });
        });

        window.sendPrompt = function(promptText) {
            if (coachInput) {
                coachInput.value = promptText;
                coachForm.dispatchEvent(new Event('submit'));
            }
        };
    }

    function appendChatBubble(sender, text) {
        if (!chatContainer) return null;
        const bubble = document.createElement('div');
        bubble.className = `chat-bubble chat-bubble-${sender}`;
        bubble.style.cssText = sender === 'user' 
            ? 'background: #2563EB; color: #FFF; padding: 12px 18px; border-radius: 14px 14px 2px 14px; margin-bottom: 12px; margin-left: auto; max-width: 80%; font-size: 0.90rem; box-shadow: 0 2px 8px rgba(37,99,235,0.25);'
            : 'background: #F1F5F9; color: #0F172A; padding: 14px 20px; border-radius: 14px 14px 14px 2px; margin-bottom: 12px; max-width: 85%; font-size: 0.90rem; border: 1px solid #E2E8F0; line-height: 1.5;';
        bubble.innerText = text;
        chatContainer.appendChild(bubble);
        chatContainer.scrollTop = chatContainer.scrollHeight;
        return bubble;
    }
});
