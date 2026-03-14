// Chat functionality for WealthWise
let chatHistory = [];
let isTyping = false;

// Initialize chat
async function initChat() {
  try {
    await loadChatHistory();
  } catch (error) {
    console.error('Failed to load chat history:', error);
    showToast('Failed to load chat history', 'error');
  }
}

// Load chat history from server
async function loadChatHistory() {
  try {
    const response = await fetch('/api/chat/history');
    const data = await response.json();

    if (data.status === 'success') {
      chatHistory = data.history || [];
      renderChatMessages();
    } else {
      throw new Error(data.message || 'Failed to load chat history');
    }
  } catch (error) {
    console.error('Error loading chat history:', error);
    throw error;
  }
}

// Send message to ARIA
async function sendChatMessage() {
  const input = document.getElementById('chat-input');
  const message = input.value.trim();

  if (!message) {
    showToast('Please enter a message', 'warning');
    return;
  }

  if (isTyping) {
    showToast('ARIA is still responding...', 'info');
    return;
  }

  // Add user message
  addMessage('user', message);
  input.value = '';
  input.disabled = true;

  // Show typing indicator
  showTypingIndicator();

  try {
    const response = await fetch('/api/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ message: message })
    });

    const data = await response.json();

    if (data.status === 'success') {
      addMessage('assistant', data.response);
    } else {
      throw new Error(data.message || 'Failed to get response from ARIA');
    }
  } catch (error) {
    console.error('Error sending message:', error);
    addMessage('assistant', 'Sorry, I\'m having trouble connecting right now. Please try again in a moment.');
    showToast('Failed to send message', 'error');
  } finally {
    hideTypingIndicator();
    input.disabled = false;
    input.focus();
  }
}

// Send quick question
function sendQuickMessage(question) {
  document.getElementById('chat-input').value = question;
  sendChatMessage();
}

// Handle Enter key in chat input
function handleChatKeyPress(event) {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault();
    sendChatMessage();
  }
}

// Add message to chat
function addMessage(role, content) {
  const message = {
    role: role,
    content: content,
    timestamp: new Date().toISOString()
  };

  chatHistory.push(message);
  renderChatMessages();
  scrollToBottom();
}

// Render all chat messages
function renderChatMessages() {
  const container = document.getElementById('chat-messages');
  if (!container) return;

  container.innerHTML = '';

  chatHistory.forEach(message => {
    const messageDiv = createMessageElement(message);
    container.appendChild(messageDiv);
  });
}

// Create message element
function createMessageElement(message) {
  const div = document.createElement('div');
  div.className = `message-wrapper message-${message.role}`;

  const contentDiv = document.createElement('div');
  contentDiv.className = 'message-content';

  const textP = document.createElement('p');
  textP.className = 'message-text';
  textP.textContent = message.content;

  contentDiv.appendChild(textP);

  if (message.timestamp) {
    const timeSpan = document.createElement('span');
    timeSpan.className = 'message-time';
    timeSpan.textContent = formatTime(message.timestamp);
    contentDiv.appendChild(timeSpan);
  }

  div.appendChild(contentDiv);
  return div;
}

// Format timestamp
function formatTime(timestamp) {
  const date = new Date(timestamp);
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

// Show typing indicator
function showTypingIndicator() {
  isTyping = true;
  const indicator = document.getElementById('typing-indicator');
  if (indicator) {
    indicator.style.display = 'flex';
    scrollToBottom();
  }
}

// Hide typing indicator
function hideTypingIndicator() {
  isTyping = false;
  const indicator = document.getElementById('typing-indicator');
  if (indicator) {
    indicator.style.display = 'none';
  }
}

// Scroll to bottom of chat
function scrollToBottom() {
  const container = document.getElementById('chat-messages');
  if (container) {
    setTimeout(() => {
      container.scrollTop = container.scrollHeight;
    }, 100);
  }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
  initChat();
});
