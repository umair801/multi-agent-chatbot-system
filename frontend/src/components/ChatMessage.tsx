'use client'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: string
  sources?: string[]
  steps_completed?: number
  status?: string
}

interface ChatMessageProps {
  message: Message
}

export default function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === 'user'

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
      {!isUser && (
        <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center mr-3 shrink-0 mt-1">
          <span className="text-white text-xs font-bold">D</span>
        </div>
      )}

      <div className={`max-w-[75%] ${isUser ? 'items-end' : 'items-start'} flex flex-col gap-1`}>
        <div
          className={`px-4 py-3 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap ${
            isUser
              ? 'bg-blue-600 text-white rounded-br-sm'
              : 'bg-white border border-gray-200 text-gray-800 rounded-bl-sm shadow-sm'
          }`}
        >
          {message.content}
        </div>

        {message.sources && message.sources.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-1">
            {message.sources.map((src, i) => (
              <span
                key={i}
                className="text-xs px-2 py-0.5 bg-blue-50 text-blue-600 border border-blue-100 rounded-full"
              >
                {src.length > 50 ? src.slice(0, 50) + '...' : src}
              </span>
            ))}
          </div>
        )}

        <span className="text-xs text-gray-400 px-1">
          {message.timestamp}
          {message.steps_completed ? ` · ${message.steps_completed} steps` : ''}
        </span>
      </div>

      {isUser && (
        <div className="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center ml-3 shrink-0 mt-1">
          <span className="text-gray-600 text-xs font-bold">U</span>
        </div>
      )}
    </div>
  )
}
