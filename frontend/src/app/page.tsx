'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import ChatMessage from '@/components/ChatMessage'
import ChatInput from '@/components/ChatInput'
import ExecutionPanel from '@/components/ExecutionPanel'
import SessionHistory from '@/components/SessionHistory'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: string
  sources?: string[]
  steps_completed?: number
  status?: string
}

interface Step {
  step_number: number
  agent: string
  task: string
  output: string
  supervisor_verdict: string
  supervisor_score: number
}

interface ChatSession {
  id: string
  title: string
  timestamp: string
  messageCount: number
  messages: Message[]
}

const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000'

export default function Home() {
  const [sessions, setSessions] = useState<ChatSession[]>([])
  const [activeSessionId, setActiveSessionId] = useState<string>('')
  const [messages, setMessages] = useState<Message[]>([])
  const [liveSteps, setLiveSteps] = useState<Step[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, liveSteps])

  const handleNewChat = useCallback(() => {
    const id = crypto.randomUUID()
    const session: ChatSession = {
      id,
      title: 'New Chat',
      timestamp: new Date().toLocaleTimeString(),
      messageCount: 0,
      messages: [],
    }
    setSessions((prev) => [session, ...prev])
    setActiveSessionId(id)
    setMessages([])
    setLiveSteps([])
  }, [])

  useEffect(() => {
    handleNewChat()
  }, [])

  const handleSelectSession = (id: string) => {
    const session = sessions.find((s) => s.id === id)
    if (!session) return
    setActiveSessionId(id)
    setMessages(session.messages)
    setLiveSteps([])
  }

  const handleClearAll = () => {
    setSessions([])
    handleNewChat()
  }

  const persistMessages = (sessionId: string, msgs: Message[]) => {
    setSessions((prev) =>
      prev.map((s) =>
        s.id === sessionId
          ? {
              ...s,
              messages: msgs,
              messageCount: msgs.length,
              title: msgs[0]?.content.slice(0, 40) ?? 'New Chat',
            }
          : s
      )
    )
  }

  const handleSend = async (text: string) => {
    if (!activeSessionId) return
    setIsLoading(true)
    setLiveSteps([])

    const userMsg: Message = {
      id: crypto.randomUUID(),
      role: 'user',
      content: text,
      timestamp: new Date().toLocaleTimeString(),
    }

    const updatedMessages = [...messages, userMsg]
    setMessages(updatedMessages)
    persistMessages(activeSessionId, updatedMessages)

    const wsProtocol = BACKEND.startsWith('https') ? 'wss' : 'ws'
    const wsBase = BACKEND.replace(/^https?:\/\//, '')
    const wsUrl = `${wsProtocol}://${wsBase}/ws/execute/${activeSessionId}`

    if (wsRef.current) wsRef.current.close()
    const ws = new WebSocket(wsUrl)
    wsRef.current = ws

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data)
        if (msg.type === 'step_update' && msg.step) {
          setLiveSteps((prev) => [...prev, msg.step])
        }
      } catch {}
    }

    try {
      const response = await fetch(`${BACKEND}/api/execute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ goal: text }),
      })

      if (!response.ok) throw new Error(`Server error: ${response.status}`)
      const data = await response.json()

      const summary =
        data.final_output?.summary ||
        data.final_output?.error ||
        'Task completed.'

      const sources: string[] = []
      if (data.steps) {
        data.steps.forEach((step: Step) => {
          if (step.agent === 'rag' && step.output) {
            const match = step.output.match(/Sources?:\s*(.+)/i)
            if (match) sources.push(...match[1].split(',').map((s: string) => s.trim()))
          }
        })
      }

      const assistantMsg: Message = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: summary,
        timestamp: new Date().toLocaleTimeString(),
        sources: sources.length > 0 ? sources : undefined,
        steps_completed: data.steps?.length ?? 0,
        status: data.status,
      }

      const finalMessages = [...updatedMessages, assistantMsg]
      setMessages(finalMessages)
      persistMessages(activeSessionId, finalMessages)

    } catch (err) {
      const errorMsg: Message = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: `Something went wrong: ${err instanceof Error ? err.message : 'Unknown error'}`,
        timestamp: new Date().toLocaleTimeString(),
        status: 'error',
      }
      const errorMessages = [...updatedMessages, errorMsg]
      setMessages(errorMessages)
      persistMessages(activeSessionId, errorMessages)
    } finally {
      setIsLoading(false)
      ws.close()
    }
  }

  return (
    <div className="flex h-screen bg-gray-50 overflow-hidden">
      <SessionHistory
        sessions={sessions}
        activeId={activeSessionId}
        onSelect={handleSelectSession}
        onNew={handleNewChat}
        onClear={handleClearAll}
      />

      <div className="flex-1 flex flex-col overflow-hidden">
        <div className="flex-1 overflow-y-auto px-4 py-6">
          <div className="max-w-3xl mx-auto">
            {messages.length === 0 && !isLoading && (
              <div className="text-center mt-20">
                <div className="w-14 h-14 bg-blue-600 rounded-2xl flex items-center justify-center mx-auto mb-4">
                  <span className="text-white text-2xl font-bold">D</span>
                </div>
                <h1 className="text-2xl font-bold text-gray-900 mb-2">
                  Datawebify AI Assistant
                </h1>
                <p className="text-gray-500 text-sm max-w-md mx-auto">
                  Ask anything. I can search the web, run code, query your knowledge base, connect to external APIs, and deliver structured answers.
                </p>
              </div>
            )}

            {messages.map((msg) => (
              <ChatMessage key={msg.id} message={msg} />
            ))}

            {isLoading && (
              <div className="flex justify-start mb-4">
                <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center mr-3 shrink-0">
                  <span className="text-white text-xs font-bold">D</span>
                </div>
                <div className="bg-white border border-gray-200 rounded-2xl rounded-bl-sm px-4 py-3 shadow-sm">
                  <div className="flex items-center gap-1.5">
                    <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                    <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                    <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        </div>

        <ChatInput onSend={handleSend} isLoading={isLoading} />
      </div>

      <ExecutionPanel steps={liveSteps} isRunning={isLoading} />
    </div>
  )
}
