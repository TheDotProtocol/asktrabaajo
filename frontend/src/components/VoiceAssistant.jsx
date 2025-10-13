import React, { useState } from 'react';
import { Mic, X } from 'lucide-react';
import { trabaajoResponses } from '../mock';

export const VoiceAssistant = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [selectedQuestion, setSelectedQuestion] = useState(null);
  const [isAnimating, setIsAnimating] = useState(false);

  const handleQuestionClick = (index) => {
    setIsAnimating(true);
    setSelectedQuestion(index);
    setTimeout(() => setIsAnimating(false), 500);
  };

  return (
    <div className="fixed bottom-8 right-8 z-40">
      {/* Voice Bubble Button */}
      {!isOpen && (
        <button
          onClick={() => setIsOpen(true)}
          className="group relative w-16 h-16 bg-gradient-to-br from-[#D4AF37] to-[#C49F2F] rounded-full shadow-2xl hover:scale-110 transition-transform duration-300"
          style={{
            animation: 'breathe 3s ease-in-out infinite'
          }}
        >
          <Mic className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 text-black" size={24} />
          <div className="absolute inset-0 rounded-full bg-[#D4AF37] opacity-20 group-hover:animate-ping"></div>
        </button>
      )}

      {/* Chat Interface */}
      {isOpen && (
        <div className="bg-white dark:bg-black border border-gray-300 dark:border-[#D4AF37]/30 rounded-2xl shadow-2xl w-80 sm:w-96 overflow-hidden">
          {/* Header */}
          <div className="bg-gradient-to-r from-[#D4AF37] to-[#C49F2F] px-4 sm:px-6 py-3 sm:py-4 flex items-center justify-between">
            <div>
              <h3 className="text-black font-bold text-base sm:text-lg">Talk to Trabaajo</h3>
              <p className="text-black/70 text-xs">AI Assistant with Attitude</p>
            </div>
            <button
              onClick={() => setIsOpen(false)}
              className="text-black hover:bg-black/10 rounded-full p-1 transition-colors duration-200"
            >
              <X size={20} />
            </button>
          </div>

          {/* Content */}
          <div className="p-4 sm:p-6 max-h-96 overflow-y-auto">
            <p className="text-gray-600 dark:text-white/60 text-sm mb-4">Try asking Trabaajo:</p>
            
            <div className="space-y-3">
              {trabaajoResponses.map((item, index) => (
                <div key={index}>
                  <button
                    onClick={() => handleQuestionClick(index)}
                    className="w-full text-left px-3 sm:px-4 py-2 sm:py-3 bg-gray-50 dark:bg-white/5 hover:bg-gray-100 dark:hover:bg-white/10 border border-gray-200 dark:border-white/10 rounded-lg transition-colors duration-200"
                  >
                    <p className="text-gray-900 dark:text-white text-xs sm:text-sm font-medium">{item.question}</p>
                  </button>
                  
                  {selectedQuestion === index && (
                    <div
                      className={`mt-3 px-3 sm:px-4 py-2 sm:py-3 bg-gradient-to-r from-[#D4AF37]/20 to-transparent border-l-2 border-[#D4AF37] rounded-r-lg ${
                        isAnimating ? 'animate-slide-in' : ''
                      }`}
                    >
                      <p className="text-gray-800 dark:text-white/90 text-xs sm:text-sm italic">"{item.answer}"</p>
                    </div>
                  )}
                </div>
              ))}
            </div>

            <div className="mt-6 p-3 sm:p-4 bg-[#D4AF37]/10 border border-[#D4AF37]/30 rounded-lg">
              <p className="text-gray-700 dark:text-white/70 text-xs">
                💡 <strong>Note:</strong> This is a demo interface. Full voice integration coming soon with real-time AI responses.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};