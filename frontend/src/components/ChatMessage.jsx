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
          max-w-[85%] px-4 py-3 text-sm leading-relaxed border relative
          ${isUser
            ? 'bg-chulbul-accent/20 border-chulbul-accent text-white'
            : 'bg-black/60 border-chulbul-border text-chulbul-text shadow-[0_0_10px_rgba(255,0,127,0.2)]'
          }
        `}
      >
        {/* Cyber HUD brackets */}
        <div className={`absolute top-0 left-0 w-2 h-2 border-t-2 border-l-2 ${isUser ? 'border-chulbul-accent-light' : 'border-chulbul-accent-light'} -mt-0.5 -ml-0.5`}></div>
        <div className={`absolute bottom-0 right-0 w-2 h-2 border-b-2 border-r-2 ${isUser ? 'border-chulbul-accent-light' : 'border-chulbul-accent-light'} -mb-0.5 -mr-0.5`}></div>

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
