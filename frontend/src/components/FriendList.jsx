function FriendList({ friends }) {
  if (!friends || friends.length === 0) {
    return (
      <div className="border border-gray-200 rounded p-6 bg-white text-center">
        <p className="text-gray-500 font-mono text-sm">
          No friends yet. Add a friend using the form above!
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {friends.map((friend) => (
        <div
          key={friend.unique_id}
          className="border border-gray-200 rounded p-4 bg-white hover:border-blue-300 transition-colors"
        >
          <div className="flex items-center justify-between">
            <div className="flex-1">
              <h3 className="font-mono font-bold text-blue-600 text-lg">
                {friend.name}
              </h3>
              <p className="text-gray-500 font-mono text-xs mt-1">
                {friend.dns_name}
              </p>
            </div>
            <div className="flex items-center gap-3">
              <a
                href={`https://${friend.dns_name}`}
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-600 hover:text-blue-700 transition-colors"
                title={`Visit ${friend.name}'s profile`}
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  className="h-6 w-6"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={2}
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
                  />
                </svg>
              </a>
              <code className="text-gray-600 font-mono text-xs bg-gray-50 px-2 py-1 rounded border border-gray-200">
                {friend.unique_id}
              </code>
            </div>
          </div>
          <div className="mt-2 text-gray-500 font-mono text-xs">
            Connected: {new Date(friend.connected_at).toLocaleString()}
          </div>
        </div>
      ))}
    </div>
  )
}

export default FriendList
