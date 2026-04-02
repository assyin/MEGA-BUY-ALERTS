'use client'

import { Brain } from 'lucide-react'

interface ModelInfoProps {
  version?: string
  accuracy?: number
  totalPredictions?: number
}

export function ModelInfo({ version = 'v2.0', accuracy, totalPredictions }: ModelInfoProps) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
      <div className="flex items-center gap-2 mb-3">
        <Brain className="w-5 h-5 text-purple-400" />
        <h3 className="font-medium text-white">ML Model</h3>
      </div>
      <div className="grid grid-cols-3 gap-4 text-center">
        <div>
          <div className="text-xs text-gray-500">Version</div>
          <div className="text-sm font-bold text-purple-400">{version}</div>
        </div>
        {accuracy != null && (
          <div>
            <div className="text-xs text-gray-500">Accuracy</div>
            <div className="text-sm font-bold text-green-400">{accuracy.toFixed(1)}%</div>
          </div>
        )}
        {totalPredictions != null && (
          <div>
            <div className="text-xs text-gray-500">Predictions</div>
            <div className="text-sm font-bold text-white">{totalPredictions}</div>
          </div>
        )}
      </div>
    </div>
  )
}
