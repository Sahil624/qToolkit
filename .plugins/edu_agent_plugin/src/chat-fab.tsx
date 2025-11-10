import React, { useState } from 'react';
import ChatPanel  from './box'; // Your existing ChatBox component

interface FABProps {
  className?: string;
}

const ChatFAB: React.FC<FABProps> = ({ className = '' }) => {
  const [isOpen, setIsOpen] = useState(false);

  const toggleChat = () => {
    setIsOpen(!isOpen);
  };

  return (
    <>
      {/* FAB Button */}
      <button
        // onClick={toggleChat}
        className={`fab-button ${className}`}
        style={{
          position: 'fixed',
          bottom: '20px',
          right: '20px',
          width: '56px',
          height: '56px',
          borderRadius: '50%',
          backgroundColor: '#2196F3',
          border: 'none',
          boxShadow: '0 2px 10px rgba(0,0,0,0.2)',
          cursor: 'pointer',
          zIndex: 1000,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: 'white',
          fontSize: '24px',
          transition: 'all 0.3s ease',
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.transform = 'scale(1.1)';
          e.currentTarget.style.boxShadow = '0 4px 20px rgba(0,0,0,0.3)';
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.transform = 'scale(1)';
          e.currentTarget.style.boxShadow = '0 2px 10px rgba(0,0,0,0.2)';
        }}
      >
        {isOpen ? '✕' : '💬'}
      </button>

      {/* Chat Box - positioned above FAB */}
      {/* {isOpen && (
        <div
          style={{
            position: 'fixed',
            bottom: '90px', // Above the FAB
            right: '20px',
            width: '350px',
            height: '500px',
            zIndex: 999,
            boxShadow: '0 4px 20px rgba(0,0,0,0.15)',
            borderRadius: '8px',
            overflow: 'hidden',
          }}
        >
          <ChatPanel onClose={() => setIsOpen(false)} />
        </div>
      )} */}
    </>
  );
};

export default ChatFAB;