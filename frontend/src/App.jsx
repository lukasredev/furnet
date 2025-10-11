import { useState, useEffect } from 'react'
import AnimalProfile from './components/AnimalProfile'
import FriendList from './components/FriendList'

function App() {
  const [animal, setAnimal] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const [friends, setFriends] = useState([])
  const [friendsLoading, setFriendsLoading] = useState(false)
  const [friendUrl, setFriendUrl] = useState('')
  const [addingFriend, setAddingFriend] = useState(false)
  const [friendError, setFriendError] = useState(null)
  const [friendSuccess, setFriendSuccess] = useState(null)

  useEffect(() => {
    fetchAnimal()
    fetchFriends()
  }, [])

  const fetchAnimal = async () => {
    try {
      setLoading(true)
      const response = await fetch('/api/me')
      if (!response.ok) throw new Error('Failed to fetch animal profile')
      const data = await response.json()
      setAnimal(data)
      setError(null)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const fetchFriends = async () => {
    try {
      setFriendsLoading(true)
      const response = await fetch('/api/friends')
      if (!response.ok) throw new Error('Failed to fetch friends')
      const data = await response.json()
      setFriends(data)
    } catch (err) {
      console.error('Error fetching friends:', err)
    } finally {
      setFriendsLoading(false)
    }
  }

  const addFriend = async (e) => {
    e.preventDefault()
    setAddingFriend(true)
    setFriendError(null)
    setFriendSuccess(null)

    try {
      // Step 1: Fetch friend's /api/me endpoint from their instance
      let friendInstanceUrl = friendUrl.trim()
      if (!friendInstanceUrl.startsWith('http://') && !friendInstanceUrl.startsWith('https://')) {
        friendInstanceUrl = 'https://' + friendInstanceUrl
      }

      // Remove trailing slash if present
      friendInstanceUrl = friendInstanceUrl.replace(/\/$/, '')

      const friendMeUrl = `${friendInstanceUrl}/api/me`

      const friendResponse = await fetch(friendMeUrl)
      if (!friendResponse.ok) {
        throw new Error(`Failed to fetch friend's profile from ${friendMeUrl}. Status: ${friendResponse.status}`)
      }

      const friendData = await friendResponse.json()

      // Check if trying to add yourself as a friend
      if (friendData.id === animal.id) {
        throw new Error("You can't add yourself as a friend!")
      }

      // Step 2: Only if Step 1 succeeds, add friend to our backend
      const addFriendResponse = await fetch('/api/friends', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          unique_id: friendData.id,
          dns_name: new URL(friendInstanceUrl).hostname,
          name: friendData.name,
        }),
      })

      if (!addFriendResponse.ok) {
        const errorData = await addFriendResponse.json()
        throw new Error(errorData.detail || 'Failed to add friend to our backend')
      }

      const newFriend = await addFriendResponse.json()

      // Step 3: Update UI with new friend
      setFriends([...friends, newFriend])
      setFriendUrl('')
      setFriendSuccess(`Successfully added ${friendData.name} as a friend!`)

      // Clear success message after 3 seconds
      setTimeout(() => setFriendSuccess(null), 3000)
    } catch (err) {
      setFriendError(err.message)
    } finally {
      setAddingFriend(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 text-gray-900">
      <div className="container mx-auto px-4 py-8 max-w-4xl">
        {/* Header */}
        <header className="mb-8 pb-4 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-mono font-bold text-blue-600">
                FurNet
              </h1>
              <p className="text-gray-600 font-mono text-sm mt-1">
                Distributed Animal Social Network
              </p>
            </div>
            <div className="flex gap-2">
              <span className="px-2 py-1 bg-green-50 text-green-700 text-xs font-mono rounded border border-green-200">
                ONLINE
              </span>
            </div>
          </div>
        </header>

        {/* Main Content */}
        <main>
          {loading && (
            <div className="flex flex-col items-center justify-center py-16">
              <div className="animate-spin rounded-full h-12 w-12 border-2 border-gray-200 border-t-blue-500 mb-4"></div>
              <p className="text-gray-500 font-mono text-sm">Loading profile...</p>
            </div>
          )}

          {error && (
            <div className="bg-red-50 border border-red-200 rounded p-4 mb-6">
              <p className="font-mono text-sm text-red-700 mb-1">ERROR</p>
              <p className="font-mono text-sm text-gray-700">{error}</p>
            </div>
          )}

          {!loading && !error && animal && (
            <>
              <AnimalProfile animal={animal} />

              {/* Friends Section */}
              <div className="mt-12 pt-8 border-t border-gray-200">
                <h2 className="text-2xl font-mono font-bold text-gray-900 mb-6">
                  Friends Network
                </h2>

                {/* Friends List */}
                <div className="mb-6">
                  <h3 className="font-mono font-bold text-gray-900 mb-4">
                    Connected Friends ({friends.length})
                  </h3>
                  {friendsLoading ? (
                    <div className="flex items-center justify-center py-8">
                      <div className="animate-spin rounded-full h-8 w-8 border-2 border-gray-200 border-t-blue-500"></div>
                    </div>
                  ) : (
                    <FriendList friends={friends} />
                  )}
                </div>

                {/* Add Friend Form */}
                <div className="bg-blue-50 border border-blue-200 rounded p-6">
                  <h3 className="font-mono font-bold text-gray-900 mb-4">
                    Add a Friend
                  </h3>
                  <form onSubmit={addFriend} className="space-y-4">
                    <div>
                      <label
                        htmlFor="friendUrl"
                        className="block text-gray-700 font-mono text-sm mb-2"
                      >
                        Friend Instance URL
                      </label>
                      <input
                        type="text"
                        id="friendUrl"
                        value={friendUrl}
                        onChange={(e) => setFriendUrl(e.target.value)}
                        placeholder="https://friend-instance.example.com"
                        className="w-full px-4 py-2 border border-gray-300 rounded font-mono text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        disabled={addingFriend}
                        required
                      />
                      <p className="text-gray-600 font-mono text-xs mt-2">
                        Enter the URL of another FurNet instance to connect
                      </p>
                    </div>

                    {friendError && (
                      <div className="bg-red-50 border border-red-200 rounded p-3">
                        <p className="font-mono text-sm text-red-700">
                          ERROR: {friendError}
                        </p>
                      </div>
                    )}

                    {friendSuccess && (
                      <div className="bg-green-50 border border-green-200 rounded p-3">
                        <p className="font-mono text-sm text-green-700">
                          {friendSuccess}
                        </p>
                      </div>
                    )}

                    <button
                      type="submit"
                      disabled={addingFriend || !friendUrl.trim()}
                      className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white font-mono text-sm py-2 px-4 rounded transition-colors"
                    >
                      {addingFriend ? 'Adding Friend...' : 'Add Friend'}
                    </button>
                  </form>
                </div>
              </div>
            </>
          )}
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

export default App
