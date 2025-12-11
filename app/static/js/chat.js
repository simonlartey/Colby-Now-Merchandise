// static/chat.js
const messagesDiv = document.getElementById("messages");

let totalMessagesShown = 0;

function loadMessages() {
  fetch(`/get_messages/${receiver_id}`)
    .then(res => res.json())
    .then(data => {
      // If no new messages, do nothing
      if (data.length <= totalMessagesShown) return;

      // Check if user is near the bottom (delta < 50px)
      // Or if this is the first load
      const isAtBottom = (messagesDiv.scrollHeight - messagesDiv.scrollTop <= messagesDiv.clientHeight + 50) || (totalMessagesShown === 0);

      // Append only new messages
      const newMessages = data.slice(totalMessagesShown);
      newMessages.forEach(msg => {
        const div = document.createElement("div");
        div.className = "message " + (msg.sender === CURRENT_USER_ID ? "sent" : "received");

        div.innerHTML = `
          ${msg.content}
          <small>${msg.time}</small>
        `;

        messagesDiv.appendChild(div);
      });

      // Update count
      totalMessagesShown = data.length;

      // Auto-scroll only if user was already at bottom or first load
      if (isAtBottom) {
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
      }
    });
}

function send() {
  const content = document.getElementById("input").value;

  fetch("/send_message", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ receiver_id, content })
  }).then(() => {
    document.getElementById("input").value = "";
    loadMessages();
  });
}

setInterval(loadMessages, 2000);
loadMessages();
