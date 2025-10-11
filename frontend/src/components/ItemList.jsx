import { useState } from 'react'

function ItemList({ items, onRefresh }) {
  const [deletingId, setDeletingId] = useState(null)

  const handleDelete = async (itemId) => {
    try {
      setDeletingId(itemId)
      const response = await fetch(`/api/items/${itemId}`, {
        method: 'DELETE',
      })
      if (!response.ok) throw new Error('Failed to delete item')
      onRefresh()
    } catch (err) {
      alert('Error deleting item: ' + err.message)
    } finally {
      setDeletingId(null)
    }
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-semibold text-gray-800">Items</h2>
        <button
          onClick={onRefresh}
          className="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded-md transition-colors"
        >
          Refresh
        </button>
      </div>

      {items.length === 0 ? (
        <p className="text-gray-500 text-center py-8">No items found</p>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {items.map((item) => (
            <div
              key={item.id}
              className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow"
            >
              <h3 className="text-lg font-semibold text-gray-800 mb-2">
                {item.name}
              </h3>
              <p className="text-gray-600 mb-4">
                {item.description || 'No description'}
              </p>
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-500">ID: {item.id}</span>
                <button
                  onClick={() => handleDelete(item.id)}
                  disabled={deletingId === item.id}
                  className="bg-red-500 hover:bg-red-600 text-white px-3 py-1 rounded text-sm transition-colors disabled:bg-gray-400"
                >
                  {deletingId === item.id ? 'Deleting...' : 'Delete'}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default ItemList
