'use client'

import { useState } from 'react'

interface Step {
  step_number: number
  agent: string
  task: string
  output: string
  supervisor_verdict: string
  supervisor_score: number
}

interface ExecutionPanelProps {
  steps: Step[]
  isRunning: boolean
}

const AGENT_LABELS: Record<string, string> = {
  web_search: 'Web Search',
  code_execution: 'Code',
  file_generation: 'File Gen',
  summarization: 'Summary',
  api_integration: 'API',
  rag: 'RAG',
}

const VERDICT_COLORS: Record<string, string> = {
  approved: 'text-green-600 bg-green-50 border-green-100',
  retry: 'text-yellow-600 bg-yellow-50 border-yellow-100',
  escalate: 'text-red-500 bg-red-50 border-red-100',
  unknown: 'text-gray-500 bg-gray-50 border-gray-100',
}

export default function ExecutionPanel({ steps, isRunning }: ExecutionPanelProps) {
  const [collapsed, setCollapsed] = useState(false)

  if (steps.length === 0 && !isRunning) return null

  return (
    <div className="border-l border-gray-200 bg-white w-80 shrink-0 flex flex-col h-full">
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100">
        <div className="flex items-center gap-2">
          {isRunning && (
            <span className="w-2 h-2 bg-blue-500 rounded-full animate-pulse" />
          )}
          <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
            Execution Feed
          </span>
        </div>
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="text-xs text-gray-400 hover:text-gray-600 transition-colors"
        >
          {collapsed ? 'Show' : 'Hide'}
        </button>
      </div>

      {!collapsed && (
        <div className="flex-1 overflow-y-auto py-3 px-3 space-y-2">
          {steps.map((step) => (
            <div
              key={step.step_number}
              className="bg-gray-50 border border-gray-100 rounded-xl p-3"
            >
              <div className="flex items-center justify-between mb-1.5">
                <div className="flex items-center gap-1.5">
                  <span className="text-xs font-bold text-gray-400">
                    #{step.step_number}
                  </span>
                  <span className="text-xs font-medium text-gray-700 bg-white border border-gray-200 px-2 py-0.5 rounded-full">
                    {AGENT_LABELS[step.agent] ?? step.agent}
                  </span>
                </div>
                <span
                  className={`text-xs px-2 py-0.5 rounded-full border font-medium ${
                    VERDICT_COLORS[step.supervisor_verdict] ?? VERDICT_COLORS.unknown
                  }`}
                >
                  {step.supervisor_score.toFixed(2)}
                </span>
              </div>
              <p className="text-xs text-gray-500 mb-1 line-clamp-1">{step.task}</p>
              <p className="text-xs text-gray-700 line-clamp-3 whitespace-pre-wrap">
                {step.output}
              </p>
            </div>
          ))}

          {isRunning && (
            <div className="flex items-center gap-2 px-3 py-2 bg-blue-50 border border-blue-100 rounded-xl">
              <span className="w-2 h-2 bg-blue-500 rounded-full animate-pulse" />
              <span className="text-xs text-blue-500">Agent working...</span>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
