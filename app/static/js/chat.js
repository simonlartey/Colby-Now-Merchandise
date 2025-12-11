// static/chat.js
const messagesDiv = document.getElementById("messages");

function loadMessages() {
  fetch(`/get_messages/${receiver_id}`)
    .then(res => res.json())
    .then(data => {
      messagesDiv.innerHTML = "";
      data.forEach(msg => {
        const div = document.createElement("div");
        div.className = "message " + (msg.sender === CURRENT_USER_ID ? "sent" : "received");

        div.innerHTML = `
          ${msg.content}
          <small>${msg.time}</small>
        `;

        messagesDiv.appendChild(div);
      });

      messagesDiv.scrollTop = messagesDiv.scrollHeight;
    });
}

function send() {
  const content = document.getElementById("input").value;

  fetch("/send_message", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({receiver_id, content})
  }).then(() => {
    document.getElementById("input").value = "";
    loadMessages();
  });
}

setInterval(loadMessages, 2000);
loadMessages();
