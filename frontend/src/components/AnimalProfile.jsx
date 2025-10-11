function AnimalProfile({ animal }) {
  if (!animal) return null

  return (
    <div className="max-w-2xl mx-auto">
      {/* Header */}
      <div className="border-b border-gray-200 pb-6 mb-6">
        <div className="flex items-center gap-4 mb-2">
          {animal.emoji && (
            <span className="text-6xl">{animal.emoji}</span>
          )}
          <div>
            <h1 className="text-3xl font-mono font-bold text-blue-600">
              {animal.name}
            </h1>
            <p className="text-gray-600 font-mono text-sm mt-1">
              {animal.species}
            </p>
          </div>
        </div>
        <p className="text-gray-700 mt-4 font-mono text-sm">
          {animal.description}
        </p>
      </div>

      {/* ID Badge */}
      <div className="bg-blue-50 border border-blue-200 rounded p-4 mb-6">
        <div className="flex items-center justify-between">
          <span className="text-gray-600 font-mono text-xs uppercase">
            Instance ID
          </span>
          <code className="text-blue-700 font-mono text-sm bg-white px-2 py-1 rounded border border-blue-200">
            {animal.id}
          </code>
        </div>
      </div>

      {/* Details Grid */}
      <div className="space-y-3">
        {animal.habitat && (
          <div className="border border-gray-200 rounded p-4 bg-white">
            <div className="text-gray-500 font-mono text-xs uppercase mb-2">
              Habitat
            </div>
            <div className="text-gray-700 font-mono text-sm">
              {animal.habitat}
            </div>
          </div>
        )}

        {animal.diet && (
          <div className="border border-gray-200 rounded p-4 bg-white">
            <div className="text-gray-500 font-mono text-xs uppercase mb-2">
              Diet
            </div>
            <div className="text-gray-700 font-mono text-sm">
              {animal.diet}
            </div>
          </div>
        )}

        {animal.fun_fact && (
          <div className="border border-gray-200 rounded p-4 bg-white">
            <div className="text-gray-500 font-mono text-xs uppercase mb-2">
              Fun Fact
            </div>
            <div className="text-gray-700 font-mono text-sm">
              {animal.fun_fact}
            </div>
          </div>
        )}

        {animal.color && (
          <div className="border border-gray-200 rounded p-4 bg-white">
            <div className="text-gray-500 font-mono text-xs uppercase mb-2">
              Color
            </div>
            <div className="flex items-center gap-3">
              <div
                className="w-8 h-8 rounded border border-gray-300"
                style={{ backgroundColor: animal.color }}
              />
              <span className="text-gray-700 font-mono text-sm">
                {animal.color}
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Instance URL */}
      <div className="mt-6 pt-6 border-t border-gray-200">
        <div className="flex items-center justify-between">
          <span className="text-gray-500 font-mono text-xs uppercase">
            Instance URL
          </span>
          <a
            href={animal.instance_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-600 hover:text-blue-700 font-mono text-sm underline"
          >
            {animal.instance_url}
          </a>
        </div>
      </div>
    </div>
  )
}

export default AnimalProfile
