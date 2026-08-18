import { useEffect, useRef } from 'react'

export interface TraceStep {
  type: string
  step?: string
  status?: string
  tool?: string
  duration_ms?: number
  content?: string
  answer?: string
}

interface AgentTraceProps {
  traceSteps: TraceStep[]
}

export default function AgentTrace({ traceSteps }: AgentTraceProps) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [traceSteps])

  const getStepIcon = (type: string) => {
    switch (type) {
      case 'agent_start': return '🔍'
      case 'tool_call': return '🔧'
      case 'tool_result': return '📊'
      case 'complete': return '✅'
      case 'error': return '❌'
      default: return '•'
    }
  }

  const getStepColor = (type: string) => {
    switch (type) {
      case 'agent_start': return 'text-info'
      case 'tool_call': return 'text-warning'
      case 'tool_result': return 'text-gray-300'
      case 'complete': return 'text-success'
      case 'error': return 'text-danger'
      default: return 'text-gray-400'
    }
  }

  if (traceSteps.length === 0) {
    return (
      <div className="h-full flex items-center justify-center text-gray-500 text-sm">
        <p>等待 Agent 开始执行...</p>
      </div>
    )
  }

  return (
    <div className="space-y-2">
      {traceSteps.map((step, i) => (
        <div key={i} className="flex gap-3 items-start">
          <span className="text-lg mt-0.5">{getStepIcon(step.type)}</span>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className={`text-sm font-medium ${getStepColor(step.type)}`}>
                {step.step || step.type}
              </span>
              {step.duration_ms !== undefined && step.duration_ms > 0 && (
                <span className="text-xs text-gray-500">({step.duration_ms.toFixed(0)}ms)</span>
              )}
            </div>
            {step.tool && (
              <p className="text-xs text-gray-500 mt-0.5">工具: {step.tool}</p>
            )}
            {step.content && (
              <p className="text-xs text-gray-400 mt-1 bg-dark-300 rounded p-2">{step.content}</p>
            )}
          </div>
          {step.status && (
            <span className={`text-xs ${step.status === 'running' ? 'text-warning animate-pulse' : step.status === 'failed' ? 'text-danger' : 'text-success'}`}>
              {step.status === 'running' ? '进行中...' : step.status === 'completed' ? '完成' : '失败'}
            </span>
          )}
        </div>
      ))}
      {traceSteps.length > 0 && traceSteps[traceSteps.length - 1].type !== 'complete' && (
        <div className="flex items-center gap-2 text-gray-500 text-sm pl-8">
          <span className="w-2 h-2 bg-primary-500 rounded-full animate-pulse" />
          <span>Agent 正在思考...</span>
        </div>
      )}
      <div ref={bottomRef} />
    </div>
  )
}