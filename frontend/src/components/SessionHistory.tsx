'use client'

interface ChatSession {
  id: string
  title: string
  timestamp: string
  messageCount: number
}

interface SessionHistoryProps {
  sessions: ChatSession[]
  activeId: string
  onSelect: (id: string) => void
  onNew: () => void
  onClear: () => void
}

export default function SessionHistory({
  sessions,
  activeId,
  onSelect,
  onNew,
  onClear,
}: SessionHistoryProps) {
  return (
    <div className="w-64 shrink-0 border-r border-gray-200 bg-white h-screen overflow-y-auto flex flex-col">
      {/* Header */}
      <div className="px-4 py-4 border-b border-gray-100">
        <div className="flex items-center gap-2 mb-3">
          <div className="w-7 h-7 bg-blue-600 rounded-lg flex items-center justify-center">
            <span className="text-white text-xs font-bold">D</span>
          </div>
          <span className="font-semibold text-gray-800 text-sm">Datawebify AI</span>
        </div>
        <button
          onClick={onNew}
          className="w-full py-2 px-3 bg-blue-600 text-white text-sm font-medium rounded-xl hover:bg-blue-700 transition-colors"
        >
          + New Chat
        </button>
      </div>

      {/* Sessions list */}
      <div className="flex-1 overflow-y-auto py-2">
        {sessions.length === 0 ? (
          <p className="text-xs text-gray-400 text-center py-6 px-4">
            No chat history yet. Start a conversation.
          </p>
        ) : (
          sessions.map((session) => (
            <button
              key={session.id}
              onClick={() => onSelect(session.id)}
              className={`w-full text-left px-4 py-3 hover:bg-gray-50 transition-colors border-l-2 ${
                activeId === session.id
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-transparent'
              }`}
            >
              <p className="text-sm text-gray-800 font-medium line-clamp-2 mb-1">
                {session.title}
              </p>
              <p className="text-xs text-gray-400">
                {session.messageCount} messages · {session.timestamp}
              </p>
            </button>
          ))
        )}
      </div>

      {/* Footer */}
      {sessions.length > 0 && (
        <div className="px-4 py-3 border-t border-gray-100">
          <button
            onClick={onClear}
            className="text-xs text-gray-400 hover:text-red-500 transition-colors"
          >
            Clear all history
          </button>
        </div>
      )}
    </div>
  )
}
