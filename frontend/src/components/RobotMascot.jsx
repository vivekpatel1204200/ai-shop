import { useState } from "react";

export default function RobotMascot() {
  const [showMessage, setShowMessage] = useState(false);

  const messages = [
    "Need help finding something?",
    "Check out the Assistant page!",
    "Happy shopping! 🛍️",
    "New arrivals just dropped!",
  ];
  const [message] = useState(messages[Math.floor(Math.random() * messages.length)]);

  return (
    <div className="robot-mascot" onMouseEnter={() => setShowMessage(true)} onMouseLeave={() => setShowMessage(false)}>
      {showMessage && <div className="robot-speech-bubble">{message}</div>}
      <div className="robot-body">
        <div className="robot-head">
          <div className="robot-eye left"></div>
          <div className="robot-eye right"></div>
        </div>
        <div className="robot-antenna"></div>
      </div>
    </div>
  );
}