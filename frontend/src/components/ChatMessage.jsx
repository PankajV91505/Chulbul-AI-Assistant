/**
 * ChatMessage — renders a single chat bubble (user or assistant).
 */

export default function ChatMessage({ role, text, toolUsed }) {
  const isUser = role === 'user';

  return (
    <div
      className={`flex animate-fade-in-up ${isUser ? 'justify-end' : 'justify-start'} mb-3`}
    >
      <div
        className={`
          max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed
          ${isUser
            ? 'bg-chulbul-accent text-white rounded-br-md'
            : 'glass-card text-chulbul-text rounded-bl-md'
          }
        `}
      >
        {/* Tool badge */}
        {!isUser && toolUsed && toolUsed !== 'direct_response' && (
          <span className="inline-block mb-1.5 text-[10px] font-semibold uppercase tracking-wider
                           bg-chulbul-accent/20 text-chulbul-accent-light px-2 py-0.5 rounded-full">
            🔧 {toolUsed.replace('_', ' ')}
          </span>
        )}

        {/* Message text */}
        <p className="whitespace-pre-wrap">{text}</p>
      </div>
    </div>
  );
}
