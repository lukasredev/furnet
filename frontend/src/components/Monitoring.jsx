import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'

function Monitoring() {
  // Default list of workshop instances
  const defaultInstances = [
    'https://viscon.monomorphic.party',
    'https://dj-viscon-workshop-0.vsos.ethz.ch',
    'https://dj-viscon-workshop-1.vsos.ethz.ch',
    'https://dj-viscon-workshop-2.vsos.ethz.ch',
    'https://dj-viscon-workshop-3.vsos.ethz.ch',
    'https://dj-viscon-workshop-4.vsos.ethz.ch',
    'https://dj-viscon-workshop-5.vsos.ethz.ch',
    'https://dj-viscon-workshop-6.vsos.ethz.ch',
    'https://dj-viscon-workshop-7.vsos.ethz.ch',
    'https://dj-viscon-workshop-8.vsos.ethz.ch',
    'https://dj-viscon-workshop-9.vsos.ethz.ch',
    'https://dj-viscon-workshop-10.vsos.ethz.ch',
    'https://dj-viscon-workshop-11.vsos.ethz.ch',
    'https://dj-viscon-workshop-12.vsos.ethz.ch',
    'https://dj-viscon-workshop-13.vsos.ethz.ch',
    'https://dj-viscon-workshop-14.vsos.ethz.ch',
  ]

  const [instances, setInstances] = useState(defaultInstances)
  const [instanceInput, setInstanceInput] = useState('')
  const [healthStatuses, setHealthStatuses] = useState({})
  const [isChecking, setIsChecking] = useState(false)
  const [lastChecked, setLastChecked] = useState(null)

  // Poll instances every 5 seconds
  useEffect(() => {
    if (instances.length === 0) return

    // Initial check
    checkHealth()

    // Set up polling interval
    const interval = setInterval(() => {
      checkHealth()
    }, 5000)

    // Cleanup interval on unmount or when instances change
    return () => clearInterval(interval)
  }, [instances])

  const checkHealth = async () => {
    if (instances.length === 0) return

    setIsChecking(true)

    try {
      const response = await fetch('/api/health-check', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          instance_urls: instances,
        }),
      })

      if (!response.ok) {
        console.error('Failed to check health')
        return
      }

      const data = await response.json()

      // Convert array to object keyed by instance_url
      const statusMap = {}
      data.forEach((status) => {
        statusMap[status.instance_url] = status
      })

      setHealthStatuses(statusMap)
      setLastChecked(new Date())
    } catch (err) {
      console.error('Error checking health:', err)
    } finally {
      setIsChecking(false)
    }
  }

  const addInstance = (e) => {
    e.preventDefault()
    const trimmedUrl = instanceInput.trim()

    if (!trimmedUrl) return

    // Don't add duplicates
    if (instances.includes(trimmedUrl)) {
      alert('This instance is already in the monitoring list')
      return
    }

    setInstances([...instances, trimmedUrl])
    setInstanceInput('')
  }

  const removeInstance = (url) => {
    setInstances(instances.filter((instance) => instance !== url))
    // Remove from health statuses
    const newStatuses = { ...healthStatuses }
    delete newStatuses[url]
    setHealthStatuses(newStatuses)
  }

  const getLivenessBadge = (instanceUrl) => {
    const status = healthStatuses[instanceUrl]

    if (!status) {
      return (
        <div className="text-center">
          <span className="inline-block px-2 py-1 bg-gray-100 text-gray-600 text-xs font-mono rounded border border-gray-300">
            PENDING
          </span>
        </div>
      )
    }

    if (status.is_alive) {
      return (
        <div className="text-center">
          <span className="inline-block px-2 py-1 bg-green-50 text-green-700 text-xs font-mono rounded border border-green-300">
            ONLINE
          </span>
          {status.response_time_ms && (
            <div className="text-gray-500 font-mono text-xs mt-1">
              {status.response_time_ms}ms
            </div>
          )}
        </div>
      )
    }

    return (
      <div className="text-center">
        <span className="inline-block px-2 py-1 bg-red-50 text-red-700 text-xs font-mono rounded border border-red-300">
          OFFLINE
        </span>
        {status.error && (
          <div className="text-red-600 font-mono text-xs mt-1 break-words">
            {status.error}
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 text-gray-900">
      <div className="container mx-auto px-4 py-8 max-w-7xl">
        {/* Header */}
        <header className="mb-8 pb-4 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-mono font-bold text-blue-600">
                FurNet Monitoring
              </h1>
              <p className="text-gray-600 font-mono text-sm mt-1">
                Monitor other FurNet instances
              </p>
            </div>
            <div className="flex items-center gap-3">
              {lastChecked && (
                <div className="text-right">
                  <div className="text-gray-500 font-mono text-xs">Last checked:</div>
                  <div className="text-gray-700 font-mono text-xs">
                    {lastChecked.toLocaleTimeString()}
                  </div>
                </div>
              )}
              {isChecking && (
                <div className="flex items-center gap-2">
                  <div className="animate-spin rounded-full h-4 w-4 border-2 border-gray-200 border-t-blue-500"></div>
                  <span className="text-gray-500 font-mono text-xs">Checking...</span>
                </div>
              )}
              <Link
                to="/"
                className="px-3 py-1 bg-gray-600 hover:bg-gray-700 text-white text-xs font-mono rounded transition-colors"
              >
                Home
              </Link>
            </div>
          </div>
        </header>

        {/* Main Content */}
        <main>
          {/* Instance List */}
          <div>
            <h2 className="font-mono font-bold text-gray-900 mb-4">
              Monitored Instances ({instances.length})
            </h2>

            {instances.length === 0 ? (
              <div className="border border-gray-200 rounded p-6 bg-white text-center">
                <p className="text-gray-500 font-mono text-sm">
                  No instances added yet. Add an instance using the form below!
                </p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
                {instances.map((instance) => {
                  // Extract just the hostname for display
                  const hostname = instance.replace('https://', '').replace('http://', '')
                  const status = healthStatuses[instance]
                  const animalName = status?.name
                  const animalEmoji = status?.emoji

                  return (
                    <div
                      key={instance}
                      className="border border-gray-200 rounded p-3 bg-white"
                    >
                      <div className="flex items-start justify-between gap-2 mb-2">
                        <div className="flex-1 min-w-0">
                          {animalName && (
                            <p className="font-mono text-sm font-bold text-blue-600 mb-1">
                              {animalEmoji && <span className="mr-1">{animalEmoji}</span>}
                              {animalName}
                            </p>
                          )}
                          <a
                            href={instance}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="font-mono text-xs text-blue-600 hover:text-blue-800 hover:underline break-all"
                          >
                            {hostname}
                          </a>
                        </div>
                        <button
                          onClick={() => removeInstance(instance)}
                          className="text-red-600 hover:text-red-700 transition-colors flex-shrink-0"
                          title="Remove instance"
                        >
                          <svg
                            xmlns="http://www.w3.org/2000/svg"
                            className="h-4 w-4"
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke="currentColor"
                            strokeWidth={2}
                          >
                            <path
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              d="M6 18L18 6M6 6l12 12"
                            />
                          </svg>
                        </button>
                      </div>
                      <div className="mt-2">
                        {getLivenessBadge(instance)}
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </div>

          {/* Auto-refresh info */}
          {instances.length > 0 && (
            <div className="mt-6 bg-gray-100 border border-gray-300 rounded p-4">
              <p className="text-gray-600 font-mono text-xs text-center">
                Auto-refreshing every 5 seconds
                {lastChecked && (
                  <span className="ml-2">
                    • Last checked: {lastChecked.toLocaleTimeString()}
                  </span>
                )}
              </p>
            </div>
          )}

          {/* Add Instance Form */}
          <div className="bg-blue-50 border border-blue-200 rounded p-6 mt-8">
            <h2 className="font-mono font-bold text-gray-900 mb-4">
              Add Instance to Monitor
            </h2>
            <form onSubmit={addInstance} className="space-y-4">
              <div>
                <label
                  htmlFor="instanceUrl"
                  className="block text-gray-700 font-mono text-sm mb-2"
                >
                  Instance URL
                </label>
                <input
                  type="text"
                  id="instanceUrl"
                  value={instanceInput}
                  onChange={(e) => setInstanceInput(e.target.value)}
                  placeholder="https://furnet-instance.example.com"
                  className="w-full px-4 py-2 border border-gray-300 rounded font-mono text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  required
                />
                <p className="text-gray-600 font-mono text-xs mt-2">
                  Enter the URL of a FurNet instance to monitor
                </p>
              </div>

              <button
                type="submit"
                className="w-full bg-blue-600 hover:bg-blue-700 text-white font-mono text-sm py-2 px-4 rounded transition-colors"
              >
                Add Instance
              </button>
            </form>
          </div>
        </main>

        {/* Footer */}
        <footer className="mt-12 pt-6 border-t border-gray-200 text-center">
          <p className="text-gray-400 font-mono text-xs">
            DevOps Workshop by{' '}
            <a
              href="https://github.com/lukasredev"
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-blue-500 transition-colors"
            >
              lukasredev
            </a>
            {' '}•{' '}
            <a
              href="https://github.com/lukasredev/furnet"
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-blue-500 transition-colors"
            >
              GitHub
            </a>
            {' '}• FurNet v0.1.0
          </p>
        </footer>
      </div>
    </div>
  )
}

export default Monitoring
