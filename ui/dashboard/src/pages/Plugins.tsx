import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Search, Download, Star, Shield, TrendingUp, Package } from 'lucide-react';
import { api } from '@/lib/api';
import toast from 'react-hot-toast';
import { motion } from 'framer-motion';

export function Plugins() {
  const [searchQuery, setSearchQuery] = useState('');
  const [category, setCategory] = useState('');
  const queryClient = useQueryClient();

  const { data: plugins, isLoading } = useQuery({
    queryKey: ['plugins', searchQuery, category],
    queryFn: () =>
      api.get('/v1/marketplace/search', {
        params: { q: searchQuery || 'plugin', category, limit: 20 },
      }),
  });

  const { data: categories } = useQuery({
    queryKey: ['categories'],
    queryFn: () => api.get('/v1/marketplace/categories'),
  });

  const downloadMutation = useMutation({
    mutationFn: (pluginId: string) => api.post(`/v1/marketplace/plugin/${pluginId}/download`),
    onSuccess: () => {
      toast.success('Plugin downloaded successfully!');
      queryClient.invalidateQueries({ queryKey: ['plugins'] });
    },
    onError: () => toast.error('Failed to download plugin'),
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Plugin Marketplace</h2>
          <p className="text-gray-600">Discover and install plugins to extend BAEL</p>
        </div>
        <button className="px-4 py-2 text-white bg-indigo-600 rounded-md hover:bg-indigo-700">
          Upload Plugin
        </button>
      </div>

      {/* Search and Filters */}
      <div className="flex flex-col gap-4 sm:flex-row">
        <div className="relative flex-1">
          <Search className="absolute w-5 h-5 text-gray-400 left-3 top-3" />
          <input
            type="text"
            placeholder="Search plugins..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full py-2 pl-10 pr-4 border border-gray-300 rounded-md focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
          />
        </div>
        <select
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          className="px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-indigo-500"
        >
          <option value="">All Categories</option>
          {categories?.categories?.map((cat: string) => (
            <option key={cat} value={cat}>
              {cat}
            </option>
          ))}
        </select>
      </div>

      {/* Featured Plugins */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {isLoading ? (
          Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="h-48 bg-gray-200 rounded-lg animate-pulse" />
          ))
        ) : plugins?.results?.length > 0 ? (
          plugins.results.map((plugin: any, index: number) => (
            <motion.div
              key={plugin.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.05 }}
              className="p-6 bg-white border border-gray-200 rounded-lg shadow-sm hover:shadow-md transition-shadow"
            >
              <div className="flex items-start justify-between mb-3">
                <div className="p-2 bg-indigo-100 rounded-lg">
                  <Package className="w-6 h-6 text-indigo-600" />
                </div>
                {plugin.trusted && (
                  <div className="flex items-center px-2 py-1 text-xs font-medium text-green-700 bg-green-100 rounded-full">
                    <Shield className="w-3 h-3 mr-1" />
                    Trusted
                  </div>
                )}
              </div>

              <h3 className="mb-2 text-lg font-semibold text-gray-900">{plugin.name}</h3>
              <p className="mb-4 text-sm text-gray-600 line-clamp-2">{plugin.description}</p>

              <div className="flex items-center justify-between mb-4 text-sm text-gray-500">
                <div className="flex items-center">
                  <Star className="w-4 h-4 mr-1 text-yellow-400 fill-current" />
                  <span>{plugin.stats?.rating?.toFixed(1) || 'N/A'}</span>
                  <span className="ml-1">({plugin.stats?.rating_count || 0})</span>
                </div>
                <div className="flex items-center">
                  <Download className="w-4 h-4 mr-1" />
                  <span>{plugin.stats?.downloads || 0}</span>
                </div>
              </div>

              <div className="flex items-center justify-between">
                <span className="inline-flex items-center px-2 py-1 text-xs font-medium text-indigo-700 bg-indigo-100 rounded-full">
                  {plugin.category}
                </span>
                <button
                  onClick={() => downloadMutation.mutate(plugin.id)}
                  disabled={downloadMutation.isPending}
                  className="px-3 py-1 text-sm text-white bg-indigo-600 rounded-md hover:bg-indigo-700 disabled:opacity-50"
                >
                  Install
                </button>
              </div>
            </motion.div>
          ))
        ) : (
          <div className="col-span-full p-12 text-center text-gray-500">
            No plugins found. Try a different search.
          </div>
        )}
      </div>
    </div>
  );
}
