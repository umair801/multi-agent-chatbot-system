'use client'

import { useState } from 'react'

interface GoalInputProps {
  onSubmit: (goal: string) => void
  isLoading: boolean
}

export default function GoalInput({ onSubmit, isLoading }: GoalInputProps) {
  const [goal, setGoal] = useState('')

  const handleSubmit = () => {
    const trimmed = goal.trim()
    if (!trimmed || isLoading) return
    onSubmit(trimmed)
    setGoal('')
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  return (
    <div className="w-full max-w-3xl mx-auto">
      <div className="relative bg-white border border-gray-200 rounded-2xl shadow-sm focus-within:border-blue-500 focus-within:ring-1 focus-within:ring-blue-500 transition-all">
        <textarea
          className="w-full px-5 pt-4 pb-14 text-gray-800 text-base resize-none outline-none rounded-2xl bg-transparent placeholder-gray-400"
          placeholder="Describe your goal and I will handle it end-to-end..."
          rows={3}
          value={goal}
          onChange={(e) => setGoal(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isLoading}
        />
        <div className="absolute bottom-3 right-3 flex items-center gap-2">
          <span className="text-xs text-gray-400">
            {goal.length > 0 ? `${goal.length} chars` : 'Enter to submit'}
          </span>
          <button
            onClick={handleSubmit}
            disabled={!goal.trim() || isLoading}
            className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-xl hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            {isLoading ? 'Running...' : 'Run'}
          </button>
        </div>
      </div>
      <p className="mt-2 text-xs text-center text-gray-400">
        Shift+Enter for new line. Enter to submit.
      </p>
    </div>
  )
}