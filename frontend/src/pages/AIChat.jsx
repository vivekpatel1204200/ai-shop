import { useState } from "react";
import api from "../api";

export default function AIChat() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSend = async (e) => {
    e.preventDefault();
    if (!input.trim()) return;

    const userMessage = { role: "user", text: input };
    const updatedMessages = [...messages, userMessage];
    setMessages(updatedMessages);
    setInput("");
    setLoading(true);

    const history = messages.map((m) => ({
      role: m.role,
      content: m.text,
    }));

    try {
      const res = await api.post("/ai/chat", { message: input, history });
      setMessages((prev) => [...prev, { role: "assistant", text: res.data.response }]);
    } catch (err) {
      setMessages((prev) => [...prev, { role: "assistant", text: "Sorry, something went wrong." }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="ai-chat-page">
      <h2>Shopping Assistant</h2>
      <div className="chat-window">
        {messages.map((msg, idx) => (
          <div key={idx} className={`chat-message ${msg.role}`}>
            <strong>{msg.role === "user" ? "You" : "Assistant"}:</strong> {msg.text}
          </div>
        ))}
        {loading && <div className="chat-message assistant"><em>Thinking...</em></div>}
      </div>
      <form onSubmit={handleSend}>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about products..."
        />
        <button type="submit" disabled={loading}>Send</button>
      </form>
    </div>
  );
}