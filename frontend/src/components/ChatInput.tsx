'use client'

import { useState } from 'react'

interface ChatInputProps {
  onSend: (message: string) => void
  isLoading: boolean
}

export default function ChatInput({ onSend, isLoading }: ChatInputProps) {
  const [text, setText] = useState('')

  const handleSend = () => {
    const trimmed = text.trim()
    if (!trimmed || isLoading) return
    onSend(trimmed)
    setText('')
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="border-t border-gray-200 bg-white px-4 py-3">
      <div className="max-w-3xl mx-auto">
        <div className="relative bg-gray-50 border border-gray-200 rounded-2xl focus-within:border-blue-500 focus-within:ring-1 focus-within:ring-blue-500 transition-all">
          <textarea
            className="w-full px-4 pt-3 pb-12 text-sm text-gray-800 resize-none outline-none bg-transparent rounded-2xl placeholder-gray-400"
            placeholder="Ask a question or describe a task..."
            rows={2}
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isLoading}
          />
          <div className="absolute bottom-3 right-3 flex items-center gap-2">
            <span className="text-xs text-gray-400">
              {isLoading ? 'Thinking...' : 'Enter to send'}
            </span>
            <button
              onClick={handleSend}
              disabled={!text.trim() || isLoading}
              className="px-4 py-1.5 bg-blue-600 text-white text-sm font-medium rounded-xl hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              {isLoading ? (
                <span className="flex items-center gap-1.5">
                  <span className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin inline-block" />
                  Running
                </span>
              ) : (
                'Send'
              )}
            </button>
          </div>
        </div>
        <p className="text-xs text-center text-gray-400 mt-1.5">
          Shift+Enter for new line
        </p>
      </div>
    </div>
  )
}
